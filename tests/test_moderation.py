from app.moderation import moderate_screen_text, moderate_text


def test_clean_message_is_clean():
    result = moderate_screen_text([{"username": "alice", "text": "Hello, how are you?"}])
    assert result == {"screen_status": "CLEAN", "total_violations": 0, "violations": []}


def test_spam_link_and_follow_request_are_low_warn():
    result = moderate_text("alice", "follow 4 follow https://example.com")
    assert any(v.rule_id == "RULE_SPAM_SOLICITATION" and v.severity == "LOW" and v.recommended_action == "WARN" for v in result)


def test_explicit_transliterated_hindi_is_high_mute():
    result = moderate_text("user", "lund")
    assert any(v.rule_id == "RULE_SEXUAL_EXPLICIT" and v.detected_language == "Transliterated Hindi/Urdu" for v in result)


def test_threat_is_critical_ban():
    result = moderate_text("user", "I will kill you")
    assert any(v.rule_id == "RULE_HARASSMENT_HATE" and v.severity == "CRITICAL" and v.recommended_action == "BAN" for v in result)


def test_nsfw_handle_requires_review():
    result = moderate_screen_text([{"username": "example_nsfw", "text": "hello"}])
    assert result["screen_status"] == "VIOLATION_DETECTED"
    assert result["violations"][0]["rule_id"] == "RULE_INAPPROPRIATE_NICKNAME_OR_MEDIA"
    assert result["violations"][0]["recommended_action"] == "REVIEW"


def test_exact_visible_text_is_preserved():
    text = "Like for like — नमस्ते"
    result = moderate_text("Alice", text)
    assert result[0].original_text == text
    assert result[0].username == "Alice"
