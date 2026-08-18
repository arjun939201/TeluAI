import pytest

from app.melimi.main_dictionary import (
    MAIN_DICTIONARY_SOURCE,
    manifest,
    validate_entry,
)


def test_main_dictionary_manifest_is_stable():
    value = manifest()
    assert value["source_type"] == "MAIN_DICTIONARY"
    assert value["source_id"] == "bangaaru_naanelu"
    assert value["book"] == "Bangaaru Naanelu"
    assert value["author"] == "Vaachaspathy"
    assert value["edition"] == "2021"
    assert value["dictionary_version"] == "1.0"
    assert value["ingestion_policy"].startswith("reviewed structured entries only")


def test_reviewed_entry_keeps_full_provenance():
    entry = validate_entry({
        "standard_form": "నిర్వచనం",
        "melimi_form": "నిర్వల్కు",
        "meaning": "definition",
        "part_of_speech": "noun",
        "root": "నిర్వచనం",
        "source_page": 123,
        "source_entry": "definition",
        "status": "APPROVED",
    })
    assert entry.standard_form == "నిర్వచనం"
    assert entry.melimi_form == "నిర్వల్కు"
    assert entry.source_metadata["source_type"] == "MAIN_DICTIONARY"
    assert entry.source_metadata["page"] == 123
    assert entry.source_metadata["status"] == "MASTER"


def test_unreviewed_entries_cannot_be_promoted():
    with pytest.raises(ValueError, match="APPROVED or MASTER"):
        validate_entry({
            "standard_form": "x",
            "melimi_form": "y",
            "status": "PENDING",
        })


def test_entries_needing_review_cannot_be_master():
    with pytest.raises(ValueError, match="NEEDS_REVIEW"):
        validate_entry({
            "standard_form": "x",
            "melimi_form": "y",
            "confidence": "NEEDS_REVIEW",
        })


def test_source_identifier_is_not_a_generic_user_source():
    assert MAIN_DICTIONARY_SOURCE == "main_dictionary:bangaaru_naanelu:2021"
