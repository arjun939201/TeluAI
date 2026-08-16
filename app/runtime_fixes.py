from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, Response
from app import database as db
from app.auth import COOKIE_NAME, current_user
from app.config import settings
from app.models import CredentialUpdateRequest, GuestRegisterRequest


def _remove_routes(app, path: str, methods: set[str]) -> None:
    app.router.routes[:] = [
        route for route in app.router.routes
        if not (getattr(route, "path", None) == path and set(getattr(route, "methods", set())) & methods)
    ]


def install(app) -> None:
    if getattr(app.state, "runtime_fixes_installed", False):
        return

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
            user = db.create_guest_user(payload.username.strip(), payload.password)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        token = db.create_session(user.id)
        response.set_cookie(
            COOKIE_NAME,
            token,
            httponly=True,
            samesite="lax",
            secure=settings.cookie_secure,
            max_age=settings.session_days * 86400,
        )
        return {"authenticated": True, "id": user.id, "username": user.username, "email": None, "role": "guest"}

    _remove_routes(app, "/auth/me", {"GET"})

    @app.get("/auth/me")
    def auth_me_fixed(user=Depends(current_user)):
        return {
            "authenticated": True,
            "id": user.id,
            "username": user.username,
            "email": None if user.role == "guest" else user.email,
            "role": user.role,
        }

    @app.put("/me/credentials")
    def credentials_fixed(payload: CredentialUpdateRequest, user=Depends(current_user)):
        try:
            updated = db.update_credentials(user.id, payload.current_password, payload.username, payload.new_password)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        db.audit_log(user.id, "account.credentials_change", "user", str(user.id), {
            "username_changed": bool(payload.username),
            "password_changed": bool(payload.new_password),
        })
        return {"ok": True, "username": updated.username, "role": updated.role}

    app.state.runtime_fixes_installed = True
