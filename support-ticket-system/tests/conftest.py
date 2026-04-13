import pytest
from app import create_app, db as _db
from app.services.notification_service import notification_service
from config import TestingConfig


@pytest.fixture(scope="session")
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function", autouse=True)
def db(app):
    with app.app_context():
        notification_service.clear()
        yield _db
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


# ---------------------------------------------------------------------------
# Convenience fixtures — pre-registered users
# ---------------------------------------------------------------------------

def _register(client, name, email, password, role="customer"):
    resp = client.post("/api/auth/register", json={
        "name": name, "email": email, "password": password, "role": role
    })
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def customer_headers(client):
    return _register(client, "Alice Customer", "alice@example.com", "password123", "customer")


@pytest.fixture
def agent_headers(client):
    return _register(client, "Bob Agent", "bob@example.com", "password123", "agent")


@pytest.fixture
def admin_headers(client):
    return _register(client, "Carol Admin", "carol@example.com", "password123", "admin")


@pytest.fixture
def second_agent_headers(client):
    return _register(client, "Dave Agent", "dave@example.com", "password123", "agent")


# ---------------------------------------------------------------------------
# Helper — create a ticket via the API
# ---------------------------------------------------------------------------

def make_ticket(client, headers, subject="Login issue", description="I cannot log in to my account after the update.",
                priority="medium", category="technical"):
    resp = client.post("/api/tickets", json={
        "subject": subject,
        "description": description,
        "priority": priority,
        "category": category,
    }, headers=headers)
    return resp
