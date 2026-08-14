from app.melimi.fast_answers import local_answer
from app.melimi.firewall import deterministic_repair, lexical_violations
from app.config import settings


def test_definition_uses_local_authoritative_answer():
    answer = local_answer("మేలిమి తెలుగు అంటే ఏమిటి?", "melimi")
    assert answer
    assert "పరిమాణం" not in answer
    assert "విశిష్ట" not in answer
    assert "వేఱైన" in answer


def test_explicit_leakage_is_detected_and_repaired():
    violations = lexical_violations("ఇది ఒక విశిష్ట రూపం.")
    assert any(v["source"] == "విశిష్ట" for v in violations)
    repaired = deterministic_repair("ఇది ఒక విశిష్ట రూపం.")
    assert "విశిష్ట" not in repaired
    assert "వేఱైన" in repaired


def test_adjective_leakage_is_repaired():
    assert deterministic_repair("ఇది ఆసక్తికరమైన ఎడాటం.") == "ఇది హాళికాను ఎడాటం."


def test_low_groq_budget_defaults():
    # max_response_tokens was previously capped at 220 to protect the Groq
    # free-tier TPM budget, but that caused real replies to be cut off
    # mid-word (see tests/test_response_completion.py). Input-side context
    # stays small; only the output budget was raised.
    assert settings.max_system_chars <= 4200
    assert settings.max_user_chars <= 2400
    assert settings.max_response_tokens >= 500
