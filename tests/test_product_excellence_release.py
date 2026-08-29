from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_product_excellence_bundle_is_wired():
    html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
    assert '/static/css/product-excellence.css?v=20260829-1' in html
    assert '/static/js/product-excellence.js?v=20260829-1' in html
    assert 'id="sidebarToggle"' in html
    assert 'id="focusToggle"' in html
