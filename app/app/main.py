
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.models import ChatRequest, ChatResponse, HealthResponse
from app.language import normalize_roman_telugu
from app.conversation import build_state, infer_intent, understanding_context
from app.knowledge import load_vocabulary, retrieve, format_knowledge, audit_melimi
from app.prompts import build_system_prompt
from app.groq_client import call_groq


app = FastAPI(title="TeluAI — Natural Standard & Melimi Telugu AI")

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
    path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(path):
        raise HTTPException(404, "index.html not found")
    return FileResponse(path)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        service="TeluAI",
        corpus_entries=len(load_vocabulary()),
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    message = req.message.strip()
    if not message:
        raise HTTPException(400, "Message cannot be empty.")

    history = [x.model_dump() for x in req.history]
    state = build_state(history)
    intent = infer_intent(message, state)
    conversation = understanding_context(message, state)

    # Local retrieval is deliberately compact. The LLM receives knowledge,
    # not a pile of unrelated data.
    entries = retrieve(message, limit=18) if req.mode == "melimi" else []
    knowledge = format_knowledge(entries, max_chars=settings.MAX_CONTEXT_CHARS)

    # Roman-Telugu normalization is a local hint; the original user message
    # remains the actual message sent to the model.
    if req.mode == "melimi":
        conversation += "\n- Roman/normalized hint: " + normalize_roman_telugu(message)

    system_prompt = build_system_prompt(
        mode=req.mode,
        knowledge=knowledge,
        conversation=conversation,
    )

    try:
        reply = await call_groq(system_prompt, history, message)
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"AI request failed: {exc}")

    audit = audit_melimi(reply) if req.mode == "melimi" else {}

    return ChatResponse(
        reply=reply,
        mode=req.mode,
        understanding=intent,
        intent=intent,
        language_audit=audit,
    )
