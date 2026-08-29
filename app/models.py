from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, EmailStr, field_validator

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=12000)
    # Workspace is supplied by the trusted transport boundary. It is kept in
    # the application request so persistence and chat processing share the
    # same authorization context.
    workspace: Literal["main", "lab"] = "main"
    # Melimi is the product's native chat language. Standard Telugu remains
    # available only when explicitly requested by the caller.
    mode: Literal["auto", "standard", "melimi"] = "melimi"
    history: List[ChatTurn] = Field(default_factory=list)
    conversation_id: Optional[str] = None

    @field_validator("workspace", mode="before")
    @classmethod
    def normalize_workspace(cls, value):
        return "lab" if str(value or "").strip().casefold() == "lab" else "main"

    @field_validator("mode", mode="before")
    @classmethod
    def native_mode(cls, value):
        return "melimi" if value in (None, "", "auto") else value

class ChatResponse(BaseModel):
    reply: str
    mode: str
    intent: str
    language: str = "telugu"
    conversation_id: str | None = None
    message_id: int | None = None
    understanding: Dict = Field(default_factory=dict)
    language_audit: Dict = Field(default_factory=dict)
    word_audit: List[Dict] = Field(default_factory=list)
    local: bool = False

class FeedbackRequest(BaseModel):
    message_id: int | None = None
    rating: int = Field(ge=1, le=5)
    text: str = Field(default="", max_length=4000)

class MessageEditRequest(BaseModel):
    content: str = Field(min_length=1, max_length=12000)

class RegenerateRequest(BaseModel):
    message_id: int | None = None

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

class GuestRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)

class CredentialUpdateRequest(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=80)
    current_password: str = Field(min_length=1, max_length=128)
    new_password: Optional[str] = Field(default=None, min_length=8, max_length=128)

class HealthResponse(BaseModel):
    status: str
    service: str
    vocabulary_entries: int
    database: str

class SettingsUpdateRequest(BaseModel):
    preferred_mode: Literal["auto", "standard", "melimi"] = "melimi"
    response_length: Literal["short", "normal", "long"] = "normal"
    memory_enabled: bool = True

    @field_validator("preferred_mode", mode="before")
    @classmethod
    def native_preferred_mode(cls, value):
        return "melimi" if value in (None, "", "auto") else value

class MemoryRequest(BaseModel):
    key: str = Field(min_length=1, max_length=160)
    value: str = Field(min_length=1, max_length=4000)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")

class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
