import os
import re
import hashlib
import smtplib
from email.message import EmailMessage

from fastapi import FastAPI, HTTPException, Depends, Response, Cookie, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.config import settings
from app.github_sync import status as github_status, GitHubSyncError
from app.models import (
    ChatRequest, ChatResponse, HealthResponse, WordRegistration,
    RegisterRequest, LoginRequest, ForgotPasswordRequest,
    VerifyResetCodeRequest, ResetPasswordRequest, FeedbackRequest,
    SettingsUpdateRequest, MemoryRequest, GuestRegisterRequest,
    CredentialUpdateRequest,
)
from app.auth import current_user, require_admin, require_owner, COOKIE_NAME
from app.account_service import create_guest_user, update_credentials
from app.database import (
    create_user, authenticate, create_session, delete_session,
    bootstrap_owner, promote_configured_owners, create_password_reset_token,
    verify_password_reset_code, reset_password, create_conversation,
    save_message, get_conversations, get_history, delete_conversation,
    get_user_settings, update_user_settings, save_usage, SessionLocal,
    Feedback, list_candidates, review_candidate, approved_learning,
    remember_user_memory, recall_user_memory, cache_get, cache_put,
    audit_log, list_users, get_user_by_id, set_user_role, set_user_active,
    delete_user, database_stats, list_audit_logs, language_snapshot,
    ingest_language_package, KnowledgeVersion,
)
from app.linguistics.normalizer import analyze_input
from app.linguistics.parser import extract_linguistic_hints
from app.conversation.state import from_history
from app.conversation.understanding import infer_intent, build_context
from app.conversation.planner import plan_response
from app.memory.manager import extract_memory_candidates, format_memory
from app.retrieval.knowledge import load_vocabulary
from app.melimi.grammar import grammar_policy
from app.melimi.validator import audit_melimi
from app.melimi.engine import build_language_engine_context
from app.melimi.index import inventory as subject_inventory
from app.melimi.registry import analyze_word
from app.melimi.firewall import deterministic_repair
from app.melimi.registration import register_word
from app.prompts import build_prompt
from app.groq_client import call_groq_detailed
from app.response import clean_response
from app.local_answer import answer as local_answer
from app.migrations import run_migrations
from app.chat_learning import learn_explicit_teaching, parse_command
from app.melimi.content_store import submit_content

app = FastAPI(title="TeluAI — Melimi Telugu AI Platform")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _knowledge_version() -> int:
    with SessionLocal() as db:
        row = db.scalars(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc())).first()
        return int(row.version) if row else 0


def _cache_key(message: str, mode: str) -> str:
    normalized = re.sub(r"\s+", " ", message.strip().lower())
    return hashlib.sha256(f"chat-conversation-v3\n{mode}\n{_knowledge_version()}\n{normalized}".encode()).hexdigest()


@app.on_event("startup")
def startup():
    run_migrations()
    owner_emails = [e.strip().lower() for e in os.getenv("OWNER_EMAILS", "throwuse829@gmail.com,draftusagw93@gmail.com").split(",") if e.strip()]
    promote_configured_owners(owner_emails)


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


@app.get("/admin/learning/pending")
def admin_learning_pending(user=Depends(require_admin)):
    return {"candidates": list_candidates("PENDING"), "role": user.role}


@app.post("/admin/learning/{candidate_id}/approve")
def admin_learning_approve(candidate_id: int, note: str = "", user=Depends(require_admin)):
    result = review_candidate(candidate_id, True, note)
    if result is None:
        raise HTTPException(404, "Candidate not found.")
    audit_log(user.id, "learning.approve", "learning_candidate", str(candidate_id), {"note": note})
    return {"ok": True, "candidate": result}


@app.post("/admin/learning/{candidate_id}/reject")
def admin_learning_reject(candidate_id: int, note: str = "", user=Depends(require_admin)):
    result = review_candidate(candidate_id, False, note)
    if result is None:
        raise HTTPException(404, "Candidate not found.")
    audit_log(user.id, "learning.reject", "learning_candidate", str(candidate_id), {"note": note})
    return {"ok": True, "candidate": result}


@app.get("/admin/database/stats")
def admin_database_stats(user=Depends(require_admin)):
    return {"stats": database_stats(), "role": user.role}


@app.get("/admin/database/language")
def admin_database_language(limit: int = 50, user=Depends(require_admin)):
    return {"language": language_snapshot(limit), "role": user.role}


@app.get("/admin/database/users")
def admin_database_users(user=Depends(require_admin)):
    return {"users": list_users(), "role": user.role}


@app.get("/admin/database/audit")
def admin_database_audit(limit: int = 100, user=Depends(require_admin)):
    return {"logs": list_audit_logs(limit), "role": user.role}


@app.post("/admin/users/{target_id}/role")
def admin_set_role(target_id: int, role: str, user=Depends(require_owner)):
    role = role.strip().lower()
    if role not in {"user", "admin", "owner"}:
        raise HTTPException(400, "Invalid role.")
    target = get_user_by_id(target_id)
    if target is None:
        raise HTTPException(404, "User not found.")
    if target.id == user.id and role != "owner":
        raise HTTPException(400, "The owner cannot demote their own account.")
    if target.role == "owner" and role != "owner":
        raise HTTPException(400, "The owner cannot be demoted through this endpoint.")
    result = set_user_role(target_id, role)
    audit_log(user.id, "user.role_change", "user", str(target_id), {"old_role": target.role, "new_role": role})
    return {"ok": True, "user": result}


@app.post("/admin/users/{target_id}/active")
def admin_set_active(target_id: int, active: bool, user=Depends(require_owner)):
    target = get_user_by_id(target_id)
    if target is None:
        raise HTTPException(404, "User not found.")
    if target.id == user.id and not active:
        raise HTTPException(400, "The owner cannot deactivate their own account.")
    if target.role == "owner" and not active:
        raise HTTPException(400, "The owner cannot be deactivated.")
    result = set_user_active(target_id, active)
    audit_log(user.id, "user.activation_change", "user", str(target_id), {"active": active})
    return {"ok": True, "user": result}


@app.delete("/admin/users/{target_id}")
def admin_delete_user(target_id: int, user=Depends(require_owner)):
    target = get_user_by_id(target_id)
    if target is None:
        raise HTTPException(404, "User not found.")
    if target.id == user.id or target.role == "owner":
        raise HTTPException(400, "The owner account cannot be deleted.")
    if not delete_user(target_id):
        raise HTTPException(404, "User not found.")
    audit_log(user.id, "user.delete", "user", str(target_id), {"username": target.username, "role": target.role})
    return {"ok": True}


@app.get("/auth/me")
def auth_me(user=Depends(current_user)):
    return {"authenticated": True, "id": user.id, "username": user.username, "email": None if user.role == "guest" else user.email, "role": user.role}


@app.post("/auth/guest")
def auth_guest(payload: GuestRegisterRequest, response: Response):
    try:
        user = create_guest_user(payload.username, payload.password)
        token = create_session(user.id, settings.session_days)
        response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", secure=settings.cookie_secure, max_age=settings.session_days * 86400)
        return {"authenticated": True, "id": user.id, "username": user.username, "email": None, "role": user.role}
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.put("/me/credentials")
def me_credentials(payload: CredentialUpdateRequest, user=Depends(current_user)):
    try:
        updated = update_credentials(user.id, payload.current_password, payload.username, payload.new_password)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    audit_log(user.id, "account.credentials_change", "user", str(user.id), {"username_changed": bool(payload.username), "password_changed": bool(payload.new_password)})
    return {"ok": True, "username": updated.username, "role": updated.role}


@app.get("/me/settings")
def me_settings(user=Depends(current_user)):
    return get_user_settings(user.id)


@app.put("/me/settings")
def update_settings(payload: SettingsUpdateRequest, user=Depends(current_user)):
    return update_user_settings(user.id, payload.preferred_mode, payload.response_length, payload.memory_enabled)


@app.post("/me/memory")
def add_memory(payload: MemoryRequest, user=Depends(current_user)):
    remember_user_memory(user.id, payload.key.strip(), payload.value.strip())
    audit_log(user.id, "memory.create", "user_memory", payload.key, {"value_length": len(payload.value)})
    return {"ok": True}


@app.get("/me/memory")
def get_memory(user=Depends(current_user)):
    return {"memory": recall_user_memory(user.id)}


@app.post("/auth/register")
def auth_register(payload: RegisterRequest, response: Response):
    try:
        user = create_user(payload.username.strip(), payload.email.strip().lower(), payload.password)
        token = create_session(user.id, settings.session_days)
        response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", secure=settings.cookie_secure, max_age=settings.session_days * 86400)
        return {"authenticated": True, "id": user.id, "username": user.username, "email": user.email, "role": user.role}
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.post("/auth/login")
def auth_login(payload: LoginRequest, response: Response):
    user = authenticate(payload.identifier.strip(), payload.password)
    if not user:
        raise HTTPException(401, "Invalid username/email or password.")
    token = create_session(user.id, settings.session_days)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", secure=settings.cookie_secure, max_age=settings.session_days * 86400)
    return {"authenticated": True, "id": user.id, "username": user.username, "email": None if user.role == "guest" else user.email, "role": user.role}


@app.post("/auth/logout")
def auth_logout(response: Response, session: str | None = Cookie(default=None, alias=COOKIE_NAME)):
    if session:
        delete_session(session)
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@app.post("/auth/forgot-password")
def auth_forgot_password(payload: ForgotPasswordRequest):
    email = payload.email.strip().lower()
    code = create_password_reset_token(email)
    if code:
        host = os.getenv("SMTP_HOST", "").strip()
        port = int(os.getenv("SMTP_PORT", "587"))
        username = os.getenv("SMTP_USERNAME", "").strip()
        password = os.getenv("SMTP_PASSWORD", "")
        sender = os.getenv("SMTP_FROM", username).strip()
        if not (host and username and password and sender):
            raise HTTPException(503, "Password reset email service is not available. Please try again later.")
        try:
            msg = EmailMessage()
            msg["Subject"] = "TeluAI password reset code"
            msg["From"] = sender
            msg["To"] = email
            msg.set_content(f"Your TeluAI password reset code is: {code}\n\nThis code expires in 10 minutes.\nIf you did not request a password reset, ignore this email.")
            with smtplib.SMTP(host, port, timeout=10) as smtp:
                smtp.starttls(); smtp.login(username, password); smtp.send_message(msg)
        except (OSError, smtplib.SMTPException) as exc:
            raise HTTPException(503, "Password reset email service is not available. Please try again later.") from exc
    return {"ok": True, "message": "If an account with that email exists, a verification code has been sent."}


@app.post("/auth/verify-reset-code")
def auth_verify_reset_code(payload: VerifyResetCodeRequest):
    token = verify_password_reset_code(payload.email.strip().lower(), payload.code.strip())
    if not token:
        raise HTTPException(400, "The verification code is invalid or expired.")
    return {"ok": True, "reset_token": token}


@app.post("/auth/reset-password")
def auth_reset_password(payload: ResetPasswordRequest, response: Response):
    user_id = reset_password(payload.token, payload.password)
    if not user_id:
        raise HTTPException(400, "The reset session is invalid or expired.")
    token = create_session(user_id, settings.session_days)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", secure=settings.cookie_secure, max_age=settings.session_days * 86400)
    return {"ok": True}


@app.get("/conversations")
def conversations(user=Depends(current_user)):
    return {"conversations": get_conversations(user.id)}


@app.get("/conversations/{conversation_id}")
def conversation_detail(conversation_id: str, user=Depends(current_user)):
    try:
        messages = get_history(user.id, conversation_id, limit=100)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"conversation_id": conversation_id, "messages": messages}


@app.delete("/conversations/{conversation_id}")
def conversation_delete(conversation_id: str, user=Depends(current_user)):
    try:
        delete_conversation(user.id, conversation_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@app.get("/github/status")
def github_sync_status(user=Depends(require_admin)):
    return github_status()


@app.post("/github/sync")
async def github_sync(user=Depends(require_admin)):
    from app.github_sync import sync_repo
    try:
        result = await sync_repo()
        audit_log(user.id, "github.sync", "repository", result.get("repository", ""), result)
        return result
    except GitHubSyncError as exc:
        raise HTTPException(502, str(exc))


@app.get("/melimi/subjects")
def melimi_subjects(user=Depends(current_user)):
    return subject_inventory()


@app.get("/melimi/analyze")
def melimi_analyze(word: str, user=Depends(current_user)):
    return analyze_word(word)


@app.post("/melimi/content/upload")
async def melimi_content_upload(file: UploadFile = File(...), user=Depends(current_user)):
    name = (file.filename or "").strip()
    ext = os.path.splitext(name.lower())[1]
    if ext not in {".txt", ".md", ".json", ".zip"}:
        raise HTTPException(400, "Upload a .txt, .md, .json, or .zip language-content file.")
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, "Language content file is too large. Maximum is 10 MB.")
    try:
        result = ingest_language_package(filename=name, raw=raw, approved=True, actor_user_id=user.id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(400, f"Could not import language content: {exc}")
    audit_log(user.id, "language.content_upload", "language_package", name, {"bytes": len(raw), "status": result.get("status"), "documents": result.get("documents", 0)})
    return {"ok": True, **result}


@app.post("/melimi/content")
async def melimi_content(payload: dict, user=Depends(current_user)):
    title = str(payload.get("title", "")).strip()
    content = str(payload.get("content", "")).strip()
    meaning = str(payload.get("meaning", "")).strip()
    if not content:
        raise HTTPException(400, "Content is required.")
    if len(content) > 50000:
        raise HTTPException(400, "Content is too large.")
    try:
        result = submit_content(user.id, title, content, approved=True)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    audit_log(user.id, "language.content.create", "language_content", title or "CHAT_COMMAND", {"chars": len(content), "meaning_chars": len(meaning)})
    return {"ok": True, "status": "MASTER", **result}


@app.post("/melimi/register")
async def melimi_register(payload: WordRegistration, user=Depends(current_user)):
    try:
        result = await register_word(payload.model_dump(), user.id)
        return {"ok": True, **result}
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except GitHubSyncError as exc:
        raise HTTPException(502, str(exc))


@app.post("/feedback")
def feedback(payload: FeedbackRequest, user=Depends(current_user)):
    with SessionLocal() as db:
        db.add(Feedback(user_id=user.id, message_id=payload.message_id, rating=payload.rating, text=payload.text))
        db.commit()
    return {"ok": True}


@app.get("/health")
def health():
    db_url = settings.database_url.lower()
    database = "postgresql" if db_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")) else "sqlite-fallback"
    return HealthResponse(status="ok", service="TeluAI", vocabulary_entries=len(load_vocabulary()), database=database)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user=Depends(current_user)):
    message = request.message.strip()
    if not message:
        raise HTTPException(400, "Message cannot be empty.")

    command = parse_command(message)
    if command:
        try:
            result = learn_explicit_teaching(message, user.id)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        if not result.get("learned"):
            raise HTTPException(400, "Invalid language command.")
        conversation_id = request.conversation_id or create_conversation(user.id, message[:70], request.mode)
        save_message(user.id, conversation_id, "user", message)
        reply = "✓ మేలిమి భాషా నిలయంలో నేరుగా చేర్చబడింది.\nస్థితి: MASTER"
        assistant_id = save_message(user.id, conversation_id, "assistant", reply, model="language-command")
        return ChatResponse(reply=reply, mode=request.mode, intent="language_command", conversation_id=conversation_id, message_id=assistant_id, local=True)

    if request.conversation_id:
        try:
            history = get_history(user.id, request.conversation_id, limit=40)
        except ValueError as exc:
            raise HTTPException(404, str(exc))
        history = [{"role": x["role"], "content": x["content"]} for x in history]
        conversation_id = request.conversation_id
    else:
        history = [turn.model_dump() for turn in request.history]
        conversation_id = create_conversation(user.id, message[:70], request.mode)

    if settings.cache_enabled and not request.conversation_id:
        cached = cache_get(_cache_key(message, request.mode), request.mode)
        if cached:
            save_message(user.id, conversation_id, "user", message)
            assistant_id = save_message(user.id, conversation_id, "assistant", cached, model="cache")
            return ChatResponse(reply=cached, mode=request.mode, intent="cached", conversation_id=conversation_id, message_id=assistant_id, local=True)

    local = local_answer(message, request.mode)
    if local is not None:
        save_message(user.id, conversation_id, "user", message)
        assistant_id = save_message(user.id, conversation_id, "assistant", local, model="local-deterministic")
        if settings.cache_enabled and not request.conversation_id:
            cache_put(_cache_key(message, request.mode), request.mode, local)
        return ChatResponse(reply=local, mode=request.mode, intent="local_knowledge", conversation_id=conversation_id, message_id=assistant_id, local=True)

    state = from_history(history)
    linguistic = extract_linguistic_hints(message)
    input_info = analyze_input(message)
    understanding = infer_intent(message, state)
    conversation = build_context(message, state, linguistic)
    plan = plan_response(understanding)
    memory = format_memory(extract_memory_candidates(history, settings.max_memory_items))
    persistent_memory = recall_user_memory(user.id)
    if persistent_memory:
        memory += "\nPERSISTENT USER MEMORY (use only when relevant):\n" + "\n".join(f"- {x['value']}" for x in persistent_memory)

    linguistic_text = "\n".join([
        f"- normalized input: {linguistic['normalized']}",
        f"- tokens: {linguistic['tokens']}",
        f"- sentence force: {linguistic['sentence_force']}",
        f"- question type: {linguistic['question_type']}",
        f"- negation hint: {linguistic['negation_hint']}",
        f"- Roman/mixed input signals: {input_info}",
    ])

    melimi_engine = ""
    if request.mode == "melimi":
        melimi_engine = build_language_engine_context(
            user_message=message,
            conversation_context=conversation,
            linguistic_analysis=linguistic_text,
            response_plan=plan,
            max_profile_chars=settings.melimi_profile_chars,
            max_relevant_chars=settings.melimi_relevant_chars,
        )

    prompt = build_prompt(
        mode=request.mode,
        conversation=conversation,
        linguistics=linguistic_text,
        memory=memory,
        grammar=grammar_policy() if request.mode == "melimi" else "",
        plan=plan,
        melimi_engine=melimi_engine,
        knowledge="",
    )[:settings.max_context_chars]

    try:
        result = await call_groq_detailed(prompt, history, message)
    except RuntimeError as exc:
        save_usage(user.id, settings.groq_model, None, None, "error")
        if request.mode == "melimi":
            from app.linguistics.normalizer import normalize_roman_telugu
            from app.melimi.root_morphology import convert_text
            normalized = normalize_roman_telugu(message)
            converted = convert_text(normalized)
            if converted != normalized and len(normalized) <= 500:
                save_message(user.id, conversation_id, "user", message)
                assistant_id = save_message(user.id, conversation_id, "assistant", converted, model="local-melimi-fallback")
                return ChatResponse(reply=converted, mode=request.mode, intent="local_conversion_fallback", conversation_id=conversation_id, message_id=assistant_id, local=True)
        raise HTTPException(502, str(exc))
    except Exception as exc:
        save_usage(user.id, settings.groq_model, None, None, "error")
        raise HTTPException(502, "AI request failed. Please try again.") from exc

    reply = clean_response(result["answer"])
    if request.mode == "melimi":
        reply = deterministic_repair(reply)
    if not reply:
        raise HTTPException(502, "AI returned an empty response.")

    save_usage(user.id, result.get("model"), result.get("input_tokens"), result.get("output_tokens"), "ok")
    save_message(user.id, conversation_id, "user", message)
    assistant_id = save_message(user.id, conversation_id, "assistant", reply, model=result.get("model"), input_tokens=result.get("input_tokens"), output_tokens=result.get("output_tokens"), latency_ms=result.get("latency_ms"))
    if settings.cache_enabled and not request.conversation_id and len(reply) >= settings.cache_min_chars:
        cache_put(_cache_key(message, request.mode), request.mode, reply)
    return ChatResponse(reply=reply, mode=request.mode, intent=understanding.get("intent"), conversation_id=conversation_id, message_id=assistant_id, local=False)
