from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'static/index.html'; JS=ROOT/'static/js/professional.js'

def test_main_ui_has_general_first_controls():
    html=INDEX.read_text(encoding='utf-8')
    for element_id in ('newChat','historySearch','historySort','settings','modeSelect','composer','input','send','chat'):
        assert f'id="{element_id}"' in html
    assert 'Auto' in html and 'Standard Telugu' in html and 'Melimi Telugu' in html
    assert 'professional.js' in html
    assert 'marked' in html and 'dompurify' in html

def test_frontend_has_streaming_and_message_actions():
    js=JS.read_text(encoding='utf-8')
    for token in ('/chat/stream','AbortController','Regenerate','navigator.clipboard','/feedback','/messages/'):
        assert token in js

def test_frontend_escapes_fallback_content():
    js=JS.read_text(encoding='utf-8')
    assert 'function esc' in js and '&lt;' in js
