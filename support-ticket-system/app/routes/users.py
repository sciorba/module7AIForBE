from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.models.user import User, UserRole
from app.schemas.user import UserSchema, AvailabilityUpdateSchema
from app.utils.decorators import get_current_user, require_role
from app.utils.error_handlers import make_error
from flask import request
from marshmallow import ValidationError

users_bp = Blueprint("users", __name__)

user_schema = UserSchema()
users_schema = UserSchema(many=True)
availability_schema = AvailabilityUpdateSchema()


@users_bp.route("/users", methods=["GET"])
@require_role("admin")
def list_users():
    """
    List all users (admin only)
    ---
    tags:
      - Users
    security:
      - Bearer: []
    responses:
      200:
        description: All users
    """
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify(users_schema.dump(users)), 200


@users_bp.route("/users/<int:user_id>", methods=["GET"])
@require_role("admin")
def get_user(user_id):
    """
    Get user by ID (admin only)
    ---
    tags:
      - Users
    security:
      - Bearer: []
    parameters:
      - {in: path, name: user_id, required: true, schema: {type: integer}}
    responses:
      200:
        description: User data
    """
    user = User.query.get(user_id)
    if not user:
        return make_error("User not found", "NOT_FOUND", 404)
    return jsonify(user_schema.dump(user)), 200


@users_bp.route("/agents", methods=["GET"])
@require_role("admin", "agent")
def list_agents():
    """
    List all agents
    ---
    tags:
      - Users
    security:
      - Bearer: []
    responses:
      200:
        description: Agent list
    """
    agents = User.query.filter_by(role=UserRole.AGENT).all()
    return jsonify(users_schema.dump(agents)), 200


@users_bp.route("/agents/<int:agent_id>/availability", methods=["PUT"])
@jwt_required()
def update_availability(agent_id):
    """
    Update agent availability status
    ---
    tags:
      - Users
    security:
      - Bearer: []
    parameters:
      - {in: path, name: agent_id, required: true, schema: {type: integer}}
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [availability_status]
            properties:
              availability_status:
                type: string
                enum: [available, busy, offline]
    responses:
      200:
        description: Availability updated
    """
    current = get_current_user()
    # Only admins or the agent themselves can update availability
    if not current.is_admin and current.id != agent_id:
        return make_error("Forbidden", "FORBIDDEN", 403)

    agent = User.query.filter_by(id=agent_id, role=UserRole.AGENT).first()
    if not agent:
        return make_error("Agent not found", "NOT_FOUND", 404)

    try:
        data = availability_schema.load(request.get_json() or {})
    except ValidationError as err:
        return make_error("Validation failed", "VALIDATION_ERROR", 400, err.messages)

    from app import db
    agent.availability_status = data["availability_status"]
    db.session.commit()
    return jsonify(user_schema.dump(agent)), 200
