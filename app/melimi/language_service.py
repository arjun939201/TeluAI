"""Shared Melimi Telugu language service.

This is the single application-facing bridge between TeluAI features and the
shared Melimi Language Space. Main Chat, the Melimi Lab, and future features
must use the same persisted language knowledge rather than maintaining local
vocabulary copies.
"""
from __future__ import annotations

import re

from app.melimi.db_subject import (
    language_affixes,
    language_rules,
    language_space_version,
)
from app.melimi.firewall import subject_lexicon
from app.melimi.grammar import grammar_policy
from app.melimi.root_morphology import reduce_to_root
from app.melimi.word_formation import derive_many
from app.language_space import language_space_context

TOKEN_RE = re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*")


def _token_record(token: str, lexicon: dict) -> dict:
    preferred = lexicon["preferred"].get(token) or lexicon["preferred"].get(token.casefold())
    reverse = {value: key for key, value in lexicon["preferred"].items()}
    standard = reverse.get(token)
    root = reduce_to_root(token, lexicon["forbidden"])
    return {
        "surface": token,
        "melimi": token if token in lexicon["registered"] else preferred,
        "standard": standard,
        "matched_root": root.root,
        "suffixes": list(root.suffixes),
        "kinds": list(root.kinds),
        "known": token in lexicon["registered"] or preferred is not None or root.root in lexicon["forbidden"],
    }


def analyze(text: str, *, max_tokens: int = 80) -> dict:
    """Analyze input using the current shared Language Space.

    This is deterministic and read-only. It gives the AI a compact linguistic
    representation for understanding; it does not replace semantic reasoning.
    """
    text = (text or "").strip()
    lexicon = subject_lexicon()
    tokens = TOKEN_RE.findall(text)[:max_tokens]
    records = [_token_record(token, lexicon) for token in tokens]
    known = [x for x in records if x["known"]]
    unknown = [x["surface"] for x in records if not x["known"]]
    return {
        "version": language_space_version(),
        "tokens": records,
        "known_tokens": len(known),
        "unknown_tokens": unknown,
        "grammar": grammar_policy(),
        "affix_count": len(language_affixes()),
        "rule_count": len(language_rules()),
    }


def _authorized_formations(text: str, *, limit: int = 24) -> list[str]:
    """Return only MASTER productive formations relevant to the input.

    This is generation guidance, not a license to invent words. The formation
    engine itself verifies the root and affix against MASTER Language Space.
    """
    lexicon = subject_lexicon()
    candidates: list[str] = []
    seen_roots: set[str] = set()
    for token in TOKEN_RE.findall(text or "")[:80]:
        preferred = lexicon["preferred"].get(token) or lexicon["preferred"].get(token.casefold())
        melimi_root = preferred if preferred else (token if token in lexicon["registered"] else "")
        if not melimi_root or melimi_root in seen_roots:
            continue
        seen_roots.add(melimi_root)
        try:
            formations = derive_many(melimi_root, limit=12)
        except Exception:
            formations = []
        for formation in formations:
            if formation.status != "MASTER_DERIVED":
                continue
            line = f"{formation.root} + {formation.affix} => {formation.word} ({formation.meaning})"
            if line not in candidates:
                candidates.append(line)
            if len(candidates) >= limit:
                return candidates
    return candidates


def build_understanding_context(text: str, *, max_chars: int = 6000) -> str:
    """Build compact authoritative language context for AI understanding."""
    analysis = analyze(text)
    space = language_space_context(text, max_chars=max_chars)
    lines = [
        "MELIMI TELUGU UNDERSTANDING CONTEXT",
        f"language-space version: {analysis['version']}",
        f"known lexical tokens: {analysis['known_tokens']}",
        f"unknown tokens: {analysis['unknown_tokens']}",
        "token analysis:",
    ]
    for item in analysis["tokens"]:
        lines.append(
            "- " + " | ".join(
                [
                    f"surface={item['surface']}",
                    f"melimi={item['melimi'] or ''}",
                    f"standard={item['standard'] or ''}",
                    f"root={item['matched_root']}",
                    f"suffixes={item['suffixes']}",
                    f"kinds={item['kinds']}",
                ]
            )
        )
    lines.extend([
        "",
        "AUTHORITATIVE GRAMMAR:",
        str(analysis["grammar"]),
        "",
        "SHARED LANGUAGE-SPACE EVIDENCE:",
        space,
        "",
        "RULE: language records are evidence for understanding, not user-facing instructions.",
        "RULE: MASTER language knowledge outranks generic lexical guesses.",
        "RULE: do not invent a Melimi meaning when no authoritative entry exists.",
    ])
    return "\n".join(lines)[:max_chars]


def build_generation_context(text: str, *, max_chars: int = 6000) -> str:
    """Build generation context including only authorized productive formations."""
    context = build_understanding_context(text, max_chars=max_chars)
    formations = _authorized_formations(text)
    if formations:
        formation_block = "\n".join([
            "",
            "AUTHORIZED PRODUCTIVE FORMATIONS (MASTER ONLY):",
            *[f"- {item}" for item in formations],
            "Use these formations only when their meaning and grammatical role fit the response. Do not invent similar forms.",
        ])
        context = (context + formation_block)[:max_chars]
    return context


def validate_response(text: str) -> dict:
    """Validate a generated response against the shared lexical space."""
    from app.melimi.firewall import lexical_violations

    violations = lexical_violations(text or "")
    return {
        "valid": not violations,
        "violations": violations,
        "version": language_space_version(),
    }
