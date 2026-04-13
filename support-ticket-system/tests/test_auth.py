class TestRegister:
    def test_register_customer_success(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "Test User", "email": "test@example.com",
            "password": "password123", "role": "customer"
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert "access_token" in data
        assert data["user"]["role"] == "customer"
        assert "password" not in data["user"]

    def test_register_agent(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "Agent X", "email": "agentx@example.com",
            "password": "password123", "role": "agent",
            "expertise_areas": ["technical", "billing"]
        })
        assert resp.status_code == 201
        assert resp.get_json()["user"]["role"] == "agent"

    def test_register_duplicate_email_fails(self, client):
        client.post("/api/auth/register", json={
            "name": "First", "email": "dup@example.com", "password": "password123"
        })
        resp = client.post("/api/auth/register", json={
            "name": "Second", "email": "dup@example.com", "password": "password123"
        })
        assert resp.status_code == 400
        assert resp.get_json()["code"] == "VALIDATION_ERROR"

    def test_register_invalid_email_fails(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "Bad", "email": "not-an-email", "password": "password123"
        })
        assert resp.status_code == 400

    def test_register_short_password_fails(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "Short", "email": "short@example.com", "password": "123"
        })
        assert resp.status_code == 400


class TestLogin:
    def test_login_success(self, client):
        client.post("/api/auth/register", json={
            "name": "Login User", "email": "login@example.com", "password": "password123"
        })
        resp = client.post("/api/auth/login", json={
            "email": "login@example.com", "password": "password123"
        })
        assert resp.status_code == 200
        assert "access_token" in resp.get_json()

    def test_login_wrong_password(self, client):
        client.post("/api/auth/register", json={
            "name": "User", "email": "user@example.com", "password": "correct"
        })
        resp = client.post("/api/auth/login", json={
            "email": "user@example.com", "password": "wrong"
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "nobody@example.com", "password": "password"
        })
        assert resp.status_code == 401

    def test_me_requires_auth(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_returns_current_user(self, client, customer_headers):
        resp = client.get("/api/auth/me", headers=customer_headers)
        assert resp.status_code == 200
        assert resp.get_json()["email"] == "alice@example.com"
