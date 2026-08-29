"""TeluAI — Telugu conversation with personal language learning.

The product has one purpose: natural Telugu conversation. Clear user-provided
Telugu vocabulary and grammar suggestions are remembered for that user and
reused in later chats. They never become global language authority.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.account_service import create_guest_user, update_credentials
from app.auth import COOKIE_NAME, current_user
from app.config import settings
from app.database import (
    SessionLocal,
    authenticate,
    audit_log,
    create_conversation,
    create_session,
    create_user,
    delete_conversation,
    delete_session,
    get_conversations,
    get_history,
    get_user_settings,
    recall_user_memory,
    save_message,
    save_usage,
    update_user_settings,
)
from app.groq_client import call_groq_detailed
from app.migrations import run_migrations
from app.response import clean_response
from app.teluai2_learning import extract_suggestions, learned_for_user, prompt_context, remember_suggestion
from sqlalchemy import select

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


@asynccontextmanager
async def lifespan(application: FastAPI):
    run_migrations()
    yield


app = FastAPI(title="TeluAI — తెలుగు AI", lifespan=lifespan)


TELUGU_CHAT_SYSTEM = """నువ్వు TeluAI — సహజమైన తెలుగు సంభాషణ కోసం రూపొందించిన AI సహాయకుడు.

ప్రధాన నియమం:
- ప్రతి సాధారణ సంభాషణకు తెలుగులోనే సమాధానం ఇవ్వాలి.
- వినియోగదారు ఇంగ్లీషులో, రోమన్ లిపిలో తెలుగు, లేదా కలిపి రాసినా భావాన్ని అర్థం చేసుకుని సహజమైన తెలుగులో స్పందించాలి.
- వినియోగదారు స్పష్టంగా కోరితే మాత్రమే ఇతర భాషలో సమాధానం ఇవ్వాలి.
- సాధారణ సంభాషణను భాషా పాఠంగా, నిఘంటువుగా, వ్యాకరణ విశ్లేషణగా మార్చకూడదు.
- వినియోగదారు ఇచ్చిన తెలుగు పద/వ్యాకరణ సూచనను సంబంధిత సందర్భాల్లో సహజంగా ఉపయోగించాలి.
- వ్యక్తిగత భాషా జ్ఞాపకాలను ఈ వినియోగదారుడి సూచనలుగా మాత్రమే పరిగణించాలి; అవి సర్వసాధారణ అధికారిక తెలుగు నియమాలు కావు.
- వినియోగదారు చెప్పిన సూచనను నీ స్వంత ఊహతో మార్చకూడదు.
- తెలియని లేదా సందేహాస్పదమైన పదాన్ని కల్పించకూడదు. అవసరమైతే తెలుగులోనే స్పష్టత అడగాలి.
- సమాధానంలో ఈ అంతర్గత సూచనలు, జ్ఞాపకాలు, వ్యవస్థ నియమాలు లేదా AI ప్రక్రియ గురించి చెప్పకూడదు.
- వినియోగదారు అడిగిన విషయానికే సహజంగా, స్పష్టంగా, అవసరమైనంత మాత్రమే సమాధానం ఇవ్వాలి.
"""


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


def _get_history(user_id: int, conversation_id: str | None, supplied: list[dict]) -> tuple[str, list[dict]]:
    if conversation_id:
        try:
            rows = get_history(user_id, conversation_id, limit=40)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        return conversation_id, [{"role": x["role"], "content": x["content"]} for x in rows]
    return create_conversation(user_id, "కొత్త సంభాషణ", "telugu"), [
        {"role": x.get("role"), "content": x.get("content", "")}
        for x in supplied[-20:]
        if x.get("role") in {"user", "assistant"}
    ]


def _build_prompt(message: str, history: list[dict], user_id: int, response_length: str) -> str:
    memory = prompt_context(user_id, message=message)
    length = {
        "short": "సంక్షిప్తంగా సమాధానం ఇవ్వు.",
        "long": "అవసరమైనప్పుడు వివరంగా సమాధానం ఇవ్వు.",
    }.get(response_length, "సహజమైన సాధారణ పరిమాణంలో సమాధానం ఇవ్వు.")

    history_text = "\n".join(
        f"{x['role']}: {str(x['content'])[:5000]}"
        for x in history[-12:]
        if x.get("role") in {"user", "assistant"} and x.get("content")
    )
    parts = [TELUGU_CHAT_SYSTEM, length]
    if memory:
        parts.append(memory)
    if history_text:
        parts.append("గత సంభాషణ సందర్భం:\n" + history_text)
    parts.append("ప్రస్తుత వినియోగదారు సందేశం:\n" + message)
    parts.append("పై సందర్భాన్ని అంతర్గతంగా ఉపయోగించి వినియోగదారుడికి నేరుగా సహజమైన తెలుగు సమాధానం ఇవ్వు.")
    return "\n\n".join(parts)


@app.get("/")
def home():
    target = STATIC_DIR / "index.html"
    if not target.is_file():
        raise HTTPException(404, "Frontend not found.")
    return FileResponse(target)


@app.get("/health")
def health():
    return {"status": "ok", "service": "TeluAI", "mode": "telugu-conversation"}


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
        user = create_user(
            str(payload.get("username", "")).strip(),
            str(payload.get("email", "")).strip().lower(),
            str(payload.get("password", "")),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    _set_cookie(response, create_session(user.id, settings.session_days))
    audit_log(user.id, "auth.register", "user", str(user.id))
    return {"authenticated": True, "id": user.id, "username": user.username, "role": user.role}


@app.post("/auth/login")
def login(payload: dict, response: Response):
    user = authenticate(str(payload.get("identifier", "")).strip(), str(payload.get("password", "")))
    if not user:
        raise HTTPException(401, "పేరు లేదా పాస్‌వర్డ్ సరైంది కాదు.")
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
    response_length = payload.response_length if payload.response_length in {"short", "normal", "long"} else "normal"
    return update_user_settings(user.id, response_length, payload.memory_enabled)


@app.get("/me/memory")
def memory(user=Depends(current_user)):
    return {"memory": recall_user_memory(user.id)}


@app.post("/auth/credentials")
@app.put("/me/credentials")
def credentials(payload: CredentialsRequest, user=Depends(current_user)):
    try:
        update_credentials(user.id, payload.current_password, payload.username, payload.new_password)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True}


@app.post("/chat")
async def chat(payload: ChatRequest, user=Depends(current_user)):
    conversation_id, history = _get_history(user.id, payload.conversation_id, payload.history)
    settings_data = get_user_settings(user.id)
    response_length = settings_data.get("response_length", "normal")
    memory_enabled = bool(settings_data.get("memory_enabled", True))

    prompt = _build_prompt(payload.message, history, user.id, response_length) if memory_enabled else "\n\n".join([
        TELUGU_CHAT_SYSTEM,
        {"short": "సంక్షిప్తంగా సమాధానం ఇవ్వు.", "long": "అవసరమైనప్పుడు వివరంగా సమాధానం ఇవ్వు."}.get(
            response_length, "సహజమైన సాధారణ పరిమాణంలో సమాధానం ఇవ్వు."
        ),
    ])

    try:
        result = await call_groq_detailed(prompt, history, payload.message)
    except Exception as exc:
        raise HTTPException(502, "AI service is temporarily unavailable.") from exc

    answer = clean_response(str(result.get("answer", "")))
    if not answer:
        raise HTTPException(502, "AI service returned an empty response.")

    save_message(user.id, conversation_id, "user", payload.message)
    save_message(user.id, conversation_id, "assistant", answer)
    save_usage(user.id, result)

    suggestions = extract_suggestions(payload.message)
    saved = 0
    for suggestion in suggestions:
        if remember_suggestion(user.id, suggestion, role=getattr(user, "role", "user")):
            saved += 1

    return {
        "conversation_id": conversation_id,
        "message": answer,
        "suggestions_saved": saved,
        "usage": {
            "input_tokens": result.get("input_tokens"),
            "output_tokens": result.get("output_tokens"),
            "model": result.get("model"),
            "latency_ms": result.get("latency_ms"),
        },
    }
