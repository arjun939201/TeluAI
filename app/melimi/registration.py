"""User-submitted Melimi knowledge.

Registration creates a review candidate only. It never silently promotes a
user suggestion into authoritative/shared Melimi knowledge.
"""
from datetime import datetime, timezone
from sqlalchemy import event
from app.database import add_learning_candidate, LearningCandidate


def build_entry(data):
    word=str(data.get("word","")).strip()
    melimi=str(data.get("melimi_equivalent","")).strip()
    if not word: raise ValueError("Source/loan word is required.")
    if not melimi: raise ValueError("Melimi Telugu word is required.")
    return {
        "standard_or_source":word,
        "source_root":str(data.get("root") or word).strip(),
        "melimi":melimi,
        "melimi_root":melimi,
        "meaning":str(data.get("meaning","")).strip(),
        "part_of_speech":str(data.get("part_of_speech","")).strip(),
        "formation":str(data.get("formation","")).strip(),
        "status":"user_verified_candidate",
        "source":"database",
        "created_at":datetime.now(timezone.utc).isoformat(),
    }


@event.listens_for(LearningCandidate, "before_insert")
def _guard_implicit_root_learning(mapper, connection, target):
    """Do not let ordinary `a = b` chat silently become learning content.

    The legacy chat heuristic uses knowledge_type=ROOT. ROOT learning is now
    accepted only when the message is an explicit /word command. Dedicated
    /melimi/register and /melimi/content endpoints remain available.
    """
    if target.knowledge_type == "ROOT":
        source = (target.source_text or "").lstrip()
        if not source.lower().startswith("/word"):
            target.status = "IGNORED"


async def register_word(data, user_id=None):
    entry=build_entry(data)
    candidate_id=add_learning_candidate(user_id,"VOCABULARY",entry["standard_or_source"],entry)
    return {"entry":entry,"candidate_id":candidate_id,"stored":"postgresql_or_local_database","committed":False,"status":"PENDING"}
