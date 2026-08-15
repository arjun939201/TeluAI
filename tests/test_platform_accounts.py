from fastapi.testclient import TestClient
from app.main import app


def test_auth_gate_and_register_login_flow():
    with TestClient(app) as client:
        r = client.get('/auth/me')
        assert r.status_code == 401
        r = client.post('/auth/register', json={
            'username': 'testuser_platform',
            'email': 'testuser_platform@example.com',
            'password': 'strong-password-123'
        })
        assert r.status_code == 200
        assert r.json()['authenticated'] is True
        assert client.get('/auth/me').status_code == 200
        assert client.get('/conversations').status_code == 200
        client.post('/auth/logout')
        assert client.get('/auth/me').status_code == 401
