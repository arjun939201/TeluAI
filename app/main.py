
import os

from fastapi import FastAPI, HTTPException
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
from app.melimi.registration import register_word
from app.prompts import build_prompt
from app.groq_client import call_groq
from app.response import clean_response


app = FastAPI(title="TeluAI — Standard & Melimi Telugu AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(400, "Message cannot be empty.")

    history = [turn.model_dump() for turn in request.history]

    state = from_history(history)
    linguistic = extract_linguistic_hints(message)
    input_info = analyze_input(message)
    understanding = infer_intent(message, state)
    conversation = build_context(message, state, linguistic)
    plan = plan_response(understanding)

    candidates = extract_memory_candidates(history, settings.max_memory_items)
    memory = format_memory(candidates)

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
    if request.mode == "melimi":
        # FILE-CONTENT AUTHORITY GATE:
        # 1) find exact Standard/source vocabulary present in the authoritative files;
        # 2) ask the model to regenerate naturally;
        # 3) if it still violates the file contract, apply the exact file-derived
        #    lexical safety net as the final deterministic barrier.
        for _ in range(max(0, settings.melimi_repair_attempts)):
            violations = lexical_violations(reply)
            if not violations:
                break
            repair_prompt = build_language_engine_context(
                user_message=message,
                conversation_context=conversation,
                linguistic_analysis=linguistic_text,
                response_plan=plan,
                max_profile_chars=6200,
                max_relevant_chars=6200,
            )
            repair_prompt += "\n\nSTRICT FILE-CONTENT VIOLATION:\n"
            repair_prompt += "\n".join(
                f"- MUST NOT output: {v['source']} ; REQUIRED Melimi form: {v['preferred']}"
                for v in violations
            )
            repair_prompt += "\nRewrite the whole answer naturally. Output only the answer."
            try:
                candidate=clean_response(await call_groq(repair_prompt, history, message))
                if candidate:
                    reply=candidate
            except Exception:
                break

        # Hard final barrier: no exact Standard/source term from an explicit
        # vocabulary mapping may survive in Melimi mode.
        reply=deterministic_repair(reply)

        # Refresh caches after any subject registration in the same process.
        reload_firewall()

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
    )
