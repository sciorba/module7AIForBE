import re
from marshmallow import Schema, fields, validate, validates, ValidationError
from app.models.ticket import TicketStatus, TicketPriority, TicketCategory
from app.schemas.user import UserSchema


class TicketSchema(Schema):
    id = fields.Int(dump_only=True)
    ticket_number = fields.Str(dump_only=True)
    subject = fields.Str(dump_only=True)
    description = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True)
    priority = fields.Str(dump_only=True)
    category = fields.Str(dump_only=True)
    customer_email = fields.Email(dump_only=True)
    customer = fields.Nested(UserSchema, dump_only=True)
    assigned_agent = fields.Nested(UserSchema, dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    resolved_at = fields.DateTime(dump_only=True)
    closed_at = fields.DateTime(dump_only=True)
    response_due_at = fields.DateTime(dump_only=True)
    resolution_due_at = fields.DateTime(dump_only=True)
    sla_status = fields.Method("get_sla_status", dump_only=True)
    comment_count = fields.Method("get_comment_count", dump_only=True)

    def get_sla_status(self, obj):
        return obj.sla_status

    def get_comment_count(self, obj):
        return obj.comments.count()


# FR-001: strict validation on ticket creation
_SUBJECT_RE = re.compile(r"^[\w\s.,!?;:()\-'\"]+$")


class TicketCreateSchema(Schema):
    subject = fields.Str(required=True, validate=validate.Length(min=5, max=200))
    description = fields.Str(required=True, validate=validate.Length(min=20, max=5000))
    priority = fields.Str(
        load_default=TicketPriority.MEDIUM,
        validate=validate.OneOf(TicketPriority.ALL),
    )
    category = fields.Str(
        required=True,
        validate=validate.OneOf(TicketCategory.ALL),
    )
    customer_email = fields.Email(required=False)   # optional — falls back to user's email

    @validates("subject")
    def validate_subject_chars(self, value):
        if not _SUBJECT_RE.match(value):
            raise ValidationError(
                "Subject may only contain alphanumeric characters and common punctuation."
            )


class TicketUpdateSchema(Schema):
    subject = fields.Str(validate=validate.Length(min=5, max=200))
    description = fields.Str(validate=validate.Length(min=20, max=5000))
    category = fields.Str(validate=validate.OneOf(TicketCategory.ALL))


class TicketStatusUpdateSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf(TicketStatus.ALL))
    note = fields.Str(validate=validate.Length(max=500))


class TicketPriorityUpdateSchema(Schema):
    # FR-024: reason required when changing priority
    priority = fields.Str(required=True, validate=validate.OneOf(TicketPriority.ALL))
    reason = fields.Str(required=True, validate=validate.Length(min=5, max=500))
