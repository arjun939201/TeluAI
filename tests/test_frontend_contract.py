from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "static" / "index.html"
JS = ROOT / "static" / "js" / "professional.js"
ENHANCEMENTS = ROOT / "static" / "js" / "chat-enhancements.js"


def test_main_ui_has_current_navigation_controls():
    html = INDEX.read_text(encoding="utf-8")
    for element_id in (
        "newChat", "profileLink", "profileMenuItem", "settingsLink", "logout",
        "history", "profile", "settings", "historySearch", "historySort", "historyAll",
    ):
        assert f'id="{element_id}"' in html
    assert 'professional.js' in html
    assert 'chat-enhancements.js' in html
    assert 'enhancements.css' in html


def test_current_frontend_contains_contextual_history_and_account_handlers():
    js = JS.read_text(encoding="utf-8")
    for token in (
        "loadHistory", "openConversation", "openProfile", "openSettings",
        "saveCredentials", "logout", "formatHistoryDate",
    ):
        assert token in js


def test_frontend_escapes_rendered_user_content():
    js = JS.read_text(encoding="utf-8")
    assert "function esc" in js
    assert "&lt;" in js or "&amp;" in js


def test_chat_enhancements_keep_rich_rendering_safe():
    js = ENHANCEMENTS.read_text(encoding="utf-8")
    assert "escapeHtml" in js
    assert "renderMarkdown" in js
    assert "navigator.clipboard" in js
    assert "innerHTML" in js
