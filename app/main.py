import os
import re
from fastapi import FastAPI, HTTPException, Depends, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.github_sync import status as github_status, GitHubSyncError
from app.models import (
    ChatRequest, ChatResponse, HealthResponse, WordRegistration,
    RegisterRequest, LoginRequest, ForgotPasswordRequest, VerifyResetCodeRequest, ResetPasswordRequest, FeedbackRequest, SettingsUpdateRequest, MemoryRequest,
)
from app.auth import current_user, require_admin, require_owner, COOKIE_NAME
from app.database import (
    init_db, create_user, authenticate, create_session, delete_session, bootstrap_owner, create_password_reset_token, verify_password_reset_code, reset_password,
    create_conversation, save_message, get_conversations, get_history, delete_conversation, get_user_settings, update_user_settings,
    add_learning_candidate, save_usage, SessionLocal, Feedback, list_candidates, review_candidate, approved_learning, remember_user_memory, recall_user_memory, cache_get, cache_put, audit_log, knowledge_version, list_users, get_user_by_id, set_user_role, set_user_active, delete_user, database_stats, list_audit_logs, language_snapshot,
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
from app.melimi.registry import audit_response, analyze_word
from app.melimi.firewall import deterministic_repair, reload_firewall
from app.melimi.registration import register_word
from app.prompts import build_prompt
from app.groq_client import call_groq_detailed
from app.response import clean_response
from app.local_answer import answer as local_answer
from app.migrations import run_migrations

app = FastAPI(title="TeluAI — Melimi Telugu AI Platform")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
def startup():
    run_migrations()

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
    target = get_user_by_id(target_id)
    if target is None:
        raise HTTPException(404, "User not found.")
    if target.id == user.id and role.lower() != "owner":
        raise HTTPException(400, "The owner cannot demote their own account.")
    if target.role == "owner" and role.lower() != "owner":
        raise HTTPException(400, "The owner cannot be demoted through this endpoint.")
    result = set_user_role(target_id, role)
    audit_log(user.id, "user.role_change", "user", str(target_id), {"old_role": target.role, "new_role": role.lower()})
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
    return {"authenticated": True, "id": user.id, "username": user.username, "email": user.email, "role": user.role}

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

@app.post("/auth/bootstrap-owner")
def auth_bootstrap_owner(user=Depends(current_user)):
    configured = os.getenv("TELUAI_OWNER_EMAIL", "").strip().lower()
    if not configured:
        raise HTTPException(503, "Owner bootstrap is not configured. Set TELUAI_OWNER_EMAIL first.")
    if user.email.lower() != configured:
        raise HTTPException(403, "This account is not the configured owner account.")
    owner, error = bootstrap_owner(configured)
    if error:
        raise HTTPException(400, error)
    audit_log(owner.id, "owner.bootstrap", "user", str(owner.id), {"email": owner.email})
    return {"ok": True, "id": owner.id, "username": owner.username, "role": owner.role}

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
    return {"authenticated": True, "id": user.id, "username": user.username, "email": user.email, "role": user.role}

@app.post("/auth/forgot-password")
def auth_forgot_password(payload: ForgotPasswordRequest):
    email = payload.email.strip().lower()
    code = create_password_reset_token(email)

    # Do not reveal whether an account exists. If SMTP is not configured,
    # fail safely because the user cannot receive the required verification code.
    if code:
        try:
            import smtplib
            from email.message import EmailMessage

            host = os.getenv("SMTP_HOST", "").strip()
            port = int(os.getenv("SMTP_PORT", "587"))
            username = os.getenv("SMTP_USERNAME", "").strip()
            password = os.getenv("SMTP_PASSWORD", "")
            sender = os.getenv("SMTP_FROM", username).strip()

            if not (host and username and password and sender):
                raise RuntimeError("SMTP is not configured")

            msg = EmailMessage()
            msg["Subject"] = "TeluAI password reset code"
            msg["From"] = sender
            msg["To"] = email
            msg.set_content(
                f"Your TeluAI password reset code is: {code}\n\n"
                "This code expires in 10 minutes.\n"
                "If you did not request a password reset, ignore this email."
            )
            with smtplib.SMTP(host, port, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(username, password)
                smtp.send_message(msg)
        except Exception:
            # Never return the reset code to the browser.
            # Avoid account enumeration while making delivery failure explicit.
            raise HTTPException(503, "Password reset email service is not available. Please try again later.")

    return {
        "ok": True,
        "message": "If an account with that email exists, a verification code has been sent."
    }


@app.post("/auth/verify-reset-code")
def auth_verify_reset_code(payload: VerifyResetCodeRequest):
    reset_token = verify_password_reset_code(payload.email.strip().lower(), payload.code.strip())
    if not reset_token:
        raise HTTPException(400, "The verification code is invalid or expired.")
    return {"ok": True, "reset_token": reset_token}


@app.post("/auth/reset-password")
def auth_reset_password(payload: ResetPasswordRequest, response: Response):
    user_id = reset_password(payload.token, payload.password)
    if not user_id:
        raise HTTPException(400, "The reset session is invalid or expired.")

    # Password reset revokes old sessions. Create a fresh authenticated session
    # so the user can continue directly to the website after resetting.
    session_token = create_session(user_id, settings.session_days)
    response.set_cookie(
        COOKIE_NAME,
        session_token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.session_days * 86400,
    )
    return {"ok": True, "message": "Password reset successfully.", "authenticated": True}

@app.post("/auth/logout")
def auth_logout(response: Response, teluai_session: str | None = Cookie(default=None)):
    delete_session(teluai_session)
    response.delete_cookie(COOKIE_NAME)
    return {"authenticated": False}

@app.get("/conversations")
def conversations(user=Depends(current_user)):
    return {"conversations": get_conversations(user.id)}

@app.get("/conversations/{conversation_id}")
def conversation(conversation_id: str, user=Depends(current_user)):
    try:
        return {"conversation_id": conversation_id, "messages": get_history(user.id, conversation_id)}
    except ValueError as exc:
        raise HTTPException(404, str(exc))

@app.delete("/conversations/{conversation_id}")
def remove_conversation(conversation_id: str, user=Depends(current_user)):
    if not delete_conversation(user.id, conversation_id):
        raise HTTPException(404, "Conversation not found.")
    audit_log(user.id, "conversation.delete", "conversation", conversation_id)
    return {"ok": True}

@app.get("/melimi/subject")
def melimi_subject():
    return subject_inventory()

@app.get("/melimi/word/{word}")
def melimi_word(word: str):
    return analyze_word(word)

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
    db_name = "postgresql" if settings.database_url.startswith(("postgres://", "postgresql://")) else "sqlite-fallback"
    return HealthResponse(status="ok", service="TeluAI", vocabulary_entries=len(load_vocabulary()), database=db_name)


def _extract_learning(message: str):
    # Only explicit user teaching is captured as a candidate. It is never
    # promoted automatically to authoritative Melimi knowledge.
    patterns = [
        re.compile(r"^\s*(.+?)\s*(?:→|->|=)\s*(.+?)\s*$"),
        re.compile(r"^\s*(.+?)\s+అంటే\s+(.+?)\s*$"),
    ]
    for pattern in patterns:
        m = pattern.match(message)
        if m:
            left, right = m.group(1).strip(), m.group(2).strip()
            if left and right and len(left) < 120 and len(right) < 120:
                return {"source_root": left, "melimi_root": right}
    return None

def _cache_key(message: str, mode: str) -> str:
    import hashlib
    normalized = re.sub(r"\s+", " ", message.strip().lower())
    return hashlib.sha256(f"{mode}\n{knowledge_version()}\n{normalized}".encode("utf-8")).hexdigest()

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user=Depends(current_user)):
    message = request.message.strip()
    if not message:
        raise HTTPException(400, "Message cannot be empty.")

    # Prefer persisted conversation history when the client supplies a chat id.
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

    # Exact deterministic/cacheable answers can avoid Groq entirely. Cache only
    # standalone user queries; conversation-specific answers remain contextual.
    if settings.cache_enabled and not request.conversation_id:
        cached = cache_get(_cache_key(message, request.mode), request.mode)
        if cached:
            user_msg_id = save_message(user.id, conversation_id, "user", message)
            assistant_id = save_message(user.id, conversation_id, "assistant", cached, model="cache")
            return ChatResponse(reply=cached, mode=request.mode, intent="cached", conversation_id=conversation_id, message_id=assistant_id, local=True)

    # Explicit teaching is durable as a candidate, but not automatically global authority.
    candidate = _extract_learning(message)
    if candidate:
        add_learning_candidate(user.id, "ROOT", message, candidate)

    local = local_answer(message, request.mode)
    if local is not None:
        user_msg_id = save_message(user.id, conversation_id, "user", message)
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
    explicit_memory = extract_memory_candidates(history, settings.max_memory_items)
    for item in explicit_memory:
        text = str(item.get("text", "")).strip()
        if text:
            remember_user_memory(user.id, "fact_" + str(abs(hash(text)))[:16], text)
    persistent_memory = recall_user_memory(user.id)
    if persistent_memory:
        memory += "\nPERSISTENT USER MEMORY (use only when relevant):\n" + "\n".join(f"- {x['value']}" for x in persistent_memory)
    approved = approved_learning()[-24:]
    approved_context = "\n".join(
        f"- {x.get('standard_root','')} → {x.get('melimi_root','')}"
        for x in approved if x.get('standard_root') and x.get('melimi_root')
    )

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
        knowledge=("APPROVED CHAT-LEARNED ROOT MAPPINGS:\n" + approved_context) if approved_context and request.mode == "melimi" else "",
    )

    # Last-resort context cap protects Groq's TPM/request-size limits.
    prompt = prompt[:settings.max_context_chars]
    try:
        result = await call_groq_detailed(prompt, history, message)
    except RuntimeError as exc:
        save_usage(user.id, settings.groq_model, None, None, "error")
        # If Groq is unavailable/rate-limited, deterministic Melimi conversion
        # can still answer simple conversion-style turns without spending a
        # retry or exposing a raw provider failure. Complex questions still
        # return the provider error.
        if request.mode == "melimi":
            from app.linguistics.normalizer import normalize_roman_telugu
            from app.melimi.root_morphology import convert_text
            normalized = normalize_roman_telugu(message)
            converted = convert_text(normalized)
            if converted != normalized and len(normalized) <= 500:
                user_msg_id = save_message(user.id, conversation_id, "user", message)
                assistant_id = save_message(user.id, conversation_id, "assistant", converted, model="local-melimi-fallback")
                return ChatResponse(reply=converted, mode=request.mode, intent="local_conversion_fallback", conversation_id=conversation_id, message_id=assistant_id, local=True)
        raise HTTPException(502, str(exc))
    except Exception:
        save_usage(user.id, settings.groq_model, None, None, "error")
        raise HTTPException(502, "AI request failed. Please try again.")

    reply = clean_response(result["answer"])
    if request.mode == "melimi":
        reply = deterministic_repair(reply)
    if not reply:
        raise HTTPException(502, "AI returned an empty response.")

    save_usage(user.id, result.get("model"), result.get("input_tokens"), result.get("output_tokens"), "ok")
    save_message(user.id, conversation_id, "user", message)
    assistant_id = save_message(
        user.id, conversation_id, "assistant", reply,
        model=result.get("model"), input_tokens=result.get("input_tokens"),
        output_tokens=result.get("output_tokens"), latency_ms=result.get("latency_ms")
    )

    audit = audit_melimi(reply) if request.mode == "melimi" else {}
    if settings.cache_enabled and not request.conversation_id and len(reply) >= settings.cache_min_chars:
        cache_put(_cache_key(message, request.mode), request.mode, reply)
    return ChatResponse(
        reply=reply,
        mode=request.mode,
        intent=understanding["intent"],
        conversation_id=conversation_id,
        message_id=assistant_id,
        understanding={"meaning": understanding["meaning"], "confidence": understanding["confidence"], "linguistics": linguistic, "response_plan": plan},
        language_audit=audit,
        word_audit=audit_response(reply) if request.mode == "melimi" else [],
    )
