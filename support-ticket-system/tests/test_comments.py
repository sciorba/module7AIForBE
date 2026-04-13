"""
Tests for FR-015 (comments system) and FR-016 (public vs internal visibility).
"""
from tests.conftest import make_ticket


def _ticket_id(client, headers):
    return make_ticket(client, headers).get_json()["id"]


class TestPublicComments:
    def test_customer_can_add_public_comment(self, client, customer_headers):
        tid = _ticket_id(client, customer_headers)
        resp = client.post(f"/api/tickets/{tid}/comments",
                           json={"content": "Any update on this issue?"},
                           headers=customer_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["content"] == "Any update on this issue?"
        assert data["is_internal"] is False

    def test_agent_can_add_public_comment(self, client, customer_headers, agent_headers):
        tid = _ticket_id(client, customer_headers)
        resp = client.post(f"/api/tickets/{tid}/comments",
                           json={"content": "We are investigating.", "is_internal": False},
                           headers=agent_headers)
        assert resp.status_code == 201
        assert resp.get_json()["is_internal"] is False

    def test_customer_can_see_public_comments(self, client, customer_headers, agent_headers):
        tid = _ticket_id(client, customer_headers)
        client.post(f"/api/tickets/{tid}/comments",
                    json={"content": "Public note from agent"},
                    headers=agent_headers)
        resp = client.get(f"/api/tickets/{tid}/comments", headers=customer_headers)
        assert resp.status_code == 200
        assert len(resp.get_json()) == 1

    def test_comment_notification_sent(self, client, customer_headers, agent_headers):
        """FR-018: notification sent on new comment."""
        from app.services.notification_service import notification_service
        tid = _ticket_id(client, customer_headers)
        notification_service.clear()
        client.post(f"/api/tickets/{tid}/comments",
                    json={"content": "Agent comment here"},
                    headers=agent_headers)
        events = [n["event"] for n in notification_service.sent]
        assert "comment_added" in events


class TestInternalComments:
    def test_agent_can_add_internal_comment(self, client, customer_headers, agent_headers):
        tid = _ticket_id(client, customer_headers)
        resp = client.post(f"/api/tickets/{tid}/comments",
                           json={"content": "Internal note: password reset needed",
                                 "is_internal": True},
                           headers=agent_headers)
        assert resp.status_code == 201
        assert resp.get_json()["is_internal"] is True

    def test_customer_cannot_add_internal_comment(self, client, customer_headers):
        tid = _ticket_id(client, customer_headers)
        resp = client.post(f"/api/tickets/{tid}/comments",
                           json={"content": "Trying to be internal", "is_internal": True},
                           headers=customer_headers)
        assert resp.status_code == 403

    def test_customer_cannot_see_internal_comments(
            self, client, customer_headers, agent_headers):
        tid = _ticket_id(client, customer_headers)
        # Agent adds internal comment
        client.post(f"/api/tickets/{tid}/comments",
                    json={"content": "Private agent note", "is_internal": True},
                    headers=agent_headers)
        # Customer fetches comments — should be empty
        resp = client.get(f"/api/tickets/{tid}/comments", headers=customer_headers)
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_agent_can_see_internal_comments(
            self, client, customer_headers, agent_headers):
        tid = _ticket_id(client, customer_headers)
        client.post(f"/api/tickets/{tid}/comments",
                    json={"content": "Internal agent note", "is_internal": True},
                    headers=agent_headers)
        resp = client.get(f"/api/tickets/{tid}/comments", headers=agent_headers)
        assert resp.status_code == 200
        assert len(resp.get_json()) == 1
        assert resp.get_json()[0]["is_internal"] is True

    def test_internal_comment_not_sent_to_customer(
            self, client, customer_headers, agent_headers):
        """Internal comments should not trigger customer notification."""
        from app.services.notification_service import notification_service
        tid = _ticket_id(client, customer_headers)
        notification_service.clear()
        client.post(f"/api/tickets/{tid}/comments",
                    json={"content": "Secret note", "is_internal": True},
                    headers=agent_headers)
        # No notification should go to the customer email
        customer_notifs = [
            n for n in notification_service.sent
            if n["event"] == "comment_added" and n["recipient"] == "alice@example.com"
        ]
        assert customer_notifs == []
