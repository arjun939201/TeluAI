from app.models import ChatRequest, SettingsUpdateRequest
from app.prompts import MELIMI_SYSTEM, build_prompt


def test_chat_auto_mode_resolves_to_native_melimi():
    request = ChatRequest(message="hi", mode="auto")
    assert request.mode == "melimi"


def test_chat_default_mode_is_native_melimi():
    request = ChatRequest(message="నమస్కారం")
    assert request.mode == "melimi"


def test_settings_auto_mode_resolves_to_native_melimi():
    settings = SettingsUpdateRequest(preferred_mode="auto")
    assert settings.preferred_mode == "melimi"


def test_melimi_prompt_is_language_centric():
    assert "Melimi Telugu is the product's native language" in MELIMI_SYSTEM
    assert "Do not fall back to Standard Telugu" in MELIMI_SYSTEM
    assert "ROOT-FIRST UNDERSTANDING" in MELIMI_SYSTEM


def test_melimi_prompt_keeps_language_evidence_internal():
    prompt = build_prompt(mode="melimi", melimi_engine="MASTER evidence")
    assert "MASTER evidence" in prompt
    assert "USE SILENTLY" in prompt
    assert "REPLY LANGUAGE SIGNAL: telugu" in prompt
