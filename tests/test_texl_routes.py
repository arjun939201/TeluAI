from app.texl_routes import owner_only
from app.texl_service import propose
from app.teluai2_learning import LearningSuggestion


def test_texl_is_owner_only():
    class User:
        role = "user"
    from fastapi import HTTPException
    try:
        owner_only(User())
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("non-owner accessed TEX-L")


def test_texl_proposal_requires_valid_learning():
    assert propose(LearningSuggestion("VOCABULARY", "", "నెనరు", "test")) is None
