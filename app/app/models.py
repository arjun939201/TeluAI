
from typing import List, Literal
from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    mode: Literal["standard", "melimi"] = "melimi"
    history: List[ChatTurn] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    mode: str
    understanding: str = ""
    intent: str = ""
    language_audit: dict = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    service: str
    corpus_entries: int
