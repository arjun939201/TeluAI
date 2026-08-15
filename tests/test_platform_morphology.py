from app.melimi.root_morphology import reduce_to_root, convert_surface


def test_root_first_plural():
    f = reduce_to_root("సమస్యలు")
    assert f.root == "సమస్య"
    assert f.suffixes == ("లు",)
    assert convert_surface("సమస్యలు") == "చిక్కులు"


def test_root_first_case_chain():
    assert convert_surface("సమస్యలను") == "చిక్కులను"
    assert convert_surface("సమస్యలకు") == "చిక్కులకు"


def test_root_first_derivational_surface():
    f = reduce_to_root("భాషా")
    assert f.root == "భాష"
    assert f.suffixes == ("ా",)
    # -ఆ is handled by the central grammatical operation, not a word-specific mapping.
    assert convert_surface("భాషా") == "నుడి"


def test_unknown_surface_is_preserved():
    assert convert_surface("పిల్లలు") == "పిల్లలు"


def test_am_stem_morphophonemics_are_generic():
    assert convert_surface("సినిమాలు") == "తెఱాటాలు"
    assert convert_surface("సినిమాలను") == "తెఱాటాలను"
    assert convert_surface("సినిమాలకు") == "తెఱాటాలకు"
