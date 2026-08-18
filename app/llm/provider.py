from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol


class LLMProvider(Protocol):
    async def complete(self, system_prompt: str, history: list[dict], user_message: str) -> dict[str, Any]: ...
    def stream(self, system_prompt: str, history: list[dict], user_message: str) -> AsyncIterator[dict[str, Any]]: ...


class GroqProvider:
    """Provider adapter. Application code depends on this boundary, not Groq HTTP details."""

    async def complete(self, system_prompt: str, history: list[dict], user_message: str) -> dict[str, Any]:
        from app.groq_client import call_groq_detailed
        return await call_groq_detailed(system_prompt, history, user_message)

    def stream(self, system_prompt: str, history: list[dict], user_message: str) -> AsyncIterator[dict[str, Any]]:
        from app.groq_client import stream_groq
        return stream_groq(system_prompt, history, user_message)


_PROVIDER: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = GroqProvider()
    return _PROVIDER


def set_llm_provider(provider: LLMProvider | None) -> None:
    global _PROVIDER
    _PROVIDER = provider
