"""Deterministic answers that require no Groq call."""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.melimi.root_morphology import load_root_dictionary
from app.melimi.registry import lexical_inventory


def _romanize_telugu(text: str) -> str:
    consonants = {"క":"k","ఖ":"kh","గ":"g","ఘ":"gh","ఙ":"n","చ":"ch","ఛ":"chh","జ":"j","ఝ":"jh","ఞ":"n","ట":"t","ఠ":"th","డ":"d","ఢ":"dh","ణ":"n","త":"t","థ":"th","ద":"d","ధ":"dh","న":"n","ప":"p","ఫ":"ph","బ":"b","భ":"bh","మ":"m","య":"y","ర":"r","ఱ":"r","ల":"l","ళ":"l","వ":"v","శ":"sh","ష":"sh","స":"s","హ":"h"}
    independent = {"అ":"a","ఆ":"aa","ఇ":"i","ఈ":"ii","ఉ":"u","ఊ":"uu","ఋ":"ru","ఎ":"e","ఏ":"ee","ఐ":"ai","ఒ":"o","ఓ":"oo","ఔ":"au"}
    signs = {"ా":"aa","ి":"i","ీ":"ii","ు":"u","ూ":"uu","ృ":"ru","ె":"e","ే":"ee","ై":"ai","ొ":"o","ో":"oo","ౌ":"au","్":"","ం":"m","ః":"h"}
    output=[]; pending=""
    for char in text:
        if char in consonants:
            if pending: output.append(pending)
            pending=consonants[char]+"a"
        elif char in signs:
            if pending: output.append(pending[:-1]+signs[char]); pending=""
            else: output.append(signs[char])
        elif char in independent:
            if pending: output.append(pending); pending=""
            output.append(independent[char])
        else:
            if pending: output.append(pending); pending=""
            output.append(char)
    if pending: output.append(pending)
    return "".join(output).lower().replace("aa","a")


def _lookup_standard(word: str, roots: dict[str, str]):
    word=(word or "").strip().strip(" ?.!,:;")
    if not word: return None
    if word in roots: return word, roots[word]
    for key, value in roots.items():
        if key.lower() == word.lower(): return key, value
    if re.search(r"[\u0C00-\u0C7F]", word):
        needle=_romanize_telugu(word); best=None
        for key, value in roots.items():
            candidate=_romanize_telugu(key) if re.search(r"[\u0C00-\u0C7F]", key) else key.lower()
            ratio=SequenceMatcher(None, needle, candidate).ratio()
            if ratio >= 0.72 and (best is None or ratio > best[0]): best=(ratio,key,value)
        if best: return best[1],best[2]
    return None


def _extract_lookup_word(q: str):
    patterns=(r"^(.+?)\s*=\s*\??$",r"^(.+?)\s+(?:ఏంటి|ఏమిటి)\??$",r"^(?:మేలిమి\s+తెలుగులో\s+)?(.+?)\s+ను?\s+ఏమంటారు\??$",r"^(.+?)\s+అంటే\s+ఏమిటి\??$",r"^(.+?)\s+అర్థం\s+ఏమిటి\??$")
    for pattern in patterns:
        match=re.fullmatch(pattern,q)
        if match:
            word=match.group(1).strip()
            return re.sub(r"^మేలిమి\s+తెలుగులో\s+", "", word).strip()
    return None


def answer(message: str, mode: str) -> str | None:
    if mode != "melimi": return None
    q=re.sub(r"\s+", " ", (message or "").strip())
    if q in {"మేలిమి తెలుగు అంటే ఏమిటి?", "మేలిమి తెలుగు అంటే ఏమిటి"}:
        return ("మేలిమి తెలుగు అనేది తెలుగు ఆధారిత వేఱైన నుడి రూపం. ఇందులో కుదిరిన మేలిమి మాటలు, "
                "పదనిర్మాణ నియమాలు, పదార్థభేదాలు, వాడుకరీతులు ఉంటాయి. సాధారణ తెలుగు వ్యాకరణ నిర్మాణం "
                "మేలిమి నియమాలతో పాటు కొనసాగుతుంది.")
    word=_extract_lookup_word(q)
    if word:
        roots=load_root_dictionary(); found=_lookup_standard(word,roots)
        if found: return found[1]
        inverse=lexical_inventory()["melimi_to_standard"].get(word)
        if inverse: return f"{word} అంటే {inverse}."
        # A lexical lookup with no MASTER mapping must not fall through to the
        # general LLM. Otherwise the model can hallucinate an "established"
        # Melimi equivalent. Be explicit about the knowledge boundary.
        return "ఈ మాటకు మేలిమి తెలుగు సమానం ఇంకా భాషా నిలయంలో కుదరలేదు."
    return None


async def try_deterministic_answer(message: str, mode: str, history_count: int = 0) -> str | None:
    """Compatibility adapter for the previous local-first API."""
    if history_count:
        return None
    return answer(message, mode)
