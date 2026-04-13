"""
Tests for FR-011 (status values), FR-012 (state-machine transitions),
FR-013 (history logging), FR-014 (notifications).
"""
from tests.conftest import make_ticket


def _get_ticket_id(client, headers):
    return make_ticket(client, headers).get_json()["id"]


def _set_status(client, ticket_id, new_status, headers, note=None):
    body = {"status": new_status}
    if note:
        body["note"] = note
    return client.put(f"/api/tickets/{ticket_id}/status",
                      json=body, headers=headers)


class TestValidTransitions:
    def test_agent_moves_open_to_in_progress_via_assigned(
            self, client, customer_headers, agent_headers, admin_headers):
        """open → assigned (by admin assign) → in_progress (by agent)"""
        ticket_id = _get_ticket_id(client, customer_headers)

        # Get agent user id first
        agent_user = client.get("/api/auth/me", headers=agent_headers).get_json()

        # Admin assigns the ticket
        client.post(f"/api/tickets/{ticket_id}/assign",
                    json={"agent_id": agent_user["id"]}, headers=admin_headers)

        resp = _set_status(client, ticket_id, "in_progress", agent_headers)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "in_progress"

    def test_in_progress_to_waiting(self, client, customer_headers, agent_headers, admin_headers):
        ticket_id = _get_ticket_id(client, customer_headers)
        agent_user = client.get("/api/auth/me", headers=agent_headers).get_json()
        client.post(f"/api/tickets/{ticket_id}/assign",
                    json={"agent_id": agent_user["id"]}, headers=admin_headers)
        _set_status(client, ticket_id, "in_progress", agent_headers)
        resp = _set_status(client, ticket_id, "waiting", agent_headers)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "waiting"

    def test_resolved_to_closed(self, client, customer_headers, agent_headers, admin_headers):
        ticket_id = _get_ticket_id(client, customer_headers)
        agent_user = client.get("/api/auth/me", headers=agent_headers).get_json()
        client.post(f"/api/tickets/{ticket_id}/assign",
                    json={"agent_id": agent_user["id"]}, headers=admin_headers)
        _set_status(client, ticket_id, "in_progress", agent_headers)
        _set_status(client, ticket_id, "resolved", agent_headers)
        resp = _set_status(client, ticket_id, "closed", agent_headers)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "closed"

    def test_resolved_at_set_on_resolve(self, client, customer_headers, agent_headers, admin_headers):
        ticket_id = _get_ticket_id(client, customer_headers)
        agent_user = client.get("/api/auth/me", headers=agent_headers).get_json()
        client.post(f"/api/tickets/{ticket_id}/assign",
                    json={"agent_id": agent_user["id"]}, headers=admin_headers)
        _set_status(client, ticket_id, "in_progress", agent_headers)
        resp = _set_status(client, ticket_id, "resolved", agent_headers)
        assert resp.get_json()["resolved_at"] is not None

    def test_closed_at_set_on_close(self, client, customer_headers, agent_headers, admin_headers):
        ticket_id = _get_ticket_id(client, customer_headers)
        agent_user = client.get("/api/auth/me", headers=agent_headers).get_json()
        client.post(f"/api/tickets/{ticket_id}/assign",
                    json={"agent_id": agent_user["id"]}, headers=admin_headers)
        _set_status(client, ticket_id, "in_progress", agent_headers)
        _set_status(client, ticket_id, "resolved", agent_headers)
        resp = _set_status(client, ticket_id, "closed", agent_headers)
        assert resp.get_json()["closed_at"] is not None


class TestInvalidTransitions:
    def test_invalid_transition_assigned_to_resolved(
            self, client, customer_headers, agent_headers, admin_headers):
        """Ticket (open or assigned after auto-assign) cannot jump directly to resolved."""
        ticket_id = _get_ticket_id(client, customer_headers)
        # Ticket is open or assigned at this point — neither can go straight to resolved
        resp = _set_status(client, ticket_id, "resolved", agent_headers)
        assert resp.status_code == 400
        assert resp.get_json()["code"] == "INVALID_TRANSITION"

    def test_waiting_cannot_go_to_resolved(
            self, client, customer_headers, agent_headers, admin_headers):
        ticket_id = _get_ticket_id(client, customer_headers)
        agent_user = client.get("/api/auth/me", headers=agent_headers).get_json()
        client.post(f"/api/tickets/{ticket_id}/assign",
                    json={"agent_id": agent_user["id"]}, headers=admin_headers)
        _set_status(client, ticket_id, "in_progress", agent_headers)
        _set_status(client, ticket_id, "waiting", agent_headers)
        resp = _set_status(client, ticket_id, "resolved", agent_headers)
        assert resp.status_code == 400

    def test_customer_cannot_change_status(self, client, customer_headers):
        ticket_id = _get_ticket_id(client, customer_headers)
        resp = _set_status(client, ticket_id, "in_progress", customer_headers)
        assert resp.status_code == 403


class TestStatusHistory:
    def test_status_change_logged(self, client, customer_headers, agent_headers, admin_headers):
        """FR-013: every status change must appear in history."""
        ticket_id = _get_ticket_id(client, customer_headers)
        agent_user = client.get("/api/auth/me", headers=agent_headers).get_json()
        client.post(f"/api/tickets/{ticket_id}/assign",
                    json={"agent_id": agent_user["id"]}, headers=admin_headers)
        _set_status(client, ticket_id, "in_progress", agent_headers, note="Starting work")

        resp = client.get(f"/api/tickets/{ticket_id}/history", headers=agent_headers)
        assert resp.status_code == 200
        history = resp.get_json()
        # Should have at least: open→assigned (from assign) + assigned→in_progress
        assert len(history) >= 2
        last = history[-1]
        assert last["old_status"] == "assigned"
        assert last["new_status"] == "in_progress"
        assert last["note"] == "Starting work"

    def test_status_change_notification_sent(
            self, client, customer_headers, agent_headers, admin_headers):
        """FR-014: notifications sent on status change."""
        from app.services.notification_service import notification_service
        ticket_id = _get_ticket_id(client, customer_headers)
        agent_user = client.get("/api/auth/me", headers=agent_headers).get_json()
        client.post(f"/api/tickets/{ticket_id}/assign",
                    json={"agent_id": agent_user["id"]}, headers=admin_headers)
        notification_service.clear()
        _set_status(client, ticket_id, "in_progress", agent_headers)

        events = [n["event"] for n in notification_service.sent]
        assert "status_changed" in events
