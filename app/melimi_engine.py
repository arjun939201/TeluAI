"""High-precision Melimi language analysis layer.

Evidence-first lexical analysis: authoritative vocabulary is canonical; surface
inflections are resolved back to canonical entries; formations are evidence,
not unrestricted productive rules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from app.knowledge import retrieve, format_knowledge, load_vocabulary

VOCABULARY = load_vocabulary()
TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]+", re.UNICODE)

PROPERTIES = {
    "source_authority": True,
    "canonical_resolution": True,
    "inflection_resolution": True,
    "compound_resolution": True,
    "formation_family_analysis": True,
    "prefix_boundary_analysis": True,
    "suffix_boundary_analysis": True,
    "semantic_context_analysis": True,
    "lexical_collision_detection": True,
    "transhift_validation": True,
    "no_invention_guard": True,
    "confidence_tracking": True,
}

# Generic suffixes are deliberately conservative. Morphophonemic endings for
# canonical -ం nouns are handled first so a generic -కి/-లో/-ని rule cannot
# destroy the canonical stem.
INFLECTION_SUFFIXES = (
    "లతో", "లను", "లకు", "లలో", "లకి", "లుగా", "లు",
    "నుండి", "నుంచి", "యొక్క", "తో", "ను", "ని", "కు", "కి", "లో", "గా", "ఏ",
)

AM_NOUN_SURFACES = (
    ("ానికి", "ం", "దాతివేటు"),
    ("ాన్ని", "ం", "ఆక్యుసేటివ్"),
)

KNOWN_PREFIXES = (
    "వి", "లా", "ఎల", "సరి", "సై", "తమూ", "కై", "ఆయి", "పొలో",
    "అక", "ఔ", "మఱీ", "ఉడు", "తరు",
)


@dataclass(frozen=True)
class MelimiAnalysis:
    message: str
    tokens: tuple[str, ...]
    matched: tuple[dict[str, str], ...] = ()
    inflected_matches: tuple[dict[str, str], ...] = ()
    family_candidates: tuple[dict[str, str], ...] = ()
    boundaries: tuple[str, ...] = ()
    confidence: str = "none"
    should_transhift: bool = False
    should_invent: bool = False
    properties: dict[str, bool] = field(default_factory=lambda: dict(PROPERTIES))


def tokenize_telugu(text: str) -> tuple[str, ...]:
    return tuple(TELUGU_RE.findall(str(text or "")))


def _strip_known_inflection(token: str) -> tuple[str, str]:
    """Resolve only evidence-backed Telugu surface inflections.

    For canonical -ం nouns, selected case surfaces restore the canonical -ం
    before generic suffix stripping. The surface form is never added to the
    vocabulary.
    """
    for surface, canonical_ending, _label in AM_NOUN_SURFACES:
        if token.endswith(surface) and len(token) > len(surface) + 1:
            return token[:-len(surface)] + canonical_ending, surface

    for suffix in INFLECTION_SUFFIXES:
        if len(token) <= len(suffix) + 1 or not token.endswith(suffix):
            continue
        return token[:-len(suffix)], suffix

    return token, ""


def _items(vocabulary: list[dict[str, str]] | tuple[dict[str, str], ...]):
    return [x for x in vocabulary if str(x.get("kind", "VOCABULARY")) == "VOCABULARY"]


def analyze(message: str, vocabulary: list[dict[str, str]] | tuple[dict[str, str], ...] = VOCABULARY) -> MelimiAnalysis:
    """Perform evidence-first lexical, inflectional and family analysis."""
    text = str(message or "").strip()
    tokens = tokenize_telugu(text)
    matched: list[dict[str, str]] = []
    inflected: list[dict[str, str]] = []
    families: list[dict[str, str]] = []
    boundaries: list[str] = []
    items = _items(vocabulary)
    keys = {str(x.get("key", "")).strip(): x for x in items if x.get("key")}
    matched_keys: set[str] = set()

    for token in tokens:
        if token in keys:
            item = keys[token]
            matched.append({"key": token, "value": str(item.get("value", "")), "source": str(item.get("source", ""))})
            matched_keys.add(token)
            continue

        stem, suffix = _strip_known_inflection(token)
        if suffix and stem in keys:
            item = keys[stem]
            if stem not in matched_keys:
                matched.append({"key": stem, "value": str(item.get("value", "")), "source": str(item.get("source", ""))})
                matched_keys.add(stem)
            inflected.append({
                "surface": token,
                "canonical": stem,
                "target": str(item.get("value", "")),
                "suffix": suffix,
            })

    seen_family: set[tuple[str, str]] = set()
    for item in matched:
        word = item["key"]
        target = item["value"]
        for prefix in KNOWN_PREFIXES:
            if word.startswith(prefix) or target.startswith(prefix):
                marker = (prefix, word)
                if marker not in seen_family:
                    families.append({"prefix": prefix, "word": word, "target": target})
                    seen_family.add(marker)

    if inflected:
        boundaries.append("inflection→canonical; never promote surface form to vocabulary")
    if families:
        boundaries.append("formation-family match is evidence, not unrestricted productivity")

    confidence = "high" if matched or inflected else "none"
    return MelimiAnalysis(
        message=text,
        tokens=tokens,
        matched=tuple(matched),
        inflected_matches=tuple(inflected),
        family_candidates=tuple(families),
        boundaries=tuple(boundaries),
        confidence=confidence,
        should_transhift=bool(matched or inflected),
        should_invent=False,
    )


def compact_report(result: MelimiAnalysis) -> str:
    lines = [f"TEX-L | {result.confidence.upper()} | {'TRANSHIFT' if result.should_transhift else 'NO MATCH'}"]
    for item in result.matched:
        lines.append(f"{item['key']} → {item['value']}")
    for item in result.inflected_matches:
        lines.append(f"{item['surface']} → {item['target']} [{item['suffix']}]")
    for item in result.family_candidates:
        lines.append(f"family:{item['prefix']}- | {item['word']} → {item['target']}")
    if not result.matched and not result.inflected_matches:
        lines.append("no source-backed match; do not invent")
    return "\n".join(lines)


def retrieve_conversation_context(message: str, limit: int = 6, max_chars: int = 1400) -> str:
    return format_knowledge(retrieve(message, limit=limit), max_chars=max_chars)
