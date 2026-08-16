"""Explicit /word and /content learning only.

Normal chat is never promoted to Language Space. Explicit commands are written
straight to the master knowledge store and become retrievable immediately.
"""
from __future__ import annotations
import hashlib,json,re
from sqlalchemy import select
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
    content=(note.group(1) or "").strip();meaning=(note.group(2) or "").strip()
    if not content:raise ValueError("Content cannot be empty.")
    return kind,{"content":content,"meaning":meaning}


def learn_explicit_teaching(message:str,user_id:int|None=None):
    """Apply an explicit language command immediately.

    /word is authoritative: an unknown source word is added, while an existing
    source-word mapping is replaced by the newly supplied Melimi equivalent.
    Ordinary chat never reaches this function.
    """
    parsed=parse_command(message)
    if not parsed:return {"learned":False,"changed":False,"roots":0,"phrases":0}
    kind,payload=parsed;source=f"chat_command:user:{user_id or 'unknown'}";changed=False;roots=phrases=0
    with SessionLocal() as db:
        if kind=="word":
            standard,melimi=payload["source"].strip(),payload["melimi"].strip()
            if not standard or not melimi or len(standard)>160 or len(melimi)>160:raise ValueError("Invalid word entry.")
            melimi_root=melimi.split("/")[0].strip()
            # Source words are canonicalized by trimmed, case-insensitive text.
            # This makes a repeated /word entry replace the existing mapping
            # instead of creating a competing dictionary entry.
            row=None
            for candidate in db.scalars(select(MelimiRoot)).all():
                if str(candidate.standard_root or "").strip().casefold()==standard.casefold():
                    row=candidate;break
            if row:
                if row.melimi_root!=melimi_root or row.status!="MASTER" or row.source!=source:
                    row.standard_root=standard;row.melimi_root=melimi_root;row.status="MASTER";row.source=source;row.version+=1;row.updated_at=now();changed=True
            else:
                db.add(MelimiRoot(standard_root=standard,melimi_root=melimi_root,status="MASTER",source=source));changed=True
            # Replace the canonical vocabulary record for this source word.
            record=None
            for item in db.scalars(select(KnowledgeEntry).where(KnowledgeEntry.kind.in_(["VOCABULARY","ROOT"]))).all():
                try: metadata=json.loads(item.metadata_json or "{}")
                except (TypeError,ValueError): metadata={}
                if str(metadata.get("standard", "")).strip().casefold()==standard.casefold():
                    record=item;break
            metadata={"standard":standard,"melimi":melimi,"source":"chat-command"}
            encoded=json.dumps(metadata,ensure_ascii=False)
            if record:
                if record.value!=melimi or record.metadata_json!=encoded or record.status!="MASTER":
                    record.kind="VOCABULARY";record.key=f"word:{standard.casefold()}";record.value=melimi;record.metadata_json=encoded;record.status="MASTER";record.source=source;record.version+=1;changed=True
            else:
                db.add(KnowledgeEntry(kind="VOCABULARY",key=f"word:{standard.casefold()}",value=melimi,metadata_json=encoded,status="MASTER",source=source));changed=True
            roots=1
        else:
            content,meaning=payload["content"],payload["meaning"]
            if len(content)>50000:raise ValueError("Content is too large. Maximum is 50,000 characters.")
            key=f"chat:{hashlib.sha256((content+'\n'+meaning).encode()).hexdigest()}"
            record=db.scalar(select(KnowledgeEntry).where((KnowledgeEntry.kind=="CONTENT")&(KnowledgeEntry.key==key)))
            if not record:
                db.add(KnowledgeEntry(kind="CONTENT",key=key,value=content,metadata_json=json.dumps({"meaning":meaning,"source":"chat-command"},ensure_ascii=False),status="MASTER",source=source));changed=True
            elif record.status!="MASTER":
                record.status="MASTER";record.source=source;record.version+=1;changed=True
            if meaning and not db.scalar(select(MelimiExample).where((MelimiExample.melimi_text==content)&(MelimiExample.standard_text==meaning))):
                db.add(MelimiExample(standard_text=meaning,melimi_text=content,category="chat-command",source=source,status="MASTER"));changed=True
            phrases=1
        if changed:
            version=db.scalars(select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc())).first()
            db.add(KnowledgeVersion(version=(version.version if version else 1)+1,source=source,checksum=hashlib.sha256(message.encode()).hexdigest()))
        db.commit()
    if changed: reload_indexes()
    return {"learned":True,"changed":changed,"roots":roots,"phrases":phrases}


def reload_indexes():
    for module,name in (("app.melimi.root_morphology","reload_root_dictionary"),("app.melimi.registry","reload_registry"),("app.melimi.index","reload_index"),("app.melimi.firewall","reload_firewall"),("app.retrieval.knowledge","reload_vocabulary")):
        try:getattr(__import__(module,fromlist=[name]),name)()
        except Exception:pass


def install_chat_learning():
    # Explicit commands are processed by the request path. No SQLAlchemy hook
    # is installed because normal conversation must never become language data.
    return None
