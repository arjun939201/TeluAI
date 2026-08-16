from __future__ import annotations

from sqlalchemy import select

from app.database import SessionLocal, UserMemory


def list_memories(user_id: int, limit: int = 50):
    with SessionLocal() as db:
        rows = db.scalars(
            select(UserMemory)
            .where(UserMemory.user_id == user_id)
            .order_by(UserMemory.created_at.desc())
            .limit(max(1, min(limit, 200)))
        ).all()
        return [
            {
                "id": row.id,
                "key": row.key,
                "value": row.value,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]


def delete_memory(user_id: int, memory_id: int) -> bool:
    with SessionLocal() as db:
        row = db.scalar(select(UserMemory).where((UserMemory.id == memory_id) & (UserMemory.user_id == user_id)))
        if row is None:
            return False
        db.delete(row)
        db.commit()
        return True
