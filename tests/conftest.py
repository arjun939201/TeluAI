import json
import pytest


ROOTS = {
    "సమస్య": "చిక్కు",
    "సహాయం": "బాసట",
    "సినిమా": "తెఱాటం",
    "వ్యవస్థ": "అమరం",
    "భాష": "నుడి",
    "ఆధారిత": "ఆనిద",
    "ఆసక్తికరం": "హాళికాను",
    "ప్రభావం": "హత్తరం",
    "నమస్కారం": "టేంకణములు",
    "విశిష్ట": "మేలిమి",
}

DOCUMENTS = [
    ("language/vocabulary/core.json", "vocabulary", [{"standard": k, "melimi": v} for k, v in ROOTS.items()]),
    ("language/grammar/core.md", "grammar", []),
    ("language/word_formation/core.md", "word_formation", []),
    ("language/syntax/core.md", "syntax", []),
    ("language/examples/core.md", "examples", []),
    ("language/rules/core.md", "rules", []),
]


@pytest.fixture(scope="session", autouse=True)
def seed_language_space_for_tests():
    from app.database import Base, engine, SessionLocal, MelimiRoot, MelimiDocument
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for standard, melimi in ROOTS.items():
            row = db.query(MelimiRoot).filter(MelimiRoot.standard_root == standard).first()
            if row is None:
                db.add(MelimiRoot(standard_root=standard, melimi_root=melimi, status="MASTER", source="test-fixture"))
            else:
                row.melimi_root = melimi
                row.status = "MASTER"
        for path, kind, entries in DOCUMENTS:
            row = db.query(MelimiDocument).filter(MelimiDocument.path == path).first()
            text = json.dumps(entries, ensure_ascii=False) if entries else f"Test {kind} Language Space document"
            if row is None:
                db.add(MelimiDocument(path=path, kind=kind, text=text, entries_json=json.dumps(entries, ensure_ascii=False), status="MASTER", source="test-fixture"))
        db.commit()
    from app.melimi.root_morphology import reload_root_dictionary
    from app.melimi.index import reload_index
    from app.melimi.registry import reload_registry
    from app.melimi.firewall import reload_firewall
    reload_root_dictionary(); reload_index(); reload_registry(); reload_firewall()
    yield
