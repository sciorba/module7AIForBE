from datetime import datetime, timezone
from app import db


class Assignment(db.Model):
    """FR-010: tracks full assignment history for each ticket."""
    __tablename__ = "assignments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    assigned_by = db.relationship("User", foreign_keys=[assigned_by_id])

    def __repr__(self):
        return f"<Assignment ticket={self.ticket_id} to={self.assigned_to_id}>"
