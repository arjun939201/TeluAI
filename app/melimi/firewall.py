
from __future__ import annotations
import re
from functools import lru_cache
from app.melimi.index import build_index

TOKEN_RE=re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*")

@lru_cache(maxsize=1)
def subject_lexicon():
    forbidden={}
    preferred={}
    registered=set()
    for doc in build_index():
        if doc.kind!="vocabulary":
            continue
        for entry in doc.entries:
            standard=entry.get("standard") or entry.get("standard_or_source")
            melimi=entry.get("melimi")
            if isinstance(standard,str) and isinstance(melimi,str) and standard.strip() and melimi.strip():
                s=standard.strip()
                m=melimi.strip()
                forbidden[s]=m
                preferred[s]=m
                registered.add(m)
    return {"forbidden":forbidden,"preferred":preferred,"registered":registered}

def reload_firewall():
    subject_lexicon.cache_clear()

def lexical_violations(text:str):
    lex=subject_lexicon()
    found=[]
    for source,melimi in lex["forbidden"].items():
        if re.search(rf"(?<![\u0C00-\u0C7F]){re.escape(source)}(?![\u0C00-\u0C7F])", text):
            found.append({"source":source,"preferred":melimi})
    return found

def deterministic_repair(text:str):
    """Final safety net for exact lexical items explicitly defined by files.

    This is deliberately limited to exact source-side vocabulary entries from
    the authoritative subject. It is not a general word-replacement engine.
    """
    out=text
    for item in lexical_violations(text):
        source=item["source"]; preferred=item["preferred"]
        out=re.sub(
            rf"(?<![\u0C00-\u0C7F]){re.escape(source)}(?![\u0C00-\u0C7F])",
            preferred,
            out
        )
    return out
