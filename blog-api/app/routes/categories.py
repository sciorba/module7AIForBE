from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError
from app import db, cache
from app.models.category import Category
from app.schemas.category import CategorySchema, make_slug
from app.utils.cache_keys import CATEGORIES_KEY

categories_bp = Blueprint("categories", __name__)

category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)

CACHE_TTL = 300


@categories_bp.route("", methods=["GET"])
def list_categories():
    """
    List all categories
    ---
    tags:
      - Categories
    responses:
      200:
        description: List of categories
    """
    cached = cache.get(CATEGORIES_KEY)
    if cached is not None:
        return jsonify(cached), 200

    categories = Category.query.order_by(Category.name).all()
    data = categories_schema.dump(categories)
    cache.set(CATEGORIES_KEY, data, timeout=CACHE_TTL)
    return jsonify(data), 200


@categories_bp.route("", methods=["POST"])
@jwt_required()
def create_category():
    """
    Create a new category
    ---
    tags:
      - Categories
    security:
      - Bearer: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [name]
            properties:
              name:
                type: string
    responses:
      201:
        description: Category created
      400:
        description: Validation error
    """
    try:
        data = category_schema.load(request.get_json() or {})
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    category = Category(name=data["name"], slug=make_slug(data["name"]))
    db.session.add(category)
    db.session.commit()

    cache.delete(CATEGORIES_KEY)

    return jsonify(category_schema.dump(category)), 201
