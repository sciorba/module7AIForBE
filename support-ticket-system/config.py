import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///support.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # NFR-006: JWT expires after 24 hours
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key-change-in-prod")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    # Notification mode: "log" (console) or "off" (silent, useful for load tests)
    NOTIFICATION_MODE = os.environ.get("NOTIFICATION_MODE", "log")


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    NOTIFICATION_MODE = "capture"   # notifications stored in a list for test assertions
