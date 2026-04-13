from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError
from app import db
from app.models.ticket import Ticket, TicketStatus, TicketPriority, TicketCategory
from app.models.comment import Comment
from app.models.user import User, UserRole
from app.schemas.ticket import (
    TicketSchema, TicketCreateSchema, TicketUpdateSchema,
    TicketStatusUpdateSchema, TicketPriorityUpdateSchema,
)
from app.schemas.comment import CommentSchema, CommentCreateSchema
from app.schemas.assignment import AssignSchema, AssignmentSchema
from app.services import ticket_service
from app.services.notification_service import notification_service
from app.utils.decorators import get_current_user, require_role
from app.utils.error_handlers import make_error

tickets_bp = Blueprint("tickets", __name__)

ticket_schema = TicketSchema()
tickets_schema = TicketSchema(many=True)
ticket_create_schema = TicketCreateSchema()
ticket_update_schema = TicketUpdateSchema()
status_schema = TicketStatusUpdateSchema()
priority_schema = TicketPriorityUpdateSchema()
comment_schema = CommentSchema()
comments_schema = CommentSchema(many=True)
comment_create_schema = CommentCreateSchema()
assign_schema = AssignSchema()
assignment_schema = AssignmentSchema()
assignments_schema = AssignmentSchema(many=True)

TICKETS_PER_PAGE = 20


# ---------------------------------------------------------------------------
# Helper — enforce visibility rules (FR-033)
# ---------------------------------------------------------------------------

def _ticket_query_for_user(user: User):
    """Return a base query scoped to what `user` is allowed to see."""
    if user.is_admin:
        return Ticket.query
    if user.is_agent:
        # Agents see tickets assigned to them + the unassigned queue
        return Ticket.query.filter(
            db.or_(
                Ticket.assigned_to_id == user.id,
                Ticket.assigned_to_id.is_(None),
            )
        )
    # Customers see only their own tickets
    return Ticket.query.filter_by(customer_id=user.id)


# ---------------------------------------------------------------------------
# GET /api/tickets  — list with filters
# ---------------------------------------------------------------------------

@tickets_bp.route("", methods=["GET"])
@jwt_required()
def list_tickets():
    """
    List tickets (filtered, paginated)
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    parameters:
      - {in: query, name: status, schema: {type: string}}
      - {in: query, name: priority, schema: {type: string}}
      - {in: query, name: category, schema: {type: string}}
      - {in: query, name: q, schema: {type: string}, description: search subject/description}
      - {in: query, name: page, schema: {type: integer, default: 1}}
    responses:
      200:
        description: Paginated tickets
    """
    user = get_current_user()
    query = _ticket_query_for_user(user)

    if status_filter := request.args.get("status"):
        query = query.filter(Ticket.status == status_filter)
    if priority_filter := request.args.get("priority"):
        query = query.filter(Ticket.priority == priority_filter)
    if category_filter := request.args.get("category"):
        query = query.filter(Ticket.category == category_filter)
    if q := request.args.get("q", "").strip():
        kw = f"%{q}%"
        query = query.filter(
            db.or_(Ticket.subject.ilike(kw), Ticket.description.ilike(kw))
        )

    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(Ticket.created_at.desc()).paginate(
        page=page, per_page=TICKETS_PER_PAGE, error_out=False
    )
    return jsonify({
        "tickets": tickets_schema.dump(pagination.items),
        "pagination": {
            "page": pagination.page, "per_page": pagination.per_page,
            "total": pagination.total, "pages": pagination.pages,
            "has_next": pagination.has_next, "has_prev": pagination.has_prev,
        },
    }), 200


# ---------------------------------------------------------------------------
# POST /api/tickets  — create
# ---------------------------------------------------------------------------

@tickets_bp.route("", methods=["POST"])
@jwt_required()
def create_ticket():
    """
    Create a support ticket (FR-001)
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [subject, description, category]
            properties:
              subject:
                type: string
              description:
                type: string
              priority:
                type: string
                enum: [low, medium, high, urgent]
              category:
                type: string
                enum: [technical, billing, general, feature_request]
              customer_email:
                type: string
                format: email
    responses:
      201:
        description: Ticket created
      400:
        description: Validation error
    """
    try:
        data = ticket_create_schema.load(request.get_json() or {})
    except ValidationError as err:
        return make_error("Validation failed", "VALIDATION_ERROR", 400, err.messages)

    user = get_current_user()
    customer_email = data.get("customer_email") or user.email

    ticket = Ticket(
        ticket_number=ticket_service.generate_ticket_number(),
        subject=data["subject"],
        description=data["description"],
        priority=data["priority"],
        category=data["category"],
        customer_email=customer_email,
        customer_id=user.id,
        status=TicketStatus.OPEN,
    )

    # FR-020: set SLA deadlines immediately
    ticket.response_due_at, ticket.resolution_due_at = (
        ticket_service.calculate_sla_deadlines(ticket.priority, ticket.created_at or
                                               datetime.now(timezone.utc))
    )

    db.session.add(ticket)
    db.session.flush()   # get ticket.id before auto-assign

    # FR-006: attempt auto-assignment
    ticket_service.auto_assign(ticket, assigned_by=user)

    db.session.commit()

    # FR-003: email confirmation to customer
    notification_service.ticket_created(ticket)

    return jsonify(ticket_schema.dump(ticket)), 201


# ---------------------------------------------------------------------------
# GET /api/tickets/<id>
# ---------------------------------------------------------------------------

@tickets_bp.route("/<int:ticket_id>", methods=["GET"])
@jwt_required()
def get_ticket(ticket_id):
    """
    Get a single ticket
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    parameters:
      - {in: path, name: ticket_id, required: true, schema: {type: integer}}
    responses:
      200:
        description: Ticket data
      404:
        description: Not found
    """
    user = get_current_user()
    ticket = _ticket_query_for_user(user).filter_by(id=ticket_id).first()
    if not ticket:
        return make_error("Ticket not found", "NOT_FOUND", 404)
    return jsonify(ticket_schema.dump(ticket)), 200


# ---------------------------------------------------------------------------
# PUT /api/tickets/<id>  — update subject/description/category
# ---------------------------------------------------------------------------

@tickets_bp.route("/<int:ticket_id>", methods=["PUT"])
@jwt_required()
def update_ticket(ticket_id):
    """
    Update ticket fields
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    parameters:
      - {in: path, name: ticket_id, required: true, schema: {type: integer}}
    responses:
      200:
        description: Updated ticket
      403:
        description: Forbidden
    """
    user = get_current_user()
    ticket = _ticket_query_for_user(user).filter_by(id=ticket_id).first()
    if not ticket:
        return make_error("Ticket not found", "NOT_FOUND", 404)

    # Customers can only edit their own open tickets
    if user.is_customer and (
        ticket.customer_id != user.id or ticket.status != TicketStatus.OPEN
    ):
        return make_error("Customers can only edit their own open tickets", "FORBIDDEN", 403)

    try:
        data = ticket_update_schema.load(request.get_json() or {})
    except ValidationError as err:
        return make_error("Validation failed", "VALIDATION_ERROR", 400, err.messages)

    for field in ("subject", "description", "category"):
        if field in data:
            setattr(ticket, field, data[field])

    db.session.commit()
    return jsonify(ticket_schema.dump(ticket)), 200


# ---------------------------------------------------------------------------
# DELETE /api/tickets/<id>  — admin only
# ---------------------------------------------------------------------------

@tickets_bp.route("/<int:ticket_id>", methods=["DELETE"])
@require_role("admin")
def delete_ticket(ticket_id):
    """
    Delete a ticket (admin only)
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    parameters:
      - {in: path, name: ticket_id, required: true, schema: {type: integer}}
    responses:
      204:
        description: Deleted
    """
    ticket = Ticket.query.get_or_404(ticket_id)
    db.session.delete(ticket)
    db.session.commit()
    return "", 204


# ---------------------------------------------------------------------------
# PUT /api/tickets/<id>/status  — FR-011, FR-012
# ---------------------------------------------------------------------------

@tickets_bp.route("/<int:ticket_id>/status", methods=["PUT"])
@jwt_required()
def update_status(ticket_id):
    """
    Update ticket status (state-machine enforced)
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    parameters:
      - {in: path, name: ticket_id, required: true, schema: {type: integer}}
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [status]
            properties:
              status:
                type: string
              note:
                type: string
    responses:
      200:
        description: Status updated
      400:
        description: Invalid transition
      403:
        description: Customers cannot change status
    """
    user = get_current_user()
    if user.is_customer:
        return make_error("Customers cannot change ticket status", "FORBIDDEN", 403)

    ticket = _ticket_query_for_user(user).filter_by(id=ticket_id).first()
    if not ticket:
        return make_error("Ticket not found", "NOT_FOUND", 404)

    try:
        data = status_schema.load(request.get_json() or {})
    except ValidationError as err:
        return make_error("Validation failed", "VALIDATION_ERROR", 400, err.messages)

    ok, err_msg = ticket_service.transition_status(
        ticket, data["status"], user, note=data.get("note")
    )
    if not ok:
        return make_error(err_msg, "INVALID_TRANSITION", 400)

    db.session.commit()
    return jsonify(ticket_schema.dump(ticket)), 200


# ---------------------------------------------------------------------------
# PUT /api/tickets/<id>/priority  — FR-023, FR-024
# ---------------------------------------------------------------------------

@tickets_bp.route("/<int:ticket_id>/priority", methods=["PUT"])
@jwt_required()
def update_priority(ticket_id):
    """
    Update ticket priority (agents + admins only; reason required)
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    parameters:
      - {in: path, name: ticket_id, required: true, schema: {type: integer}}
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [priority, reason]
            properties:
              priority:
                type: string
                enum: [low, medium, high, urgent]
              reason:
                type: string
    responses:
      200:
        description: Priority updated
    """
    user = get_current_user()
    if user.is_customer:
        return make_error("Customers cannot change priority", "FORBIDDEN", 403)

    ticket = _ticket_query_for_user(user).filter_by(id=ticket_id).first()
    if not ticket:
        return make_error("Ticket not found", "NOT_FOUND", 404)

    try:
        data = priority_schema.load(request.get_json() or {})
    except ValidationError as err:
        return make_error("Validation failed", "VALIDATION_ERROR", 400, err.messages)

    old_priority = ticket.priority
    ticket.priority = data["priority"]

    # Recalculate SLA deadlines when priority changes
    ticket.response_due_at, ticket.resolution_due_at = (
        ticket_service.calculate_sla_deadlines(
            ticket.priority, ticket.created_at or datetime.now(timezone.utc)
        )
    )

    # Log the change as a comment
    comment = Comment(
        ticket_id=ticket.id,
        user_id=user.id,
        content=f"Priority changed from {old_priority} to {data['priority']}. Reason: {data['reason']}",
        is_internal=True,
    )
    db.session.add(comment)
    db.session.commit()
    return jsonify(ticket_schema.dump(ticket)), 200


# ---------------------------------------------------------------------------
# POST /api/tickets/<id>/assign  — FR-005, FR-006, FR-009
# ---------------------------------------------------------------------------

@tickets_bp.route("/<int:ticket_id>/assign", methods=["POST"])
@require_role("admin")
def assign_ticket(ticket_id):
    """
    Assign / re-assign a ticket (admin only)
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    parameters:
      - {in: path, name: ticket_id, required: true, schema: {type: integer}}
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              agent_id:
                type: integer
              auto:
                type: boolean
                default: false
    responses:
      200:
        description: Ticket assigned
      404:
        description: Agent not found
    """
    user = get_current_user()
    ticket = Ticket.query.filter_by(id=ticket_id).first()
    if not ticket:
        return make_error("Ticket not found", "NOT_FOUND", 404)

    try:
        data = assign_schema.load(request.get_json() or {})
    except ValidationError as err:
        return make_error("Validation failed", "VALIDATION_ERROR", 400, err.messages)

    if data.get("auto"):
        agent = ticket_service.auto_assign(ticket, assigned_by=user)
        if not agent:
            return make_error("No available agents found", "NOT_FOUND", 404)
    elif data.get("agent_id"):
        agent = User.query.filter_by(id=data["agent_id"], role=UserRole.AGENT).first()
        if not agent:
            return make_error("Agent not found", "NOT_FOUND", 404)
        ticket_service.assign_ticket(ticket, agent, assigned_by=user)

    db.session.commit()
    return jsonify(ticket_schema.dump(ticket)), 200


# ---------------------------------------------------------------------------
# POST /api/tickets/<id>/comments  — FR-015, FR-016
# ---------------------------------------------------------------------------

@tickets_bp.route("/<int:ticket_id>/comments", methods=["POST"])
@jwt_required()
def add_comment(ticket_id):
    """
    Add a comment to a ticket
    ---
    tags:
      - Comments
    security:
      - Bearer: []
    parameters:
      - {in: path, name: ticket_id, required: true, schema: {type: integer}}
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
              is_internal:
                type: boolean
                default: false
    responses:
      201:
        description: Comment created
    """
    user = get_current_user()
    ticket = _ticket_query_for_user(user).filter_by(id=ticket_id).first()
    if not ticket:
        return make_error("Ticket not found", "NOT_FOUND", 404)

    try:
        data = comment_create_schema.load(request.get_json() or {})
    except ValidationError as err:
        return make_error("Validation failed", "VALIDATION_ERROR", 400, err.messages)

    # FR-016: customers can only post public comments
    if user.is_customer and data.get("is_internal"):
        return make_error("Customers cannot add internal comments", "FORBIDDEN", 403)

    comment = Comment(
        ticket_id=ticket.id,
        user_id=user.id,
        content=data["content"],
        is_internal=data.get("is_internal", False),
    )
    db.session.add(comment)
    db.session.commit()

    notification_service.comment_added(ticket, comment, user)
    return jsonify(comment_schema.dump(comment)), 201


# ---------------------------------------------------------------------------
# GET /api/tickets/<id>/comments  — FR-015, FR-016 visibility
# ---------------------------------------------------------------------------

@tickets_bp.route("/<int:ticket_id>/comments", methods=["GET"])
@jwt_required()
def list_comments(ticket_id):
    """
    Get comments for a ticket
    ---
    tags:
      - Comments
    security:
      - Bearer: []
    parameters:
      - {in: path, name: ticket_id, required: true, schema: {type: integer}}
    responses:
      200:
        description: List of comments
    """
    user = get_current_user()
    ticket = _ticket_query_for_user(user).filter_by(id=ticket_id).first()
    if not ticket:
        return make_error("Ticket not found", "NOT_FOUND", 404)

    q = Comment.query.filter_by(ticket_id=ticket_id)
    # FR-016: customers only see public comments
    if user.is_customer:
        q = q.filter_by(is_internal=False)
    comments = q.order_by(Comment.created_at.asc()).all()
    return jsonify(comments_schema.dump(comments)), 200


# ---------------------------------------------------------------------------
# GET /api/tickets/<id>/history  — FR-013
# ---------------------------------------------------------------------------

@tickets_bp.route("/<int:ticket_id>/history", methods=["GET"])
@jwt_required()
def get_history(ticket_id):
    """
    Get status change history for a ticket
    ---
    tags:
      - Tickets
    security:
      - Bearer: []
    parameters:
      - {in: path, name: ticket_id, required: true, schema: {type: integer}}
    responses:
      200:
        description: History log
    """
    from app.schemas.ticket import TicketSchema
    user = get_current_user()
    ticket = _ticket_query_for_user(user).filter_by(id=ticket_id).first()
    if not ticket:
        return make_error("Ticket not found", "NOT_FOUND", 404)

    from marshmallow import Schema, fields as mfields
    from app.schemas.user import UserSchema as US

    class HistorySchema(Schema):
        id = mfields.Int()
        old_status = mfields.Str()
        new_status = mfields.Str()
        note = mfields.Str()
        changed_at = mfields.DateTime()
        changed_by = mfields.Nested(US)

    return jsonify(HistorySchema(many=True).dump(ticket.history.all())), 200
