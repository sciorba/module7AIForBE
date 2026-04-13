from datetime import datetime, timezone
from app import db

post_categories = db.Table(
    "post_categories",
    db.Column("post_id", db.Integer, db.ForeignKey("posts.id"), primary_key=True),
    db.Column("category_id", db.Integer, db.ForeignKey("categories.id"), primary_key=True),
)


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    categories = db.relationship("Category", secondary=post_categories, backref="posts", lazy="subquery")
    comments = db.relationship("Comment", backref="post", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (
        # Speeds up the common query: published posts ordered by date (list + search)
        db.Index("ix_posts_published_created", "published", "created_at"),
        # Speeds up "posts by user" lookups (author pages, ownership checks)
        db.Index("ix_posts_user_id", "user_id"),
    )

    def __repr__(self):
        return f"<Post {self.title}>"
