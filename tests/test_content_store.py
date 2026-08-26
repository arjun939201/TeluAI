from app.melimi.content_store import _entries_for_text, parse_mapping_line


def test_parse_melimi_to_standard_mapping_and_aliases():
    rows = parse_mapping_line("చేవీనం - cellphone, mobile. hand phone")
    assert rows
    assert {row["melimi"] for row in rows} == {"చేవీనం"}
    assert {row["standard"] for row in rows} == {"cellphone", "mobile", "hand phone"}


def test_parse_standard_to_melimi_mapping():
    rows = parse_mapping_line("mobile camera - చేవీనపు మేవరం")
    assert rows == [{
        "standard": "mobile camera",
        "melimi": "చేవీనపు మేవరం",
        "source_type": "uploaded_mapping",
        "status": "master",
    }]


def test_parse_arbitrary_document_keeps_only_detected_mappings():
    text = """# Vocabulary\n\nచేవీనం - cellphone, mobile\n\nThis is a paragraph of Melimi language knowledge.\n"""
    rows = _entries_for_text(text)
    assert len(rows) == 2
    assert rows[0]["melimi"] == "చేవీనం"
