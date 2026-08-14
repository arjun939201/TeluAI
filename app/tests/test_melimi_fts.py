from app.melimi.fts import _fts_query, chunk_text


def test_fts_query_preserves_telugu_terms():
    q = _fts_query("ఎడాటం గురించి తెలిమి")
    assert "ఎడాటం" in q
    assert "తెలిమి" in q


def test_chunk_text_returns_chunks():
    chunks = list(chunk_text("ఒకటి\n\nరెండు\n\nమూడు", size=8, overlap=2))
    assert chunks
