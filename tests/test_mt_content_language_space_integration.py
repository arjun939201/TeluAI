from app.melimi.content_processor import extract_explicit_items
from app.melimi.content_store import _entries_for_text


def test_content_parser_preserves_vocabulary_and_structured_rules():
    text = """
హాళి = interest
grammar: కాను is an agent/doer suffix
"""

    mappings = _entries_for_text(text)
    assert {entry["melimi"] for entry in mappings} == {"హాళి"}
    assert {entry["standard"] for entry in mappings} == {"interest"}

    items = extract_explicit_items(text)
    assert any(item.kind == "vocabulary" and item.form == "హాళి" for item in items)
    assert any(item.kind == "rule" and item.form == "grammar" for item in items)


def test_content_processor_does_not_promote_unstructured_observations():
    text = "This is merely an observation without an explicit mapping."
    assert extract_explicit_items(text) == []
