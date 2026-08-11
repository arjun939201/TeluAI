from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's message in Telugu")
    mode: Literal["standard", "melimi"] = "standard"
    history: List[ChatTurn] = Field(default_factory=list, description="Prior turns, oldest first")


class ChatResponse(BaseModel):
    reply: str
    mode: str
    matched_vocab: List[str] = Field(
        default_factory=list, description="Vocab entries that were injected into the prompt, for debugging"
    )
