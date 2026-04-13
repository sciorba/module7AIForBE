from marshmallow import Schema, fields, validate
from app.schemas.user import UserSchema


class CommentSchema(Schema):
    id = fields.Int(dump_only=True)
    ticket_id = fields.Int(dump_only=True)
    content = fields.Str(dump_only=True)
    is_internal = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    author = fields.Nested(UserSchema, dump_only=True)


class CommentCreateSchema(Schema):
    content = fields.Str(required=True, validate=validate.Length(min=1, max=5000))
    # FR-016: customers can only post public comments (enforced in the route)
    is_internal = fields.Bool(load_default=False)
