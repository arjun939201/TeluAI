from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "static" / "index.html"
NAV = ROOT / "static" / "js" / "navigation-fix.js"


def test_main_ui_has_core_navigation_controls():
    html = INDEX.read_text(encoding="utf-8")
    for element_id in ("historyLink", "profileLink", "profileMenuItem", "settingsLink", "logout", "history", "profile", "settings"):
        assert f'id="{element_id}"' in html
    assert 'navigation-fix.js' in html


def test_navigation_guard_is_fail_safe():
    js = NAV.read_text(encoding="utf-8")
    assert "if (!node) return" in js
    assert "openHistory" in js
    assert "openProfileSafe" in js
    assert "#settingsLink" in js
    assert "#logout" in js


def test_navigation_guard_does_not_require_optional_assistant_control():
    js = NAV.read_text(encoding="utf-8")
    assert "bind('#assistantLink'" not in js
