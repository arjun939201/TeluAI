"""Runtime compatibility and small cross-cutting application overrides."""
from __future__ import annotations
import json
from app import database as db
from app.melimi import content_store


def _content_candidate_or_approved(user_id, knowledge_type, source_text, payload):
    if knowledge_type == "CONTENT" and isinstance(payload, dict):
        user = None
        if user_id is not None:
            with db.SessionLocal() as session: user = session.get(db.User, user_id)
        result = content_store.submit_content(user_id or 0, str(payload.get("title", "")), str(payload.get("content", "")), approved=bool(user and user.role in {"owner", "admin"}))
        return result.get("candidate_id", 0)
    return _original_add_learning_candidate(user_id, knowledge_type, source_text, payload)


def _language_roots():
    with db.SessionLocal() as session:
        return {r.standard_root: r.melimi_root for r in session.scalars(db.select(db.MelimiRoot).where(db.MelimiRoot.status != "REJECTED")).all()}


def _language_documents():
    with db.SessionLocal() as session:
        rows = session.scalars(db.select(db.MelimiDocument).where(db.MelimiDocument.status != "REJECTED")).all()
        result=[]
        for row in rows:
            try: entries=json.loads(row.entries_json or "[]")
            except Exception: entries=[]
            result.append({"path":row.path,"kind":row.kind,"text":row.text,"entries":entries})
        return result


def _install_credential_route():
    try:
        from fastapi import Depends, HTTPException
        from app.auth import current_user
        from app.models import CredentialUpdateRequest
        from fastapi.applications import FastAPI
        original_init=FastAPI.__init__
        if getattr(FastAPI,"_teluai_guest_route_hook",False): return
        def patched_init(self,*args,**kwargs):
            original_init(self,*args,**kwargs)
            if getattr(self,"title","")=="TeluAI — Melimi Telugu AI":
                def update_credentials(payload: CredentialUpdateRequest, user=Depends(current_user)):
                    try:u=db.update_credentials(user.id,payload.current_password,payload.username,payload.new_password)
                    except ValueError as exc:raise HTTPException(400,str(exc))
                    db.audit_log(user.id,"account.credentials_change","user",str(user.id),{"username_changed":bool(payload.username),"password_changed":bool(payload.new_password)})
                    return {"ok":True,"username":u.username,"role":u.role}
                self.add_api_route("/me/credentials",update_credentials,methods=["PUT"])
        FastAPI.__init__=patched_init;FastAPI._teluai_guest_route_hook=True
    except Exception:pass


def apply():
    global _original_add_learning_candidate
    _original_add_learning_candidate=db.add_learning_candidate
    db._read_seed=lambda:{};db._seed_language=lambda:None
    db.ingest_language_package=content_store.ingest_language_package
    db.review_candidate=content_store.review_candidate
    db.add_learning_candidate=_content_candidate_or_approved
    db.language_roots=_language_roots
    db.language_documents=_language_documents
    _install_credential_route()

apply()
