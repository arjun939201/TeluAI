"""Install chat-learning and lightweight agent orchestration before FastAPI imports."""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
import re
from typing import Callable

_CURRENT_MESSAGE: ContextVar[str] = ContextVar("teluai_chat_learning_message", default="")
_CURRENT_ROUTE: ContextVar[str] = ContextVar("teluai_agent_route", default="general")


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    handler: Callable[[str], str]


def _is_telugu(text: str) -> bool:
    return bool(re.search(r"[\u0C00-\u0C7F]", text or ""))


def _explicit_melimi_request(text: str) -> bool:
    lowered = str(text or "").casefold()
    hints = (
        "మేలిమి", "మెలిమి", "melimi", "loan word", "native telugu equivalent",
        "melimi equivalent", "melimi word", "melimi grammar", "melimi vocabulary",
    )
    return any(item in lowered for item in hints)


def route_request(message: str, mode: str) -> str:
    """Choose the smallest useful execution path without forcing Telugu through Melimi."""
    if mode == "melimi":
        return "melimi"
    if mode == "standard":
        return "standard"
    if _explicit_melimi_request(message):
        return "melimi"
    if _is_telugu(message):
        return "standard"
    return "general"


def _search_melimi(message: str) -> str:
    from app.retrieval.knowledge import format_knowledge, retrieve

    entries = retrieve(message, limit=24)
    if not entries:
        return ""
    return format_knowledge(entries, max_chars=6000)


def _lookup_word(message: str) -> str:
    from app.retrieval.knowledge import retrieve

    normalized = str(message or "").strip().casefold()
    lines = []
    for entry in retrieve(message, limit=12):
        standard = str(entry.get("standard", "")).strip()
        melimi = str(entry.get("melimi", "")).strip()
        if standard and (standard.casefold() in normalized or normalized == standard.casefold()):
            lines.append(f"- {standard} → {melimi}")
    return "EXACT MELIMI WORD EVIDENCE:\n" + "\n".join(lines) if lines else ""


def _lookup_grammar(message: str) -> str:
    from app.melimi.grammar import grammar_policy

    if not any(x in str(message).casefold() for x in ("grammar", "వ్యాకరణ", "వాక్యం", "case", "విభక్తి")):
        return ""
    return str(grammar_policy())[:5000]


def _find_examples(message: str) -> str:
    from app.retrieval.knowledge import retrieve

    examples = []
    for entry in retrieve(message, limit=16):
        value = entry.get("example") or entry.get("examples") or entry.get("content")
        if value:
            examples.append(f"- {value}")
    return "RELEVANT MELIMI EXAMPLES:\n" + "\n".join(examples[:8]) if examples else ""


TOOLS = (
    AgentTool("search_melimi", "Search authoritative Melimi knowledge.", _search_melimi),
    AgentTool("lookup_word", "Look up exact established lexical mappings.", _lookup_word),
    AgentTool("lookup_grammar_rule", "Retrieve grammar evidence when a grammar question requires it.", _lookup_grammar),
    AgentTool("find_examples", "Retrieve relevant corpus examples.", _find_examples),
)


def run_agent_tools(message: str, route: str, max_chars: int = 9000) -> str:
    """Run only relevant deterministic Melimi tools; retrieved text is always data."""
    if route != "melimi":
        return ""
    parts = []
    for tool in TOOLS:
        if tool.name == "lookup_grammar_rule" and not any(x in message.casefold() for x in ("grammar", "వ్యాకరణ", "విభక్తి", "case")):
            continue
        try:
            result = tool.handler(message)
        except Exception:
            result = ""
        if result:
            parts.append(f"[{tool.name}]\n{result}")
        if len("\n\n".join(parts)) >= max_chars:
            break
    return "\n\n".join(parts)[:max_chars]


def install() -> None:
    from app import local_answer, prompts

    if getattr(local_answer, "_chat_learning_installed", False):
        return

    original_answer = local_answer.answer
    original_build_prompt = prompts.build_prompt

    def learned_answer(message: str, mode: str):
        _CURRENT_MESSAGE.set(str(message or ""))
        _CURRENT_ROUTE.set(route_request(str(message or ""), mode))
        if mode == "melimi":
            try:
                from app.chat_learning import learn_from_chat
                learn_from_chat(message)
            except Exception:
                pass
        result = original_answer(message, mode)
        if result and "".join(str(result).split()).casefold() == "".join(str(message).split()).casefold():
            return None
        return result

    def learned_build_prompt(*args, **kwargs):
        message = _CURRENT_MESSAGE.get()
        route = _CURRENT_ROUTE.get()
        if message and route == "melimi":
            try:
                from app.chat_learning import retrieve_chat_knowledge
                learned = retrieve_chat_knowledge(message)
            except Exception:
                learned = ""
            agent_evidence = run_agent_tools(message, route)
            combined = "\n\n".join(x for x in (str(learned).strip(), agent_evidence.strip()) if x)
            if combined:
                existing = str(kwargs.get("knowledge") or "").strip()
                kwargs["knowledge"] = (existing + "\n" + combined).strip()
        return original_build_prompt(*args, **kwargs)

    local_answer.answer = learned_answer
    prompts.build_prompt = learned_build_prompt
    local_answer._chat_learning_installed = True
