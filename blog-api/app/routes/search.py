from flask import Blueprint, request, jsonify
from app import cache
from app.models.post import Post
from app.schemas.post import PostSchema
from app.utils.cache_keys import search_key

search_bp = Blueprint("search", __name__)

posts_schema = PostSchema(many=True)

POSTS_PER_PAGE = 20
CACHE_TTL = 300


@search_bp.route("", methods=["GET"])
def search_posts():
    """
    Search posts by keyword
    ---
    tags:
      - Search
    parameters:
      - in: query
        name: q
        required: true
        schema:
          type: string
        description: Search keyword
      - in: query
        name: page
        schema:
          type: integer
          default: 1
    responses:
      200:
        description: Matching posts
      400:
        description: Missing query parameter
    """
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Query parameter 'q' is required"}), 400

    page = request.args.get("page", 1, type=int)

    cache_key = search_key(q, page)
    cached = cache.get(cache_key)
    if cached is not None:
        return jsonify(cached), 200

    keyword = f"%{q}%"
    pagination = (
        Post.query.filter(
            Post.published == True,
            (Post.title.ilike(keyword)) | (Post.content.ilike(keyword)),
        )
        .order_by(Post.created_at.desc())
        .paginate(page=page, per_page=POSTS_PER_PAGE, error_out=False)
    )

    result = {
        "posts": posts_schema.dump(pagination.items),
        "query": q,
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
