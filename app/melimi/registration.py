
import json
from datetime import datetime,timezone
from pathlib import Path
from app.melimi.index import reload_index
from app.melimi.registry import reload_registry
TARGET=Path(__file__).resolve().parents[2]/"melimi_telugu/vocabulary/chat_registered.json"
def register_word(data):
    word=str(data.get("word","")).strip(); melimi=str(data.get("melimi_equivalent","")).strip()
    if not word or not melimi: raise ValueError("word and melimi_equivalent are required")
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    try: rows=json.loads(TARGET.read_text(encoding="utf-8"))
    except Exception: rows=[]
    if not isinstance(rows,list): rows=[]
    rows=[x for x in rows if x.get("standard_or_source")!=word]
    rows.append({"standard_or_source":word,"melimi":melimi,
      "root":str(data.get("root","")).strip(),"meaning":str(data.get("meaning","")).strip(),
      "part_of_speech":str(data.get("part_of_speech","")).strip(),
      "formation":str(data.get("formation","")).strip(),"status":"user_verified",
      "source":"chat_interface","created_at":datetime.now(timezone.utc).isoformat()})
    TARGET.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
    reload_index(); reload_registry()
    return rows[-1]
