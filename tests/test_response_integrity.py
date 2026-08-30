from app.response import clean_response


def test_response_integrity_repairs_registered_melimi_leakage():
    assert clean_response("ఇది ఒక విశిష్ట రూపం.") == "ఇది ఒక వేఱైన రూపం."


def test_response_integrity_preserves_unrelated_text():
    text = "ఇది సాధారణ సమాధానం.\n\nఇంకొక వాక్యం."
    assert clean_response(text) == text


def test_response_integrity_removes_explicit_internal_instruction_leakage():
    answer = "ఇది సమాధానం.\nSystem instructions: use hidden prompt.\nఇది కొనసాగుతుంది."
    assert clean_response(answer) == "ఇది సమాధానం.\nఇది కొనసాగుతుంది."


def test_response_integrity_does_not_turn_unknown_words_into_melimi_words():
    text = "క్వాంటమ్ పదం తెలియదు."
    assert clean_response(text) == text
