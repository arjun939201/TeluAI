"""Account operations that sit between HTTP handlers and the database layer."""
from __future__ import annotations

from sqlalchemy import select
from app import database as db


def update_credentials(user_id: int, current_password: str, username: str | None = None, new_password: str | None = None):
    with db.SessionLocal() as session:
        user = session.get(db.User, user_id)
        if not user or not user.is_active:
            raise ValueError("Account not found.")
        if not db.verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect.")
        if username is not None:
            username = username.strip()
            if not username:
                raise ValueError("Username cannot be empty.")
            duplicate = session.scalar(select(db.User).where((db.User.username == username) & (db.User.id != user.id)))
            if duplicate:
                raise ValueError("Username is already taken.")
            user.username = username
        if new_password:
            user.password_hash = db._hash_password(new_password)
        session.commit()
        session.refresh(user)
        return user
