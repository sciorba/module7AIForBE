from marshmallow import Schema, fields, validate
from app.schemas.user import UserSchema
from app.schemas.category import CategorySchema


class PostSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(dump_only=True)
    content = fields.Str(dump_only=True)
    published = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    author = fields.Nested(UserSchema, dump_only=True)
    categories = fields.List(fields.Nested(CategorySchema), dump_only=True)
    comment_count = fields.Method("get_comment_count", dump_only=True)

    def get_comment_count(self, obj):
        return obj.comments.count()


class PostCreateSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    content = fields.Str(required=True, validate=validate.Length(min=1))
    published = fields.Bool(load_default=True)
    category_ids = fields.List(fields.Int(), load_default=[])


class PostUpdateSchema(Schema):
    title = fields.Str(validate=validate.Length(min=1, max=200))
    content = fields.Str(validate=validate.Length(min=1))
    published = fields.Bool()
    category_ids = fields.List(fields.Int())
