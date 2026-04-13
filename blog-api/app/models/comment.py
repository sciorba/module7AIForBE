from datetime import datetime, timezone
from app import db


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)

    __table_args__ = (
        # Speeds up fetching comments for a post (most common comment query)
        db.Index("ix_comments_post_id", "post_id"),
    )

    def __repr__(self):
        return f"<Comment {self.id} on Post {self.post_id}>"
