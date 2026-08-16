from app.chat_commands import parse_chat_command


def test_word_command_parses_mapping():
    command = parse_chat_command("/word દ્વેષస్పదం = కంటుపాదు")
    assert command.kind == "word"
    assert command.payload["standard_or_source"] == "ద్వేషస్పదం"
    assert command.payload["melimi_root"] == "కంటుపాదు"


def test_content_command_parses_optional_meaning():
    command = parse_chat_command("/content ముప్పుకాను చోటులు ఎన్నో మన ఒలవులో ఉన్నాయి (ప్రమాదకరమైన ప్రదేశాలు ఎన్నో మన ప్రపంచంలో ఉన్నాయి)")
    assert command.kind == "content"
    assert command.payload["content"] == "ముప్పుకాను చోటులు ఎన్నో మన ఒలవులో ఉన్నాయి"
    assert command.payload["meaning"] == "ప్రమాదకరమైన ప్రదేశాలు ఎన్నో మన ప్రపంచంలో ఉన్నాయి"


def test_normal_sentence_is_not_a_command():
    assert parse_chat_command("ద్వేషస్పదం = కంటుపాదు") is None
