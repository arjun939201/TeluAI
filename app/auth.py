from fastapi import Cookie, Depends, HTTPException
from app.database import user_from_session

COOKIE_NAME = "teluai_session"

def current_user(teluai_session: str | None = Cookie(default=None)):
    user = user_from_session(teluai_session)
    if not user or not getattr(user, "is_active", True) or str(getattr(user, "role", "user") or "user").lower() == "guest":
        raise HTTPException(status_code=401, detail="Please log in or register to continue.")
    return user

def require_admin(user=Depends(current_user)):
    role = str(getattr(user, "role", "user") or "user").lower()
    if role not in {"admin", "owner"}:
        raise HTTPException(status_code=403, detail="Administrator permission required.")
    return user

def require_owner(user=Depends(current_user)):
    if str(getattr(user, "role", "user") or "user").lower() != "owner":
        raise HTTPException(status_code=403, detail="Owner permission required.")
    return user
