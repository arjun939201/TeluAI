"""Install chat-learning hooks before FastAPI imports its endpoint helpers.

This keeps the existing request flow intact while making ordinary chat a
language-learning surface: declarative content is learned before the local
answer path, and relevant learned evidence is injected into the existing
prompt builder. Conversation messages are never replaced or re-created.
"""
from __future__ import annotations


def install() -> None:
    from app import local_answer, prompts

    if getattr(local_answer, "_chat_learning_installed", False):
        return

    original_answer = local_answer.answer
    original_build_prompt = prompts.build_prompt

    def learned_answer(message: str, mode: str):
        try:
            from app.chat_learning import learn_from_chat
            learn_from_chat(message)
        except Exception:
            # Language learning must never take the chat service down.
            pass
        result = original_answer(message, mode)
        # A just-shared content item must be answered conversationally rather
        # than echoed as a dictionary-style local answer.
        if result and "".join(str(result).split()).casefold() == "".join(str(message).split()).casefold():
            return None
        return result

    def learned_build_prompt(*args, **kwargs):
        message = str(kwargs.get("knowledge_query") or "")
        if not message:
            # main.py passes the current user message to the LLM separately;
            # recover it from the optional keyword supplied by this hook.
            message = str(kwargs.get("user_message") or "")
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

    # The endpoint imports these functions after app/__init__.py runs, so the
    # patched module attributes become the functions used by the endpoint.
    local_answer.answer = learned_answer
    prompts.build_prompt = learned_build_prompt
    local_answer._chat_learning_installed = True
