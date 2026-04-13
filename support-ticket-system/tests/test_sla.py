"""
Tests for FR-020 (SLA deadlines) and FR-021 (SLA status flagging).
"""
from datetime import datetime, timezone, timedelta
from tests.conftest import make_ticket


class TestSlaDeadlines:
    def test_urgent_sla_deadlines(self, client, customer_headers):
        """FR-020: urgent → response 2h, resolution 24h."""
        # Use naive UTC (SQLite strips tzinfo on round-trip)
        before = datetime.utcnow()
        resp = make_ticket(client, customer_headers, priority="urgent")
        data = resp.get_json()

        assert data["response_due_at"] is not None
        assert data["resolution_due_at"] is not None

        from dateutil.parser import parse as parse_dt
        # Strip tzinfo so comparison is always naive vs naive
        response_due = parse_dt(data["response_due_at"]).replace(tzinfo=None)
        resolution_due = parse_dt(data["resolution_due_at"]).replace(tzinfo=None)

        assert timedelta(hours=1, minutes=50) <= (response_due - before) <= timedelta(hours=2, minutes=10)
        assert timedelta(hours=23, minutes=50) <= (resolution_due - before) <= timedelta(hours=24, minutes=10)

    def test_low_priority_sla_deadlines(self, client, customer_headers):
        """FR-020: low → response 24h, resolution 240h (10 days)."""
        before = datetime.utcnow()
        resp = make_ticket(client, customer_headers, priority="low")
        data = resp.get_json()

        from dateutil.parser import parse as parse_dt
        response_due = parse_dt(data["response_due_at"]).replace(tzinfo=None)
        resolution_due = parse_dt(data["resolution_due_at"]).replace(tzinfo=None)

        assert timedelta(hours=23, minutes=50) <= (response_due - before) <= timedelta(hours=24, minutes=10)
        assert timedelta(hours=239, minutes=50) <= (resolution_due - before) <= timedelta(hours=240, minutes=10)

    def test_sla_recalculated_on_priority_change(
            self, client, customer_headers, agent_headers):
        """Changing priority should update SLA deadlines."""
        resp = make_ticket(client, customer_headers, priority="low")
        data = resp.get_json()
        old_resolution_due = data["resolution_due_at"]
        tid = data["id"]

        client.put(f"/api/tickets/{tid}/priority",
                   json={"priority": "urgent", "reason": "Customer escalated the issue"},
                   headers=agent_headers)

        new_data = client.get(f"/api/tickets/{tid}", headers=customer_headers).get_json()
        assert new_data["resolution_due_at"] != old_resolution_due


class TestSlaStatus:
    def test_sla_status_ok_on_fresh_ticket(self, client, customer_headers):
        """FR-021: a newly created ticket should have sla_status=ok."""
        resp = make_ticket(client, customer_headers, priority="low")
        assert resp.get_json()["sla_status"] == "ok"

    def test_sla_status_breached_on_past_deadline(self, app, client, customer_headers):
        """FR-021: ticket past its resolution deadline should be 'breached'."""
        resp = make_ticket(client, customer_headers)
        tid = resp.get_json()["id"]

        # Manually set resolution_due_at to the past
        with app.app_context():
            from app.models.ticket import Ticket
            from app import db
            t = Ticket.query.get(tid)
            t.resolution_due_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db.session.commit()

        data = client.get(f"/api/tickets/{tid}", headers=customer_headers).get_json()
        assert data["sla_status"] == "breached"

    def test_priority_change_requires_reason(self, client, customer_headers, agent_headers):
        """FR-024: priority change without reason must fail."""
        tid = make_ticket(client, customer_headers).get_json()["id"]
        resp = client.put(f"/api/tickets/{tid}/priority",
                          json={"priority": "urgent"},   # missing 'reason'
                          headers=agent_headers)
        assert resp.status_code == 400

    def test_customer_cannot_change_priority(self, client, customer_headers):
        """FR-023: customers cannot change priority."""
        tid = make_ticket(client, customer_headers).get_json()["id"]
        resp = client.put(f"/api/tickets/{tid}/priority",
                          json={"priority": "urgent", "reason": "I want urgent"},
                          headers=customer_headers)
        assert resp.status_code == 403


class TestAdminDashboard:
    def test_dashboard_returns_metrics(self, client, customer_headers, admin_headers):
        make_ticket(client, customer_headers)
        resp = client.get("/api/admin/dashboard", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "tickets" in data
        assert "by_status" in data["tickets"]
        assert "by_priority" in data["tickets"]
        assert data["tickets"]["total"] >= 1

    def test_dashboard_requires_admin(self, client, agent_headers):
        resp = client.get("/api/admin/dashboard", headers=agent_headers)
        assert resp.status_code == 403
