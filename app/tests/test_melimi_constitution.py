from app.melimi.constitution import language_constitution
from app.prompts import build_prompt


def test_constitution_contains_core_language_identity_and_morphology():
    c = language_constitution()
    assert "distinct Telugu-based language register/language system" in c
    assert "ముప్పుకాను" in c
    assert "హాళికాను" in c
    assert "అలవి/అల్వి" in c
    assert "సమస్య→చిక్కు" in c


def test_melimi_prompt_always_contains_constitution():
    prompt = build_prompt("melimi")
    assert "MELIMI TELUGU — CORE LANGUAGE CONSTITUTION" in prompt
    assert "ముప్పుకాను" in prompt
    assert "Standard Telugu" in prompt and "Mixed Telugu" in prompt and "Melimi Telugu" in prompt
