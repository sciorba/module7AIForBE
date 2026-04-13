import pytest


def create_post(client, headers):
    resp = client.post(
        "/api/posts",
        json={"title": "Post with comments", "content": "Content"},
        headers=headers,
    )
    return resp.get_json()["id"]


class TestComments:
    def test_create_comment_success(self, client, auth_headers):
        post_id = create_post(client, auth_headers)
        resp = client.post(
            f"/api/posts/{post_id}/comments",
            json={"content": "Great post!"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["content"] == "Great post!"
        assert data["author"]["username"] == "testuser"

    def test_create_comment_unauthenticated(self, client, auth_headers):
        post_id = create_post(client, auth_headers)
        resp = client.post(
            f"/api/posts/{post_id}/comments",
            json={"content": "Anonymous comment"},
        )
        assert resp.status_code == 401

    def test_create_comment_on_nonexistent_post(self, client, auth_headers):
        resp = client.post(
            "/api/posts/9999/comments",
            json={"content": "Ghost comment"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_list_comments(self, client, auth_headers, second_auth_headers):
        post_id = create_post(client, auth_headers)
        client.post(
            f"/api/posts/{post_id}/comments",
            json={"content": "First comment"},
            headers=auth_headers,
        )
        client.post(
            f"/api/posts/{post_id}/comments",
            json={"content": "Second comment"},
            headers=second_auth_headers,
        )
        resp = client.get(f"/api/posts/{post_id}/comments")
        assert resp.status_code == 200
        comments = resp.get_json()
        assert len(comments) == 2

    def test_list_comments_empty(self, client, auth_headers):
        post_id = create_post(client, auth_headers)
        resp = client.get(f"/api/posts/{post_id}/comments")
        assert resp.status_code == 200
        assert resp.get_json() == []


class TestDeleteComment:
    def test_author_can_delete_own_comment(self, client, auth_headers):
        post_id = create_post(client, auth_headers)
        comment_id = client.post(
            f"/api/posts/{post_id}/comments",
            json={"content": "Delete me"},
            headers=auth_headers,
        ).get_json()["id"]
        resp = client.delete(
            f"/api/posts/{post_id}/comments/{comment_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204
        # Comment should be gone
        comments = client.get(f"/api/posts/{post_id}/comments").get_json()
        assert all(c["id"] != comment_id for c in comments)

    def test_post_owner_can_delete_any_comment(self, client, auth_headers, second_auth_headers):
        """Post author can moderate their own post's comments."""
        post_id = create_post(client, auth_headers)
        comment_id = client.post(
            f"/api/posts/{post_id}/comments",
            json={"content": "Someone else's comment"},
            headers=second_auth_headers,
        ).get_json()["id"]
        resp = client.delete(
            f"/api/posts/{post_id}/comments/{comment_id}",
            headers=auth_headers,   # post owner, not comment author
        )
        assert resp.status_code == 204

    def test_other_user_cannot_delete_comment(self, client, auth_headers, second_auth_headers):
        post_id = create_post(client, auth_headers)
        comment_id = client.post(
            f"/api/posts/{post_id}/comments",
            json={"content": "Mine"},
            headers=auth_headers,
        ).get_json()["id"]
        resp = client.delete(
            f"/api/posts/{post_id}/comments/{comment_id}",
            headers=second_auth_headers,
        )
        assert resp.status_code == 403

    def test_delete_nonexistent_comment(self, client, auth_headers):
        post_id = create_post(client, auth_headers)
        resp = client.delete(
            f"/api/posts/{post_id}/comments/9999",
            headers=auth_headers,
        )
        assert resp.status_code == 404
