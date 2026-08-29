from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'static/index.html'
JS = ROOT / 'static/js/professional.js'
ENGINE = ROOT / 'static/js/teluai-engine.js'


def test_main_ui_is_a_single_telugu_chat_surface():
    html = INDEX.read_text(encoding='utf-8')
    for element_id in ('newChat', 'historySearch', 'historySort', 'settingsButton', 'composer', 'input', 'send', 'chat'):
        assert f'id="{element_id}"' in html
    assert 'id="modeSelect"' not in html
    assert 'Standard Telugu' not in html
    assert 'Melimi Telugu' not in html
    assert 'Melimi Telugu Lab' not in html
    assert 'Write a Python function' not in html
    assert 'What is Python and why is it useful?' not in html
    assert 'professional.js' in html
    assert 'marked' in html and 'dompurify' in html


def test_frontend_has_streaming_and_message_actions():
    js = JS.read_text(encoding='utf-8')
    for token in ('/chat/stream', 'AbortController', 'Regenerate', 'navigator.clipboard', '/feedback', '/messages/'):
        assert token in js


def test_frontend_escapes_fallback_content():
    js = JS.read_text(encoding='utf-8')
    assert 'function esc' in js and '&lt;' in js


def test_engine_status_uses_health_without_transport_override():
    js = ENGINE.read_text(encoding='utf-8')
    assert "fetch('/health'" in js
    assert 'window.fetch' not in js
    assert 'ReadableStream' not in js
    assert "'/chat'" not in js


def test_engine_does_not_own_language_mode_routing():
    js = ENGINE.read_text(encoding='utf-8')
    assert 'preferred_mode' not in js
