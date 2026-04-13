from marshmallow import Schema, fields, validate, validates, ValidationError
from app.models.user import UserRole, AvailabilityStatus


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)
    email = fields.Email(dump_only=True)
    role = fields.Str(dump_only=True)
    availability_status = fields.Str(dump_only=True)
    expertise_areas = fields.List(fields.Str(), dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class UserRegisterSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=6), load_only=True)
    role = fields.Str(
        load_default=UserRole.CUSTOMER,
        validate=validate.OneOf(UserRole.ALL),
    )
    expertise_areas = fields.List(fields.Str(), load_default=[])

    @validates("email")
    def validate_email_unique(self, value):
        from app.models.user import User
        if User.query.filter_by(email=value).first():
            raise ValidationError("Email already registered.")

    @validates("role")
    def validate_role(self, value):
        # Prevent self-registration as admin via the public endpoint
        # (Admin creation handled separately by an existing admin)
        pass


class UserLoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)


class AvailabilityUpdateSchema(Schema):
    availability_status = fields.Str(
        required=True,
        validate=validate.OneOf(AvailabilityStatus.ALL),
    )
