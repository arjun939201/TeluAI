"""TeluAI persistent data layer with first-class guest accounts."""
from __future__ import annotations
import hashlib,json,os,secrets,uuid,io,zipfile
from datetime import datetime,timedelta,timezone
from pathlib import Path
from sqlalchemy import Boolean,DateTime,ForeignKey,Integer,String,Text,create_engine,select,delete,func
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,sessionmaker
ROOT=Path(__file__).resolve().parents[1]
DB_URL=os.getenv("DATABASE_URL","").strip()
if not DB_URL and os.getenv("RENDER"): raise RuntimeError("DATABASE_URL is required on Render.")
if DB_URL.startswith("postgres://"): DB_URL="postgresql+psycopg://"+DB_URL[len("postgres://"):]
elif DB_URL.startswith("postgresql://"): DB_URL="postgresql+psycopg://"+DB_URL[len("postgresql://"):]
if not DB_URL:
    p=ROOT/"data"/"teluai.sqlite3";p.parent.mkdir(parents=True,exist_ok=True);DB_URL=f"sqlite:///{p}"
engine=create_engine(DB_URL,pool_pre_ping=True,connect_args={"check_same_thread":False} if DB_URL.startswith("sqlite") else {})
SessionLocal=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
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
 __tablename__="audit_logs";id:Mapped[int]=mapped_column(Integer,primary_key=True);actor_user_id:Mapped[int|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"),nullable=True,index=True);action:Mapped[str]=mapped_column(String(100),index=True);target_type:Mapped[str]=mapped_column(String(80),default="");target_id:Mapped[str]=mapped_column(String(120),default="");details_json:Mapped[str]=mapped_column(Text,default="{}");created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)

def _hash_password(p):
 salt=secrets.token_bytes(16);r=310000;d=hashlib.pbkdf2_hmac("sha256",p.encode(),salt,r);return f"pbkdf2_sha256${r}${salt.hex()}${d.hex()}"
def verify_password(p,e):
 try:
  _,r,s,d=e.split("$",3);x=hashlib.pbkdf2_hmac("sha256",p.encode(),bytes.fromhex(s),int(r));return secrets.compare_digest(x.hex(),d)
 except Exception:return False
def create_user(username,email,password):
 with SessionLocal() as db:
  if db.scalar(select(User).where((User.username==username)|(User.email==email))):raise ValueError("Username or email is already registered.")
  u=User(username=username.strip(),email=email.lower(),password_hash=_hash_password(password),role="user",is_active=True);db.add(u);db.flush();db.add(UserSetting(user_id=u.id));db.commit();return u
def create_guest_user(username,password):
 with SessionLocal() as db:
  username=username.strip()
  if db.scalar(select(User).where(User.username==username)):raise ValueError("Username is already taken.")
  email=f"guest+{uuid.uuid4().hex}@guest.teluai.local";u=User(username=username,email=email,password_hash=_hash_password(password),role="guest",is_active=True);db.add(u);db.flush();db.add(UserSetting(user_id=u.id));db.commit();return u
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
  u=db.scalar(select(User).where((User.email==identifier.lower())|(User.username==identifier)))
  if not u or not u.is_active or not verify_password(password,u.password_hash):return None
  u.last_login=now();db.commit();return u
def create_session(uid,days=30):
 raw=secrets.token_urlsafe(48);h=hashlib.sha256(raw.encode()).hexdigest()
 with SessionLocal() as db:db.add(Session(token_hash=h,user_id=uid,expires_at=now()+timedelta(days=days)));db.commit()
 return raw
def user_from_session(raw):
 if not raw:return None
 h=hashlib.sha256(raw.encode()).hexdigest()
 with SessionLocal() as db:
  row=db.scalar(select(Session).where(Session.token_hash==h))
  if not row:return None
  exp=row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at
  return db.get(User,row.user_id) if exp>=now() else None
def delete_session(raw):
 if raw:
  h=hashlib.sha256(raw.encode()).hexdigest()
  with SessionLocal() as db:db.execute(delete(Session).where(Session.token_hash==h));db.commit()
def create_conversation(uid,title,mode):
 cid=str(uuid.uuid4());t=now()
 with SessionLocal() as db:db.add(Conversation(id=cid,user_id=uid,title=title[:200] or "New chat",mode=mode,created_at=t,updated_at=t));db.commit()
 return cid
def save_message(uid,cid,role,content,model=None,input_tokens=None,output_tokens=None,latency_ms=None):
 with SessionLocal() as db:
  c=db.scalar(select(Conversation).where((Conversation.id==cid)&(Conversation.user_id==uid)))
  if not c:raise ValueError("Conversation not found.")
  m=Message(user_id=uid,conversation_id=cid,role=role,content=content,model=model,input_tokens=input_tokens,output_tokens=output_tokens,latency_ms=latency_ms);db.add(m);c.updated_at=now();db.commit();db.refresh(m);return m.id
def get_conversations(uid):
 with SessionLocal() as db:
  return [{"id":x.id,"title":x.title,"mode":x.mode,"summary":x.summary,"created_at":x.created_at.isoformat(),"updated_at":x.updated_at.isoformat()} for x in db.scalars(select(Conversation).where(Conversation.user_id==uid).order_by(Conversation.updated_at.desc())).all()]
def get_history(uid,cid,limit=40):
 with SessionLocal() as db:
  if not db.scalar(select(Conversation).where((Conversation.id==cid)&(Conversation.user_id==uid))):raise ValueError("Conversation not found.")
  rows=db.scalars(select(Message).where((Message.conversation_id==cid)&(Message.user_id==uid)).order_by(Message.created_at.desc()).limit(limit)).all();rows.reverse();return [{"id":r.id,"role":r.role,"content":r.content,"created_at":r.created_at.isoformat()} for r in rows]
def delete_conversation(uid,cid):
 with SessionLocal() as db:
  c=db.scalar(select(Conversation).where((Conversation.id==cid)&(Conversation.user_id==uid)))
  if not c:raise ValueError("Conversation not found.")
  db.delete(c);db.commit()
def get_user_settings(uid):
 with SessionLocal() as db:
  r=db.get(UserSetting,uid)
  if not r:r=UserSetting(user_id=uid);db.add(r);db.commit()
  return {"preferred_mode":r.preferred_mode,"response_length":r.response_length,"memory_enabled":r.memory_enabled}
def update_user_settings(uid,mode,length,memory):
 with SessionLocal() as db:
  r=db.get(UserSetting,uid) or UserSetting(user_id=uid);db.add(r);r.preferred_mode=mode;r.response_length=length;r.memory_enabled=memory;db.commit();return {"preferred_mode":r.preferred_mode,"response_length":r.response_length,"memory_enabled":r.memory_enabled}
def add_learning_candidate(uid,kind,source,payload):
 with SessionLocal() as db:x=LearningCandidate(user_id=uid,knowledge_type=kind,source_text=source,payload_json=json.dumps(payload,ensure_ascii=False));db.add(x);db.commit();db.refresh(x);return x.id
def save_usage(uid,model,input_tokens,output_tokens,status="ok"):
 with SessionLocal() as db:db.add(Usage(user_id=uid,model=model,input_tokens=input_tokens,output_tokens=output_tokens,status=status));db.commit()
def list_candidates(status="PENDING"):
 with SessionLocal() as db:return [{"id":x.id,"user_id":x.user_id,"knowledge_type":x.knowledge_type,"source_text":x.source_text,"payload":json.loads(x.payload_json or "{}"),"status":x.status,"created_at":x.created_at.isoformat()} for x in db.scalars(select(LearningCandidate).where(LearningCandidate.status==status).order_by(LearningCandidate.created_at.desc())).all()]
def review_candidate(cid,approve,note=""):
 with SessionLocal() as db:
  x=db.get(LearningCandidate,cid)
  if not x:return None
  p=json.loads(x.payload_json or "{}");p["reviewer_note"]=note;x.status="APPROVED" if approve else "REJECTED";x.reviewed_at=now();x.payload_json=json.dumps(p,ensure_ascii=False)
  if approve and x.knowledge_type in {"ROOT","VOCABULARY"}:
   s=str(p.get("source_root") or p.get("standard_root") or p.get("word") or "").strip();t=str(p.get("melimi_root") or p.get("melimi_equivalent") or "").strip()
   if s and t:
    r=db.scalar(select(MelimiRoot).where(MelimiRoot.standard_root==s));
    if r:r.melimi_root=t.split("/")[0].strip();r.status="APPROVED";r.version+=1;r.updated_at=now()
    else:db.add(MelimiRoot(standard_root=s,melimi_root=t.split("/")[0].strip(),meaning=str(p.get("meaning","")),category=str(p.get("part_of_speech","")),status="APPROVED",source="approved_chat_learning"))
  db.commit();return {"id":x.id,"status":x.status,"payload":p}
def approved_learning():
 with SessionLocal() as db:return [json.loads(x.payload_json or "{}")|{"knowledge_type":x.knowledge_type} for x in db.scalars(select(LearningCandidate).where(LearningCandidate.status=="APPROVED").order_by(LearningCandidate.created_at.asc())).all()]
def remember_user_memory(uid,key,value):
 with SessionLocal() as db:
  r=db.scalar(select(UserMemory).where((UserMemory.user_id==uid)&(UserMemory.key==key)))
  if r:r.value=value
  else:db.add(UserMemory(user_id=uid,key=key,value=value))
  db.commit()
def recall_user_memory(uid,limit=12):
 with SessionLocal() as db:return [{"key":x.key,"value":x.value} for x in db.scalars(select(UserMemory).where(UserMemory.user_id==uid).order_by(UserMemory.created_at.desc()).limit(limit)).all()]
def cache_get(key,mode):
 with SessionLocal() as db:
  x=db.scalar(select(ResponseCache).where((ResponseCache.cache_key==key)&(ResponseCache.mode==mode)));return x.response if x else None
def cache_put(key,mode,response):
 with SessionLocal() as db:
  x=db.scalar(select(ResponseCache).where(ResponseCache.cache_key==key))
  if x:x.response=response;x.knowledge_version=knowledge_version()
  else:db.add(ResponseCache(cache_key=key,mode=mode,knowledge_version=knowledge_version(),response=response))
  db.commit()
def knowledge_version():
 with SessionLocal() as db:return (db.scalar(select(func.max(KnowledgeVersion.version))) or 1)
def audit_log(uid,action,target_type="",target_id="",details=None):
 with SessionLocal() as db:db.add(AuditLog(actor_user_id=uid,action=action,target_type=target_type,target_id=target_id,details_json=json.dumps(details or {},ensure_ascii=False));db.commit()
def get_user_by_id(uid):
 with SessionLocal() as db:return db.get(User,uid)
def list_users():
 with SessionLocal() as db:return [{"id":x.id,"username":x.username,"email":x.email if x.role!="guest" else None,"role":x.role,"is_active":x.is_active,"created_at":x.created_at.isoformat()} for x in db.scalars(select(User).order_by(User.created_at.desc())).all()]
def set_user_role(uid,role):
 role=role.lower()
 if role not in {"guest","user","admin","owner"}:raise ValueError("Invalid role.")
 with SessionLocal() as db:r=db.get(User,uid);r.role=role;db.commit();return {"id":r.id,"username":r.username,"role":r.role}
def set_user_active(uid,active):
 with SessionLocal() as db:r=db.get(User,uid);r.is_active=active;db.commit();return {"id":r.id,"username":r.username,"is_active":r.is_active}
def delete_user(uid):
 with SessionLocal() as db:r=db.get(User,uid);db.delete(r);db.commit();return bool(r)
def database_stats():
 with SessionLocal() as db:return {"users":db.scalar(select(func.count(User.id))) or 0,"guests":db.scalar(select(func.count(User.id)).where(User.role=="guest")) or 0,"conversations":db.scalar(select(func.count(Conversation.id))) or 0,"messages":db.scalar(select(func.count(Message.id))) or 0,"language_roots":db.scalar(select(func.count(MelimiRoot.id))) or 0}
def list_audit_logs(limit=100):
 with SessionLocal() as db:return [{"id":x.id,"actor_user_id":x.actor_user_id,"action":x.action,"target_type":x.target_type,"target_id":x.target_id,"details":json.loads(x.details_json or "{}"),"created_at":x.created_at.isoformat()} for x in db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()]
def language_snapshot(limit=50):
 with SessionLocal() as db:return {"roots":[{"standard_root":x.standard_root,"melimi_root":x.melimi_root,"meaning":x.meaning,"category":x.category,"status":x.status} for x in db.scalars(select(MelimiRoot).order_by(MelimiRoot.updated_at.desc()).limit(limit)).all()]}
def bootstrap_owner(email):
 with SessionLocal() as db:
  u=db.scalar(select(User).where(User.email==email.lower()))
  if not u:return None,"Owner account not found."
  existing=db.scalar(select(User).where(User.role=="owner"))
  if existing and existing.id!=u.id:return None,"An owner already exists."
  u.role="owner";db.commit();return u,None
def promote_configured_owners(emails):
 with SessionLocal() as db:
  for e in emails:
   u=db.scalar(select(User).where(User.email==e))
   if u:u.role="owner"
  db.commit()
def create_password_reset_token(email):
 code=f"{secrets.randbelow(1000000):06d}"
 with SessionLocal() as db:
  u=db.scalar(select(User).where(User.email==email.lower()))
  if not u or not u.is_active or u.role=="guest":return None
  db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id==u.id));db.add(PasswordResetToken(token_hash=hashlib.sha256(code.encode()).hexdigest(),user_id=u.id,expires_at=now()+timedelta(minutes=10)));db.commit()
 return code
def verify_password_reset_code(email,code):
 h=hashlib.sha256(code.encode()).hexdigest()
 with SessionLocal() as db:
  u=db.scalar(select(User).where(User.email==email.lower()));r=db.scalar(select(PasswordResetToken).where((PasswordResetToken.user_id==u.id)&(PasswordResetToken.token_hash==h))) if u else None
  if not u or not r or r.expires_at<now():return None
  token=secrets.token_urlsafe(48);db.delete(r);db.add(PasswordResetToken(token_hash=hashlib.sha256(token.encode()).hexdigest(),user_id=u.id,expires_at=now()+timedelta(minutes=10)));db.commit();return token
def reset_password(token,password):
 h=hashlib.sha256(token.encode()).hexdigest()
 with SessionLocal() as db:
  r=db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash==h));
  if not r or r.expires_at<now():return None
  u=db.get(User,r.user_id);u.password_hash=_hash_password(password);r.used_at=now();db.execute(delete(Session).where(Session.user_id==u.id));db.commit();return u.id
def init_db():
 Base.metadata.create_all(engine)
 try:
  from app.migrations import run_migrations;run_migrations()
 except Exception:pass
def ingest_language_package(filename,raw,approved,actor_user_id=None):
 try:
  from app.melimi.content_store import ingest_language_package as f;return f(filename,raw,approved,actor_user_id)
 except Exception:return {"status":"PENDING"}
