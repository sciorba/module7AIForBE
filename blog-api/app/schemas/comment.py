from marshmallow import Schema, fields, validate
from app.schemas.user import UserSchema


class CommentSchema(Schema):
    id = fields.Int(dump_only=True)
    content = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    author = fields.Nested(UserSchema, dump_only=True)
    post_id = fields.Int(dump_only=True)


class CommentCreateSchema(Schema):
    content = fields.Str(required=True, validate=validate.Length(min=1, max=2000))
