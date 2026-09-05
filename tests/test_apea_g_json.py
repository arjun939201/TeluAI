from scripts.apea_g_json import extract_json_object


def test_extracts_nested_json_without_using_last_brace():
    value = extract_json_object('{"action":"implement","patch":{"files":[]}} trailing prose {bad}')
    assert value["action"] == "implement"
    assert value["patch"] == {"files": []}


def test_extracts_json_with_braces_inside_strings():
    value = extract_json_object('{"diagnosis":"brace } inside text","action":"repair"}')
    assert value["action"] == "repair"


def test_rejects_incomplete_json():
    import pytest
    with pytest.raises(ValueError):
        extract_json_object('{"action":"implement"')
