from datetime import datetime, timezone
from app import db


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    # FR-016: public (visible to all) vs internal (agents/admins only)
    is_internal = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("ix_comments_ticket_id", "ticket_id"),
    )

    def __repr__(self):
        kind = "internal" if self.is_internal else "public"
        return f"<Comment {self.id} [{kind}] on Ticket {self.ticket_id}>"
