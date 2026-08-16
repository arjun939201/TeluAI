from __future__ import annotations

import inspect
import os

from fastapi import Cookie, Depends, File, HTTPException, Response, UploadFile
from app import database as db
from app.account_service import create_guest_user, update_credentials
from app.auth import COOKIE_NAME, current_user
from app.chat_commands import parse_chat_command
from app.chat_learning import learn_explicit_teaching
from app.config import settings
from app.melimi import content_store
from app.models import ChatRequest, ChatResponse, CredentialUpdateRequest, GuestRegisterRequest


def _remove_routes(app, path: str, methods: set[str]) -> None:
    app.router.routes[:] = [
        route for route in app.router.routes
        if not (getattr(route, "path", None) == path and set(getattr(route, "methods", set())) & methods)
    ]


def _install_chat_command_gateway(app) -> None:
    routes = [r for r in app.router.routes if getattr(r, "path", None) == "/chat" and "POST" in getattr(r, "methods", set())]
    if not routes:
        return
    original_chat = routes[0].endpoint
    globals_map = getattr(original_chat, "__globals__", {})
    if "_extract_learning" in globals_map:
        globals_map["_extract_learning"] = lambda message: None
    _remove_routes(app, "/chat", {"POST"})

    @app.post("/chat", response_model=ChatResponse)
    async def chat_gateway(request: ChatRequest, user=Depends(current_user)):
        message = request.message.strip()
        try:
            command = parse_chat_command(message)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        if command is None:
            result = original_chat(request, user)
            return await result if inspect.isawaitable(result) else result

        if request.conversation_id:
            try:
                db.get_history(user.id, request.conversation_id, limit=1)
            except ValueError as exc:
                raise HTTPException(404, str(exc))
            conversation_id = request.conversation_id
        else:
            conversation_id = db.create_conversation(user.id, message[:70], request.mode)
        db.save_message(user.id, conversation_id, "user", message)
        try:
            learned = learn_explicit_teaching(message, user.id)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        if command.kind == "word":
            source = command.payload["standard_or_source"]
            target = command.payload["melimi"]
            reply = f"✓ పలుకు చేర్చబడింది\n{source} → {target}\nఇది ఇప్పుడు మేలిమి భాషా నిలయంలో అందుబాటులో ఉంది."
        else:
            reply = "✓ కంటెంట్ చేర్చబడింది\nఇది ఇప్పుడు మేలిమి భాషా నిలయంలో అందుబాటులో ఉంది."
        assistant_id = db.save_message(user.id, conversation_id, "assistant", reply, model="language-command")
        db.audit_log(user.id, f"language.command.{command.kind}", "language_entry", str(assistant_id), {"learned": learned})
        return ChatResponse(reply=reply, mode=request.mode, intent=f"language_{command.kind}_entry", conversation_id=conversation_id, message_id=assistant_id, local=True)


def _install_direct_content_routes(app) -> None:
    _remove_routes(app, "/melimi/content", {"POST"})
    _remove_routes(app, "/melimi/content/upload", {"POST"})

    @app.post("/melimi/content")
    async def direct_content(payload: dict, user=Depends(current_user)):
        title = str(payload.get("title", "")).strip()
        content = str(payload.get("content", "")).strip()
        if not content:
            raise HTTPException(400, "Content is required.")
        if len(content) > 50000:
            raise HTTPException(400, "Content is too large.")
        try:
            result = content_store.submit_content(user.id, title, content, approved=True)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        db.audit_log(user.id, "language.content.create", "language_content", title or "pasted-content", {"chars": len(content)})
        return {"ok": True, **result, "status": "MASTER"}

    @app.post("/melimi/content/upload")
    async def direct_content_upload(file: UploadFile = File(...), user=Depends(current_user)):
        name = (file.filename or "").strip()
        ext = os.path.splitext(name.lower())[1]
        if ext not in {".txt", ".md", ".json", ".zip"}:
            raise HTTPException(400, "Upload a .txt, .md, .json, or .zip language-content file.")
        raw = await file.read()
        if len(raw) > 10 * 1024 * 1024:
            raise HTTPException(413, "Language content file is too large. Maximum is 10 MB.")
        try:
            result = content_store.ingest_language_package(name, raw, approved=True, actor_user_id=user.id)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        except Exception as exc:
            raise HTTPException(400, f"Could not import language content: {exc}")
        db.audit_log(user.id, "language.content_upload", "language_package", name, {"bytes": len(raw), "documents": result.get("documents", 0)})
        return {"ok": True, **result, "status": "MASTER"}


def install(app) -> None:
    if getattr(app.state, "runtime_fixes_installed", False):
        return

    _install_chat_command_gateway(app)
    _install_direct_content_routes(app)

    _remove_routes(app, "/conversations/{conversation_id}", {"GET", "DELETE"})

    @app.get("/conversations/{conversation_id}")
    def conversation_detail_fixed(conversation_id: str, user=Depends(current_user)):
        try:
            return {"conversation_id": conversation_id, "messages": db.get_history(user.id, conversation_id, limit=100)}
        except ValueError as exc:
            raise HTTPException(404, str(exc))

    @app.delete("/conversations/{conversation_id}")
    def conversation_delete_fixed(conversation_id: str, user=Depends(current_user)):
        try:
            db.delete_conversation(user.id, conversation_id)
            return {"ok": True}
        except ValueError as exc:
            raise HTTPException(404, str(exc))

    _remove_routes(app, "/auth/logout", {"GET", "POST"})

    def logout_fixed(response: Response, session: str | None = Cookie(default=None, alias=COOKIE_NAME)):
        if session:
            db.delete_session(session)
        response.delete_cookie(COOKIE_NAME)
        return {"ok": True}

    app.add_api_route("/auth/logout", logout_fixed, methods=["POST", "GET"])

    @app.post("/auth/guest")
    def guest_register(payload: GuestRegisterRequest, response: Response):
        try:
            user = create_guest_user(payload.username, payload.password)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        token = db.create_session(user.id, settings.session_days)
        response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", secure=settings.cookie_secure, max_age=settings.session_days * 86400)
        return {"authenticated": True, "id": user.id, "username": user.username, "email": None, "role": "guest"}

    _remove_routes(app, "/auth/me", {"GET"})

    @app.get("/auth/me")
    def auth_me_fixed(user=Depends(current_user)):
        return {"authenticated": True, "id": user.id, "username": user.username, "email": None if user.role == "guest" else user.email, "role": user.role}

    _remove_routes(app, "/me/credentials", {"PUT"})

    @app.put("/me/credentials")
    def credentials_fixed(payload: CredentialUpdateRequest, user=Depends(current_user)):
        try:
            updated = update_credentials(user.id, payload.current_password, payload.username, payload.new_password)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        db.audit_log(user.id, "account.credentials_change", "user", str(user.id), {"username_changed": bool(payload.username), "password_changed": bool(payload.new_password)})
        return {"ok": True, "username": updated.username, "role": updated.role}

    app.state.runtime_fixes_installed = True
