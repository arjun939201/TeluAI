from __future__ import annotations
import json, re
from typing import Any
from dataclasses import dataclass

@dataclass
class LanguageDocument:
    path: str
    kind: str
    text: str
    entries: list[dict[str, Any]]

def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[\u0C00-\u0C7F]+|[A-Za-z]+", (text or "").lower()))

def _stringify(value: Any) -> str:
    if isinstance(value, dict): return " ".join(f"{k} {_stringify(v)}" for k,v in value.items())
    if isinstance(value, list): return " ".join(_stringify(v) for v in value)
    return str(value or "")

def load_documents() -> list[dict[str, Any]]:
    try:
        from app.database import language_documents
        return [LanguageDocument(d["path"],d["kind"],d.get("text",""),d.get("entries",[])) for d in language_documents()]
    except Exception:
        return []

def search_subject(query: str, limit: int = 10) -> list[dict[str, Any]]:
    q = _tokens(query)
    if not q: return []
    scored=[]
    for doc in load_documents():
        text=doc.text; tokens=_tokens(text); score=len(q & tokens)*5
        low=text.lower()
        score += sum(2 for t in q if len(t)>2 and t in low)
        if score: scored.append((score,doc,None))
        for entry in doc.entries:
            es=len(q & _tokens(_stringify(entry)))*12
            if es: scored.append((es,doc,entry))
    scored.sort(key=lambda x:-x[0]); results=[]; seen=set()
    for score,doc,entry in scored:
        key=(doc.path,json.dumps(entry,ensure_ascii=False,sort_keys=True) if entry else "")
        if key in seen: continue
        seen.add(key); results.append({"source":doc.path,"kind":doc.kind,"entry":entry,"excerpt":doc.text[:1800] if not entry else "","score":score})
        if len(results)>=limit: break
    return results

def build_subject_context(query: str, limit: int = 10, max_chars: int = 8000) -> str:
    results=search_subject(query,limit)
    if not results: return "MELIMI SUBJECT KNOWLEDGE: No directly retrieved item. Do not invent facts."
    lines=["MELIMI TELUGU LANGUAGE SUBJECT KNOWLEDGE","The following are linguistic sources, not response templates."]
    for r in results:
        lines.append(f"\nSOURCE: {r['source']} [{r['kind']}]")
        lines.append(json.dumps(r["entry"],ensure_ascii=False) if r["entry"] else re.sub(r"\n{3,}","\n\n",r["excerpt"]).strip()[:1400])
    return "\n".join(lines)[:max_chars]

def subject_inventory() -> dict:
    docs=load_documents()
    kinds={"vocabulary","grammar","word_formation","syntax","examples","prose","rules","other"}
    return {"documents":len(docs),"by_kind":{k:sum(1 for d in docs if d.kind==k) for k in kinds},"paths":[d.path for d in docs]}
