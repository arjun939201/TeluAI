"""Shared Melimi Telugu language service.

Main Chat, the Melimi Lab, and future features use the same persisted
Language Space. Existing authoritative MT vocabulary/forms are preferred;
productive derivation is supporting evidence, not a vocabulary factory.
"""
from __future__ import annotations

import re

from app.melimi.db_subject import language_affixes, language_roots, language_rules, language_space_version
from app.melimi.firewall import subject_lexicon
from app.melimi.grammar import grammar_policy, NON_GENERATIVE_AGENT_SUFFIXES
from app.melimi.root_morphology import reduce_to_root
from app.melimi.word_formation import derive_many
from app.language_space import language_space_context

TOKEN_RE = re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*")


def _melimi_root_index() -> dict[str, str]:
    return {
        str(melimi).strip(): str(source).strip()
        for source, melimi in language_roots().items()
        if str(melimi).strip()
    }


def _token_record(token: str, lexicon: dict, melimi_roots: dict[str, str]) -> dict:
    preferred = lexicon["preferred"].get(token) or lexicon["preferred"].get(token.casefold())
    reverse = {value: key for key, value in lexicon["preferred"].items()}
    standard = reverse.get(token)
    mt_morph = reduce_to_root(token, set(melimi_roots))
    mt_known = token in lexicon["registered"] or mt_morph.root in melimi_roots
    if mt_known:
        return {
            "surface": token, "melimi": token, "standard": standard,
            "matched_root": mt_morph.root, "suffixes": list(mt_morph.suffixes),
            "kinds": list(mt_morph.kinds), "known": True, "language_side": "melimi",
        }

    # Source/Standard Telugu is an input bridge, not a preferred output lexicon.
    source_morph = reduce_to_root(token, lexicon["forbidden"])
    source_known = source_morph.root in lexicon["forbidden"] or preferred is not None
    return {
        "surface": token, "melimi": preferred,
        "standard": standard or (source_morph.root if source_known else None),
        "matched_root": source_morph.root if source_known else "",
        "suffixes": list(source_morph.suffixes) if source_known else [],
        "kinds": list(source_morph.kinds) if source_known else [],
        "known": source_known, "language_side": "source" if source_known else "unknown",
    }


def analyze(text: str, *, max_tokens: int = 80) -> dict:
    text = (text or "").strip()
    lexicon = subject_lexicon()
    melimi_roots = _melimi_root_index()
    tokens = TOKEN_RE.findall(text)[:max_tokens]
    records = [_token_record(token, lexicon, melimi_roots) for token in tokens]
    return {
        "version": language_space_version(),
        "tokens": records,
        "known_tokens": sum(1 for x in records if x["known"]),
        "unknown_tokens": [x["surface"] for x in records if not x["known"]],
        "grammar": grammar_policy(),
        "affix_count": len(language_affixes()), "rule_count": len(language_rules()),
        "melimi_root_count": len(melimi_roots),
    }


def _authorized_formations(text: str, *, limit: int = 24) -> list[str]:
    """Return existing forms first, then only clearly licensed MASTER derivations."""
    lexicon = subject_lexicon()
    melimi_roots = _melimi_root_index()
    candidates: list[str] = []
    seen: set[str] = set()

    # Existing registered forms are the strongest generation evidence.
    for token in TOKEN_RE.findall(text or "")[:80]:
        if token in lexicon["registered"] and token not in seen:
            seen.add(token)
            candidates.append(f"EXISTING MT FORM => {token}")
            if len(candidates) >= limit:
                return candidates

    # Only derive from a known MT root, never from an unknown/guessed root.
    for token in TOKEN_RE.findall(text or "")[:80]:
        root = token if token in melimi_roots else reduce_to_root(token, set(melimi_roots)).root
        if root not in melimi_roots or root in seen:
            continue
        seen.add(root)
        try:
            formations = derive_many(root, limit=12)
        except Exception:
            formations = []
        for formation in formations:
            if formation.status != "MASTER_DERIVED" or formation.affix in NON_GENERATIVE_AGENT_SUFFIXES:
                continue
            # Avoid presenting every possible derivative as vocabulary. Only
            # forms already present in the registered lexicon are generation
            # candidates; productive rules remain available to deterministic
            # grammar code when a future update explicitly requests one.
            if formation.word not in lexicon["registered"]:
                continue
            line = f"{formation.root} + {formation.affix} => {formation.word} ({formation.meaning})"
            if line not in candidates:
                candidates.append(line)
            if len(candidates) >= limit:
                return candidates
    return candidates


def build_understanding_context(text: str, *, max_chars: int = 6000) -> str:
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
        "", "GENERATION PRIORITY: existing registered/native MT forms first.",
        "GENERATION SAFETY: do not create a new MT word unless the source clearly establishes the base, formation, and meaning.",
        "RULE: MASTER language knowledge outranks generic lexical guesses.",
        "RULE: a recognized Melimi surface must be interpreted from the Melimi root/derivation before considering Standard Telugu similarity.",
        "RULE: do not invent a Melimi meaning when no authoritative entry exists.",
    ])
    return "\n".join(lines)[:max_chars]


def build_generation_context(text: str, *, max_chars: int = 6000) -> str:
    context = build_understanding_context(text, max_chars=max_chars)
    formations = _authorized_formations(text)
    if formations:
        context = (context + "\n\nAUTHORIZED EXISTING MT FORMS / FORMATIONS:\n" +
                   "\n".join(f"- {item}" for item in formations) +
                   "\nPrefer these existing forms. Do not invent parallel forms.")[:max_chars]
    return context


def validate_response(text: str) -> dict:
    from app.melimi.firewall import lexical_violations
    violations = lexical_violations(text or "")
    return {"valid": not violations, "violations": violations, "version": language_space_version()}
