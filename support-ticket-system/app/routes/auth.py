from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required
from marshmallow import ValidationError
from app import db
from app.models.user import User
from app.schemas.user import UserRegisterSchema, UserLoginSchema, UserSchema
from app.utils.decorators import get_current_user
from app.utils.error_handlers import make_error

auth_bp = Blueprint("auth", __name__)

register_schema = UserRegisterSchema()
login_schema = UserLoginSchema()
user_schema = UserSchema()


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user
    ---
    tags:
      - Auth
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [name, email, password]
            properties:
              name:
                type: string
              email:
                type: string
                format: email
              password:
                type: string
                minLength: 6
              role:
                type: string
                enum: [customer, agent, admin]
    responses:
      201:
        description: User registered
      400:
        description: Validation error
    """
    try:
        data = register_schema.load(request.get_json() or {})
    except ValidationError as err:
        return make_error("Validation failed", "VALIDATION_ERROR", 400, err.messages)

    user = User(
        name=data["name"],
        email=data["email"],
        role=data["role"],
        expertise_areas=data.get("expertise_areas", []),
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({"user": user_schema.dump(user), "access_token": token}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login and receive JWT token
    ---
    tags:
      - Auth
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [email, password]
            properties:
              email:
                type: string
              password:
                type: string
    responses:
      200:
        description: Login successful
      401:
        description: Invalid credentials
    """
    try:
        data = login_schema.load(request.get_json() or {})
    except ValidationError as err:
        return make_error("Validation failed", "VALIDATION_ERROR", 400, err.messages)

    user = User.query.filter_by(email=data["email"]).first()
    if not user or not user.check_password(data["password"]):
        return make_error("Invalid email or password", "UNAUTHORIZED", 401)

    token = create_access_token(identity=str(user.id))
    return jsonify({"user": user_schema.dump(user), "access_token": token}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """
    Get current authenticated user
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    responses:
      200:
        description: Current user data
    """
    user = get_current_user()
    return jsonify(user_schema.dump(user)), 200
