"""
Notification service — FR-003, FR-007, FR-014, FR-018, FR-035.

In production this would dispatch real emails via SMTP/SendGrid/SES.
Three modes (set via NOTIFICATION_MODE in config):
  "log"     — print to stdout (development)
  "capture" — store in self.sent list (testing/assertions)
  "off"     — silently discard
"""
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        self._mode = "log"
        self.sent: list[dict] = []   # populated in "capture" mode

    def init_app(self, app):
        self._mode = app.config.get("NOTIFICATION_MODE", "log")

    # ------------------------------------------------------------------
    # Internal dispatcher
    # ------------------------------------------------------------------
    def _send(self, event: str, recipient: str, context: dict):
        payload = {"event": event, "recipient": recipient, **context}
        if self._mode == "capture":
            self.sent.append(payload)
        elif self._mode == "log":
            logger.info("[EMAIL] event=%s to=%s ctx=%s", event, recipient, context)

    def clear(self):
        """Reset captured notifications between tests."""
        self.sent.clear()

    # ------------------------------------------------------------------
    # FR-003: ticket created → customer confirmation
    # ------------------------------------------------------------------
    def ticket_created(self, ticket):
        self._send(
            "ticket_created",
            ticket.customer_email,
            {"ticket_number": ticket.ticket_number, "subject": ticket.subject},
        )

    # FR-007: ticket assigned → agent notification
    def ticket_assigned(self, ticket, agent):
        self._send(
            "ticket_assigned",
            agent.email,
            {"ticket_number": ticket.ticket_number, "agent_name": agent.name},
        )

    # FR-014: status changed → customer + agent
    def status_changed(self, ticket, old_status: str, new_status: str):
        self._send(
            "status_changed",
            ticket.customer_email,
            {"ticket_number": ticket.ticket_number,
             "old_status": old_status, "new_status": new_status},
        )
        if ticket.assigned_to_id and ticket.assigned_agent:
            self._send(
                "status_changed",
                ticket.assigned_agent.email,
                {"ticket_number": ticket.ticket_number,
                 "old_status": old_status, "new_status": new_status},
            )

    # FR-018: new comment → relevant parties
    def comment_added(self, ticket, comment, author):
        recipients = {ticket.customer_email}
        if ticket.assigned_agent:
            recipients.add(ticket.assigned_agent.email)
        # internal comments don't go to the customer
        if comment.is_internal:
            recipients.discard(ticket.customer_email)
        for email in recipients:
            self._send(
                "comment_added",
                email,
                {"ticket_number": ticket.ticket_number,
                 "author": author.name,
                 "is_internal": comment.is_internal},
            )

    # FR-035: SLA deadline approaching
    def sla_warning(self, ticket, agent):
        self._send(
            "sla_warning",
            agent.email,
            {"ticket_number": ticket.ticket_number,
             "sla_status": ticket.sla_status},
        )


notification_service = NotificationService()
