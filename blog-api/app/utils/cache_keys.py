"""
Cache key builders.

We cache JSON-serialisable dicts (not Flask Response objects) so the values
can be round-tripped through pickle/SimpleCache and verified directly in tests.
"""

CATEGORIES_KEY = "categories:all"


def post_list_key(page: int, per_page: int) -> str:
    return f"posts:list:{page}:{per_page}"


def post_detail_key_for_id(post_id: int) -> str:
    return f"posts:detail:{post_id}"


def search_key(q: str, page: int) -> str:
    return f"posts:search:{q.strip().lower()}:{page}"
