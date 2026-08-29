"""TeluAI 2 production application.

One product: a Telugu-first AI chat. Ordinary conversation is the default.
Explicit Melimi suggestions made in chat are remembered per user and reused in
future conversations. They never become global language authority automatically.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.account_service import create_guest_user, update_credentials
from app.auth import COOKIE_NAME, current_user
from app.config import settings
from app.database import (
    SessionLocal,
    create_conversation,
    create_session,
    create_user,
    delete_conversation,
    delete_session,
    get_conversations,
    get_history,
    get_user_settings,
    save_message,
    save_usage,
    update_user_settings,
    authenticate,
    audit_log,
    run_migrations if False else None,
)
from app.groq_client import call_groq_detailed
from app.local_answer import answer as local_answer
from app.melimi.engine import build_language_engine_context
from app.melimi.firewall import deterministic_repair
from app.melimi.grammar import grammar_policy
from app.linguistics.normalizer import analyze_input
from app.linguistics.parser import extract_linguistic_hints
from app.conversation.state import from_history
from app.conversation.understanding import build_context, infer_intent
from app.conversation.planner import plan_response
from app.prompts import build_prompt
from app.response import clean_response
from app.teluai2_learning import extract_suggestion, learned_for_user, prompt_context, remember_suggestion
from app.migrations import run_migrations

BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = BASE_DIR / "static"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    conversation_id: str | None = None
    history: list[dict] = Field(default_factory=list, max_length=40)


class CredentialsRequest(BaseModel):
    current_password: str = ""
    username: str | None = None
    new_password: str | None = None


class SettingsRequest(BaseModel):
    response_length: str = "normal"
    memory_enabled: bool = True


class MemoryRequest(BaseModel):
    key: str = Field(min_length=1, max_length=160)
    value: str = Field(min_length=1, max_length=2000)


@asynccontextmanager
async def lifespan(application: FastAPI):
    run_migrations()
    yield


app = FastAPI(title="TeluAI — Telugu AI", lifespan=lifespan)


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.session_days * 86400,
        path="/",
    )


def _history(user_id: int, conversation_id: str | None, supplied: list[dict]) -> tuple[str, list[dict]]:
    if conversation_id:
        try:
            rows = get_history(user_id, conversation_id, limit=40)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        return conversation_id, [{"role": x["role"], "content": x["content"]} for x in rows]
    return create_conversation(user_id, "New chat", "melimi"), supplied[-20:]


def _build_telugu_prompt(message: str, history: list[dict], user_id: int) -> tuple[str, dict]:
    state = from_history([x for x in history if x.get("role") in {"user", "assistant"}])
    hints = extract_linguistic_hints(message)
    input_info = analyze_input(message)
    understanding = infer_intent(message, state)
    conversation = build_context(message, state, hints)
    plan = plan_response(understanding)
    learned = prompt_context(user_id)
    linguistic_text = "\n".join([
        f"- normalized input: {hints.get('normalized', '')}",
        f"- tokens: {hints.get('tokens', [])}",
        f"- sentence force: {hints.get('sentence_force', '')}",
        f"- question type: {hints.get('question_type', '')}",
        f"- language signal: Telugu-first",
        f"- Roman/mixed input signals: {input_info}",
    ])
    engine = build_language_engine_context(
        user_message=message,
        conversation_context=conversation,
        linguistic_analysis=linguistic_text,
        response_plan=plan,
        max_profile_chars=settings.melimi_profile_chars,
        max_relevant_chars=settings.melimi_relevant_chars,
    )
    instructions = """You are TeluAI, a Telugu-first AI assistant.
Respond in Telugu by default for every ordinary conversation, even when the user writes English, Roman Telugu, or mixed Telugu. Use natural modern Telugu while respecting Melimi Telugu knowledge when it is relevant.
Do not invent Melimi words, roots, grammar, historical evidence, or authority. If a user-provided Melimi suggestion is present, it is personal learned context, not global authority.
Have a normal helpful conversation. Do not turn ordinary questions into a language-research workflow. Do not use a generic chatbot meta voice.
If the user explicitly teaches a word or grammar rule, acknowledge it naturally and use it in later relevant conversations."""
    if learned:
        instructions += "\n\n" + learned
    prompt = build_prompt(
        mode="melimi",
        conversation=conversation,
        linguistics=linguistic_text,
        memory="",
        grammar=grammar_policy(),
        plan=plan,
        melimi_engine=engine,
        knowledge="",
    )
    return instructions + "\n\n" + prompt, {"intent": understanding.get("intent"), "learned_count": len(learned_for_user(user_id))}


@app.get("/")
def home():
    target = STATIC_DIR / "index.html"
    if not target.exists():
        raise HTTPException(404, "Frontend not found.")
    return FileResponse(target)


@app.get("/health")
def health():
    return {"status": "ok", "service": "TeluAI", "mode": "telugu-first"}


@app.get("/health/ready")
def ready():
    try:
        with SessionLocal() as db:
            db.execute(select(1))
    except Exception as exc:
        raise HTTPException(503, "Database is not ready.") from exc
    return {"status": "ready", "service": "TeluAI"}


@app.get("/auth/me")
def me(user=Depends(current_user)):
    return {"authenticated": True, "id": user.id, "username": user.username, "email": None if user.role == "guest" else user.email, "role": user.role}


@app.post("/auth/guest")
def guest(payload: dict, response: Response):
    try:
        user = create_guest_user(str(payload.get("username", "")).strip(), str(payload.get("password", "")))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    _set_cookie(response, create_session(user.id, settings.session_days))
    audit_log(user.id, "auth.guest_register", "user", str(user.id))
    return {"authenticated": True, "id": user.id, "username": user.username, "role": user.role}


@app.post("/auth/register")
def register(payload: dict, response: Response):
    try:
        user = create_user(str(payload.get("username", "")).strip(), str(payload.get("email", "")).strip().lower(), str(payload.get("password", "")))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    _set_cookie(response, create_session(user.id, settings.session_days))
    audit_log(user.id, "auth.register", "user", str(user.id))
    return {"authenticated": True, "id": user.id, "username": user.username, "role": user.role}


@app.post("/auth/login")
def login(payload: dict, response: Response):
    user = authenticate(str(payload.get("identifier", "")).strip(), str(payload.get("password", "")))
    if not user:
        raise HTTPException(401, "Username/email or password is incorrect.")
    _set_cookie(response, create_session(user.id, settings.session_days))
    audit_log(user.id, "auth.login", "user", str(user.id))
    return {"authenticated": True, "id": user.id, "username": user.username, "role": user.role}


@app.post("/auth/logout")
def logout(response: Response, session: str | None = Cookie(default=None, alias=COOKIE_NAME)):
    if session:
        delete_session(session)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/conversations")
def conversations(user=Depends(current_user)):
    return {"conversations": get_conversations(user.id)}


@app.get("/conversations/{conversation_id}")
def conversation(conversation_id: str, user=Depends(current_user)):
    try:
        return {"conversation_id": conversation_id, "messages": get_history(user.id, conversation_id, limit=100)}
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.delete("/conversations/{conversation_id}")
def remove_conversation(conversation_id: str, user=Depends(current_user)):
    if not delete_conversation(user.id, conversation_id):
        raise HTTPException(404, "Conversation not found.")
    return {"ok": True}


@app.get("/me/settings")
def settings_get(user=Depends(current_user)):
    return get_user_settings(user.id)


@app.put("/me/settings")
def settings_put(payload: SettingsRequest, user=Depends(current_user)):
    return update_user_settings(user.id, "melimi", payload.response_length, payload.memory_enabled)


@app.get("/me/learned")
def learned(user=Depends(current_user)):
    return {"items": learned_for_user(user.id)}


@app.post("/me/memory")
def memory(payload: MemoryRequest, user=Depends(current_user)):
    from app.database import remember_user_memory
    remember_user_memory(user.id, payload.key.strip(), payload.value.strip())
    return {"ok": True}


@app.post("/chat")
async def chat(request: ChatRequest, user=Depends(current_user)):
    message = request.message.strip()
    conversation_id, history = _history(user.id, request.conversation_id, request.history)

    suggestion = extract_suggestion(message)
    learned_notice = None
    if suggestion:
        remember_suggestion(user.id, suggestion)
        learned_notice = suggestion

    local = local_answer(message, "melimi")
    if local is not None and not suggestion:
        reply = clean_response(local)
        save_message(user.id, conversation_id, "user", message)
        mid = save_message(user.id, conversation_id, "assistant", reply, model="local")
        return {"reply": reply, "conversation_id": conversation_id, "message_id": mid, "local": True, "learned": None}

    prompt, meta = _build_telugu_prompt(message, history, user.id)
    try:
        result = await call_groq_detailed(prompt, history, message)
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "AI request failed. Please try again.") from exc

    reply = clean_response(result.get("answer", ""))
    reply = deterministic_repair(reply)
    if not reply:
        raise HTTPException(502, "AI returned an empty response.")

    if learned_notice:
        if learned_notice.kind == "VOCABULARY":
            reply = f"గుర్తుంచుకున్నాను. ఈ సంభాషణ నుంచి మీ సూచనను మీ మేలిమి భాషా జ్ఞాపకంలో భద్రపరిచాను: {learned_notice.key} → {learned_notice.value}\n\n" + reply
        else:
            reply = f"గుర్తుంచుకున్నాను. మీరు ఇచ్చిన మేలిమి వ్యాకరణ సూచనను మీ భాషా జ్ఞాపకంలో భద్రపరిచాను.\n\n" + reply

    save_usage(user.id, result.get("model"), result.get("input_tokens"), result.get("output_tokens"), "ok")
    save_message(user.id, conversation_id, "user", message)
    mid = save_message(user.id, conversation_id, "assistant", reply, model=result.get("model"), input_tokens=result.get("input_tokens"), output_tokens=result.get("output_tokens"), latency_ms=result.get("latency_ms"))
    return {"reply": reply, "conversation_id": conversation_id, "message_id": mid, "local": False, "learned": None if not learned_notice else {"kind": learned_notice.kind, "key": learned_notice.key, "value": learned_notice.value}}


@app.put("/me/credentials")
def credentials(payload: CredentialsRequest, user=Depends(current_user)):
    try:
        updated = update_credentials(user.id, payload.current_password, payload.username, payload.new_password)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "username": updated.username, "role": updated.role}
