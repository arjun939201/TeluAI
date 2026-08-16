from app.melimi.root_morphology import reduce_to_root, convert_surface


def test_reduce_inflected_word_to_root():
    a = reduce_to_root("సమస్యలు")
    assert a.root == "సమస్య" and a.suffixes == ("లు",)


def test_convert_root():
    assert convert_surface("సమస్య") == "చిక్కు"


def test_convert_inflected_word_by_same_operation():
    assert convert_surface("సమస్యలు") == "చిక్కులు"


def test_unknown_word_is_unchanged():
    assert convert_surface("పిల్లలు") == "పిల్లలు"


def test_derivational_surface_reduces_without_per_word_rule():
    a = reduce_to_root("భాషా")
    assert a.root == "భాష" and a.suffixes == ("ా",)


def test_derivational_operation_is_central_not_word_specific():
    # The -ఆ operation is applied centrally; the dictionary contains only the root.
    assert convert_surface("భాషా") == "నుడి"


def test_am_noun_accusative_is_reduced_to_abstract_case_operation():
    roots = {"సంతోషం": "అలరిక"}
    a = reduce_to_root("సంతోషాన్ని", roots)
    assert a.root == "సంతోషం"
    assert a.operations == (("case", "ACCUSATIVE"),)


def test_am_noun_accusative_reinflects_for_non_am_melimi_root():
    roots = {"సంతోషం": "అలరిక"}
    assert convert_surface("సంతోషాన్ని", roots) == "అలరికని"


def test_am_noun_accusative_reinflects_for_am_melimi_root():
    roots = {"సంతోషం": "ఉల్లాసం"}
    assert convert_surface("సంతోషాన్ని", roots) == "ఉల్లాసాన్ని"


def test_am_noun_dative_is_reduced_to_abstract_case_operation():
    roots = {"సంతోషం": "అలరిక"}
    a = reduce_to_root("సంతోషానికి", roots)
    assert a.root == "సంతోషం"
    assert a.operations == (("case", "DATIVE"),)
    assert convert_surface("సంతోషానికి", roots) == "అలరికకి"
