from datetime import datetime, timezone
from app import db


class TicketStatus:
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"
    ALL = [OPEN, ASSIGNED, IN_PROGRESS, WAITING, RESOLVED, CLOSED, REOPENED]

    # FR-012: valid state-machine transitions
    TRANSITIONS = {
        OPEN:        [ASSIGNED, CLOSED],
        ASSIGNED:    [IN_PROGRESS, CLOSED],
        IN_PROGRESS: [WAITING, RESOLVED, CLOSED],
        WAITING:     [IN_PROGRESS],
        RESOLVED:    [CLOSED, REOPENED],
        CLOSED:      [REOPENED],   # 7-day guard enforced in service layer
        REOPENED:    [IN_PROGRESS],
    }

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        return to_status in cls.TRANSITIONS.get(from_status, [])


class TicketPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    ALL = [LOW, MEDIUM, HIGH, URGENT]

    # FR-020: SLA hours (response, resolution)
    SLA = {
        URGENT: {"response_hours": 2,  "resolution_hours": 24},
        HIGH:   {"response_hours": 4,  "resolution_hours": 48},
        MEDIUM: {"response_hours": 8,  "resolution_hours": 120},
        LOW:    {"response_hours": 24, "resolution_hours": 240},
    }


class TicketCategory:
    TECHNICAL = "technical"
    BILLING = "billing"
    GENERAL = "general"
    FEATURE_REQUEST = "feature_request"
    ALL = [TECHNICAL, BILLING, GENERAL, FEATURE_REQUEST]


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=TicketStatus.OPEN)
    priority = db.Column(db.String(20), nullable=False, default=TicketPriority.MEDIUM)
    category = db.Column(db.String(30), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    resolved_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    # SLA deadlines (FR-020)
    response_due_at = db.Column(db.DateTime, nullable=True)
    resolution_due_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    comments = db.relationship("Comment", backref="ticket", lazy="dynamic",
                               cascade="all, delete-orphan")
    history = db.relationship("TicketHistory", backref="ticket", lazy="dynamic",
                              cascade="all, delete-orphan",
                              order_by="TicketHistory.changed_at")
    assignments = db.relationship("Assignment", backref="ticket", lazy="dynamic",
                                  cascade="all, delete-orphan",
                                  order_by="Assignment.assigned_at")

    __table_args__ = (
        db.Index("ix_tickets_status_priority", "status", "priority"),
        db.Index("ix_tickets_customer_id", "customer_id"),
        db.Index("ix_tickets_assigned_to_id", "assigned_to_id"),
    )

    @property
    def sla_status(self) -> str:
        """FR-021: flag tickets approaching or past their resolution SLA."""
        if self.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
            return "resolved"
        if not self.resolution_due_at:
            return "none"
        now = datetime.now(timezone.utc)
        # Make resolution_due_at tz-aware for comparison
        due = self.resolution_due_at
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        delta = (due - now).total_seconds()
        if delta < 0:
            return "breached"
        elif delta < 3600:   # < 1 hour
            return "critical"
        elif delta < 7200:   # < 2 hours
            return "warning"
        return "ok"

    def __repr__(self):
        return f"<Ticket {self.ticket_number} [{self.status}]>"
