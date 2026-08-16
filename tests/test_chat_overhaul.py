from app.chat.router import detect_language, route_message
from app.melimi import lexical


def test_auto_router_keeps_general_chat_out_of_melimi():
    assert route_message('hi', 'auto').mode == 'standard'
    assert route_message('Explain black holes', 'auto').mode == 'standard'
    assert route_message('Write a Python REST API', 'auto').intent == 'coding'


def test_language_detection_supports_telugu_roman_and_mixed():
    assert detect_language('How are you?') == 'english'
    assert detect_language('ఎలా ఉన్నావు?') == 'telugu'
    assert detect_language('ela unnav?') == 'roman_telugu'
    assert detect_language('bro ela unnav?') == 'roman_telugu'
    assert detect_language('Python అంటే ఏమిటి?') == 'mixed'


def test_root_first_melimi_lookup_preserves_source_case(monkeypatch):
    monkeypatch.setattr(lexical, 'language_roots', lambda: {'సంతోషం': 'అలరిక'})
    assert lexical.direct_lookup('సంతోషం మేలిమి తెలుగు పదం ఏమిటి?') == 'అలరిక'
    assert lexical.direct_lookup('సంతోషాన్ని మేలిమి తెలుగు పదం ఏమిటి?') == 'అలరికని'
    assert lexical.direct_lookup('సంతోషానికి మేలిమి తెలుగు పదం ఏమిటి?') == 'అలరికకి'


def test_unknown_melimi_word_is_not_invented(monkeypatch):
    monkeypatch.setattr(lexical, 'language_roots', lambda: {})
    assert lexical.direct_lookup('అపరిచితపదం మేలిమి తెలుగు పదం ఏమిటి?') is None
