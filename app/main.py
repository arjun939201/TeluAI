
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.github_sync import status as github_status, GitHubSyncError
from app.models import ChatRequest, ChatResponse, HealthResponse, WordRegistration, LearningStatusUpdate
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
from app.chat_learner import learn_from_user_message, format_learned
from app.learner_store import init_store, list_learning, set_status
from app.response import clean_response
from app.melimi.fast_answers import local_answer


app = FastAPI(title="TeluAI — Standard & Melimi Telugu AI")

# Chat-time learning is persistent but isolated from the authoritative corpus.
init_store()

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


@app.get("/learner/knowledge")
def learner_knowledge(status: str | None = None, limit: int = 100):
    """Inspect chat-time learning. Approved knowledge is used in future chats."""
    return {"items": list_learning(status=status, limit=limit)}


@app.post("/learner/{item_id}/status")
def learner_status(item_id: int, payload: LearningStatusUpdate):
    try:
        updated = set_status(item_id, payload.status)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if not updated:
        raise HTTPException(404, "Learning item not found.")
    return updated


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

    # Learn only explicit user-authored mappings; ordinary AI output is never
    # promoted into language authority. The master Melimi corpus is untouched.
    learn_from_user_message(message)

    history = [turn.model_dump() for turn in request.history]

    state = from_history(history)
    linguistic = extract_linguistic_hints(message)
    input_info = analyze_input(message)
    understanding = infer_intent(message, state)
    conversation = build_context(message, state, linguistic)
    plan = plan_response(understanding)

    candidates = extract_memory_candidates(history, settings.max_memory_items)
    memory = format_memory(candidates)
    learned = format_learned(message, limit=6) if request.mode == "melimi" else ""

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
        memory=(memory + "\n\nAPPROVED CHAT-TIME MELIMI KNOWLEDGE:\n" + learned) if learned else memory,
        knowledge=knowledge,
        grammar=grammar_policy() if request.mode == "melimi" else "",
        plan=plan,
        melimi_engine=melimi_engine,
    )

    # High-confidence language-definition questions are answered locally from
    # the authoritative contract. This both improves exactness and prevents a
    # trivial FAQ from consuming Groq quota.
    reply = local_answer(message, request.mode)
    truncated = False
    if reply is None:
        try:
            completion = await call_groq(prompt, history, message)
        except RuntimeError as exc:
            raise HTTPException(502, str(exc))
        except Exception as exc:
            raise HTTPException(502, f"AI request failed: {exc}")
        reply = completion.text
        truncated = completion.truncated

    reply = clean_response(reply)
    if request.mode == "melimi":
        # ONE-GROQ ARCHITECTURE: validation/repair is entirely local.
        # Never regenerate through Groq for a lexical violation.
        #
        # The lexical firewall itself is root-aware: it derives Standard
        # Telugu roots from suffixed surface forms and reconstructs the
        # correct Melimi inflection (including "ం"-final noun sandhi, e.g.
        # సినిమాలు -> తెఱాటాలు) generally, from the authoritative vocabulary
        # files. It intentionally does not rely on the older
        # melimi_morphology.repair_known_forms per-word hardcoded table —
        # that module is kept only for its own standalone regression tests.
        reply = deterministic_repair(reply)

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
        truncated=truncated,
    )
