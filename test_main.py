import os
from types import SimpleNamespace

os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_KEY"] = "test-anon-key"

import httpx
import pytest
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError

import main

USER = SimpleNamespace(id="u1", email="test@example.com", created_at="2026-01-01", app_metadata={})
ADMIN = SimpleNamespace(id="a1", email="admin@example.com", created_at="2026-01-01", app_metadata={"role": "admin"})
SESSION = SimpleNamespace(access_token="good", refresh_token="new-refresh", expires_in=3600)


def api_error(msg="nope"):
    return AuthApiError(msg, 400, "error")


class FakeAuth:
    def get_user(self, token):
        users = {"good": USER, "admin": ADMIN}
        if token not in users:
            raise api_error("invalid jwt")
        return SimpleNamespace(user=users[token])

    def sign_up(self, data):
        if data["email"] == "taken@example.com":
            raise api_error("User already registered")
        return SimpleNamespace(user=USER)

    def sign_in_with_password(self, data):
        if data["password"] != "password123":
            raise api_error("Invalid login credentials")
        return SimpleNamespace(session=SESSION)

    def refresh_session(self, token):
        if token != "valid-refresh":
            raise api_error("bad refresh")
        return SimpleNamespace(session=SESSION)


@pytest.fixture(autouse=True)
def fake_supabase(monkeypatch):
    monkeypatch.setattr(main, "get_client", lambda: SimpleNamespace(auth=FakeAuth()))


client = TestClient(main.app)
GOOD = {"Authorization": "Bearer good"}
ADMIN_H = {"Authorization": "Bearer admin"}


def test_public():
    assert client.get("/public/info").status_code == 200


def test_signup():
    assert client.post("/auth/signup", json={"email": "a@b.co"}).status_code == 400
    assert client.post("/auth/signup", json={"email": "  ", "password": " "}).status_code == 400
    assert client.post("/auth/signup", json={"email": "taken@example.com", "password": "password123"}).status_code == 400
    assert client.post("/auth/signup", json={"email": "a@b.co", "password": "password123"}).status_code == 201


def test_login():
    assert client.post("/auth/login", json={"email": "a@b.co"}).status_code == 400
    r = client.post("/auth/login", json={"email": "a@b.co", "password": "wrong"})
    assert r.status_code == 401 and r.json() == {"error": "Invalid login credentials"}
    r = client.post("/auth/login", json={"email": "a@b.co", "password": "password123"})
    assert r.status_code == 200 and r.json()["access_token"] == "good"


def test_guard():
    r = client.get("/protected/profile")
    assert r.status_code == 401 and r.json() == {"error": "Access token required"}
    assert client.get("/protected/profile", headers={"Authorization": "Token good"}).status_code == 401
    r = client.get("/protected/profile", headers={"Authorization": "Bearer goox"})
    assert r.status_code == 401 and r.json() == {"error": "Invalid or expired token"}
    assert client.get("/protected/profile", headers=GOOD).status_code == 200
    assert client.get("/protected/dashboard", headers=GOOD).status_code == 200
    assert client.get("/protected/dashboard", headers={"Authorization": "Bearer bad"}).status_code == 401


def test_refresh():
    assert client.post("/auth/refresh", json={}).status_code == 400
    assert client.post("/auth/refresh", json={"refresh_token": "nope"}).status_code == 401
    r = client.post("/auth/refresh", json={"refresh_token": "valid-refresh"})
    assert r.status_code == 200 and r.json()["refresh_token"] == "new-refresh"


def test_admin():
    assert client.get("/admin/stats", headers=GOOD).status_code == 403
    assert client.get("/admin/stats", headers=ADMIN_H).status_code == 200
    assert client.get("/admin/stats").status_code == 401


def test_logout_sends_user_token(monkeypatch):
    seen = {}

    def fake_post(url, params=None, headers=None, timeout=None):
        seen.update(url=url, params=params, headers=headers)
        return SimpleNamespace(status_code=204)

    monkeypatch.setattr(main.httpx, "post", fake_post)
    assert client.post("/auth/logout", headers=GOOD).status_code == 204
    assert seen["url"].endswith("/auth/v1/logout")
    assert seen["params"] == {"scope": "global"}
    assert seen["headers"]["Authorization"] == "Bearer good"
    assert client.post("/auth/logout").status_code == 401


def test_logout_failure_is_reported(monkeypatch):
    monkeypatch.setattr(main.httpx, "post", lambda *a, **k: SimpleNamespace(status_code=401))
    assert client.post("/auth/logout", headers=GOOD).status_code == 502

    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(main.httpx, "post", boom)
    assert client.post("/auth/logout", headers=GOOD).status_code == 502
