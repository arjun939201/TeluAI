"""Optional chat-learning helpers without implicit authority mutation.

Ordinary conversation is runtime input, not a language-authority publication
channel. Authoritative Melimi changes must arrive through explicit language
commands and the reviewed/publication workflow. This module therefore keeps
the advisory tool helpers available but deliberately does not monkey-patch
FastAPI, ``local_answer`` or prompt construction.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable


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
        "morphology", "morphological", "derivative", "derivation", "inflection",
        "విభక్తి", "పదనిర్మాణం", "రూపం", "వ్యుత్పత్తి",
    )
    return any(item in lowered for item in hints)


def route_request(message: str, mode: str) -> str:
    """Choose the smallest useful execution path without mutating authority."""
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
    return format_knowledge(entries, max_chars=6000) if entries else ""


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
    if not any(x in str(message).casefold() for x in ("grammar", "వ్యాకరణ", "వాక్యం", "case", "విభక్తి", "morphology", "derivation", "inflection")):
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


def _ai_linguistics(message: str) -> str:
    from app.melimi.ai_linguistics import analyze, format_for_agent
    task = (
        "Analyze the supplied word/phrase using the authoritative roots and grammar. "
        "Resolve root, POS, inflectional operations and derivational operations; generate "
        "supported Melimi derivatives and inflections where the supplied grammar licenses them. "
        "Use general linguistic knowledge only for reasoning, never as authority over the corpus."
    )
    return "AI LINGUISTICS (ADVISORY; NOT MASTER):\n" + format_for_agent(analyze(message, task))


TOOLS = (
    AgentTool("search_melimi", "Search authoritative Melimi knowledge.", _search_melimi),
    AgentTool("lookup_word", "Look up exact established lexical mappings.", _lookup_word),
    AgentTool("lookup_grammar_rule", "Retrieve grammar evidence for grammar/morphology questions.", _lookup_grammar),
    AgentTool("find_examples", "Retrieve relevant corpus examples.", _find_examples),
    AgentTool("ai_linguistics", "Use general AI linguistic knowledge only as advisory analysis.", _ai_linguistics),
)


def run_agent_tools(message: str, route: str, max_chars: int = 12000) -> str:
    """Run advisory Melimi tools; their output is never published automatically."""
    if route != "melimi":
        return ""
    parts = []
    for tool in TOOLS:
        if tool.name == "lookup_grammar_rule" and not any(x in message.casefold() for x in ("grammar", "వ్యాకరణ", "విభక్తి", "case", "morphology", "derivation", "inflection")):
            continue
        if tool.name == "ai_linguistics" and not any(x in message.casefold() for x in ("morphology", "morphological", "derivative", "derivation", "inflection", "విభక్తి", "పదనిర్మాణం", "రూపం", "వ్యుత్పత్తి", "grammar", "వ్యాకరణ", "word")):
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
    """Compatibility hook retained without import-time monkey patching.

    Runtime composition is explicit in ``app.server``. Ordinary conversation
    must never call ``learn_from_chat`` or mutate MASTER language data.
    """
    return None
