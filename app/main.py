
import hashlib
import os

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.github_sync import status as github_status, GitHubSyncError
from app.models import ChatRequest, ChatResponse, HealthResponse, WordRegistration
from app.linguistics.normalizer import analyze_input
from app.linguistics.parser import extract_linguistic_hints
from app.conversation.state import from_history
from app.conversation.understanding import infer_intent, build_context
from app.conversation.planner import plan_response
from app.memory.manager import extract_memory_candidates, format_memory
from app.retrieval.knowledge import load_vocabulary, retrieve, format_knowledge
from app.melimi.grammar import grammar_policy
from app.melimi.validator import audit_melimi
from app.melimi.engine import build_language_engine_context
from app.melimi.index import inventory as subject_inventory
from app.melimi.registry import audit_response, analyze_word, strict_violations
from app.melimi.firewall import lexical_violations, deterministic_repair, reload_firewall
from app.melimi.local_repair import validate, repair
from app.melimi.registration import register_word
from app.prompts import build_prompt
from app.groq_client import call_groq
from app.response import clean_response
from app.db import engine as db_engine
from app.db import repository as db_repo
from app.knowledge_version import knowledge_version
from app.local_answer import try_deterministic_answer
from app.teaching import detect_teaching


app = FastAPI(title="TeluAI — Standard & Melimi Telugu AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    # Optional: if DATABASE_URL isn't set, this just leaves the DB layer
    # disabled and every db-backed feature degrades to a no-op.
    await db_engine.init_db()


def require_admin(x_admin_token: str = Header(default="")) -> bool:
    if not settings.admin_token:
        raise HTTPException(503, "Admin endpoints are disabled (set ADMIN_TOKEN to enable).")
    if x_admin_token != settings.admin_token:
        raise HTTPException(401, "Invalid admin token.")
    return True

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def home():
    target = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(target):
        raise HTTPException(404, "Frontend not found.")
    return FileResponse(target)


@app.get("/admin")
def admin_page():
    target = os.path.join(STATIC_DIR, "admin.html")
    if not os.path.exists(target):
        raise HTTPException(404, "Admin page not found.")
    return FileResponse(target)


@app.get("/melimi/subject")
def melimi_subject():
    return subject_inventory()


@app.get("/melimi/word/{word}")
def melimi_word(word: str):
    return analyze_word(word)

@app.post("/melimi/register")
async def melimi_register(payload: WordRegistration):
    try:
        return {"ok": True, **(await register_word(payload.model_dump()))}
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except GitHubSyncError as exc:
        raise HTTPException(502, str(exc))


@app.get("/github/status")
def github_sync_status():
    return github_status()


@app.get("/health")
def health():
    return HealthResponse(
        status="ok",
        service="TeluAI",
        vocabulary_entries=len(load_vocabulary()),
    )


@app.get("/db/health")
def db_health():
    return {
        "configured": db_engine.is_configured(),
        "available": db_engine.is_available(),
    }


@app.get("/admin/learning/pending")
async def admin_learning_pending(status: str = "pending", _: bool = Depends(require_admin)):
    return {"candidates": await db_repo.list_candidates(status=status)}


@app.post("/admin/learning/{candidate_id}/approve")
async def admin_learning_approve(candidate_id: int, note: str = "", _: bool = Depends(require_admin)):
    result = await db_repo.review_candidate(candidate_id, approve=True, reviewer_note=note)
    if result is None:
        raise HTTPException(404, "Candidate not found, or the database is unavailable.")
    return {"ok": True, "candidate": result}


@app.post("/admin/learning/{candidate_id}/reject")
async def admin_learning_reject(candidate_id: int, note: str = "", _: bool = Depends(require_admin)):
    result = await db_repo.review_candidate(candidate_id, approve=False, reviewer_note=note)
    if result is None:
        raise HTTPException(404, "Candidate not found, or the database is unavailable.")
    return {"ok": True, "candidate": result}


@app.get("/admin/learning/stats")
async def admin_learning_stats(_: bool = Depends(require_admin)):
    return await db_repo.candidate_stats()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(400, "Message cannot be empty.")

    history = [turn.model_dump() for turn in request.history]
    user_id = request.user_id.strip()

    state = from_history(history)
    linguistic = extract_linguistic_hints(message)
    input_info = analyze_input(message)
    understanding = infer_intent(message, state)
    conversation = build_context(message, state, linguistic)
    plan = plan_response(understanding)

    candidates = extract_memory_candidates(history, settings.max_memory_items)
    memory = format_memory(candidates)

    # Postgres-backed per-user memory: small explicit facts (name, stated
    # likes/dislikes) that persist across sessions, not just within the
    # client-sent history for this one conversation.
    if user_id and db_engine.is_available():
        recalled = await db_repo.recall_user_facts(user_id)
        if recalled:
            recalled_text = "\n".join(f"- {item['value']}" for item in recalled)
            memory = f"{memory}\n{recalled_text}".strip() if memory else recalled_text
        for item in candidates:
            text = item.get("text", "").strip()
            if text:
                fact_key = "fact_" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
                await db_repo.remember_user_fact(user_id, fact_key, text)

    # Melimi subject retrieval is handled by the dedicated language engine.
    # Do not separately stuff the legacy vocabulary retrieval into the prompt.
    knowledge_entries = []
    knowledge = ""

    linguistic_text = "\n".join([
        f"- normalized input: {linguistic['normalized']}",
        f"- tokens: {linguistic['tokens']}",
        f"- sentence force: {linguistic['sentence_force']}",
        f"- question type: {linguistic['question_type']}",
        f"- negation hint: {linguistic['negation_hint']}",
        f"- first-person hint: {linguistic['first_person_hint']}",
        f"- second-person hint: {linguistic['second_person_hint']}",
        f"- Roman/mixed input signals: {input_info}",
    ])

    melimi_engine = ""
    if request.mode == "melimi":
        melimi_engine = build_language_engine_context(
            user_message=message,
            conversation_context=conversation,
            linguistic_analysis=linguistic_text,
            response_plan=plan,
        )

    # --- Local-first pipeline -------------------------------------------
    # Tier 0: known-word definition questions answered from local/DB
    # knowledge with zero Groq calls at all.
    source = "groq"
    reply = None
    if settings.enable_local_first:
        reply = await try_deterministic_answer(message, request.mode, len(history))
        if reply is not None:
            source = "deterministic"

    kv = knowledge_version()
    cache_eligible = settings.enable_response_cache and len(history) == 0

    if reply is None and cache_eligible:
        cached = await db_repo.get_cached_answer(request.mode, message, kv)
        if cached is not None:
            reply = cached
            source = "cache"

    if reply is None:
        # Tier 2: only now do we build the full prompt and spend Groq tokens.
        prompt = build_prompt(
            mode=request.mode,
            conversation=conversation,
            linguistics=linguistic_text,
            memory=memory,
            knowledge=knowledge,
            grammar=grammar_policy() if request.mode == "melimi" else "",
            plan=plan,
            melimi_engine=melimi_engine,
        )

        try:
            reply = await call_groq(prompt, history, message)
        except RuntimeError as exc:
            raise HTTPException(502, str(exc))
        except Exception as exc:
            raise HTTPException(502, f"AI request failed: {exc}")

        reply = clean_response(reply)
        source = "groq"

    if request.mode == "melimi":
        # ONE-GROQ ARCHITECTURE: validation/repair is entirely local.
        # Never regenerate through Groq for a lexical violation.
        reply = deterministic_repair(reply)

    if source == "groq" and cache_eligible:
        await db_repo.set_cached_answer(request.mode, message, kv, reply)

    # Chat-time teaching capture: "X = Y" / "X ni Y antaru" style statements
    # become pending learning candidates for human review, never auto-applied.
    if settings.enable_chat_learning_capture and request.mode == "melimi":
        taught = detect_teaching(message)
        if taught:
            await db_repo.propose_candidate(
                standard_root=taught["standard_root"],
                melimi_root=taught["melimi_root"],
                source="chat",
                proposed_message=message,
            )

    audit = audit_melimi(reply) if request.mode == "melimi" else {}

    return ChatResponse(
        reply=reply,
        mode=request.mode,
        intent=understanding["intent"],
        understanding={
            "meaning": understanding["meaning"],
            "confidence": understanding["confidence"],
            "linguistics": linguistic,
            "response_plan": plan,
        },
        language_audit=audit,
        word_audit=audit_response(reply) if request.mode == "melimi" else [],
        source=source,
    )
