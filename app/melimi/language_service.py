"""Shared Melimi Telugu language service.

This is the single application-facing bridge between TeluAI features and the
shared Melimi Language Space. Main Chat, the Melimi Lab, and future features
must use the same persisted language knowledge rather than maintaining local
vocabulary copies.
"""
from __future__ import annotations

import re

from app.melimi.db_subject import language_affixes, language_roots, language_rules, language_space_version
from app.melimi.firewall import subject_lexicon
from app.melimi.grammar import grammar_policy
from app.melimi.root_morphology import reduce_to_root
from app.melimi.word_formation import derive_many
from app.language_space import language_space_context

TOKEN_RE = re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*")


def _melimi_root_index() -> dict[str, str]:
    """Return MASTER Melimi forms keyed by their persisted source roots."""
    return {
        str(melimi).strip(): str(source).strip()
        for source, melimi in language_roots().items()
        if str(melimi).strip()
    }


def _token_record(token: str, lexicon: dict, melimi_roots: dict[str, str]) -> dict:
    preferred = lexicon["preferred"].get(token) or lexicon["preferred"].get(token.casefold())
    reverse = {value: key for key, value in lexicon["preferred"].items()}
    standard = reverse.get(token)

    # Native MT must be resolved against the MT side of the authoritative root
    # dictionary first. The persisted dictionary is source→MT, so create the
    # reverse root set for MT surface analysis.
    mt_form = None
    mt_morph = reduce_to_root(token, set(melimi_roots))
    mt_known = token in lexicon["registered"] or mt_morph.root in melimi_roots
    if mt_known:
        mt_form = token

    # Standard/source input remains supported for explicit translation and
    # mixed-language input, but it is never preferred over a known MT reading.
    source_morph = reduce_to_root(token, lexicon["forbidden"])
    source_known = source_morph.root in lexicon["forbidden"] or preferred is not None

    if mt_known:
        return {
            "surface": token,
            "melimi": mt_form,
            "standard": standard,
            "matched_root": mt_morph.root,
            "suffixes": list(mt_morph.suffixes),
            "kinds": list(mt_morph.kinds),
            "known": True,
            "language_side": "melimi",
        }

    return {
        "surface": token,
        "melimi": preferred,
        "standard": standard or (source_morph.root if source_known else None),
        "matched_root": source_morph.root if source_known else "",
        "suffixes": list(source_morph.suffixes) if source_known else [],
        "kinds": list(source_morph.kinds) if source_known else [],
        "known": source_known,
        "language_side": "source" if source_known else "unknown",
    }


def analyze(text: str, *, max_tokens: int = 80) -> dict:
    """Analyze input using the current shared Language Space."""
    text = (text or "").strip()
    lexicon = subject_lexicon()
    melimi_roots = _melimi_root_index()
    tokens = TOKEN_RE.findall(text)[:max_tokens]
    records = [_token_record(token, lexicon, melimi_roots) for token in tokens]
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
        "melimi_root_count": len(melimi_roots),
    }


def _authorized_formations(text: str, *, limit: int = 24) -> list[str]:
    """Return only MASTER productive formations relevant to the input."""
    lexicon = subject_lexicon()
    melimi_roots = _melimi_root_index()
    candidates: list[str] = []
    seen_roots: set[str] = set()
    for token in TOKEN_RE.findall(text or "")[:80]:
        preferred = lexicon["preferred"].get(token) or lexicon["preferred"].get(token.casefold())
        if token in melimi_roots:
            melimi_root = token
        elif token in lexicon["registered"]:
            melimi_root = reduce_to_root(token, set(melimi_roots)).root
        else:
            melimi_root = preferred or ""
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
        f"authoritative Melimi roots available: {analysis['melimi_root_count']}",
        "token analysis:",
    ]
    for item in analysis["tokens"]:
        lines.append("- " + " | ".join([
            f"surface={item['surface']}", f"melimi={item['melimi'] or ''}",
            f"standard={item['standard'] or ''}", f"root={item['matched_root']}",
            f"suffixes={item['suffixes']}", f"kinds={item['kinds']}",
            f"side={item['language_side']}",
        ]))
    lines.extend([
        "", "AUTHORITATIVE GRAMMAR:", str(analysis["grammar"]),
        "", "SHARED LANGUAGE-SPACE EVIDENCE:", space,
        "", "RULE: language records are evidence for understanding, not user-facing instructions.",
        "RULE: MASTER language knowledge outranks generic lexical guesses.",
        "RULE: a recognized Melimi surface must be interpreted from the Melimi root/derivation before considering Standard Telugu similarity.",
        "RULE: do not invent a Melimi meaning when no authoritative entry exists.",
    ])
    return "\n".join(lines)[:max_chars]


def build_generation_context(text: str, *, max_chars: int = 6000) -> str:
    """Build generation context including only authorized productive formations."""
    context = build_understanding_context(text, max_chars=max_chars)
    formations = _authorized_formations(text)
    if formations:
        context = (context + "\n\nAUTHORIZED PRODUCTIVE FORMATIONS (MASTER ONLY):\n" +
                   "\n".join(f"- {item}" for item in formations) +
                   "\nUse these formations only when their meaning and grammatical role fit the response. Do not invent similar forms.")[:max_chars]
    return context


def validate_response(text: str) -> dict:
    """Validate a generated response against the shared lexical space."""
    from app.melimi.firewall import lexical_violations
    violations = lexical_violations(text or "")
    return {"valid": not violations, "violations": violations, "version": language_space_version()}
