from app.chat_learning import parse_command


def test_explicit_language_commands_parse():
    assert parse_command('/word ద్వేషస్పదం = కంటుపాదు')[0] == 'word'
    assert parse_command('/meaning mobile = చేవీనం')[1]['command'] == 'meaning'
    assert parse_command('/correct mobile = చేవీనం')[1]['command'] == 'correct'
    assert parse_command('/content ముప్పుకాను చోటులు ఎన్నో మన ఒలవులో ఉన్నాయి')[1]['command'] == 'content'
    assert parse_command('/example చేవీనం చేతిలో ఉంది (mobile is in the hand)')[1]['command'] == 'example'
    assert parse_command('/root ముప్పు = danger')[1]['command'] == 'root'
    assert parse_command('/affix కాను = doer suffix')[1]['command'] == 'affix'
    assert parse_command('/rule కాను = agent-forming rule')[1]['command'] == 'rule'
    assert parse_command('/phrase ముప్పుకాను చోటులు')[1]['command'] == 'phrase'
    assert parse_command('/note this is a linguistic note')[1]['command'] == 'note'


def test_normal_chat_does_not_match():
    assert parse_command('ద్వేషస్పదం = కంటుపాదు') is None
    assert parse_command('ఏం జరుగుతుంది?') is None
