from app.texl_brain import analyze_language

VOCAB = [
    {"kind": "VOCABULARY", "key": "ధన్యవాదం", "value": "నెనరు", "source": "owner"},
]


def test_accusative_am_noun_surface_exposes_morphology():
    result = analyze_language("ధన్యవాదాన్ని", VOCAB)
    item = next(x for x in result.evidence if x.token == "ధన్యవాదాన్ని")
    assert item.canonical == "ధన్యవాదం"
    assert item.melimi == "నెనరు"
    assert item.relation == "validated_inflection"
    assert item.morphology == "accusative"
    assert item.authoritative is True


def test_dative_am_noun_surface_exposes_morphology():
    result = analyze_language("ధన్యవాదానికి", VOCAB)
    item = next(x for x in result.evidence if x.token == "ధన్యవాదానికి")
    assert item.canonical == "ధన్యవాదం"
    assert item.morphology == "dative"
