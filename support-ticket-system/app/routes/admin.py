from flask import Blueprint, jsonify
from app.models.ticket import Ticket, TicketStatus, TicketPriority, TicketCategory
from app.models.user import User, UserRole
from app.utils.decorators import require_role

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard", methods=["GET"])
@require_role("admin")
def dashboard():
    """
    Admin dashboard — ticket counts, SLA compliance, agent workload (FR-029)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    responses:
      200:
        description: Dashboard metrics
    """
    # Ticket counts by status
    status_counts = {}
    for status in TicketStatus.ALL:
        status_counts[status] = Ticket.query.filter_by(status=status).count()

    # Ticket counts by priority
    priority_counts = {}
    for priority in TicketPriority.ALL:
        priority_counts[priority] = Ticket.query.filter_by(priority=priority).count()

    # Ticket counts by category
    category_counts = {}
    for category in TicketCategory.ALL:
        category_counts[category] = Ticket.query.filter_by(category=category).count()

    # SLA compliance — resolved tickets within their resolution deadline
    from app import db
    resolved = Ticket.query.filter(
        Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
        Ticket.resolved_at.isnot(None),
        Ticket.resolution_due_at.isnot(None),
    ).all()
    compliant = sum(1 for t in resolved
                    if t.resolved_at and t.resolution_due_at and
                    t.resolved_at <= t.resolution_due_at)
    sla_rate = round(compliant / len(resolved) * 100, 1) if resolved else None

    # Agent workload
    agents = User.query.filter_by(role=UserRole.AGENT).all()
    agent_workload = [
        {
            "id": a.id,
            "name": a.name,
            "availability_status": a.availability_status,
            "open_tickets": a.assigned_tickets.filter(
                Ticket.status.notin_([TicketStatus.CLOSED, TicketStatus.RESOLVED])
            ).count(),
        }
        for a in agents
    ]

    return jsonify({
        "tickets": {
            "by_status": status_counts,
            "by_priority": priority_counts,
            "by_category": category_counts,
            "total": Ticket.query.count(),
        },
        "sla_compliance_pct": sla_rate,
        "agents": agent_workload,
    }), 200
