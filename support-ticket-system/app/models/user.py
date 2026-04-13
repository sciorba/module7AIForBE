from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class UserRole:
    CUSTOMER = "customer"
    AGENT = "agent"
    ADMIN = "admin"
    ALL = [CUSTOMER, AGENT, ADMIN]


class AvailabilityStatus:
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ALL = [AVAILABLE, BUSY, OFFLINE]


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRole.CUSTOMER)
    availability_status = db.Column(db.String(20), default=AvailabilityStatus.AVAILABLE)
    # JSON-stored list of expertise areas (e.g. ["technical", "billing"])
    expertise_areas = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    created_tickets = db.relationship(
        "Ticket", foreign_keys="Ticket.customer_id",
        backref="customer", lazy="dynamic", cascade="all, delete-orphan"
    )
    assigned_tickets = db.relationship(
        "Ticket", foreign_keys="Ticket.assigned_to_id",
        backref="assigned_agent", lazy="dynamic"
    )
    comments = db.relationship("Comment", backref="author", lazy="dynamic",
                               cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_agent(self):
        return self.role == UserRole.AGENT

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def is_customer(self):
        return self.role == UserRole.CUSTOMER

    def __repr__(self):
        return f"<User {self.email} [{self.role}]>"
