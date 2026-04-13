from marshmallow import Schema, fields
from app.schemas.user import UserSchema


class AssignmentSchema(Schema):
    id = fields.Int(dump_only=True)
    ticket_id = fields.Int(dump_only=True)
    assigned_to = fields.Nested(UserSchema, dump_only=True)
    assigned_by = fields.Nested(UserSchema, dump_only=True)
    assigned_at = fields.DateTime(dump_only=True)


class AssignSchema(Schema):
    # agent_id is optional when auto=True; validated in the route
    agent_id = fields.Int(load_default=None)
    # FR-006: if auto=True, system picks the best agent
    auto = fields.Bool(load_default=False)
