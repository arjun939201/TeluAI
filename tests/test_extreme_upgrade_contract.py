from app.linguistics.normalizer import normalize_roman_telugu
from app.local_answer import _extract_lookup_word
from app.prompts import build_prompt


def test_specific_telugu_lookup_pattern_wins_over_generic_what_pattern():
    assert _extract_lookup_word("సాయం అంటే ఏమిటి?") == "సాయం"


def test_unknown_lookup_is_not_claimed_as_authoritative():
    prompt = build_prompt("melimi")
    assert "PRIMARY RULE — CONVERSATION BEFORE ANALYSIS" in prompt
    assert "సాధారణ సంభాషణను భాషా పాఠం, నిఘంటువు, వ్యాకరణ విశ్లేషణ లేదా పరిశోధనా నివేదికగా మార్చవద్దు" in prompt
    assert "తెలియని పదాన్ని ఊహించి కల్పించవద్దు" in prompt


def test_mixed_roman_telugu_is_normalized():
    assert normalize_roman_telugu("nenu బాగున్నాను") == "నేను బాగున్నాను"
