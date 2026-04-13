import pytest


class TestSearch:
    def test_search_missing_query(self, client):
        resp = client.get("/api/search")
        assert resp.status_code == 400

    def test_search_by_title(self, client, auth_headers):
        client.post(
            "/api/posts",
            json={"title": "Flask Tutorial", "content": "Learn Flask"},
            headers=auth_headers,
        )
        client.post(
            "/api/posts",
            json={"title": "Django Guide", "content": "Learn Django"},
            headers=auth_headers,
        )
        resp = client.get("/api/search?q=Flask")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["posts"]) == 1
        assert data["posts"][0]["title"] == "Flask Tutorial"
        assert data["query"] == "Flask"

    def test_search_by_content(self, client, auth_headers):
        client.post(
            "/api/posts",
            json={"title": "Python Tips", "content": "Use list comprehensions for performance"},
            headers=auth_headers,
        )
        resp = client.get("/api/search?q=comprehensions")
        assert resp.status_code == 200
        assert len(resp.get_json()["posts"]) == 1

    def test_search_no_results(self, client):
        resp = client.get("/api/search?q=zzznomatch")
        assert resp.status_code == 200
        assert resp.get_json()["posts"] == []

    def test_search_case_insensitive(self, client, auth_headers):
        client.post(
            "/api/posts",
            json={"title": "SQLAlchemy Deep Dive", "content": "ORM patterns"},
            headers=auth_headers,
        )
        resp = client.get("/api/search?q=sqlalchemy")
        assert resp.status_code == 200
        assert len(resp.get_json()["posts"]) == 1

    def test_search_pagination(self, client, auth_headers):
        for i in range(5):
            client.post(
                "/api/posts",
                json={"title": f"Searchable Post {i}", "content": "unique keyword"},
                headers=auth_headers,
            )
        resp = client.get("/api/search?q=unique+keyword&page=1")
        assert resp.status_code == 200
        assert resp.get_json()["pagination"]["total"] == 5

    def test_search_excludes_unpublished(self, client, auth_headers):
        client.post(
            "/api/posts",
            json={"title": "Secret Draft", "content": "hidden content", "published": False},
            headers=auth_headers,
        )
        resp = client.get("/api/search?q=Secret+Draft")
        assert resp.status_code == 200
        assert resp.get_json()["posts"] == []

    def test_search_empty_string_returns_400(self, client):
        resp = client.get("/api/search?q=")
        assert resp.status_code == 400

    def test_search_returns_pagination_metadata(self, client, auth_headers):
        client.post(
            "/api/posts",
            json={"title": "Meta Post", "content": "pagination check"},
            headers=auth_headers,
        )
        resp = client.get("/api/search?q=Meta+Post")
        data = resp.get_json()
        assert "pagination" in data
        assert "total" in data["pagination"]
        assert "pages" in data["pagination"]
        assert "has_next" in data["pagination"]
