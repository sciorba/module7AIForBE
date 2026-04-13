import pytest


class TestRegister:
    def test_register_success(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "secret123"},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert "access_token" in data
        assert data["user"]["username"] == "alice"
        assert data["user"]["email"] == "alice@example.com"
        assert "password" not in data["user"]

    def test_register_duplicate_email(self, client):
        payload = {"username": "bob", "email": "bob@example.com", "password": "secret123"}
        client.post("/api/auth/register", json=payload)
        payload["username"] = "bob2"
        resp = client.post("/api/auth/register", json=payload)
        assert resp.status_code == 400
        assert "email" in resp.get_json()["errors"]

    def test_register_duplicate_username(self, client):
        client.post(
            "/api/auth/register",
            json={"username": "charlie", "email": "charlie@example.com", "password": "secret123"},
        )
        resp = client.post(
            "/api/auth/register",
            json={"username": "charlie", "email": "charlie2@example.com", "password": "secret123"},
        )
        assert resp.status_code == 400
        assert "username" in resp.get_json()["errors"]

    def test_register_missing_fields(self, client):
        resp = client.post("/api/auth/register", json={"username": "dave"})
        assert resp.status_code == 400

    def test_register_short_password(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"username": "eve", "email": "eve@example.com", "password": "123"},
        )
        assert resp.status_code == 400


class TestLogin:
    def test_login_success(self, client):
        client.post(
            "/api/auth/register",
            json={"username": "frank", "email": "frank@example.com", "password": "password123"},
        )
        resp = client.post(
            "/api/auth/login",
            json={"email": "frank@example.com", "password": "password123"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.get_json()

    def test_login_wrong_password(self, client):
        client.post(
            "/api/auth/register",
            json={"username": "grace", "email": "grace@example.com", "password": "correct"},
        )
        resp = client.post(
            "/api/auth/login",
            json={"email": "grace@example.com", "password": "wrong"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "password"},
        )
        assert resp.status_code == 401
