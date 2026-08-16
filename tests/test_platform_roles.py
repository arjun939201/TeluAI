import os
os.environ.setdefault("TELUAI_OWNER_EMAIL","role_owner@example.com")
from fastapi.testclient import TestClient
from app.main import app

def test_owner_bootstrap_and_admin_permissions():
    with TestClient(app) as owner:
        r=owner.post("/auth/register",json={"username":"role_owner","email":"role_owner@example.com","password":"strong-password-123"}); assert r.status_code==200
        r=owner.post("/auth/bootstrap-owner"); assert r.status_code==200; assert r.json()["role"]=="owner"
        with TestClient(app) as second:
            r=second.post("/auth/register",json={"username":"role_admin","email":"role_admin@example.com","password":"strong-password-123"}); assert r.status_code==200
            assert second.get("/admin/database/stats").status_code==403
        users=owner.get("/admin/database/users").json()["users"]; admin_id=next(u["id"] for u in users if u["email"]=="role_admin@example.com"); owner_id=next(u["id"] for u in users if u["email"]=="role_owner@example.com")
        r=owner.post(f"/admin/users/{admin_id}/role?role=admin"); assert r.status_code==200; assert r.json()["user"]["role"]=="admin"
        assert owner.get("/admin/database/stats").status_code==200; assert owner.get("/admin/database/language").status_code==200
        with TestClient(app) as admin:
            r=admin.post("/auth/login",json={"identifier":"role_admin@example.com","password":"strong-password-123"}); assert r.status_code==200
            assert admin.get("/admin/database/stats").status_code==200; assert admin.post(f"/admin/users/{owner_id}/role?role=user").status_code==403
