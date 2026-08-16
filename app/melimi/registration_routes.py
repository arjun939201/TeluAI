from __future__ import annotations

from fastapi import Depends, HTTPException

from app.auth import current_user
from app.learning.service import submit_command_candidate
from app.melimi.registration import register_word


def install_routes(app):
    if getattr(app.state, "melimi_registration_installed", False):
        return

    @app.post("/melimi/register")
    async def melimi_register(payload: dict, user=Depends(current_user)):
        source = str(payload.get("word", "")).strip()
        melimi = str(payload.get("melimi_equivalent", "")).strip()
        if not source or not melimi:
            raise HTTPException(400, "Source word and Melimi equivalent are required.")
        if len(source) > 160 or len(melimi) > 160:
            raise HTTPException(400, "Word entries are limited to 160 characters per side.")

        if user.role in {"admin", "owner"}:
            try:
                result = await register_word(payload, user.id)
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
            return {"ok": True, **result}

        try:
            submission = submit_command_candidate(
                "word",
                {"source": source, "melimi": melimi},
                f"/word {source} = {melimi}",
                user.id,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"ok": True, "status": "PENDING", "candidate_id": submission.candidate_id}

    app.state.melimi_registration_installed = True
