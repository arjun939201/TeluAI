"""HTTP API for screenshot/chat moderation."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.moderation import moderate_screen_text, moderate_text

router = APIRouter(prefix="/moderation", tags=["moderation"])


class ModerationMessage(BaseModel):
    username: str = Field(default="", max_length=200)
    text: str = Field(min_length=1, max_length=12000)


class ModerationRequest(BaseModel):
    messages: list[ModerationMessage] = Field(min_length=1, max_length=200)


@router.post("/check")
def check_message(payload: ModerationMessage) -> dict[str, Any]:
    return moderate_screen_text([payload.model_dump()])


@router.post("/screen-text")
def check_screen_text(payload: ModerationRequest) -> dict[str, Any]:
    return moderate_screen_text([item.model_dump() for item in payload.messages])
