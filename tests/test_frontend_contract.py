from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "static/index.html"
JS = ROOT / "static/teluai2.js"
CSS = ROOT / "static/teluai2.css"


def test_main_ui_is_focused_telugu_chat():
    html = INDEX.read_text(encoding="utf-8")
    for element_id in ("newChat", "history", "composer", "input", "send", "chat", "messages", "auth"):
        assert f'id="{element_id}"' in html
    assert 'lang="te"' in html
    assert "తెలుగులో మాట్లాడండి" in html
    assert "/static/teluai2.js" in html
    assert "/static/teluai2.css" in html
    assert "/melimi-lab" not in html
    assert "modeSelect" not in html


def test_new_frontend_uses_one_chat_transport():
    js = JS.read_text(encoding="utf-8")
    assert "'/chat'" in js
    assert "conversation_id" in js
    assert "credentials:'same-origin'" in js
    assert "const esc" in js


def test_frontend_has_no_legacy_stream_or_workspace_controls():
    html = INDEX.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert "/chat/stream" not in js
    assert "Melimi Telugu Lab" not in html
    assert "adminButton" not in html


def test_product_css_is_responsive():
    css = CSS.read_text(encoding="utf-8")
    assert "@media(max-width:760px)" in css
    assert "overflow:hidden" in css
