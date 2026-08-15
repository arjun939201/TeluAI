
from typing import Dict, List, Literal
from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    mode: Literal["standard", "melimi"] = "standard"
    history: List[ChatTurn] = Field(default_factory=list)
    # Optional stable client-generated id (e.g. a UUID kept in the browser).
    # When provided and PostgreSQL is configured, TeluAI remembers a small
    # set of explicit user facts (name, stated likes/dislikes) across
    # sessions instead of relying solely on client-sent history.
    user_id: str = Field(default="", max_length=128)


class WordRegistration(BaseModel):
    word: str
    melimi_equivalent: str
    root: str = ""
    meaning: str = ""
    part_of_speech: str = ""
    formation: str = ""


class ChatResponse(BaseModel):
    reply: str
    mode: str
    intent: str
    understanding: Dict = Field(default_factory=dict)
    language_audit: Dict = Field(default_factory=dict)
    word_audit: List[Dict] = Field(default_factory=list)
    # Where the reply came from: "deterministic" (Tier 0, local, zero Groq),
    # "cache" (a previous Groq answer for this exact question), or "groq".
    source: str = "groq"


class HealthResponse(BaseModel):
    status: str
    service: str
    vocabulary_entries: int
