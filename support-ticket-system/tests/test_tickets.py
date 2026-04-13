from tests.conftest import make_ticket


class TestCreateTicket:
    def test_create_ticket_success(self, client, customer_headers):
        resp = make_ticket(client, customer_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "open"
        assert data["priority"] == "medium"
        assert data["category"] == "technical"
        assert "ticket_number" in data

    def test_ticket_number_auto_generated(self, client, customer_headers):
        """FR-002: ticket number format TICK-YYYYMMDD-XXXX"""
        resp = make_ticket(client, customer_headers)
        tn = resp.get_json()["ticket_number"]
        assert tn.startswith("TICK-")
        parts = tn.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8   # YYYYMMDD
        assert len(parts[2]) == 4   # zero-padded sequence

    def test_ticket_numbers_are_sequential(self, client, customer_headers):
        t1 = make_ticket(client, customer_headers, subject="First issue",
                         description="First issue description here please fix").get_json()
        t2 = make_ticket(client, customer_headers, subject="Second issue",
                         description="Second issue description here please fix").get_json()
        seq1 = int(t1["ticket_number"].split("-")[2])
        seq2 = int(t2["ticket_number"].split("-")[2])
        assert seq2 == seq1 + 1

    def test_create_ticket_subject_too_short(self, client, customer_headers):
        resp = client.post("/api/tickets", json={
            "subject": "Hi",   # < 5 chars
            "description": "This description is long enough to pass validation",
            "category": "general"
        }, headers=customer_headers)
        assert resp.status_code == 400

    def test_create_ticket_description_too_short(self, client, customer_headers):
        resp = client.post("/api/tickets", json={
            "subject": "Valid subject",
            "description": "Too short",   # < 20 chars
            "category": "general"
        }, headers=customer_headers)
        assert resp.status_code == 400

    def test_create_ticket_invalid_category(self, client, customer_headers):
        resp = client.post("/api/tickets", json={
            "subject": "Valid subject",
            "description": "This description is long enough to pass validation checks",
            "category": "invalid_cat"
        }, headers=customer_headers)
        assert resp.status_code == 400

    def test_create_ticket_requires_auth(self, client):
        resp = client.post("/api/tickets", json={
            "subject": "No auth", "description": "No auth description here test",
            "category": "general"
        })
        assert resp.status_code == 401

    def test_sla_deadlines_set_on_creation(self, client, customer_headers):
        """FR-020: SLA deadlines calculated automatically."""
        resp = make_ticket(client, customer_headers, priority="urgent")
        data = resp.get_json()
        assert data["response_due_at"] is not None
        assert data["resolution_due_at"] is not None

    def test_notification_sent_on_creation(self, client, customer_headers):
        """FR-003: customer receives confirmation notification."""
        from app.services.notification_service import notification_service
        make_ticket(client, customer_headers)
        events = [n["event"] for n in notification_service.sent]
        assert "ticket_created" in events


class TestGetTicket:
    def test_get_own_ticket(self, client, customer_headers):
        ticket_id = make_ticket(client, customer_headers).get_json()["id"]
        resp = client.get(f"/api/tickets/{ticket_id}", headers=customer_headers)
        assert resp.status_code == 200
        assert resp.get_json()["id"] == ticket_id

    def test_customer_cannot_see_other_users_ticket(self, client, customer_headers, agent_headers):
        # Agent creates a ticket
        ticket_id = make_ticket(client, agent_headers).get_json()["id"]
        # Customer tries to access it
        resp = client.get(f"/api/tickets/{ticket_id}", headers=customer_headers)
        assert resp.status_code == 404

    def test_admin_can_see_any_ticket(self, client, customer_headers, admin_headers):
        ticket_id = make_ticket(client, customer_headers).get_json()["id"]
        resp = client.get(f"/api/tickets/{ticket_id}", headers=admin_headers)
        assert resp.status_code == 200


class TestListTickets:
    def test_customer_sees_only_own_tickets(self, client, customer_headers, agent_headers):
        make_ticket(client, customer_headers, subject="My ticket",
                    description="My ticket description here okay")
        make_ticket(client, agent_headers, subject="Agent ticket",
                    description="Agent ticket description here okay")
        resp = client.get("/api/tickets", headers=customer_headers)
        assert resp.status_code == 200
        tickets = resp.get_json()["tickets"]
        assert len(tickets) == 1
        assert tickets[0]["subject"] == "My ticket"

    def test_filter_by_status(self, client, customer_headers):
        make_ticket(client, customer_headers)
        resp = client.get("/api/tickets?status=open", headers=customer_headers)
        assert resp.status_code == 200
        for t in resp.get_json()["tickets"]:
            assert t["status"] == "open"

    def test_filter_by_priority(self, client, customer_headers):
        make_ticket(client, customer_headers, priority="urgent")
        resp = client.get("/api/tickets?priority=urgent", headers=customer_headers)
        assert resp.status_code == 200
        for t in resp.get_json()["tickets"]:
            assert t["priority"] == "urgent"


class TestDeleteTicket:
    def test_admin_can_delete(self, client, customer_headers, admin_headers):
        ticket_id = make_ticket(client, customer_headers).get_json()["id"]
        resp = client.delete(f"/api/tickets/{ticket_id}", headers=admin_headers)
        assert resp.status_code == 204

    def test_agent_cannot_delete(self, client, customer_headers, agent_headers):
        ticket_id = make_ticket(client, customer_headers).get_json()["id"]
        resp = client.delete(f"/api/tickets/{ticket_id}", headers=agent_headers)
        assert resp.status_code == 403

    def test_customer_cannot_delete(self, client, customer_headers):
        ticket_id = make_ticket(client, customer_headers).get_json()["id"]
        resp = client.delete(f"/api/tickets/{ticket_id}", headers=customer_headers)
        assert resp.status_code == 403
