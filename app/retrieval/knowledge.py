import re
from functools import lru_cache
from typing import Any, Dict, List


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


@lru_cache(maxsize=1)
def load_vocabulary() -> List[Dict[str, Any]]:
    try:
        from app.melimi.db_subject import language_documents
        out=[]
        for doc in language_documents():
            for entry in doc.get("entries",[]):
                if isinstance(entry,dict):
                    item=dict(entry)
                    item.setdefault("_source", doc.get("path", ""))
                    item.setdefault("_kind", doc.get("kind", "other"))
                    out.append(item)
        return out
    except Exception:
        return []


def reload_vocabulary():
    load_vocabulary.cache_clear()


def fields(entry:Dict)->str:
    values=[]
    for key in ("standard","melimi","source","content","note","meaning","definition","english","gloss","description","example","examples","category","tags","related","synonyms","key","value"):
        value=entry.get(key,"")
        if isinstance(value,list): values.extend(str(v) for v in value)
        elif isinstance(value,dict): values.extend(str(v) for v in value.values())
        else: values.append(str(value))
    return norm(" ".join(values))


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[\u0C00-\u0C7F]+|[A-Za-z]+", norm(text)))


def retrieve(text:str,limit:int=24)->List[Dict]:
    query=norm(text)
    if not query:return []
    qwords=_tokens(query); scored=[]
    for index,entry in enumerate(load_vocabulary()):
        standard=norm(entry.get("standard", "")); melimi=norm(entry.get("melimi", "")); searchable=fields(entry); score=0.0
        # Exact lexical hits are much stronger than generic token overlap.
        if standard and standard in query: score += 300 + len(standard) * 2
        if melimi and melimi in query: score += 350 + len(melimi) * 2
        if entry.get("content") and norm(entry.get("content")) == query: score += 500
        overlap=sum(1 for word in qwords if len(word)>=2 and word in searchable)
        score += min(overlap, 8) * 8
        # Prefer entries from explicit knowledge commands when relevance ties.
        source=norm(entry.get("_source", ""))
        if source.startswith("knowledge/"): score += 3
        if score: scored.append((score,index,entry))
    scored.sort(key=lambda x:(-x[0],x[1])); return [item[2] for item in scored[:limit]]


def format_knowledge(entries:List[Dict],max_chars:int=6000)->str:
    lines=["RELEVANT MELIMI LANGUAGE KNOWLEDGE:","These entries are linguistic evidence, NOT response templates."]
    for entry in entries:
        standard=str(entry.get("standard","")).strip(); melimi=str(entry.get("melimi","")).strip()
        content=str(entry.get("content","")).strip(); note=str(entry.get("note","")).strip()
        if content:
            line=f"- CONTENT: {content}"
            if entry.get("meaning"): line+=f" — {entry.get('meaning')}"
        elif standard or melimi:
            line=f"- {standard} → {melimi}"
            if note: line+=f" ({note})"
        else:
            continue
        lines.append(line)
        if len("\n".join(lines))>=max_chars: break
    return "\n".join(lines)[:max_chars]
