from app.texl_generation import build_generation_contract, validate_generated_response
from app.texl_representation import represent_language

VOCAB = [{"kind": "VOCABULARY", "key": "ధన్యవాదం", "value": "నెనరు", "source": "owner"}]


def test_lexical_generation_contract_requires_canonical_equivalent():
    representation = represent_language("ధన్యవాదాన్ని మేలిమి తెలుగులో ఏమంటారు?", VOCAB)
    contract = build_generation_contract(representation)
    assert "lexical-equivalent question" in contract
    assert "నెనరు" in contract
    assert "not a source-case-inflected version" in contract


def test_lexical_validator_rejects_inflected_melimi_answer():
    representation = represent_language("ధన్యవాదాన్ని మేలిమి తెలుగులో ఏమంటారు?", VOCAB)
    result = validate_generated_response("నెనరును అంటారు.", representation)
    assert result["valid"] is False
    assert "lexical_equivalent_has_source_case_transfer" in result["issues"]
    assert result["repairable"] is True


def test_lexical_validator_accepts_canonical_melimi_answer():
    representation = represent_language("ధన్యవాదాన్ని మేలిమి తెలుగులో ఏమంటారు?", VOCAB)
    result = validate_generated_response("నెనరు అంటారు.", representation)
    assert result["valid"] is True
    assert result["issues"] == []


def test_sentence_contract_preserves_role_without_inventing_inflection():
    representation = represent_language("ధన్యవాదాన్ని తెలియజేయు", VOCAB)
    contract = build_generation_contract(representation)
    result = validate_generated_response("నెనరును తెలియజేయు.", representation)
    assert representation.regeneration_role == "object"
    assert "Target grammatical role identified by TEX-L: object." in contract
    assert result["valid"] is True
    assert result["repairable"] is False


def test_unknown_sentence_does_not_claim_regeneration():
    representation = represent_language("తెలియని పదాన్ని తెలియజేయు", VOCAB)
    contract = build_generation_contract(representation)
    assert "No authoritative grammatical regeneration role" in contract
    result = validate_generated_response("తెలియని పదాన్ని తెలియజేయు.", representation)
    assert result["valid"] is True
