"""Chat-native Melimi learning.

Normal chat can teach TeluAI when the user provides language evidence. Explicit
x = y mappings are authoritative user teaching; longer declarative content is
mined into reusable lexical items, phrases, sentences, patterns, and
loan/native signals. All learned items are persisted and immediately available
to retrieval.
"""
from __future__ import annotations

import hashlib
import json
import re

from sqlalchemy import select

from app.database import KnowledgeEntry, KnowledgeVersion, MelimiAffix, MelimiExample, MelimiRoot, MelimiRule, SessionLocal, now
from app.learner_store import add_learning, approved_for_query

_COMMAND_RE = re.compile(r"^\s*/(?P<kind>word|meaning|content|example|root|affix|rule|phrase|note|correct)\b(?P<body>.*?)\s*$", re.I | re.S)
_MAPPING_RE = re.compile(r"^\s*(?P<source>.+?)\s*(?:=|→|->)\s*(?P<melimi>.+?)\s*$", re.S)
_INLINE_MAPPING_RE = re.compile(r"(?<!\w)([^=→➜⇒\n]{1,100}?)(?:\s*=\s*|\s*(?:→|➜|⇒|->)\s*)([^=→➜⇒\n]{1,120})(?=$|[.!?;\n])")
_TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]+")
_TOKEN_RE = re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*")
_SENTENCE_RE = re.compile(r"[^.!?。！？\n]+[.!?。！？]?", re.S)
_LOAN_HINTS = re.compile(r"(?:loan\s*word|loanword|borrowed|sanskrit\s*based|sanskrit-derived|foreign\s*word|అరువు\s*మాట|రుణ\s*మాట|సంస్కృత|అరువుమాట)", re.I)
_NATIVE_HINTS = re.compile(r"(?:native\s*telugu|native\s*word|pure\s*telugu|తెలుగు\s*మాట|నాటు\s*మాట|తెనుగు\s*మాట|మేలిమి\s*మాట)", re.I)
_QUESTION_HINTS = re.compile(r"(?:\?|ఏమిటి|ఏంటి|ఏమంటారు|ఏమంటావు|ఎందుకు|ఎలా|ఎక్కడ|ఎప్పుడు|ఎవరు|ఎంత|ఎన్ని)", re.I)


def parse_command(message: str):
    match = _COMMAND_RE.match(message or "")
    if not match:
        return None
    raw_kind = match.group("kind").lower(); body = match.group("body").strip()
    if raw_kind in {"word", "meaning", "correct"}:
        parsed = _MAPPING_RE.match(body)
        if not parsed:
            raise ValueError(f"Usage: /{raw_kind} source = melimi")
        source = parsed.group("source").strip(); melimi = parsed.group("melimi").strip()
        if not source or not melimi or len(source) > 160 or len(melimi) > 160:
            raise ValueError("Word entries must be 160 characters or less per side.")
        return "word", {"source": source, "melimi": melimi, "command": raw_kind}
    if not body:
        raise ValueError(f"/{raw_kind} cannot be empty.")
    if len(body) > 50000:
        raise ValueError("Language content is too large. Maximum is 50,000 characters.")
    if raw_kind == "example":
        note = re.match(r"^(.*?)(?:\s*\(([^()]*)\))?\s*$", body, re.S)
        content = (note.group(1) or "").strip(); meaning = (note.group(2) or "").strip()
    elif raw_kind in {"root", "affix", "rule"}:
        parsed = _MAPPING_RE.match(body)
        if not parsed:
            raise ValueError(f"Usage: /{raw_kind} name = meaning")
        content = parsed.group("source").strip(); meaning = parsed.group("melimi").strip()
    else:
        content, meaning = body, ""
    if not content:
        raise ValueError(f"/{raw_kind} cannot be empty.")
    return "content", {"content": content, "meaning": meaning, "command": raw_kind}


def _find_root(db, standard: str):
    for candidate in db.scalars(select(MelimiRoot)).all():
        if str(candidate.standard_root or "").strip().casefold() == standard.casefold():
            return candidate
    return None


def _upsert_knowledge(db, kind: str, key: str, value: str, metadata: dict, source: str) -> bool:
    encoded = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
    record = db.scalar(select(KnowledgeEntry).where((KnowledgeEntry.kind == kind) & (KnowledgeEntry.key == key)))
    if record:
        if record.value == value and record.metadata_json == encoded and record.status == "MASTER":
            return False
        record.value = value; record.metadata_json = encoded; record.status = "MASTER"; record.source = source; record.version += 1
        return True
    db.add(KnowledgeEntry(kind=kind, key=key, value=value, metadata_json=encoded, status="MASTER", source=source))
    return True


def _store_learning(kind: str, *, standard: str = "", melimi: str = "", rule: str = "", meaning: str = "", evidence: str = "", confidence: float = 1.0, metadata: dict | None = None):
    return add_learning(kind=kind, standard=standard, melimi=melimi, rule=rule, meaning=meaning, evidence=evidence, source="chat", status="approved", confidence=confidence, metadata=metadata or {})


def _source_class(text: str, known_word: str = "") -> str:
    if _LOAN_HINTS.search(text or ""):
        return "loan"
    if _NATIVE_HINTS.search(text or ""):
        return "native"
    try:
        from app.melimi.registry import analyze_word
        info = analyze_word(known_word) if known_word else {}
        if info.get("loan"):
            return "loan"
        if info.get("native"):
            return "native"
    except Exception:
        pass
    return "unknown"


def _mapping_pairs(text: str) -> list[tuple[str, str]]:
    pairs = []
    for match in _INLINE_MAPPING_RE.finditer(text or ""):
        left = match.group(1).strip(" \t.,:;()[]{}"); right = match.group(2).strip(" \t.,:;()[]{}")
        if not left or not right or len(left) > 100 or len(right) > 120 or len(left.split()) > 8 or len(right.split()) > 8:
            continue
        pairs.append((left, right))
    seen = set(); out = []
    for pair in pairs:
        key = (pair[0].casefold(), pair[1].casefold())
        if key not in seen:
            seen.add(key); out.append(pair)
    return out


def _sentence_parts(text: str) -> list[str]:
    out = []
    for raw in _SENTENCE_RE.findall(text or ""):
        sentence = re.sub(r"\s+", " ", raw).strip()
        if len(sentence) >= 3:
            out.append(sentence)
    return out


def _content_items(text: str) -> tuple[list[str], list[str], list[str]]:
    try:
        from app.melimi.registry import FUNCTION_WORDS
    except Exception:
        FUNCTION_WORDS = set()
    words = []
    for token in _TOKEN_RE.findall(text or ""):
        if not _TELUGU_RE.fullmatch(token) or token in FUNCTION_WORDS or len(token) < 2:
            continue
        if token not in words:
            words.append(token)
    sentences = _sentence_parts(text); phrases = []
    for sentence in sentences:
        tokens = [t for t in _TOKEN_RE.findall(sentence) if _TELUGU_RE.fullmatch(t) and t not in FUNCTION_WORDS]
        for size in (2, 3):
            for i in range(0, max(0, len(tokens) - size + 1)):
                phrase = " ".join(tokens[i:i + size])
                if phrase not in phrases:
                    phrases.append(phrase)
                if len(phrases) >= 40:
                    break
            if len(phrases) >= 40:
                break
    patterns = []
    for sentence in sentences:
        tokens = _TOKEN_RE.findall(sentence)
        shape = " ".join("TELUGU" if _TELUGU_RE.fullmatch(t) else "WORD" for t in tokens)
        if shape and shape not in patterns:
            patterns.append(shape)
    return words[:80], phrases[:40], patterns[:20]


def _learn_mapping(standard: str, melimi: str, evidence: str, source_class: str = "unknown") -> bool:
    source = "chat"; changed = False
    with SessionLocal() as db:
        melimi_root = melimi.split("/")[0].strip(); row = _find_root(db, standard)
        if row:
            if row.melimi_root != melimi_root or row.status != "MASTER" or row.source != source:
                row.melimi_root = melimi_root; row.status = "MASTER"; row.source = source; row.version += 1; row.updated_at = now(); changed = True
        else:
            db.add(MelimiRoot(standard_root=standard, melimi_root=melimi_root, meaning=standard, status="MASTER", source=source)); changed = True
        metadata = {"standard": standard, "melimi": melimi, "learning": "chat", "source_class": source_class, "evidence": evidence[:2000]}
        changed = _upsert_knowledge(db, "VOCABULARY", f"word:{standard.casefold()}", melimi, metadata, source) or changed
        if changed:
            latest = db.scalars(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc())).first()
            db.add(KnowledgeVersion(version=(latest.version if latest else 0) + 1, source=source, checksum=hashlib.sha256(evidence.encode()).hexdigest()))
        db.commit()
    _store_learning("vocabulary", standard=standard, melimi=melimi, meaning=standard, evidence=evidence, metadata={"source_class": source_class, "method": "chat_mapping"})
    return changed


def learn_from_chat(message: str) -> dict:
    """Learn explicit mappings and declarative language evidence from ordinary chat."""
    text = (message or "").strip()
    if not text or text.startswith("/"):
        return {"changed": False, "mappings": 0, "words": 0, "phrases": 0, "sentences": 0, "patterns": 0}
    changed = False; mappings = 0
    for standard, melimi in _mapping_pairs(text):
        changed = _learn_mapping(standard, melimi, text, _source_class(text, standard)) or changed; mappings += 1
    words, phrases, patterns = _content_items(text); sentences = _sentence_parts(text)
    declarative = not _QUESTION_HINTS.search(text)
    rich_content = declarative and (len(text) >= 30 or len(sentences) >= 2 or len(words) >= 2)
    if rich_content:
        for sentence in sentences[:30]:
            _store_learning("sentence", melimi=sentence, evidence=text, confidence=0.9, metadata={"method": "chat_content"})
        for word in words:
            _store_learning("word_observation", melimi=word, evidence=text, confidence=0.75, metadata={"source_class": _source_class(text, word), "method": "chat_content"})
        for phrase in phrases:
            _store_learning("phrase", melimi=phrase, evidence=text, confidence=0.7, metadata={"method": "chat_pattern"})
        for pattern in patterns:
            _store_learning("pattern", rule=pattern, meaning="Observed Telugu sentence pattern", evidence=text, confidence=0.65, metadata={"method": "chat_pattern"})
        with SessionLocal() as db:
            key = "chat-content:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
            changed = _upsert_knowledge(db, "CHAT_CONTENT", key, text[:50000], {"words": words, "phrases": phrases, "sentences": sentences[:30], "patterns": patterns, "learning": "chat"}, "chat") or changed
            if changed:
                latest = db.scalars(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc())).first()
                db.add(KnowledgeVersion(version=(latest.version if latest else 0) + 1, source="chat", checksum=hashlib.sha256(text.encode()).hexdigest()))
            db.commit()
    if changed:
        reload_indexes()
    return {"changed": changed, "mappings": mappings, "words": len(words) if rich_content else 0, "phrases": len(phrases) if rich_content else 0, "sentences": len(sentences) if rich_content else 0, "patterns": len(patterns) if rich_content else 0}


def retrieve_chat_knowledge(query: str, limit: int = 10) -> str:
    rows = approved_for_query(query, limit=max(1, min(limit, 20)))
    if not rows:
        return ""
    lines = []
    for row in rows:
        kind = row.get("kind"); meta = row.get("metadata") or {}
        if kind == "vocabulary":
            lines.append(f"- USER-TAUGHT WORD: {row.get('standard','')} → {row.get('melimi','')} ({meta.get('source_class','unknown')})")
        elif kind == "sentence":
            lines.append(f"- LEARNED SENTENCE: {row.get('melimi','')}")
        elif kind == "phrase":
            lines.append(f"- LEARNED PHRASE: {row.get('melimi','')}")
        elif kind == "pattern":
            lines.append(f"- LEARNED PATTERN: {row.get('rule','')}")
        elif kind == "word_observation":
            lines.append(f"- OBSERVED WORD: {row.get('melimi','')} ({meta.get('source_class','unknown')})")
    return "\n".join(lines[:limit])


def learn_explicit_teaching(message: str, user_id: int | None = None):
    parsed = parse_command(message)
    if not parsed:
        return {"learned": False, "changed": False, "roots": 0, "phrases": 0}
    kind, payload = parsed
    if kind == "word":
        standard = payload["source"].strip(); melimi = payload["melimi"].strip()
        changed = _learn_mapping(standard, melimi, message, _source_class(message, standard))
        return {"learned": True, "changed": changed, "roots": 1, "phrases": 0}
    content = payload["content"]; meaning = payload.get("meaning", ""); command = payload.get("command", "content")
    source = "chat"; changed = False; roots = phrases = 0
    with SessionLocal() as db:
        key = f"chat:{command}:{hashlib.sha256((content + chr(10) + meaning).encode()).hexdigest()}"
        changed = _upsert_knowledge(db, {"example":"EXAMPLE","phrase":"PHRASE","note":"NOTE","content":"CONTENT","root":"ROOT","affix":"AFFIX","rule":"RULE"}.get(command, "CONTENT"), key, content, {"meaning": meaning, "command": command, "source": "chat"}, source) or changed
        if command in {"example", "content", "phrase"}:
            if meaning and not db.scalar(select(MelimiExample).where((MelimiExample.melimi_text == content) & (MelimiExample.standard_text == meaning))):
                db.add(MelimiExample(standard_text=meaning, melimi_text=content, category=command, source=source, status="MASTER")); changed = True
            phrases = 1
        elif command == "root":
            row = _find_root(db, content)
            if row:
                row.melimi_root = meaning; row.meaning = meaning; row.status = "MASTER"; row.source = source; row.version += 1; row.updated_at = now(); changed = True
            else:
                db.add(MelimiRoot(standard_root=content, melimi_root=meaning, meaning=meaning, status="MASTER", source=source)); changed = True
            roots = 1
        elif command == "affix":
            existing = db.scalar(select(MelimiAffix).where(MelimiAffix.form == content))
            if existing:
                existing.meaning = meaning; existing.status = "MASTER"; existing.source = source; changed = True
            else:
                db.add(MelimiAffix(form=content, kind="suffix", meaning=meaning, status="MASTER", source=source)); changed = True
        elif command == "rule":
            existing = db.scalar(select(MelimiRule).where(MelimiRule.name == content))
            if existing:
                existing.rule_text = meaning; existing.status = "MASTER"; existing.source = source; existing.version += 1; changed = True
            else:
                db.add(MelimiRule(name=content, category="chat", rule_text=meaning, status="MASTER", source=source)); changed = True
        if changed:
            latest = db.scalars(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc())).first()
            db.add(KnowledgeVersion(version=(latest.version if latest else 0) + 1, source=source, checksum=hashlib.sha256(message.encode()).hexdigest()))
        db.commit()
    _store_learning(command, standard=content if command == "root" else "", melimi=content if command != "root" else meaning, rule=meaning if command == "rule" else "", meaning=meaning, evidence=message, metadata={"command": command})
    if changed:
        reload_indexes()
    return {"learned": True, "changed": changed, "roots": roots, "phrases": phrases}


def reload_indexes():
    for module, name in (("app.melimi.root_morphology", "reload_root_dictionary"), ("app.melimi.registry", "reload_registry"), ("app.melimi.index", "reload_index"), ("app.melimi.firewall", "reload_firewall"), ("app.retrieval.knowledge", "reload_vocabulary")):
        try:
            getattr(__import__(module, fromlist=[name]), name)()
        except Exception:
            pass


def refresh_language_indexes():
    reload_indexes()
    return True
