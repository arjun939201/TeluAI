from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_main_workspace_uses_product_shell_assets():
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    assert "/static/css/product-excellence.css?v=20260829-1" in html
    assert "/static/js/product-excellence.js?v=20260829-1" in html
    assert 'id="sidebarToggle"' in html
    assert 'id="focusToggle"' in html


def test_product_workspace_assets_are_real_files():
    assert (ROOT / "static" / "css" / "product-excellence.css").is_file()
    assert (ROOT / "static" / "js" / "product-excellence.js").is_file()
