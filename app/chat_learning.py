"""Explicit /word and /content learning only.

Normal chat is never promoted to Language Space. Explicit commands are written
straight to the master knowledge store so they are immediately retrievable.
"""
from __future__ import annotations
import hashlib,json,re
from sqlalchemy import select
from sqlalchemy.orm import Session as SASession
from app.database import SessionLocal,MelimiRoot,MelimiExample,KnowledgeEntry,KnowledgeVersion,now
_COMMAND_RE=re.compile(r"^\s*/(?P<kind>word|content)\b(?P<body>.*?)\s*$",re.I|re.S)
_MAPPING_RE=re.compile(r"^\s*(?P<source>.+?)\s*(?:=|→|->)\s*(?P<melimi>.+?)\s*$",re.S)
def parse_command(message:str):
 m=_COMMAND_RE.match(message or "")
 if not m:return None
 kind=m.group("kind").lower();body=m.group("body").strip()
 if kind=="word":
  p=_MAPPING_RE.match(body)
  if not p:raise ValueError("Usage: /word source-word = melimi-word")
  return kind,{"source":p.group("source").strip(),"melimi":p.group("melimi").strip()}
 if not body:raise ValueError("Content cannot be empty.")
 note=re.match(r"^(.*?)(?:\s*\(([^()]*)\))?\s*$",body,re.S)
 return kind,{"content":(note.group(1) or "").strip(),"meaning":(note.group(2) or "").strip()}
def learn_explicit_teaching(message:str,user_id:int|None=None):
 parsed=parse_command(message)
 if not parsed:return {"learned":False,"roots":0,"phrases":0}
 kind,payload=parsed;source=f"chat_command:user:{user_id or 'unknown'}"
 with SessionLocal() as db:
  if kind=="word":
   standard,melimi=payload["source"],payload["melimi"]
   if not standard or not melimi or len(standard)>160 or len(melimi)>160:raise ValueError("Invalid word entry.")
   row=db.scalar(select(MelimiRoot).where(MelimiRoot.standard_root==standard))
   if row: row.melimi_root=melimi.split("/")[0].strip();row.status="MASTER";row.source=source;row.version+=1;row.updated_at=now()
   else: db.add(MelimiRoot(standard_root=standard,melimi_root=melimi.split("/")[0].strip(),status="MASTER",source=source))
   key=f"{standard} → {melimi}"
   if not db.scalar(select(KnowledgeEntry).where((KnowledgeEntry.kind=="VOCABULARY")&(KnowledgeEntry.key==key))):db.add(KnowledgeEntry(kind="VOCABULARY",key=key,value=melimi,metadata_json=json.dumps({"standard":standard,"melimi":melimi,"source":"chat-command"},ensure_ascii=False),status="MASTER",source=source))
   roots=1;phrases=0
  else:
   content,meaning=payload["content"],payload["meaning"]
   if not content or len(content)>50000:raise ValueError("Content is empty or too large.")
   key=f"chat:{hashlib.sha256((content+'\n'+meaning).encode()).hexdigest()}"
   if not db.scalar(select(KnowledgeEntry).where((KnowledgeEntry.kind=="CONTENT")&(KnowledgeEntry.key==key))):db.add(KnowledgeEntry(kind="CONTENT",key=key,value=content,metadata_json=json.dumps({"meaning":meaning,"source":"chat-command"},ensure_ascii=False),status="MASTER",source=source))
   if meaning and not db.scalar(select(MelimiExample).where((MelimiExample.melimi_text==content)&(MelimiExample.standard_text==meaning))):db.add(MelimiExample(standard_text=meaning,melimi_text=content,category="chat-command",source=source,status="MASTER"))
   roots=0;phrases=1
  version=db.scalars(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc())).first();db.add(KnowledgeVersion(version=(version.version if version else 1)+1,source=source,checksum=hashlib.sha256(message.encode()).hexdigest()));db.commit()
 reload_indexes();return {"learned":True,"roots":roots,"phrases":phrases}
def reload_indexes():
 for module,name in (("app.melimi.root_morphology","reload_root_dictionary"),("app.melimi.registry","reload_registry"),("app.melimi.index","reload_index"),("app.melimi.firewall","reload_firewall")):
  try:getattr(__import__(module,fromlist=[name]),name)()
  except Exception:pass
def install_chat_learning():return None
