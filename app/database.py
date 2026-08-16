"""TeluAI persistent data layer with first-class guest accounts."""
from __future__ import annotations
import hashlib,json,os,secrets,uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
from sqlalchemy import Boolean,DateTime,ForeignKey,Integer,String,Text,create_engine,select,delete,func
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,sessionmaker
ROOT=Path(__file__).resolve().parents[1];DB_URL=os.getenv("DATABASE_URL","").strip()
if not DB_URL and os.getenv("RENDER"):raise RuntimeError("DATABASE_URL is required on Render.")
if DB_URL.startswith("postgres://"):DB_URL="postgresql+psycopg://"+DB_URL[len("postgres://"):]
elif DB_URL.startswith("postgresql://"):DB_URL="postgresql+psycopg://"+DB_URL[len("postgresql://"):]
if not DB_URL:
 p=ROOT/"data"/"teluai.sqlite3";p.parent.mkdir(parents=True,exist_ok=True);DB_URL=f"sqlite:///{p}"
engine=create_engine(DB_URL,pool_pre_ping=True,connect_args={"check_same_thread":False} if DB_URL.startswith("sqlite") else {});SessionLocal=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
class Base(DeclarativeBase):pass
def now():return datetime.now(timezone.utc)
class MelimiRoot(Base):
 __tablename__="melimi_roots";id:Mapped[int]=mapped_column(Integer,primary_key=True);standard_root:Mapped[str]=mapped_column(String(160),unique=True,index=True);melimi_root:Mapped[str]=mapped_column(String(160));meaning:Mapped[str]=mapped_column(Text,default="");category:Mapped[str]=mapped_column(String(80),default="");status:Mapped[str]=mapped_column(String(30),default="MASTER",index=True);source:Mapped[str]=mapped_column(String(255),default="master_corpus");version:Mapped[int]=mapped_column(Integer,default=1);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class MelimiDocument(Base):
 __tablename__="melimi_documents";id:Mapped[int]=mapped_column(Integer,primary_key=True);path:Mapped[str]=mapped_column(String(700),unique=True,index=True);kind:Mapped[str]=mapped_column(String(80),index=True);text:Mapped[str]=mapped_column(Text,default="");entries_json:Mapped[str]=mapped_column(Text,default="[]");source:Mapped[str]=mapped_column(String(255),default="master_corpus");status:Mapped[str]=mapped_column(String(30),default="MASTER",index=True);version:Mapped[int]=mapped_column(Integer,default=1)
class MelimiAffix(Base):
 __tablename__="melimi_affixes";id:Mapped[int]=mapped_column(Integer,primary_key=True);form:Mapped[str]=mapped_column(String(80),index=True);kind:Mapped[str]=mapped_column(String(30),index=True);meaning:Mapped[str]=mapped_column(Text,default="");applies_to:Mapped[str]=mapped_column(String(80),default="");notes:Mapped[str]=mapped_column(Text,default="");status:Mapped[str]=mapped_column(String(30),default="MASTER",index=True);source:Mapped[str]=mapped_column(String(255),default="user_corpus")
class MelimiRule(Base):
 __tablename__="melimi_rules";id:Mapped[int]=mapped_column(Integer,primary_key=True);name:Mapped[str]=mapped_column(String(180),unique=True,index=True);category:Mapped[str]=mapped_column(String(60),index=True);rule_text:Mapped[str]=mapped_column(Text);operation:Mapped[str]=mapped_column(Text,default="");status:Mapped[str]=mapped_column(String(30),default="MASTER",index=True);source:Mapped[str]=mapped_column(String(255),default="user_corpus");version:Mapped[int]=mapped_column(Integer,default=1)
class MelimiExample(Base):
 __tablename__="melimi_examples";id:Mapped[int]=mapped_column(Integer,primary_key=True);standard_text:Mapped[str]=mapped_column(Text,default="");melimi_text:Mapped[str]=mapped_column(Text,default="");category:Mapped[str]=mapped_column(String(80),default="");source:Mapped[str]=mapped_column(String(255),default="user_corpus");status:Mapped[str]=mapped_column(String(30),default="MASTER",index=True)
class KnowledgeVersion(Base):
 __tablename__="knowledge_versions";id:Mapped[int]=mapped_column(Integer,primary_key=True);version:Mapped[int]=mapped_column(Integer,unique=True,index=True);source:Mapped[str]=mapped_column(String(255));checksum:Mapped[str]=mapped_column(String(128));created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class KnowledgeEntry(Base):
 __tablename__="knowledge_entries";id:Mapped[int]=mapped_column(Integer,primary_key=True);kind:Mapped[str]=mapped_column(String(50),index=True);key:Mapped[str]=mapped_column(String(255),index=True);value:Mapped[str]=mapped_column(Text);metadata_json:Mapped[str]=mapped_column(Text,default="{}");status:Mapped[str]=mapped_column(String(30),default="MASTER",index=True);source:Mapped[str]=mapped_column(String(255),default="user_corpus");version:Mapped[int]=mapped_column(Integer,default=1)
class ResponseCache(Base):
 __tablename__="response_cache";id:Mapped[int]=mapped_column(Integer,primary_key=True);cache_key:Mapped[str]=mapped_column(String(128),unique=True,index=True);mode:Mapped[str]=mapped_column(String(20),default="melimi");knowledge_version:Mapped[int]=mapped_column(Integer,default=1);response:Mapped[str]=mapped_column(Text);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)
class User(Base):
 __tablename__="users";id:Mapped[int]=mapped_column(Integer,primary_key=True);username:Mapped[str]=mapped_column(String(80),unique=True,index=True);email:Mapped[str]=mapped_column(String(255),unique=True,index=True);password_hash:Mapped[str]=mapped_column(String(255));role:Mapped[str]=mapped_column(String(30),default="user",index=True);is_active:Mapped[bool]=mapped_column(Boolean,default=True,index=True);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now);last_login:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
class PasswordResetToken(Base):
 __tablename__="password_reset_tokens";token_hash:Mapped[str]=mapped_column(String(64),primary_key=True);user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True);expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True);used_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Session(Base):
 __tablename__="sessions";token_hash:Mapped[str]=mapped_column(String(64),primary_key=True);user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True);expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Conversation(Base):
 __tablename__="conversations";id:Mapped[str]=mapped_column(String(36),primary_key=True);user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True);title:Mapped[str]=mapped_column(String(200),default="New chat");mode:Mapped[str]=mapped_column(String(20),default="melimi");summary:Mapped[str]=mapped_column(Text,default="");created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)
class Message(Base):
 __tablename__="messages";id:Mapped[int]=mapped_column(Integer,primary_key=True);conversation_id:Mapped[str]=mapped_column(ForeignKey("conversations.id",ondelete="CASCADE"),index=True);user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True);role:Mapped[str]=mapped_column(String(20));content:Mapped[str]=mapped_column(Text);model:Mapped[str|None]=mapped_column(String(100),nullable=True);input_tokens:Mapped[int|None]=mapped_column(Integer,nullable=True);output_tokens:Mapped[int|None]=mapped_column(Integer,nullable=True);latency_ms:Mapped[int|None]=mapped_column(Integer,nullable=True);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)
class UserSetting(Base):
 __tablename__="user_settings";user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),primary_key=True);preferred_mode:Mapped[str]=mapped_column(String(20),default="melimi");response_length:Mapped[str]=mapped_column(String(20),default="normal");memory_enabled:Mapped[bool]=mapped_column(Boolean,default=True)
class LearningCandidate(Base):
 __tablename__="learning_candidates";id:Mapped[int]=mapped_column(Integer,primary_key=True);user_id:Mapped[int|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"),nullable=True,index=True);knowledge_type:Mapped[str]=mapped_column(String(60),default="VOCABULARY");source_text:Mapped[str]=mapped_column(Text);payload_json:Mapped[str]=mapped_column(Text,default="{}");status:Mapped[str]=mapped_column(String(20),default="PENDING",index=True);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now);reviewed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
class UserMemory(Base):
 __tablename__="user_memory";id:Mapped[int]=mapped_column(Integer,primary_key=True);user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True);key:Mapped[str]=mapped_column(String(160));value:Mapped[str]=mapped_column(Text);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Feedback(Base):
 __tablename__="feedback";id:Mapped[int]=mapped_column(Integer,primary_key=True);user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True);message_id:Mapped[int|None]=mapped_column(ForeignKey("messages.id",ondelete="SET NULL"),nullable=True);rating:Mapped[int]=mapped_column(Integer);text:Mapped[str]=mapped_column(Text,default="");created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Usage(Base):
 __tablename__="usage";id:Mapped[int]=mapped_column(Integer,primary_key=True);user_id:Mapped[int|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"),nullable=True,index=True);model:Mapped[str|None]=mapped_column(String(100),nullable=True);input_tokens:Mapped[int|None]=mapped_column(Integer,nullable=True);output_tokens:Mapped[int|None]=mapped_column(Integer,nullable=True);status:Mapped[str]=mapped_column(String(60),default="ok");created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)
class AuditLog(Base):
 __tablename__="audit_logs";id:Mapped[int]=mapped_column(Integer,primary_key=True);actor_user_id:Mapped[int|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"),nullable=True,index=True);action:Mapped[str]=mapped_column(String(100),index=True);target_type:Mapped[str]=mapped_column(String(80),default="");target_id:Mapped[str]=mapped_column(String(120),default="");details_json:Mapped[str]=mapped_column(Text,default="{}");created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
def _hash_password(p):
 salt=secrets.token_bytes(16);r=310000;d=hashlib.pbkdf2_hmac("sha256",p.encode(),salt,r);return f"pbkdf2_sha256${r}${salt.hex()}${d.hex()}"
def verify_password(p,e):
 try:_,r,s,d=e.split("$",3);x=hashlib.pbkdf2_hmac("sha256",p.encode(),bytes.fromhex(s),int(r));return secrets.compare_digest(x.hex(),d)
 except Exception:return False
def create_user(username,email,password):
 with SessionLocal() as db:
  if db.scalar(select(User).where((User.username==username)|(User.email==email))):raise ValueError("Username or email is already registered.")
  role="guest" if email.lower().endswith("@guest.teluai.local") else "user";u=User(username=username.strip(),email=email.lower(),password_hash=_hash_password(password),role=role,is_active=True);db.add(u);db.flush();db.add(UserSetting(user_id=u.id));db.commit();return u
def create_guest_user(username,password):
 with SessionLocal() as db:
  if db.scalar(select(User).where(User.username==username.strip())):raise ValueError("Username is already taken.")
  u=User(username=username.strip(),email=f"guest+{uuid.uuid4().hex}@guest.teluai.local",password_hash=_hash_password(password),role="guest",is_active=True);db.add(u);db.flush();db.add(UserSetting(user_id=u.id));db.commit();return u
def update_credentials(user_id,current_password,username=None,new_password=None):
 with SessionLocal() as db:
  u=db.get(User,user_id)
  if not u or not u.is_active:raise ValueError("Account not found.")
  if not verify_password(current_password,u.password_hash):raise ValueError("Current password is incorrect.")
  if username and username.strip()!=u.username:
   username=username.strip()
   if db.scalar(select(User).where((User.username==username)&(User.id!=u.id))):raise ValueError("Username is already taken.")
   u.username=username
  if new_password:u.password_hash=_hash_password(new_password)
  db.commit();return u

def authenticate(identifier,password):
 with SessionLocal() as db:
  u=db.scalar(select(User).where((User.username==identifier)|(User.email==identifier.lower())))
  if not u or not u.is_active or not verify_password(password,u.password_hash):return None
  u.last_login=now();db.commit();return u

def create_session(user_id,days=30):
 raw=secrets.token_urlsafe(32);h=hashlib.sha256(raw.encode()).hexdigest()
 with SessionLocal() as db:db.add(Session(token_hash=h,user_id=user_id,expires_at=now()+timedelta(days=days)));db.commit()
 return raw

def get_user_by_session(raw):
 if not raw:return None
 h=hashlib.sha256(raw.encode()).hexdigest()
 with SessionLocal() as db:
  s=db.scalar(select(Session).where(Session.token_hash==h,Session.expires_at>now()))
  return db.get(User,s.user_id) if s else None

def delete_session(raw):
 if not raw:return
 h=hashlib.sha256(raw.encode()).hexdigest()
 with SessionLocal() as db:db.execute(delete(Session).where(Session.token_hash==h));db.commit()

def ensure_schema():Base.metadata.create_all(engine)

def get_or_create_conversation(user_id,conversation_id=None,mode="melimi"):
 with SessionLocal() as db:
  if conversation_id:
   c=db.get(Conversation,str(conversation_id))
   if c and c.user_id==user_id:return c
  c=Conversation(id=str(uuid.uuid4()),user_id=user_id,mode=mode,title="New chat");db.add(c);db.commit();return c

def save_message(conversation_id,user_id,role,content,model=None,input_tokens=None,output_tokens=None,latency_ms=None):
 with SessionLocal() as db:
  c=db.get(Conversation,str(conversation_id))
  if not c or c.user_id!=user_id:raise ValueError("Conversation not found")
  m=Message(conversation_id=c.id,user_id=user_id,role=role,content=content,model=model,input_tokens=input_tokens,output_tokens=output_tokens,latency_ms=latency_ms);db.add(m);c.updated_at=now();db.commit();return m

def get_conversation_messages(user_id,conversation_id,limit=20):
 with SessionLocal() as db:
  c=db.get(Conversation,str(conversation_id))
  if not c or c.user_id!=user_id:return []
  return list(db.scalars(select(Message).where(Message.conversation_id=c.id).order_by(Message.created_at.desc()).limit(limit)))[::-1]

def list_conversations(user_id,limit=50):
 with SessionLocal() as db:return list(db.scalars(select(Conversation).where(Conversation.user_id==user_id).order_by(Conversation.updated_at.desc()).limit(limit)))
