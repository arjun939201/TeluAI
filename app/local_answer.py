"""Deterministic answers for authoritative Melimi lookups.

Only explicit lookup questions are answered locally. Unknown vocabulary falls
through to the conversational AI so the model can explain uncertainty naturally
instead of returning a canned dictionary-style error.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from sqlalchemy import select

from app.database import SessionLocal, KnowledgeEntry, MelimiExample
from app.melimi.root_morphology import load_root_dictionary, reduce_to_root, reapply_operations
from app.melimi.registry import lexical_inventory


def _romanize_telugu(text: str) -> str:
    consonants = {"క":"k","ఖ":"kh","గ":"g","ఘ":"gh","ఙ":"n","చ":"ch","ఛ":"chh","జ":"j","ఝ":"jh","ఞ":"n","ట":"t","ఠ":"th","డ":"d","ఢ":"dh","ణ":"n","త":"t","థ":"th","ద":"d","ధ":"dh","న":"n","ప":"p","ఫ":"ph","బ":"b","భ":"bh","మ":"m","య":"y","ర":"r","ఱ":"r","ల":"l","ళ":"l","వ":"v","శ":"sh","ష":"sh","స":"s","హ":"h"}
    independent = {"అ":"a","ఆ":"aa","ఇ":"i","ఈ":"ii","ఉ":"u","ఊ":"uu","ఋ":"ru","ఎ":"e","ఏ":"ee","ఐ":"ai","ఒ":"o","ఓ":"oo","ఔ":"au"}
    signs = {"ా":"aa","ి":"i","ీ":"ii","ు":"u","ూ":"uu","ృ":"ru","ె":"e","ే":"ee","ై":"ai","ొ":"o","ో":"oo","ౌ":"au","్":"","ం":"m","ః":"h"}
    output = []
    pending = ""
    for char in text:
        if char in consonants:
            if pending:
                output.append(pending)
            pending = consonants[char] + "a"
        elif char in signs:
            if pending:
                output.append(pending[:-1] + signs[char])
                pending = ""
            else:
                output.append(signs[char])
        elif char in independent:
            if pending:
                output.append(pending)
                pending = ""
            output.append(independent[char])
        else:
            if pending:
                output.append(pending)
                pending = ""
            output.append(char)
    if pending:
        output.append(pending)
    return "".join(output).lower().replace("aa", "a")


def _lookup_standard(word: str, roots: dict[str, str]):
    word = (word or "").strip().strip(" ?.!,:;")
    if not word:
        return None
    if word in roots:
        return word, roots[word]
    for key, value in roots.items():
        if key.casefold() == word.casefold():
            return key, value
    if re.search(r"[\u0C00-\u0C7F]", word):
        needle = _romanize_telugu(word)
        best = None
        for key, value in roots.items():
            candidate = _romanize_telugu(key) if re.search(r"[\u0C00-\u0C7F]", key) else key.lower()
            ratio = SequenceMatcher(None, needle, candidate).ratio()
            if ratio >= 0.90 and (best is None or ratio > best[0]):
                best = (ratio, key, value)
        if best:
            return best[1], best[2]
    return None


def _extract_lookup_word(q: str):
    patterns = (
        r"^(.+?)\s+అంటే\s+ఏమిటి\??$",
        r"^(.+?)\s+అర్థం\s+ఏమిటి\??$",
        r"^(.+?)\s+(?:ఏంటి|ఏమిటి)\??$",
        r"^(?:మేలిమి\s+తెలుగులో\s+)?(.+?)\s+ను?\s+ఏమంటారు\??$",
        r"^(.+?)\s*=\s*\??$",
        r"^(.+?)\s+కు\s+మేలిమి\s+తెలుగులో\s+ఏమంటారు\??$",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, q)
        if match:
            return re.sub(r"^మేలిమి\s+తెలుగులో\s+", "", match.group(1).strip()).strip()
    return None


def _lookup_content(q: str):
    """Return an exact MASTER phrase/example only when explicitly supplied."""
    candidates = []
    with SessionLocal() as db:
        rows = db.scalars(select(KnowledgeEntry).where(KnowledgeEntry.status == "MASTER")).all()
        for row in rows:
            if row.kind not in {"CONTENT", "EXAMPLE", "POST", "FACT", "NOTE"}:
                continue
            value = (row.value or "").strip()
            if value.casefold() == q.casefold():
                candidates.append((value, row.metadata_json or "{}"))
        examples = db.scalars(select(MelimiExample).where(MelimiExample.status == "MASTER")).all()
        for row in examples:
            if (row.melimi_text or "").strip().casefold() == q.casefold():
                candidates.append((row.melimi_text, row.standard_text))
    if not candidates:
        return None
    value, meta = candidates[0]
    if isinstance(meta, str) and meta.strip().startswith("{"):
        try:
            import json
            meaning = str(json.loads(meta).get("meaning", "")).strip()
        except Exception:
            meaning = ""
    else:
        meaning = str(meta).strip()
    return f"{value}\n{meaning}" if meaning else value


def _grammatical_role(form) -> str | None:
    """Give a concise grammatical role instead of a repetitive word definition."""
    roles = []
    for kind, suffix in form.operations:
        if kind == "case":
            roles.append({
                "ACCUSATIVE": "కర్మ విభక్తి (Accusative)",
                "DATIVE": "సంప్రదాన విభక్తి (Dative)",
            }.get(suffix, suffix))
        elif kind == "grammar":
            roles.append({
                "లు": "బహువచనం",
                "ల": "బహువచనం",
                "లను": "బహువచనం + కర్మ విభక్తి",
                "లని": "బహువచనం + కర్మ విభక్తి",
                "లకు": "బహువచనం + సంప్రదాన విభక్తి",
                "లకై": "బహువచనం + కొరకు రూపం",
                "లపై": "బహువచనం + పై విభక్తి",
                "లతో": "బహువచనం + తో విభక్తి",
                "లలో": "బహువచనం + లో విభక్తి",
                "ను": "కర్మ విభక్తి",
                "ని": "కర్మ విభక్తి",
                "కు": "సంప్రదాన విభక్తి",
                "కి": "సంప్రదాన విభక్తి",
                "లో": "స్థాన విభక్తి",
                "తో": "సహచర్య విభక్తి",
                "పై": "స్థాన/పై విభక్తి",
                "గా": "రీతి రూపం",
            }.get(suffix, suffix))
        elif kind == "derivation":
            roles.append(f"-{suffix} ప్రత్యయ రూపం")
        elif kind.startswith("adjective"):
            roles.append("విశేషణ రూపం")
    return " + ".join(dict.fromkeys(roles)) if roles else None


def _lookup_inflected(word: str, roots: dict[str, str]):
    form = reduce_to_root(word, roots)
    if form.root not in roots or not form.operations:
        return None
    melimi = reapply_operations(roots[form.root], form)
    role = _grammatical_role(form)
    return f"{melimi}\nవ్యాకరణ పాత్ర: {role}" if role else melimi


def answer(message: str, mode: str) -> str | None:
    if mode != "melimi":
        return None
    q = re.sub(r"\s+", " ", (message or "").strip())
    if q in {"మేలిమి తెలుగు అంటే ఏమిటి?", "మేలిమి తెలుగు అంటే ఏమిటి"}:
        return (
            "మేలిమి తెలుగు అనేది తెలుగు ఆధారిత వేఱైన నుడి రూపం. ఇందులో కుదిరిన మేలిమి మాటలు, "
            "పదనిర్మాణ నియమాలు, పదార్థభేదాలు, వాడుకరీతులు ఉంటాయి. సాధారణ తెలుగు వ్యాకరణ నిర్మాణం "
            "మేలిమి నియమాలతో పాటు కొనసాగుతుంది."
        )

    word = _extract_lookup_word(q)
    if word:
        roots = load_root_dictionary()
        inflected = _lookup_inflected(word, roots)
        if inflected:
            return inflected
        found = _lookup_standard(word, roots)
        if found:
            return found[1]
        inverse = lexical_inventory()["melimi_to_standard"].get(word)
        if inverse:
            return f"{word} అంటే {inverse}."
        return None

    return _lookup_content(q)


async def try_deterministic_answer(message: str, mode: str, history_count: int = 0) -> str | None:
    if history_count:
        return None
    return answer(message, mode)
