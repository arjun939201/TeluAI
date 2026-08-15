from fastapi import Cookie, HTTPException
from app.database import user_from_session

COOKIE_NAME = "teluai_session"

def current_user(teluai_session: str | None = Cookie(default=None)):
    user = user_from_session(teluai_session)
    if not user:
        raise HTTPException(status_code=401, detail="Please login or register to use TeluAI.")
    return user
