from app.melimi.root_morphology import convert_surface


def test_word_mapping_propagates_to_passive_participle():
    roots = {"నిర్వచనం": "నిర్వల్కు"}
    assert convert_surface("నిర్వచించబడిన", roots) == "నిర్వల్కబడిన"
