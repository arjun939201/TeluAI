from app.texl_routes import owner_only, admin_or_owner
from app.texl_service import propose
from app.teluai2_learning import LearningSuggestion


def test_texl_is_owner_only_compatibility_guard():
    class User:
        role = "user"
    from fastapi import HTTPException
    try:
        owner_only(User())
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("non-owner passed owner-only guard")


def test_texl_admin_or_owner_accepts_admin():
    class User:
        role = "admin"
    assert admin_or_owner(User()) is not None


def test_texl_admin_or_owner_accepts_owner():
    class User:
        role = "owner"
    assert admin_or_owner(User()) is not None


def test_texl_admin_or_owner_rejects_user():
    class User:
        role = "user"
    from fastapi import HTTPException
    try:
        admin_or_owner(User())
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("ordinary user accessed trusted TEX-L guard")


def test_texl_proposal_requires_valid_learning():
    assert propose(LearningSuggestion("VOCABULARY", "", "నెనరు", "test")) is None
