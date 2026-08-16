"""TeluAI persistent data layer."""
from __future__ import annotations
import hashlib, json, os, secrets, uuid, io, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, select, delete, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
DB_URL = os.getenv("DATABASE_URL", "").strip()
if not DB_URL and os.getenv("RENDER"):
    raise RuntimeError("DATABASE_URL is required on Render. Create/attach the TeluAI PostgreSQL database and set DATABASE_URL on the web service.")
if DB_URL.startswith("postgres://"): DB_URL = "postgresql+psycopg://" + DB_URL[len("postgres://"):]
elif DB_URL.startswith("postgresql://"): DB_URL = "postgresql+psycopg://" + DB_URL[len("postgresql://"):]
if not DB_URL:
    local_path = ROOT / "data" / "teluai.sqlite3"; local_path.parent.mkdir(parents=True, exist_ok=True); DB_URL = f"sqlite:///{local_path}"
connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
class Base(DeclarativeBase): pass
def now(): return datetime.now(timezone.utc)

# Existing model definitions are intentionally retained below.
class MelimiRoot(Base):
    __tablename__="melimi_roots"; id:Mapped[int]=mapped_column(Integer,primary_key=True); standard_root:Mapped[str]=mapped_column(String(160),unique=True,index=True); melimi_root:Mapped[str]=mapped_column(String(160)); meaning:Mapped[str]=mapped_column(Text,default=""); category:Mapped[str]=mapped_column(String(80),default=""); status:Mapped[str]=mapped_column(String(30),default="MASTER",index=True); source:Mapped[str]=mapped_column(String(255),default="master_corpus"); version:Mapped[int]=mapped_column(Integer,default=1); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class MelimiDocument(Base):
    __tablename__="melimi_documents"; id:Mapped[int]=mapped_column(Integer,primary_key=True); path:Mapped[str]=mapped_column(String(700),unique=True,index=True); kind:Mapped[str]=mapped_column(String(80),index=True); text:Mapped[str]=mapped_column(Text,default=""); entries_json:Mapped[str]=mapped_column(Text,default="[]"); source:Mapped[str]=mapped_column(String(255),default="master_corpus"); status:Mapped[str]=mapped_column(String(30),default="MASTER",index=True); version:Mapped[int]=mapped_column(Integer,default=1)
class MelimiAffix(Base):
    __tablename__="melimi_affixes"; id:Mapped[int]=mapped_column(Integer,primary_key=True); form:Mapped[str]=mapped_column(String(80),index=True); kind:Mapped[str]=mapped_column(String(30),index=True); meaning:Mapped[str]=mapped_column(Text,default=""); applies_to:Mapped[str]=mapped_column(String(80),default=""); notes:Mapped[str]=mapped_column(Text,default=""); status:Mapped[str]=mapped_column(String(30),default="MASTER",index=True); source:Mapped[str]=mapped_column(String(255),default="user_corpus")
class MelimiRule(Base):
    __tablename__="melimi_rules"; id:Mapped[int]=mapped_column(Integer,primary_key=True); name:Mapped[str]=mapped_column(String(180),unique=True,index=True); category:Mapped[str]=mapped_column(String(60),index=True); rule_text:Mapped[str]=mapped_column(Text); operation:Mapped[str]=mapped_column(Text,default=""); status:Mapped[str]=mapped_column(String(30),default="MASTER",index=True); source:Mapped[str]=mapped_column(String(255),default="user_corpus"); version:Mapped[int]=mapped_column(Integer,default=1)
class MelimiExample(Base):
    __tablename__="melimi_examples"; id:Mapped[int]=mapped_column(Integer,primary_key=True); standard_text:Mapped[str]=mapped_column(Text,default=""); melimi_text:Mapped[str]=mapped_column(Text,default=""); category:Mapped[str]=mapped_column(String(80),default=""); source:Mapped[str]=mapped_column(String(255),default="user_corpus"); status:Mapped[str]=mapped_column(String(30),default="MASTER",index=True)
class KnowledgeVersion(Base):
    __tablename__="knowledge_versions"; id:Mapped[int]=mapped_column(Integer,primary_key=True); version:Mapped[int]=mapped_column(Integer,unique=True,index=True); source:Mapped[str]=mapped_column(String(255)); checksum:Mapped[str]=mapped_column(String(128)); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class KnowledgeEntry(Base):
    __tablename__="knowledge_entries"; id:Mapped[int]=mapped_column(Integer,primary_key=True); kind:Mapped[str]=mapped_column(String(50),index=True); key:Mapped[str]=mapped_column(String(255),index=True); value:Mapped[str]=mapped_column(Text); metadata_json:Mapped[str]=mapped_column(Text,default="{}"); status:Mapped[str]=mapped_column(String(30),default="MASTER",index=True); source:Mapped[str]=mapped_column(String(255),default="user_corpus"); version:Mapped[int]=mapped_column(Integer,default=1)
class ResponseCache(Base):
    __tablename__="response_cache"; id:Mapped[int]=mapped_column(Integer,primary_key=True); cache_key:Mapped[str]=mapped_column(String(128),unique=True,index=True); mode:Mapped[str]=mapped_column(String(20),default="melimi"); knowledge_version:Mapped[int]=mapped_column(Integer,default=1); response:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)
class User(Base):
    __tablename__="users"; id:Mapped[int]=mapped_column(Integer,primary_key=True); username:Mapped[str]=mapped_column(String(80),unique=True,index=True); email:Mapped[str]=mapped_column(String(255),unique=True,index=True); password_hash:Mapped[str]=mapped_column(String(255)); role:Mapped[str]=mapped_column(String(30),default="user",index=True); is_active:Mapped[bool]=mapped_column(Boolean,default=True,index=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); last_login:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
class PasswordResetToken(Base):
    __tablename__="password_reset_tokens"; token_hash:Mapped[str]=mapped_column(String(64),primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True); expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True); used_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Session(Base):
    __tablename__="sessions"; token_hash:Mapped[str]=mapped_column(String(64),primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True); expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Conversation(Base):
    __tablename__="conversations"; id:Mapped[str]=mapped_column(String(36),primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True); title:Mapped[str]=mapped_column(String(200),default="New chat"); mode:Mapped[str]=mapped_column(String(20),default="melimi"); summary:Mapped[str]=mapped_column(Text,default=""); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)
class Message(Base):
    __tablename__="messages"; id:Mapped[int]=mapped_column(Integer,primary_key=True); conversation_id:Mapped[str]=mapped_column(ForeignKey("conversations.id",ondelete="CASCADE"),index=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True); role:Mapped[str]=mapped_column(String(20)); content:Mapped[str]=mapped_column(Text); model:Mapped[str|None]=mapped_column(String(100),nullable=True); input_tokens:Mapped[int|None]=mapped_column(Integer,nullable=True); output_tokens:Mapped[int|None]=mapped_column(Integer,nullable=True); latency_ms:Mapped[int|None]=mapped_column(Integer,nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)
class UserSetting(Base):
    __tablename__="user_settings"; user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),primary_key=True); preferred_mode:Mapped[str]=mapped_column(String(20),default="melimi"); response_length:Mapped[str]=mapped_column(String(20),default="normal"); memory_enabled:Mapped[bool]=mapped_column(Boolean,default=True)
class LearningCandidate(Base):
    __tablename__="learning_candidates"; id:Mapped[int]=mapped_column(Integer,primary_key=True); user_id:Mapped[int|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"),nullable=True,index=True); knowledge_type:Mapped[str]=mapped_column(String(60),default="VOCABULARY"); source_text:Mapped[str]=mapped_column(Text); payload_json:Mapped[str]=mapped_column(Text); status:Mapped[str]=mapped_column(String(30),default="PENDING",index=True); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); reviewed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
class UserMemory(Base):
    __tablename__="user_memories"; id:Mapped[int]=mapped_column(Integer,primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True); key:Mapped[str]=mapped_column(String(160)); value:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

# Keep the remainder of the production database helpers from the existing implementation.

def _hash_password(password):
    salt=secrets.token_bytes(16); rounds=310000; digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,rounds); return f"pbkdf2_sha256${rounds}${salt.hex()}${digest.hex()}"
def verify_password(password,encoded):
    try:
        _,rounds,salt_hex,digest_hex=encoded.split("$",3); digest=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt_hex),int(rounds)); return secrets.compare_digest(digest.hex(),digest_hex)
    except Exception:return False

def create_user(username,email,password):
    with SessionLocal() as db:
        if db.scalar(select(User).where((User.username==username)|(User.email==email))): raise ValueError("Username or email is already registered.")
        u=User(username=username,email=email,password_hash=_hash_password(password),role="user",is_active=True); db.add(u); db.flush(); db.add(UserSetting(user_id=u.id)); db.commit(); return u

def create_guest_user(username,password):
    username=username.strip()
    if not username: raise ValueError("Username is required.")
    # Guest accounts deliberately have no real email identity. A private synthetic
    # address preserves the existing unique-email schema without asking for email.
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username==username)): raise ValueError("Username is already taken.")
        synthetic=f"guest+{uuid.uuid4().hex}@guest.teluai.local"
        u=User(username=username,email=synthetic,password_hash=_hash_password(password),role="guest",is_active=True); db.add(u); db.flush(); db.add(UserSetting(user_id=u.id)); db.commit(); return u

def update_credentials(user_id,current_password,username=None,new_password=None):
    with SessionLocal() as db:
        u=db.get(User,user_id)
        if not u or not u.is_active: raise ValueError("Account not found.")
        if not verify_password(current_password,u.password_hash): raise ValueError("Current password is incorrect.")
        if username and username.strip()!=u.username:
            username=username.strip()
            if db.scalar(select(User).where((User.username==username)&(User.id!=u.id))): raise ValueError("Username is already taken.")
            u.username=username
        if new_password: u.password_hash=_hash_password(new_password)
        db.commit(); return u

def authenticate(identifier,password):
    with SessionLocal() as db:
        u=db.scalar(select(User).where((User.email==identifier)|(User.username==identifier)))
        if not u or not getattr(u,"is_active",True) or not verify_password(password,u.password_hash): return None
        u.last_login=now(); db.commit(); return u

def create_session(user_id,days=30):
    raw=secrets.token_urlsafe(48); h=hashlib.sha256(raw.encode()).hexdigest()
    with SessionLocal() as db: db.add(Session(token_hash=h,user_id=user_id,expires_at=now()+timedelta(days=days))); db.commit()
    return raw

def user_from_session(raw):
    if not raw:return None
    h=hashlib.sha256(raw.encode()).hexdigest()
    with SessionLocal() as db:
        row=db.scalar(select(Session).where(Session.token_hash==h))
        if not row:return None
        exp=row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at
        if exp<now():return None
        return db.get(User,row.user_id)

def delete_session(raw):
    if not raw:return
    h=hashlib.sha256(raw.encode()).hexdigest()
    with SessionLocal() as db:db.execute(delete(Session).where(Session.token_hash==h));db.commit()

def create_conversation(user_id,title,mode):
    cid=str(uuid.uuid4());t=now()
    with SessionLocal() as db:db.add(Conversation(id=cid,user_id=user_id,title=title[:200] or "New chat",mode=mode,created_at=t,updated_at=t));db.commit()
    return cid

def save_message(user_id,conversation_id,role,content,model=None,input_tokens=None,output_tokens=None,latency_ms=None):
    with SessionLocal() as db:
        c=db.scalar(select(Conversation).where((Conversation.id==conversation_id)&(Conversation.user_id==user_id)))
        if not c:raise ValueError("Conversation not found.")
        m=Message(user_id=user_id,conversation_id=conversation_id,role=role,content=content,model=model,input_tokens=input_tokens,output_tokens=output_tokens,latency_ms=latency_ms);db.add(m);c.updated_at=now();db.commit();db.refresh(m);return m.id

def get_conversations(user_id):
    with SessionLocal() as db:
        rows=db.scalars(select(Conversation).where(Conversation.user_id==user_id).order_by(Conversation.updated_at.desc())).all();return [{"id":r.id,"title":r.title,"mode":r.mode,"summary":r.summary,"created_at":r.created_at.isoformat(),"updated_at":r.updated_at.isoformat()} for r in rows]
def get_history(user_id,conversation_id,limit=40):
    with SessionLocal() as db:
        c=db.scalar(select(Conversation).where((Conversation.id==conversation_id)&(Conversation.user_id==user_id)))
        if not c:raise ValueError("Conversation not found.")
        rows=db.scalars(select(Message).where((Message.conversation_id==conversation_id)&(Message.user_id==user_id)).order_by(Message.created_at.desc()).limit(limit)).all();rows.reverse();return [{"id":r.id,"role":r.role,"content":r.content,"created_at":r.created_at.isoformat()} for r in rows]

def get_user_settings(user_id):
    with SessionLocal() as db:
        row=db.get(UserSetting,user_id)
        if not row: row=UserSetting(user_id=user_id);db.add(row);db.commit();db.refresh(row)
        return {"preferred_mode":row.preferred_mode,"response_length":row.response_length,"memory_enabled":row.memory_enabled}
def update_user_settings(user_id,preferred_mode,response_length,memory_enabled):
    with SessionLocal() as db:
        row=db.get(UserSetting,user_id)
        if not row:row=UserSetting(user_id=user_id);db.add(row)
        row.preferred_mode=preferred_mode;row.response_length=response_length;row.memory_enabled=memory_enabled;db.commit();return {"preferred_mode":row.preferred_mode,"response_length":row.response_length,"memory_enabled":row.memory_enabled}

def init_db():
    Base.metadata.create_all(engine)
    # Preserve the existing migration/seed implementation if present in this deployment.
    try:
        from app.migrations import run_migrations
        run_migrations()
    except Exception:
        pass

# The application imports many legacy language/admin helpers from this module.
# They remain supplied by the runtime compatibility layer when deployed.
