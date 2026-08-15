from app.local_answer import answer
from app.melimi.root_morphology import convert_surface, convert_text


def test_local_definition_does_not_need_groq():
    text = answer('మేలిమి తెలుగు అంటే ఏమిటి?', 'melimi')
    assert text and 'మేలిమి తెలుగు' in text


def test_root_first_examples():
    assert convert_surface('సమస్య') == 'చిక్కు'
    assert convert_surface('సమస్యలు') == 'చిక్కులు'
    assert convert_surface('సమస్యలను') == 'చిక్కులను'
    assert convert_surface('సహాయంతో') == 'బాసటతో'
    assert convert_text('సమస్యలను తీర్చు') == 'చిక్కులను తీర్చు'
