
from typing import Dict, List, Literal
from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    mode: Literal["standard", "melimi"] = "standard"
    history: List[ChatTurn] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    mode: str
    intent: str
    understanding: Dict = Field(default_factory=dict)
    language_audit: Dict = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    service: str
    vocabulary_entries: int
