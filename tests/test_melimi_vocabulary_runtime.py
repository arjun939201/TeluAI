from app.melimi.vocabulary_runtime import convert_text


def test_seed_vocabulary_conversion():
    assert convert_text("నమస్కారం, ఆసక్తికరమైన విషయం.") == "టేంకణం, హాళికాను ఎడాటం."


def test_english_and_unknown_words_are_handled_safely():
    assert convert_text("hi interesting subject") == "టేంకణం హాళికాను ఎడాటం"
    assert convert_text("తెలియని పదం") == "తెలియని పదం"
