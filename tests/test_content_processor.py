from app.melimi.content_processor import extract_explicit_items, summarize_content


def test_content_processor_extracts_explicit_mapping():
    items = extract_explicit_items("danger = ముప్పుకాను")
    assert len(items) == 1
    assert items[0].kind == "vocabulary"
    assert items[0].form == "danger"
    assert items[0].meaning == "ముప్పుకాను"


def test_content_processor_extracts_language_structure():
    summary = summarize_content(
        "danger = ముప్పుకాను\n"
        "root: ముప్పు = danger\n"
        "suffix (affix) = కాను\n"
        "grammar: కాను is an agent/doer suffix\n"
        "example: ముప్పుకాను = dangerous\n"
        "phrase: ముప్పుకాను మాట\n"
    )
    assert summary["item_count"] == 5
    assert summary["vocabulary"][0]["meaning"] == "ముప్పుకాను"
    assert summary["roots"][0]["form"] == "ముప్పు"
    assert summary["affixes"][0]["form"] == "suffix"
    assert summary["rules"][0]["form"] == "grammar"
    assert summary["examples"][0]["form"] == "ముప్పుకాను"
    assert summary["phrases"][0]["form"] == "ముప్పుకాను మాట"


def test_content_processor_handles_bullets_and_deduplicates():
    items = extract_explicit_items(
        "- danger = ముప్పుకాను\n"
        "* danger = ముప్పుకాను\n"
        "1. singer = పాటకాను\n"
    )
    assert [(i.form, i.meaning) for i in items] == [
        ("danger", "ముప్పుకాను"),
        ("singer", "పాటకాను"),
    ]


def test_content_processor_does_not_promote_plain_observation():
    assert extract_explicit_items("ఇది ఒక మేలిమి తెలుగు వాక్యం") == []
