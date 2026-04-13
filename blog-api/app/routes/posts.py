from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app import db, cache
from app.models.post import Post
from app.models.category import Category
from app.schemas.post import PostSchema, PostCreateSchema, PostUpdateSchema
from app.schemas.comment import CommentSchema, CommentCreateSchema
from app.models.comment import Comment
from app.utils.cache_keys import post_list_key, post_detail_key_for_id

posts_bp = Blueprint("posts", __name__)

post_schema = PostSchema()
posts_schema = PostSchema(many=True)
post_create_schema = PostCreateSchema()
post_update_schema = PostUpdateSchema()
comment_schema = CommentSchema()
comments_schema = CommentSchema(many=True)
comment_create_schema = CommentCreateSchema()

POSTS_PER_PAGE = 20
CACHE_TTL = 300


@posts_bp.route("", methods=["GET"])
def list_posts():
    """
    List all published posts (paginated)
    ---
    tags:
      - Posts
    parameters:
      - in: query
        name: page
        schema:
          type: integer
          default: 1
      - in: query
        name: per_page
        schema:
          type: integer
          default: 20
    responses:
      200:
        description: Paginated list of posts
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", POSTS_PER_PAGE, type=int), POSTS_PER_PAGE)

    cache_key = post_list_key(page, per_page)
    cached = cache.get(cache_key)
    if cached is not None:
        return jsonify(cached), 200

    pagination = (
        Post.query.filter_by(published=True)
        .order_by(Post.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    result = {
        "posts": posts_schema.dump(pagination.items),
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        },
    }
    cache.set(cache_key, result, timeout=CACHE_TTL)
    return jsonify(result), 200


@posts_bp.route("", methods=["POST"])
@jwt_required()
def create_post():
    """
    Create a new blog post
    ---
    tags:
      - Posts
    security:
      - Bearer: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [title, content]
            properties:
              title:
                type: string
              content:
                type: string
              published:
                type: boolean
                default: true
              category_ids:
                type: array
                items:
                  type: integer
    responses:
      201:
        description: Post created
      400:
        description: Validation error
      401:
        description: Unauthorized
    """
    try:
        data = post_create_schema.load(request.get_json() or {})
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    user_id = int(get_jwt_identity())
    post = Post(
        title=data["title"],
        content=data["content"],
        published=data["published"],
        user_id=user_id,
    )

    if data.get("category_ids"):
        categories = Category.query.filter(Category.id.in_(data["category_ids"])).all()
        post.categories = categories

    db.session.add(post)
    db.session.commit()

    # New post invalidates all list and search caches (unknown which pages are affected)
    cache.clear()

    return jsonify(post_schema.dump(post)), 201


@posts_bp.route("/<int:post_id>", methods=["GET"])
def get_post(post_id):
    """
    Get a single post by ID
    ---
    tags:
      - Posts
    parameters:
      - in: path
        name: post_id
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Post data
      404:
        description: Post not found
    """
    cache_key = post_detail_key_for_id(post_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return jsonify(cached), 200

    post = Post.query.filter_by(id=post_id, published=True).first_or_404()
    data = post_schema.dump(post)
    cache.set(cache_key, data, timeout=CACHE_TTL)
    return jsonify(data), 200


@posts_bp.route("/<int:post_id>", methods=["PUT"])
@jwt_required()
def update_post(post_id):
    """
    Update a post (author only)
    ---
    tags:
      - Posts
    security:
      - Bearer: []
    parameters:
      - in: path
        name: post_id
        required: true
        schema:
          type: integer
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              title:
                type: string
              content:
                type: string
              published:
                type: boolean
              category_ids:
                type: array
                items:
                  type: integer
    responses:
      200:
        description: Post updated
      403:
        description: Forbidden
      404:
        description: Post not found
    """
    post = Post.query.filter_by(id=post_id).first_or_404()
    user_id = int(get_jwt_identity())

    if post.user_id != user_id:
        return jsonify({"error": "Forbidden"}), 403

    try:
        data = post_update_schema.load(request.get_json() or {})
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    if "title" in data:
        post.title = data["title"]
    if "content" in data:
        post.content = data["content"]
    if "published" in data:
        post.published = data["published"]
    if "category_ids" in data:
        categories = Category.query.filter(Category.id.in_(data["category_ids"])).all()
        post.categories = categories

    db.session.commit()

    cache.delete(post_detail_key_for_id(post_id))
    cache.clear()  # Also bust list/search caches

    return jsonify(post_schema.dump(post)), 200


@posts_bp.route("/<int:post_id>", methods=["DELETE"])
@jwt_required()
def delete_post(post_id):
    """
    Delete a post (author only)
    ---
    tags:
      - Posts
    security:
      - Bearer: []
    parameters:
      - in: path
        name: post_id
        required: true
        schema:
          type: integer
    responses:
      204:
        description: Post deleted
      403:
        description: Forbidden
      404:
        description: Post not found
    """
    post = Post.query.filter_by(id=post_id).first_or_404()
    user_id = int(get_jwt_identity())

    if post.user_id != user_id:
        return jsonify({"error": "Forbidden"}), 403

    db.session.delete(post)
    db.session.commit()

    cache.clear()

    return "", 204


@posts_bp.route("/<int:post_id>/comments", methods=["POST"])
@jwt_required()
def create_comment(post_id):
    """
    Add a comment to a post
    ---
    tags:
      - Comments
    security:
      - Bearer: []
    parameters:
      - in: path
        name: post_id
        required: true
        schema:
          type: integer
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [content]
            properties:
              content:
                type: string
    responses:
      201:
        description: Comment created
      401:
        description: Unauthorized
      404:
        description: Post not found
    """
    Post.query.filter_by(id=post_id, published=True).first_or_404()

    try:
        data = comment_create_schema.load(request.get_json() or {})
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    user_id = int(get_jwt_identity())
    comment = Comment(content=data["content"], user_id=user_id, post_id=post_id)
    db.session.add(comment)
    db.session.commit()

    # Comment count changed — bust the post's detail cache
    cache.delete(post_detail_key_for_id(post_id))

    return jsonify(comment_schema.dump(comment)), 201


@posts_bp.route("/<int:post_id>/comments", methods=["GET"])
def list_comments(post_id):
    """
    List comments for a post
    ---
    tags:
      - Comments
    parameters:
      - in: path
        name: post_id
        required: true
        schema:
          type: integer
    responses:
      200:
        description: List of comments
      404:
        description: Post not found
    """
    Post.query.filter_by(id=post_id, published=True).first_or_404()

    comments = (
        Comment.query.filter_by(post_id=post_id)
        .order_by(Comment.created_at.asc())
        .all()
    )
    return jsonify(comments_schema.dump(comments)), 200


@posts_bp.route("/<int:post_id>/comments/<int:comment_id>", methods=["DELETE"])
@jwt_required()
def delete_comment(post_id, comment_id):
    """
    Delete a comment (author or post owner only)
    ---
    tags:
      - Comments
    security:
      - Bearer: []
    parameters:
      - in: path
        name: post_id
        required: true
        schema:
          type: integer
      - in: path
        name: comment_id
        required: true
        schema:
          type: integer
    responses:
      204:
        description: Comment deleted
      403:
        description: Forbidden
      404:
        description: Comment not found
    """
    post = Post.query.filter_by(id=post_id, published=True).first_or_404()
    comment = Comment.query.filter_by(id=comment_id, post_id=post_id).first_or_404()
    user_id = int(get_jwt_identity())

    # Only the comment author or the post author can delete a comment
    if comment.user_id != user_id and post.user_id != user_id:
        return jsonify({"error": "Forbidden"}), 403

    db.session.delete(comment)
    db.session.commit()

    cache.delete(post_detail_key_for_id(post_id))

    return "", 204
