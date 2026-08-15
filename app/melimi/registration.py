from __future__ import annotations
from datetime import datetime, timezone
from app.database import register_language_root
from app.melimi.root_morphology import load_root_dictionary
from app.melimi.index import reload_index
from app.melimi.registry import reload_registry

def build_entry(data):
    word=str(data.get("word","")).strip(); melimi=str(data.get("melimi_equivalent","")).strip()
    if not word: raise ValueError("Source/loan word is required.")
    if not melimi: raise ValueError("Melimi Telugu word is required.")
    return {"standard_or_source":word,"melimi":melimi,"root":str(data.get("root","")).strip(),"meaning":str(data.get("meaning","")).strip(),"part_of_speech":str(data.get("part_of_speech","")).strip(),"formation":str(data.get("formation","")).strip(),"status":"user_verified","source":"database","created_at":datetime.now(timezone.utc).isoformat()}

async def register_word(data):
    entry=build_entry(data)
    register_language_root(entry["standard_or_source"], entry["melimi"], entry)
    load_root_dictionary.cache_clear(); reload_index(); reload_registry()
    return {"entry":entry,"stored":"postgresql_or_local_database","committed":False}
