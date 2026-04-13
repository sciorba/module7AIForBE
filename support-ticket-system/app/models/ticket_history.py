from datetime import datetime, timezone
from app import db


class TicketHistory(db.Model):
    """FR-013: immutable log of every status change on a ticket."""
    __tablename__ = "ticket_history"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    old_status = db.Column(db.String(20), nullable=False)
    new_status = db.Column(db.String(20), nullable=False)
    note = db.Column(db.String(500), nullable=True)   # optional reason/comment
    changed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    changed_by = db.relationship("User", foreign_keys=[changed_by_id])

    def __repr__(self):
        return f"<History ticket={self.ticket_id} {self.old_status}→{self.new_status}>"
