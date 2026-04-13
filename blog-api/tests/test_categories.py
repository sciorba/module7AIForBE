import pytest


class TestCategories:
    def test_list_categories_empty(self, client):
        resp = client.get("/api/categories")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_create_category_success(self, client, auth_headers):
        resp = client.post(
            "/api/categories", json={"name": "Python"}, headers=auth_headers
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Python"
        assert data["slug"] == "python"

    def test_create_category_slug_generation(self, client, auth_headers):
        resp = client.post(
            "/api/categories",
            json={"name": "Web Development"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.get_json()["slug"] == "web-development"

    def test_create_category_duplicate(self, client, auth_headers):
        client.post("/api/categories", json={"name": "Tech"}, headers=auth_headers)
        resp = client.post("/api/categories", json={"name": "Tech"}, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_category_unauthenticated(self, client):
        resp = client.post("/api/categories", json={"name": "Anon"})
        assert resp.status_code == 401

    def test_list_categories_after_creation(self, client, auth_headers):
        client.post("/api/categories", json={"name": "Flask"}, headers=auth_headers)
        client.post("/api/categories", json={"name": "Django"}, headers=auth_headers)
        resp = client.get("/api/categories")
        assert resp.status_code == 200
        assert len(resp.get_json()) == 2
