"""
Error responses match the PRD section 8 format:
{
  "status": "error",
  "message": "...",
  "code": "ERROR_CODE",
  "errors": { "field": ["detail"] }   # optional
}
"""
from flask import jsonify
from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError


def make_error(message: str, code: str, status_code: int, errors: dict = None):
    body = {"status": "error", "message": message, "code": code}
    if errors:
        body["errors"] = errors
    return jsonify(body), status_code


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return make_error(str(e), "BAD_REQUEST", 400)

    @app.errorhandler(401)
    def unauthorized(e):
        return make_error("Authentication required", "UNAUTHORIZED", 401)

    @app.errorhandler(403)
    def forbidden(e):
        return make_error("Insufficient permissions", "FORBIDDEN", 403)

    @app.errorhandler(404)
    def not_found(e):
        return make_error("Resource not found", "NOT_FOUND", 404)

    @app.errorhandler(405)
    def method_not_allowed(e):
        return make_error("Method not allowed", "METHOD_NOT_ALLOWED", 405)

    @app.errorhandler(409)
    def conflict(e):
        return make_error(str(e), "CONFLICT", 409)

    @app.errorhandler(422)
    def unprocessable(e):
        return make_error("Unprocessable entity", "VALIDATION_ERROR", 422)

    @app.errorhandler(429)
    def rate_limit(e):
        return make_error("Too many requests", "RATE_LIMIT_EXCEEDED", 429)

    @app.errorhandler(500)
    def internal_error(e):
        return make_error("Internal server error", "INTERNAL_ERROR", 500)

    @app.errorhandler(NoAuthorizationError)
    def missing_token(e):
        return make_error("Missing or invalid authorization token", "UNAUTHORIZED", 401)

    @app.errorhandler(InvalidHeaderError)
    def invalid_header(e):
        return make_error("Invalid authorization header", "UNAUTHORIZED", 401)
