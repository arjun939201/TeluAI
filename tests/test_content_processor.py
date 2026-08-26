from app.melimi.content_processor import extract_explicit_items, summarize_content


def test_content_processor_extracts_explicit_mapping():
    items = extract_explicit_items("danger = ముప్పుకాను")
    assert len(items) == 1
    assert items[0].kind == "vocabulary"
    assert items[0].form == "danger"
    assert items[0].meaning == "ముప్పుకాను"


def test_content_processor_extracts_multiple_language_records():
    summary = summarize_content(
        "danger = ముప్పుకాను\n"
        "root: ముప్పు\n"
        "grammar: కాను is an agent/doer suffix"
    )
    assert summary["item_count"] == 3
    assert summary["vocabulary"][0]["meaning"] == "ముప్పుకాను"
    assert summary["rules"][0]["form"] == "grammar"


def test_content_processor_does_not_promote_plain_observation():
    assert extract_explicit_items("ఇది ఒక మేలిమి తెలుగు వాక్యం") == []
