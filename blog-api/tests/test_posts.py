import pytest


def create_post(client, headers, title="Test Post", content="Test content"):
    return client.post(
        "/api/posts",
        json={"title": title, "content": content},
        headers=headers,
    )


class TestListPosts:
    def test_list_posts_empty(self, client):
        resp = client.get("/api/posts")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["posts"] == []
        assert data["pagination"]["total"] == 0

    def test_list_posts_with_data(self, client, auth_headers):
        create_post(client, auth_headers, "Post 1", "Content 1")
        create_post(client, auth_headers, "Post 2", "Content 2")
        resp = client.get("/api/posts")
        assert resp.status_code == 200
        assert len(resp.get_json()["posts"]) == 2

    def test_list_posts_pagination(self, client, auth_headers):
        for i in range(5):
            create_post(client, auth_headers, f"Post {i}", f"Content {i}")
        resp = client.get("/api/posts?page=1&per_page=3")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["posts"]) == 3
        assert data["pagination"]["total"] == 5


class TestCreatePost:
    def test_create_post_success(self, client, auth_headers):
        resp = create_post(client, auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["title"] == "Test Post"
        assert data["author"]["username"] == "testuser"

    def test_create_post_unauthenticated(self, client):
        resp = client.post("/api/posts", json={"title": "T", "content": "C"})
        assert resp.status_code == 401

    def test_create_post_missing_title(self, client, auth_headers):
        resp = client.post("/api/posts", json={"content": "only content"}, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_post_with_categories(self, client, auth_headers):
        cat_resp = client.post(
            "/api/categories", json={"name": "Tech"}, headers=auth_headers
        )
        cat_id = cat_resp.get_json()["id"]
        resp = client.post(
            "/api/posts",
            json={"title": "Tech Post", "content": "Content", "category_ids": [cat_id]},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert len(resp.get_json()["categories"]) == 1


class TestGetPost:
    def test_get_post_success(self, client, auth_headers):
        post_resp = create_post(client, auth_headers)
        post_id = post_resp.get_json()["id"]
        resp = client.get(f"/api/posts/{post_id}")
        assert resp.status_code == 200
        assert resp.get_json()["id"] == post_id

    def test_get_post_not_found(self, client):
        resp = client.get("/api/posts/9999")
        assert resp.status_code == 404


class TestUpdatePost:
    def test_update_post_success(self, client, auth_headers):
        post_id = create_post(client, auth_headers).get_json()["id"]
        resp = client.put(
            f"/api/posts/{post_id}",
            json={"title": "Updated Title"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["title"] == "Updated Title"

    def test_update_post_forbidden(self, client, auth_headers, second_auth_headers):
        post_id = create_post(client, auth_headers).get_json()["id"]
        resp = client.put(
            f"/api/posts/{post_id}",
            json={"title": "Hijacked"},
            headers=second_auth_headers,
        )
        assert resp.status_code == 403

    def test_update_post_unauthenticated(self, client, auth_headers):
        post_id = create_post(client, auth_headers).get_json()["id"]
        resp = client.put(f"/api/posts/{post_id}", json={"title": "X"})
        assert resp.status_code == 401


class TestDeletePost:
    def test_delete_post_success(self, client, auth_headers):
        post_id = create_post(client, auth_headers).get_json()["id"]
        resp = client.delete(f"/api/posts/{post_id}", headers=auth_headers)
        assert resp.status_code == 204
        assert client.get(f"/api/posts/{post_id}").status_code == 404

    def test_delete_post_forbidden(self, client, auth_headers, second_auth_headers):
        post_id = create_post(client, auth_headers).get_json()["id"]
        resp = client.delete(f"/api/posts/{post_id}", headers=second_auth_headers)
        assert resp.status_code == 403

    def test_delete_post_cascades_comments(self, client, auth_headers):
        """Deleting a post must also delete its comments (cascade)."""
        post_id = create_post(client, auth_headers).get_json()["id"]
        client.post(
            f"/api/posts/{post_id}/comments",
            json={"content": "will be deleted"},
            headers=auth_headers,
        )
        client.delete(f"/api/posts/{post_id}", headers=auth_headers)
        # Post is gone — comment endpoint also returns 404
        assert client.get(f"/api/posts/{post_id}/comments").status_code == 404


class TestUnpublishedPosts:
    def test_unpublished_post_not_in_list(self, client, auth_headers):
        client.post(
            "/api/posts",
            json={"title": "Draft", "content": "Not ready", "published": False},
            headers=auth_headers,
        )
        resp = client.get("/api/posts")
        titles = [p["title"] for p in resp.get_json()["posts"]]
        assert "Draft" not in titles

    def test_unpublished_post_not_accessible_by_id(self, client, auth_headers):
        post_id = client.post(
            "/api/posts",
            json={"title": "Hidden", "content": "Secret", "published": False},
            headers=auth_headers,
        ).get_json()["id"]
        assert client.get(f"/api/posts/{post_id}").status_code == 404

    def test_publish_post_makes_it_visible(self, client, auth_headers):
        post_id = client.post(
            "/api/posts",
            json={"title": "Coming Soon", "content": "...", "published": False},
            headers=auth_headers,
        ).get_json()["id"]

        client.put(
            f"/api/posts/{post_id}",
            json={"published": True},
            headers=auth_headers,
        )
        assert client.get(f"/api/posts/{post_id}").status_code == 200

    def test_list_posts_ordered_newest_first(self, client, auth_headers):
        create_post(client, auth_headers, "First Post")
        create_post(client, auth_headers, "Second Post")
        create_post(client, auth_headers, "Third Post")

        resp = client.get("/api/posts")
        titles = [p["title"] for p in resp.get_json()["posts"]]
        assert titles[0] == "Third Post"
        assert titles[-1] == "First Post"

    def test_update_post_categories(self, client, auth_headers):
        cat1_id = client.post(
            "/api/categories", json={"name": "Backend"}, headers=auth_headers
        ).get_json()["id"]
        cat2_id = client.post(
            "/api/categories", json={"name": "Frontend"}, headers=auth_headers
        ).get_json()["id"]

        post_id = create_post(client, auth_headers).get_json()["id"]

        # Assign categories on update
        client.put(
            f"/api/posts/{post_id}",
            json={"category_ids": [cat1_id, cat2_id]},
            headers=auth_headers,
        )
        resp = client.get(f"/api/posts/{post_id}")
        cat_names = [c["name"] for c in resp.get_json()["categories"]]
        assert "Backend" in cat_names
        assert "Frontend" in cat_names
