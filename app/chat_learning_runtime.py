"""Install chat-learning hooks before FastAPI imports its endpoint helpers.

Ordinary declarative chat can teach the language system. The hook stores the
message first, then lets the existing local-answer/prompt pipeline continue.
No conversation is replaced or recreated by the learning layer.
"""
from __future__ import annotations

from contextvars import ContextVar

_CURRENT_MESSAGE: ContextVar[str] = ContextVar("teluai_chat_learning_message", default="")


def install() -> None:
    from app import local_answer, prompts

    if getattr(local_answer, "_chat_learning_installed", False):
        return

    original_answer = local_answer.answer
    original_build_prompt = prompts.build_prompt

    def learned_answer(message: str, mode: str):
        token = _CURRENT_MESSAGE.set(str(message or ""))
        try:
            try:
                from app.chat_learning import learn_from_chat
                learn_from_chat(message)
            except Exception:
                pass
            result = original_answer(message, mode)
            if result and "".join(str(result).split()).casefold() == "".join(str(message).split()).casefold():
                return None
            return result
        finally:
            _CURRENT_MESSAGE.reset(token)

    def learned_build_prompt(*args, **kwargs):
        message = _CURRENT_MESSAGE.get()
        if message:
            try:
                from app.chat_learning import retrieve_chat_knowledge
                learned = retrieve_chat_knowledge(message)
                if learned:
                    existing = str(kwargs.get("knowledge") or "").strip()
                    kwargs["knowledge"] = (existing + "\n" + learned).strip()
            except Exception:
                pass
        return original_build_prompt(*args, **kwargs)

    local_answer.answer = learned_answer
    prompts.build_prompt = learned_build_prompt
    local_answer._chat_learning_installed = True
