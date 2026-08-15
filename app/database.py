"""TeluAI persistent data layer.

PostgreSQL is the production/runtime store. SQLite is retained only as a local
fallback. The authoritative Melimi seed is versioned in Git and imported into
runtime tables; chat-learned knowledge is kept separate and requires approval.
"""
from __future__ import annotations

import hashlib, json, os, secrets, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, select, delete, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
DB_URL = os.getenv("DATABASE_URL", "").strip()
if not DB_URL and os.getenv("RENDER"):
    raise RuntimeError("DATABASE_URL is required on Render. Create/attach the TeluAI PostgreSQL database and set DATABASE_URL on the web service.")
if DB_URL.startswith("postgres://"):
    DB_URL = "postgresql+psycopg://" + DB_URL[len("postgres://"):]
elif DB_URL.startswith("postgresql://"):
    DB_URL = "postgresql+psycopg://" + DB_URL[len("postgresql://"):]
if not DB_URL:
    local_path = ROOT / "data" / "teluai.sqlite3"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    DB_URL = f"sqlite:///{local_path}"
connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase): pass

def now(): return datetime.now(timezone.utc)

class MelimiRoot(Base):
    __tablename__ = "melimi_roots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    standard_root: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    melimi_root: Mapped[str] = mapped_column(String(160))
    meaning: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(30), default="MASTER", index=True)
    source: Mapped[str] = mapped_column(String(255), default="master_corpus")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class MelimiDocument(Base):
    __tablename__ = "melimi_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(String(700), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(80), index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    entries_json: Mapped[str] = mapped_column(Text, default="[]")
    source: Mapped[str] = mapped_column(String(255), default="master_corpus")
    status: Mapped[str] = mapped_column(String(30), default="MASTER", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

class MelimiAffix(Base):
    __tablename__ = "melimi_affixes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    form: Mapped[str] = mapped_column(String(80), index=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)  # prefix, noun_suffix, verb_suffix, particle
    meaning: Mapped[str] = mapped_column(Text, default="")
    applies_to: Mapped[str] = mapped_column(String(80), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="MASTER", index=True)
    source: Mapped[str] = mapped_column(String(255), default="user_corpus")

class MelimiRule(Base):
    __tablename__ = "melimi_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    rule_text: Mapped[str] = mapped_column(Text)
    operation: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="MASTER", index=True)
    source: Mapped[str] = mapped_column(String(255), default="user_corpus")
    version: Mapped[int] = mapped_column(Integer, default=1)

class MelimiExample(Base):
    __tablename__ = "melimi_examples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    standard_text: Mapped[str] = mapped_column(Text, default="")
    melimi_text: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(80), default="")
    source: Mapped[str] = mapped_column(String(255), default="user_corpus")
    status: Mapped[str] = mapped_column(String(30), default="MASTER", index=True)

class KnowledgeVersion(Base):
    __tablename__ = "knowledge_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    source: Mapped[str] = mapped_column(String(255))
    checksum: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(50), index=True)
    key: Mapped[str] = mapped_column(String(255), index=True)
    value: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(30), default="MASTER", index=True)
    source: Mapped[str] = mapped_column(String(255), default="user_corpus")
    version: Mapped[int] = mapped_column(Integer, default=1)

class ResponseCache(Base):
    __tablename__ = "response_cache"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    mode: Mapped[str] = mapped_column(String(20), default="melimi")
    knowledge_version: Mapped[int] = mapped_column(Integer, default=1)
    response: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="user", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="New chat")
    mode: Mapped[str] = mapped_column(String(20), default="melimi")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

class UserSetting(Base):
    __tablename__ = "user_settings"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    preferred_mode: Mapped[str] = mapped_column(String(20), default="melimi")
    response_length: Mapped[str] = mapped_column(String(20), default="normal")
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

class LearningCandidate(Base):
    __tablename__ = "learning_candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    knowledge_type: Mapped[str] = mapped_column(String(60), default="VOCABULARY")
    source_text: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class UserMemory(Base):
    __tablename__ = "user_memory"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(160))
    value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Usage(Base):
    __tablename__ = "usage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(60), default="ok")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    target_type: Mapped[str] = mapped_column(String(80), default="")
    target_id: Mapped[str] = mapped_column(String(120), default="")
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)

SCHEMA_VERSION = 5

def _read_seed():
    p = ROOT / "data" / "melimi_seed.json"
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}

def _seed_language():
    seed = _read_seed()
    if not seed: return
    with SessionLocal() as db:
        # roots are upserted so adding a larger corpus later does not lose existing data
        for item in seed.get("roots", []):
            source = str(item.get("standard_root", "")).strip(); target = str(item.get("melimi_root", "")).strip().split("/")[0].strip()
            if not source or not target: continue
            row = db.scalar(select(MelimiRoot).where(MelimiRoot.standard_root == source))
            if not row:
                db.add(MelimiRoot(standard_root=source, melimi_root=target, meaning=str(item.get("meaning", "")), category=str(item.get("category", "")), status=str(item.get("status", "MASTER")).upper(), source=str(item.get("source", "master_corpus"))))
        for doc in seed.get("documents", []):
            path = str(doc.get("path", "")).strip()
            if not path: continue
            row = db.scalar(select(MelimiDocument).where(MelimiDocument.path == path))
            payload = json.dumps(doc.get("entries", []), ensure_ascii=False)
            if not row:
                db.add(MelimiDocument(path=path, kind=str(doc.get("kind", "other")), text=str(doc.get("text", "")), entries_json=payload, source=str(doc.get("source", "master_corpus")), status=str(doc.get("status", "MASTER"))))
            else:
                row.text = str(doc.get("text", row.text)); row.entries_json = payload
        for item in seed.get("affixes", []):
            form=str(item.get("form","")).strip(); kind=str(item.get("kind","other")).strip()
            if form and not db.scalar(select(MelimiAffix).where((MelimiAffix.form==form)&(MelimiAffix.kind==kind))):
                db.add(MelimiAffix(form=form, kind=kind, meaning=str(item.get("meaning","")), applies_to=str(item.get("applies_to","")), notes=str(item.get("notes",""))))
        for item in seed.get("rules", []):
            name=str(item.get("name","")).strip()
            if name and not db.scalar(select(MelimiRule).where(MelimiRule.name==name)):
                db.add(MelimiRule(name=name, category=str(item.get("category","grammar")), rule_text=str(item.get("rule_text","")), operation=str(item.get("operation",""))))
        for item in seed.get("examples", []):
            db.add(MelimiExample(standard_text=str(item.get("standard","")), melimi_text=str(item.get("melimi","")), category=str(item.get("category","")), source=str(item.get("source","user_corpus"))))
        for item in seed.get("knowledge", []):
            key=str(item.get("key","")).strip()
            if key and not db.scalar(select(KnowledgeEntry).where((KnowledgeEntry.kind==str(item.get("kind","FACT")))&(KnowledgeEntry.key==key))):
                db.add(KnowledgeEntry(kind=str(item.get("kind","FACT")), key=key, value=str(item.get("value","")), metadata_json=json.dumps(item.get("metadata",{}), ensure_ascii=False)))
        version=int(seed.get("version",1)); checksum=str(seed.get("checksum", ""))
        if not db.scalar(select(KnowledgeVersion).where(KnowledgeVersion.version==version)):
            db.add(KnowledgeVersion(version=version, source="melimi_seed", checksum=checksum))
        db.commit()

def _upgrade_existing_schema():
    # create_all does not add columns to an already-existing local SQLite DB.
    # Render/PostgreSQL normally starts with the migration schema, but this
    # small compatibility upgrader keeps local development and old databases
    # usable without deleting user data.
    from sqlalchemy import inspect
    inspector = inspect(engine)
    additions = {
        "melimi_roots": {"version":"INTEGER DEFAULT 1", "updated_at":"DATETIME"},
        "melimi_documents": {"version":"INTEGER DEFAULT 1"},
        "conversations": {"summary":"TEXT DEFAULT ''"},
        "users": {"role":"TEXT DEFAULT 'user'", "is_active":"BOOLEAN DEFAULT TRUE"},
    }
    with engine.begin() as conn:
        for table, cols in additions.items():
            if not inspector.has_table(table):
                continue
            existing={c["name"] for c in inspect(engine).get_columns(table)}
            for name, sqltype in cols.items():
                if name not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {sqltype}")

def init_db():
    Base.metadata.create_all(engine)
    _upgrade_existing_schema()
    Base.metadata.create_all(engine)
    _seed_language()

def _hash_password(password):
    salt=secrets.token_bytes(16); rounds=310000
    digest=hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${digest.hex()}"

def verify_password(password, encoded):
    try:
        _, rounds, salt_hex, digest_hex=encoded.split("$",3)
        digest=hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return secrets.compare_digest(digest.hex(), digest_hex)
    except Exception: return False

def create_user(username,email,password):
    with SessionLocal() as db:
        if db.scalar(select(User).where((User.username==username)|(User.email==email))): raise ValueError("Username or email is already registered.")
        u=User(username=username,email=email,password_hash=_hash_password(password),role="user",is_active=True); db.add(u); db.flush(); db.add(UserSetting(user_id=u.id)); db.commit(); return u

def authenticate(identifier,password):
    with SessionLocal() as db:
        u=db.scalar(select(User).where((User.email==identifier)|(User.username==identifier)))
        if not u or not getattr(u, "is_active", True) or not verify_password(password,u.password_hash): return None
        u.last_login=now(); db.commit(); return u

def create_session(user_id,days=30):
    raw=secrets.token_urlsafe(48); h=hashlib.sha256(raw.encode()).hexdigest()
    with SessionLocal() as db: db.add(Session(token_hash=h,user_id=user_id,expires_at=now()+timedelta(days=days))); db.commit()
    return raw

def user_from_session(raw):
    if not raw: return None
    h=hashlib.sha256(raw.encode()).hexdigest()
    with SessionLocal() as db:
        row=db.scalar(select(Session).where(Session.token_hash==h))
        if not row: return None
        exp=row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at
        if exp < now(): return None
        return db.get(User,row.user_id)

def delete_session(raw):
    if not raw:return
    h=hashlib.sha256(raw.encode()).hexdigest()
    with SessionLocal() as db: db.execute(delete(Session).where(Session.token_hash==h)); db.commit()

def create_conversation(user_id,title,mode):
    cid=str(uuid.uuid4()); t=now()
    with SessionLocal() as db: db.add(Conversation(id=cid,user_id=user_id,title=title[:200] or "New chat",mode=mode,created_at=t,updated_at=t)); db.commit()
    return cid

def save_message(user_id,conversation_id,role,content,model=None,input_tokens=None,output_tokens=None,latency_ms=None):
    with SessionLocal() as db:
        c=db.scalar(select(Conversation).where((Conversation.id==conversation_id)&(Conversation.user_id==user_id)))
        if not c: raise ValueError("Conversation not found.")
        m=Message(user_id=user_id,conversation_id=conversation_id,role=role,content=content,model=model,input_tokens=input_tokens,output_tokens=output_tokens,latency_ms=latency_ms); db.add(m); c.updated_at=now(); db.commit(); db.refresh(m); return m.id

def update_conversation_summary(user_id,conversation_id,summary):
    with SessionLocal() as db:
        c=db.scalar(select(Conversation).where((Conversation.id==conversation_id)&(Conversation.user_id==user_id)))
        if c: c.summary=summary[:10000]; c.updated_at=now(); db.commit()

def get_conversations(user_id):
    with SessionLocal() as db:
        rows=db.scalars(select(Conversation).where(Conversation.user_id==user_id).order_by(Conversation.updated_at.desc())).all()
        return [{"id":r.id,"title":r.title,"mode":r.mode,"summary":r.summary,"created_at":r.created_at.isoformat(),"updated_at":r.updated_at.isoformat()} for r in rows]

def get_history(user_id,conversation_id,limit=40):
    with SessionLocal() as db:
        c=db.scalar(select(Conversation).where((Conversation.id==conversation_id)&(Conversation.user_id==user_id)))
        if not c: raise ValueError("Conversation not found.")
        rows=db.scalars(select(Message).where((Message.conversation_id==conversation_id)&(Message.user_id==user_id)).order_by(Message.created_at.desc()).limit(limit)).all(); rows.reverse()
        return [{"id":r.id,"role":r.role,"content":r.content,"created_at":r.created_at.isoformat()} for r in rows]

def add_learning_candidate(user_id,knowledge_type,source_text,payload):
    with SessionLocal() as db:
        x=LearningCandidate(user_id=user_id,knowledge_type=knowledge_type,source_text=source_text,payload_json=json.dumps(payload,ensure_ascii=False)); db.add(x); db.commit(); db.refresh(x); return x.id

def save_usage(user_id,model,input_tokens,output_tokens,status="ok"):
    with SessionLocal() as db: db.add(Usage(user_id=user_id,model=model,input_tokens=input_tokens,output_tokens=output_tokens,status=status)); db.commit()

def list_candidates(status="PENDING"):
    with SessionLocal() as db:
        rows=db.scalars(select(LearningCandidate).where(LearningCandidate.status==status).order_by(LearningCandidate.created_at.desc())).all()
        return [{"id":r.id,"user_id":r.user_id,"knowledge_type":r.knowledge_type,"source_text":r.source_text,"payload":json.loads(r.payload_json or "{}"),"status":r.status,"created_at":r.created_at.isoformat()} for r in rows]

def review_candidate(candidate_id,approve,reviewer_note=""):
    with SessionLocal() as db:
        row=db.get(LearningCandidate,candidate_id)
        if not row:return None
        payload=json.loads(row.payload_json or "{}"); payload["reviewer_note"]=reviewer_note
        row.status="APPROVED" if approve else "REJECTED"; row.reviewed_at=now(); row.payload_json=json.dumps(payload,ensure_ascii=False)
        if approve and row.knowledge_type in {"ROOT","VOCABULARY"}:
            source=str(payload.get("source_root") or payload.get("standard_root") or payload.get("word") or "").strip()
            target=str(payload.get("melimi_root") or payload.get("melimi_equivalent") or "").strip()
            if source and target:
                existing=db.scalar(select(MelimiRoot).where(MelimiRoot.standard_root==source))
                if existing:
                    existing.melimi_root=target.split("/")[0].strip(); existing.status="APPROVED"; existing.source="approved_chat_learning"; existing.updated_at=now(); existing.version+=1
                else:
                    db.add(MelimiRoot(standard_root=source,melimi_root=target.split("/")[0].strip(),meaning=str(payload.get("meaning","")),category=str(payload.get("part_of_speech", "")),status="APPROVED",source="approved_chat_learning"))
        db.commit()
        # Invalidate in-process language caches immediately after approval.
        try:
            from app.melimi.root_morphology import reload_root_dictionary
            from app.melimi.registry import reload_registry
            from app.melimi.index import reload_index
            from app.melimi.firewall import reload_firewall
            reload_root_dictionary(); reload_registry(); reload_index(); reload_firewall()
        except Exception:
            pass
        return {"id":row.id,"status":row.status,"payload":payload}

def approved_learning():
    with SessionLocal() as db:
        rows=db.scalars(select(LearningCandidate).where(LearningCandidate.status=="APPROVED").order_by(LearningCandidate.created_at.asc())).all()
        return [json.loads(r.payload_json or "{}")|{"knowledge_type":r.knowledge_type} for r in rows]

def remember_user_memory(user_id,key,value):
    with SessionLocal() as db:
        row=db.scalar(select(UserMemory).where((UserMemory.user_id==user_id)&(UserMemory.key==key)))
        if row: row.value=value
        else: db.add(UserMemory(user_id=user_id,key=key,value=value))
        db.commit()

def recall_user_memory(user_id,limit=12):
    with SessionLocal() as db:
        rows=db.scalars(select(UserMemory).where(UserMemory.user_id==user_id).order_by(UserMemory.created_at.desc()).limit(limit)).all()
        return [{"key":r.key,"value":r.value} for r in rows]

def language_roots():
    init_db()
    with SessionLocal() as db:
        rows=db.scalars(select(MelimiRoot).where(MelimiRoot.status!="REJECTED")).all()
        return {r.standard_root:r.melimi_root for r in rows}

def language_documents():
    init_db()
    with SessionLocal() as db:
        rows=db.scalars(select(MelimiDocument).where(MelimiDocument.status!="REJECTED")).all()
        return [{"path":r.path,"kind":r.kind,"text":r.text,"entries":json.loads(r.entries_json or "[]")} for r in rows]

def language_rules():
    init_db()
    with SessionLocal() as db:
        return [{"name":r.name,"category":r.category,"rule_text":r.rule_text,"operation":r.operation} for r in db.scalars(select(MelimiRule).where(MelimiRule.status!="REJECTED")).all()]

def language_affixes():
    init_db()
    with SessionLocal() as db:
        return [{"form":r.form,"kind":r.kind,"meaning":r.meaning,"applies_to":r.applies_to,"notes":r.notes} for r in db.scalars(select(MelimiAffix).where(MelimiAffix.status!="REJECTED")).all()]

def knowledge_version():
    with SessionLocal() as db:
        row=db.scalars(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc())).first()
        return row.version if row else 1

def cache_get(key,mode="melimi"):
    with SessionLocal() as db:
        row=db.scalar(select(ResponseCache).where((ResponseCache.cache_key==key)&(ResponseCache.mode==mode)))
        if row and row.knowledge_version==knowledge_version(): return row.response
        return None

def cache_put(key,mode,response):
    with SessionLocal() as db:
        v=knowledge_version(); row=db.scalar(select(ResponseCache).where(ResponseCache.cache_key==key))
        if row: row.response=response; row.knowledge_version=v; row.created_at=now()
        else: db.add(ResponseCache(cache_key=key,mode=mode,knowledge_version=v,response=response))
        db.commit()

def audit_log(actor_user_id,action,target_type="",target_id="",details=None):
    with SessionLocal() as db: db.add(AuditLog(actor_user_id=actor_user_id,action=action,target_type=target_type,target_id=target_id,details_json=json.dumps(details or {},ensure_ascii=False))); db.commit()

def register_language_root(standard_root,melimi_root,metadata=None):
    return _register_language_root_approved({"standard_root":standard_root.strip(),"melimi_root":melimi_root.strip(),**(metadata or {})})

def _register_language_root_approved(payload):
    with SessionLocal() as db:
        source=payload["standard_root"]; target=payload["melimi_root"]
        row=db.scalar(select(MelimiRoot).where(MelimiRoot.standard_root==source))
        if row: row.melimi_root=target; row.status="APPROVED"; row.source="user_verified"; row.version+=1; row.updated_at=now()
        else: row=MelimiRoot(standard_root=source,melimi_root=target,meaning=str(payload.get("meaning","")),category=str(payload.get("part_of_speech","")),status="APPROVED",source="user_verified"); db.add(row)
        db.commit(); db.refresh(row); return row.id

def get_user_settings(user_id):
    with SessionLocal() as db:
        row=db.get(UserSetting,user_id)
        if not row:
            row=UserSetting(user_id=user_id); db.add(row); db.commit(); db.refresh(row)
        return {"preferred_mode":row.preferred_mode,"response_length":row.response_length,"memory_enabled":row.memory_enabled}

def update_user_settings(user_id, preferred_mode="melimi", response_length="normal", memory_enabled=True):
    with SessionLocal() as db:
        row=db.get(UserSetting,user_id)
        if not row: row=UserSetting(user_id=user_id); db.add(row)
        row.preferred_mode=preferred_mode; row.response_length=response_length; row.memory_enabled=memory_enabled; db.commit()
        return {"preferred_mode":row.preferred_mode,"response_length":row.response_length,"memory_enabled":row.memory_enabled}

def delete_conversation(user_id, conversation_id):
    with SessionLocal() as db:
        row=db.scalar(select(Conversation).where((Conversation.id==conversation_id)&(Conversation.user_id==user_id)))
        if not row:return False
        db.delete(row); db.commit(); return True


def get_user_by_id(user_id: int):
    with SessionLocal() as db:
        return db.get(User, user_id)


def list_users():
    with SessionLocal() as db:
        rows = db.scalars(select(User).order_by(User.created_at.asc())).all()
        return [{
            "id": r.id, "username": r.username, "email": r.email,
            "role": r.role, "is_active": r.is_active,
            "created_at": r.created_at.isoformat(),
            "last_login": r.last_login.isoformat() if r.last_login else None,
        } for r in rows]


def set_user_role(target_id: int, role: str):
    role = role.lower().strip()
    if role not in {"user", "admin", "owner"}:
        raise ValueError("Invalid role.")
    with SessionLocal() as db:
        row = db.get(User, target_id)
        if not row: return None
        row.role = role
        db.commit(); db.refresh(row)
        return {"id": row.id, "username": row.username, "email": row.email, "role": row.role, "is_active": row.is_active}


def set_user_active(target_id: int, active: bool):
    with SessionLocal() as db:
        row = db.get(User, target_id)
        if not row: return None
        row.is_active = bool(active)
        db.commit(); db.refresh(row)
        return {"id": row.id, "username": row.username, "email": row.email, "role": row.role, "is_active": row.is_active}


def delete_user(target_id: int):
    with SessionLocal() as db:
        row = db.get(User, target_id)
        if not row: return False
        db.delete(row); db.commit(); return True


def database_stats():
    with SessionLocal() as db:
        return {
            "users": db.scalar(select(func.count()).select_from(User)) or 0,
            "active_users": db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0,
            "admins": db.scalar(select(func.count()).select_from(User).where(User.role == "admin")) or 0,
            "owners": db.scalar(select(func.count()).select_from(User).where(User.role == "owner")) or 0,
            "conversations": db.scalar(select(func.count()).select_from(Conversation)) or 0,
            "messages": db.scalar(select(func.count()).select_from(Message)) or 0,
            "melimi_roots": db.scalar(select(func.count()).select_from(MelimiRoot)) or 0,
            "melimi_documents": db.scalar(select(func.count()).select_from(MelimiDocument)) or 0,
            "melimi_affixes": db.scalar(select(func.count()).select_from(MelimiAffix)) or 0,
            "melimi_rules": db.scalar(select(func.count()).select_from(MelimiRule)) or 0,
            "melimi_examples": db.scalar(select(func.count()).select_from(MelimiExample)) or 0,
            "knowledge_entries": db.scalar(select(func.count()).select_from(KnowledgeEntry)) or 0,
            "pending_learning": db.scalar(select(func.count()).select_from(LearningCandidate).where(LearningCandidate.status == "PENDING")) or 0,
            "feedback": db.scalar(select(func.count()).select_from(Feedback)) or 0,
            "usage_records": db.scalar(select(func.count()).select_from(Usage)) or 0,
            "audit_logs": db.scalar(select(func.count()).select_from(AuditLog)) or 0,
        }


def list_audit_logs(limit: int = 100):
    with SessionLocal() as db:
        rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(max(1, min(limit, 500)))).all()
        return [{
            "id": r.id, "actor_user_id": r.actor_user_id, "action": r.action,
            "target_type": r.target_type, "target_id": r.target_id,
            "details": json.loads(r.details_json or "{}"), "created_at": r.created_at.isoformat()
        } for r in rows]


def bootstrap_owner(email: str):
    email = email.strip().lower()
    with SessionLocal() as db:
        existing_owner = db.scalar(select(User).where(User.role == "owner"))
        if existing_owner:
            return None, "An owner already exists."
        row = db.scalar(select(User).where(User.email == email))
        if not row:
            return None, "Register the owner account first using the configured owner email."
        row.role = "owner"
        db.commit(); db.refresh(row)
        return row, None

def language_snapshot(limit: int = 50):
    with SessionLocal() as db:
        roots = db.scalars(select(MelimiRoot).order_by(MelimiRoot.updated_at.desc()).limit(max(1, min(limit, 200)))).all()
        rules = db.scalars(select(MelimiRule).order_by(MelimiRule.id.desc()).limit(max(1, min(limit, 200)))).all()
        return {
            "roots": [{"id": r.id, "standard_root": r.standard_root, "melimi_root": r.melimi_root, "meaning": r.meaning, "status": r.status, "source": r.source, "version": r.version} for r in roots],
            "rules": [{"id": r.id, "name": r.name, "category": r.category, "status": r.status, "source": r.source, "version": r.version} for r in rules],
        }
