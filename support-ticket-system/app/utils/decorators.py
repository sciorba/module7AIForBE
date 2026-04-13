"""
RBAC decorators — FR-032, FR-033.
Usage:
    @require_role("admin")
    @require_role("agent", "admin")   # any of these roles
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.error_handlers import make_error


def require_role(*roles):
    """Decorator that enforces one of the given roles after JWT verification."""
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            from app.models.user import User
            user_id = int(get_jwt_identity())
            user = User.query.get(user_id)
            if not user or user.role not in roles:
                return make_error("Insufficient permissions", "FORBIDDEN", 403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def get_current_user():
    """Return the authenticated User object from JWT identity."""
    from app.models.user import User
    user_id = int(get_jwt_identity())
    return User.query.get(user_id)
