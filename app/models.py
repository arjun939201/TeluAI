from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's message in Telugu")
    mode: Literal["standard", "melimi"] = "melimi"
    history: List[ChatTurn] = Field(default_factory=list, description="Prior turns, oldest first")


class ChatResponse(BaseModel):
    reply: str
    mode: str
    matched_vocab: List[str] = Field(
        default_factory=list, description="Vocab entries that were injected into the prompt, for debugging"
    )
    matched_grammar_suffixes: List[str] = Field(
        default_factory=list, description="Suffix rules that were injected into the prompt, for debugging"
    )
    matched_grammar_prefixes: List[str] = Field(
        default_factory=list, description="Prefix rules that were injected into the prompt, for debugging"
    )
    root_candidates: List[str] = Field(
        default_factory=list,
        description="Melimi-looking tokens in the user's message that aren't fixed vocabulary "
                     "entries, so were treated as roots for grammar-driven derivation",
    )


class LearnVocabRequest(BaseModel):
    standard: str = Field(..., min_length=1)
    melimi: str = Field(..., min_length=1)
    note: str = ""


class LearnGrammarRequest(BaseModel):
    kind: Literal["prefixes", "suffixes", "reduplication"]
    element: str = Field(..., min_length=1, description="The suffix/prefix/pattern itself")
    meaning: str = Field(..., min_length=1)
    examples: List[str] = Field(default_factory=list)
    note: str = ""


class LearnPhraseRequest(BaseModel):
    standard: str = Field(..., min_length=1)
    melimi: str = Field(..., min_length=1)


class LearnResponse(BaseModel):
    added: bool
    message: str
