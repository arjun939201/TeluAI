from app.database import KnowledgeVersion, MelimiRoot, SessionLocal, now
from app.melimi.firewall import deterministic_repair
from app.melimi.root_morphology import convert_surface, load_root_dictionary
from app.retrieval.knowledge import retrieve


def test_new_master_word_is_visible_without_manual_cache_reload():
    standard = "సార్వత్రికపరీక్షపదం"
    first = "మొదటిపలుకు"
    second = "అన్నిచోట్లపలుకు"

    with SessionLocal() as db:
        db.add(MelimiRoot(standard_root=standard, melimi_root=first, meaning=standard, status="MASTER", source="test"))
        latest = db.query(KnowledgeVersion).order_by(KnowledgeVersion.version.desc()).first()
        db.add(KnowledgeVersion(version=(latest.version if latest else 0) + 1, source="test", checksum="universal-refresh-1"))
        db.commit()

    assert convert_surface(standard) == first
    assert deterministic_repair(standard) == first

    with SessionLocal() as db:
        row = db.query(MelimiRoot).filter(MelimiRoot.standard_root == standard).one()
        row.melimi_root = second
        row.updated_at = now()
        row.version += 1
        latest = db.query(KnowledgeVersion).order_by(KnowledgeVersion.version.desc()).first()
        db.add(KnowledgeVersion(version=(latest.version if latest else 0) + 1, source="test", checksum="universal-refresh-2"))
        db.commit()

    # No reload_* call: a subsequent request must see the newest shared value.
    assert convert_surface(standard) == second
    assert deterministic_repair(standard) == second
    matches = retrieve(standard, limit=20)
    assert any(str(item.get("standard")) == standard and str(item.get("melimi")) == second for item in matches)
