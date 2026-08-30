from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app.auth import current_user, require_admin
from app.groq_client import call_groq_detailed
from app.response import clean_response
from app.texl_service import all_learned, approve, approve_all, pending, propose_from_text, reject
from app.teluai2_learning import learned_global

router = APIRouter()
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

class TexLRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    history: list[dict] = Field(default_factory=list, max_length=20)

class ApprovalRequest(BaseModel):
    key: str | None = None
    value: str | None = None


def owner_only(user=Depends(current_user)):
    if str(getattr(user, "role", "")).lower() != "owner":
        raise HTTPException(403, "TEX-L owner permission required.")
    return user


def admin_or_owner(user=Depends(require_admin)):
    """Allow trusted admins/owners in both FastAPI and direct guard tests."""
    role = str(getattr(user, "role", "user") or "user").lower()
    if role not in {"admin", "owner"}:
        raise HTTPException(403, "Administrator permission required.")
    return user

@router.get("/texl")
def texl_page(user=Depends(admin_or_owner)):
    return FileResponse(STATIC_DIR / "texl.html")

@router.get("/texl/learning")
def texl_learning(user=Depends(admin_or_owner)):
    return all_learned()

@router.get("/texl/pending")
def texl_pending(user=Depends(admin_or_owner)):
    return {"pending": pending(500)}

@router.post("/texl/learning/{item_id}/approve")
def texl_approve(item_id: int, payload: ApprovalRequest | None = None, user=Depends(admin_or_owner)):
    try:
        return approve(item_id, user.id, role=getattr(user, "role", "user"), key=payload.key if payload else None, value=payload.value if payload else None)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@router.post("/texl/learning/approve-all")
def texl_approve_all(user=Depends(admin_or_owner)):
    return {"approved": approve_all(user.id, role=getattr(user, "role", "user"))}

@router.delete("/texl/learning/{item_id}")
def texl_reject(item_id: int, user=Depends(admin_or_owner)):
    if not reject(item_id):
        raise HTTPException(404, "Pending TEX-L item not found.")
    return {"ok": True, "status": "rejected"}

@router.post("/texl/chat")
async def texl_chat(payload: TexLRequest, user=Depends(admin_or_owner)):
    proposed = propose_from_text(payload.message)
    approved = learned_global(limit=200)
    pending_items = pending(200)
    knowledge = "\n".join(f"- {x.get('key','')} → {x.get('value','')} [{x.get('source','')}]" for x in approved)
    pending_text = "\n".join(f"- {x['key']} → {x['value']} [PENDING]" for x in pending_items)
    system = """You are TEX-L, the dedicated Melimi Telugu language laboratory inside TeluAI. Analyze language deeply but display only compact high-signal results. Source-attested and owner/admin-approved knowledge is authoritative. A formative element is not automatically an independent word. Never invent unsupported Melimi vocabulary. Distinguish observed, pending, approved, inferred, and rejected knowledge. Test canonical forms, inflection, compounds, formations, semantic boundaries, context, and TRANSHIFT. Explicit owner/admin teaching is trusted and may become shared authoritative knowledge directly; ordinary-user teaching is not shared authority. Do not claim approval until the authorized reviewer approves a pending item."""
    prompt = system + "\n\nAPPROVED:\n" + knowledge + "\n\nPENDING:\n" + pending_text + "\n\nAUTHORIZED REVIEWER:\n" + payload.message + "\n\nRespond briefly: status + finding/test + proposed learning if any."
    history = [x for x in payload.history[-12:] if x.get("role") in {"user", "assistant"} and x.get("content")]
    try:
        result = await call_groq_detailed(prompt, history, payload.message)
    except Exception as exc:
        raise HTTPException(502, "TEX-L AI service is temporarily unavailable.") from exc
    answer = clean_response(str(result.get("answer", "")))
    return {"message": answer, "proposed": proposed, "pending": pending(200), "approved": approved}
