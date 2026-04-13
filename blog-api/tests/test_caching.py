"""
Tests for caching behaviour.

We cache dicts (not Flask Response objects) so cache.get() works directly
in tests. This also avoids the pytest-flask JSONResponse pickling issue.

Two layers of verification:
  1. Internal — cache.get(key) confirms data is stored / evicted.
  2. Functional — GET after a write returns fresh data (not the stale cached value).
"""
import pytest
from app import cache as _cache
from app.utils.cache_keys import CATEGORIES_KEY, post_detail_key_for_id, post_list_key, search_key


def create_post(client, headers, title="Cached Post", content="Some content"):
    resp = client.post(
        "/api/posts",
        json={"title": title, "content": content},
        headers=headers,
    )
    return resp.get_json()["id"]


# ---------------------------------------------------------------------------
# Post detail caching
# ---------------------------------------------------------------------------

class TestPostDetailCaching:
    def test_cache_populated_after_get(self, app, client, auth_headers):
        post_id = create_post(client, auth_headers)

        with app.app_context():
            assert _cache.get(post_detail_key_for_id(post_id)) is None

        client.get(f"/api/posts/{post_id}")

        with app.app_context():
            assert _cache.get(post_detail_key_for_id(post_id)) is not None

    def test_cache_invalidated_after_update(self, app, client, auth_headers):
        post_id = create_post(client, auth_headers, "Original")
        client.get(f"/api/posts/{post_id}")  # populate cache

        with app.app_context():
            assert _cache.get(post_detail_key_for_id(post_id)) is not None

        client.put(
            f"/api/posts/{post_id}",
            json={"title": "Updated"},
            headers=auth_headers,
        )

        with app.app_context():
            assert _cache.get(post_detail_key_for_id(post_id)) is None

    def test_stale_data_not_served_after_update(self, client, auth_headers):
        """After update, GET must return fresh data — not the old cached value."""
        post_id = create_post(client, auth_headers, "Old Title")
        client.get(f"/api/posts/{post_id}")  # populate cache

        client.put(
            f"/api/posts/{post_id}",
            json={"title": "New Title"},
            headers=auth_headers,
        )

        resp = client.get(f"/api/posts/{post_id}")
        assert resp.get_json()["title"] == "New Title"

    def test_cache_cleared_after_delete(self, app, client, auth_headers):
        post_id = create_post(client, auth_headers)
        client.get(f"/api/posts/{post_id}")  # populate cache

        with app.app_context():
            assert _cache.get(post_detail_key_for_id(post_id)) is not None

        client.delete(f"/api/posts/{post_id}", headers=auth_headers)

        with app.app_context():
            assert _cache.get(post_detail_key_for_id(post_id)) is None

    def test_cache_invalidated_after_comment(self, app, client, auth_headers):
        """Adding a comment changes comment_count — detail cache must be busted."""
        post_id = create_post(client, auth_headers)
        client.get(f"/api/posts/{post_id}")  # populate cache (comment_count=0)

        with app.app_context():
            assert _cache.get(post_detail_key_for_id(post_id)) is not None

        client.post(
            f"/api/posts/{post_id}/comments",
            json={"content": "A comment"},
            headers=auth_headers,
        )

        with app.app_context():
            assert _cache.get(post_detail_key_for_id(post_id)) is None

    def test_comment_count_reflects_after_comment(self, client, auth_headers):
        post_id = create_post(client, auth_headers)
        client.get(f"/api/posts/{post_id}")  # cache comment_count=0

        client.post(
            f"/api/posts/{post_id}/comments",
            json={"content": "hello"},
            headers=auth_headers,
        )

        resp = client.get(f"/api/posts/{post_id}")
        assert resp.get_json()["comment_count"] == 1


# ---------------------------------------------------------------------------
# Post list caching
# ---------------------------------------------------------------------------

class TestPostListCaching:
    def test_cache_populated_after_list(self, app, client, auth_headers):
        create_post(client, auth_headers)
        client.get("/api/posts")

        with app.app_context():
            assert _cache.get(post_list_key(1, 20)) is not None

    def test_cache_invalidated_after_create(self, app, client, auth_headers):
        client.get("/api/posts")  # populate cache

        with app.app_context():
            assert _cache.get(post_list_key(1, 20)) is not None

        create_post(client, auth_headers, "New Post")

        with app.app_context():
            assert _cache.get(post_list_key(1, 20)) is None

    def test_new_post_appears_in_list_after_create(self, client, auth_headers):
        """List must reflect the new post immediately after creation."""
        client.get("/api/posts")  # warm up cache (empty list)

        create_post(client, auth_headers, "Fresh Post")

        resp = client.get("/api/posts")
        titles = [p["title"] for p in resp.get_json()["posts"]]
        assert "Fresh Post" in titles

    def test_list_cache_stores_correct_data(self, app, client, auth_headers):
        create_post(client, auth_headers, "My Post")
        client.get("/api/posts")

        with app.app_context():
            data = _cache.get(post_list_key(1, 20))
        assert data is not None
        assert any(p["title"] == "My Post" for p in data["posts"])


# ---------------------------------------------------------------------------
# Category caching
# ---------------------------------------------------------------------------

class TestCategoryCaching:
    def test_cache_populated_after_list(self, app, client):
        client.get("/api/categories")

        with app.app_context():
            assert _cache.get(CATEGORIES_KEY) is not None

    def test_cache_invalidated_after_create(self, app, client, auth_headers):
        client.get("/api/categories")  # populate cache

        with app.app_context():
            assert _cache.get(CATEGORIES_KEY) is not None

        client.post("/api/categories", json={"name": "Python"}, headers=auth_headers)

        with app.app_context():
            assert _cache.get(CATEGORIES_KEY) is None

    def test_new_category_appears_after_create(self, client, auth_headers):
        client.get("/api/categories")  # warm up cache

        client.post("/api/categories", json={"name": "Go"}, headers=auth_headers)

        resp = client.get("/api/categories")
        names = [c["name"] for c in resp.get_json()]
        assert "Go" in names


# ---------------------------------------------------------------------------
# Search caching
# ---------------------------------------------------------------------------

class TestSearchCaching:
    def test_cache_populated_after_search(self, app, client, auth_headers):
        client.post(
            "/api/posts",
            json={"title": "Flask deep dive", "content": "ORM tips"},
            headers=auth_headers,
        )
        client.get("/api/search?q=Flask")

        with app.app_context():
            assert _cache.get(search_key("Flask", 1)) is not None

    def test_search_cache_invalidated_after_post_created(self, app, client, auth_headers):
        client.post(
            "/api/posts",
            json={"title": "Existing post", "content": "content"},
            headers=auth_headers,
        )
        client.get("/api/search?q=Existing")  # populate cache

        with app.app_context():
            assert _cache.get(search_key("Existing", 1)) is not None

        # New post that matches the same query
        client.post(
            "/api/posts",
            json={"title": "Existing post 2", "content": "content"},
            headers=auth_headers,
        )

        with app.app_context():
            assert _cache.get(search_key("Existing", 1)) is None

    def test_search_result_reflects_new_post(self, client, auth_headers):
        client.get("/api/search?q=Rocket")  # prime empty cache

        client.post(
            "/api/posts",
            json={"title": "Rocket Science", "content": "hard"},
            headers=auth_headers,
        )

        resp = client.get("/api/search?q=Rocket")
        assert len(resp.get_json()["posts"]) == 1
