from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, EmailStr

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=12000)
    mode: Literal["standard", "melimi"] = "melimi"
    history: List[ChatTurn] = Field(default_factory=list)
    conversation_id: Optional[str] = None

class WordRegistration(BaseModel):
    word: str
    melimi_equivalent: str
    root: str = ""
    meaning: str = ""
    part_of_speech: str = ""
    formation: str = ""

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)

class FeedbackRequest(BaseModel):
    message_id: int | None = None
    rating: int = Field(ge=1, le=5)
    text: str = Field(default="", max_length=4000)

class ChatResponse(BaseModel):
    reply: str
    mode: str
    intent: str
    conversation_id: str | None = None
    message_id: int | None = None
    understanding: Dict = Field(default_factory=dict)
    language_audit: Dict = Field(default_factory=dict)
    word_audit: List[Dict] = Field(default_factory=list)
    local: bool = False

class HealthResponse(BaseModel):
    status: str
    service: str
    vocabulary_entries: int
    database: str

class SettingsUpdateRequest(BaseModel):
    preferred_mode: Literal["standard", "melimi"] = "melimi"
    response_length: Literal["short", "normal", "long"] = "normal"
    memory_enabled: bool = True

class MemoryRequest(BaseModel):
    key: str = Field(min_length=1, max_length=160)
    value: str = Field(min_length=1, max_length=4000)
