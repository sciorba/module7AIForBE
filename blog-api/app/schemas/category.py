import re
from marshmallow import Schema, fields, validate, validates, ValidationError
from app.models.category import Category


class CategorySchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=80))
    slug = fields.Str(dump_only=True)

    @validates("name")
    def validate_name_unique(self, value):
        if Category.query.filter_by(name=value).first():
            raise ValidationError("Category name already exists.")


def make_slug(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    return re.sub(r"[\s_-]+", "-", slug).strip("-")
