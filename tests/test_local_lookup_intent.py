from app.local_answer import _extract_lookup_word


def test_telugu_melimi_lookup_extracts_source_word_only():
    assert _extract_lookup_word("సంతోషం మేలిమిలో ఏమంటారు?") == "సంతోషం"
    assert _extract_lookup_word("సంతోషం మేలిమి తెలుగులో ఏమంటారు?") == "సంతోషం"
    assert _extract_lookup_word("మేలిమి తెలుగులో సంతోషం ఏమంటారు?") == "సంతోషం"
