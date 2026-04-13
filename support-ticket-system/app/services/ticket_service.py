"""
Core ticket business logic:
  - Ticket number generation  (FR-002)
  - SLA deadline calculation  (FR-020)
  - Status transition guard   (FR-012)
  - Auto-assignment            (FR-006)
"""
from datetime import datetime, timezone, timedelta
from app import db
from app.models.ticket import Ticket, TicketStatus, TicketPriority
from app.models.ticket_history import TicketHistory
from app.models.assignment import Assignment
from app.models.user import User, UserRole, AvailabilityStatus
from app.services.notification_service import notification_service


# ---------------------------------------------------------------------------
# FR-002: auto-generate TICK-YYYYMMDD-XXXX
# ---------------------------------------------------------------------------

def generate_ticket_number() -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"TICK-{date_str}-"
    count = Ticket.query.filter(Ticket.ticket_number.like(f"{prefix}%")).count()
    return f"{prefix}{str(count + 1).zfill(4)}"


# ---------------------------------------------------------------------------
# FR-020: SLA deadline calculation
# ---------------------------------------------------------------------------

def calculate_sla_deadlines(priority: str, created_at: datetime):
    sla = TicketPriority.SLA[priority]
    response_due = created_at + timedelta(hours=sla["response_hours"])
    resolution_due = created_at + timedelta(hours=sla["resolution_hours"])
    return response_due, resolution_due


# ---------------------------------------------------------------------------
# FR-012: status transition validation + FR-013: history logging
# ---------------------------------------------------------------------------

def transition_status(ticket: Ticket, new_status: str, changed_by: User,
                      note: str = None) -> tuple[bool, str]:
    """
    Attempt a status transition.
    Returns (success: bool, error_message: str).
    On success mutates ticket.status and writes a TicketHistory row.
    """
    old_status = ticket.status

    if not TicketStatus.can_transition(old_status, new_status):
        return False, (f"Cannot transition from '{old_status}' to '{new_status}'. "
                       f"Valid transitions: {TicketStatus.TRANSITIONS.get(old_status, [])}")

    # FR-012 special rule: Closed → Reopened only within 7 days
    if old_status == TicketStatus.CLOSED and new_status == TicketStatus.REOPENED:
        if ticket.closed_at:
            closed_at = ticket.closed_at
            if closed_at.tzinfo is None:
                closed_at = closed_at.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - closed_at
            if age.days > 7:
                return False, "Ticket can only be reopened within 7 days of closing."

    ticket.status = new_status
    now = datetime.now(timezone.utc)
    ticket.updated_at = now

    if new_status == TicketStatus.RESOLVED:
        ticket.resolved_at = now
    if new_status == TicketStatus.CLOSED:
        ticket.closed_at = now

    # FR-013: write history entry
    history = TicketHistory(
        ticket_id=ticket.id,
        changed_by_id=changed_by.id,
        old_status=old_status,
        new_status=new_status,
        note=note,
    )
    db.session.add(history)

    # FR-014: notify customer + agent
    notification_service.status_changed(ticket, old_status, new_status)

    return True, ""


# ---------------------------------------------------------------------------
# FR-006: auto-assign to least-loaded available agent
# ---------------------------------------------------------------------------

def auto_assign(ticket: Ticket, assigned_by: User) -> User | None:
    """
    Pick the available agent with the fewest open tickets.
    Returns the assigned User or None if no agents are available.
    """
    agents = User.query.filter_by(
        role=UserRole.AGENT,
        availability_status=AvailabilityStatus.AVAILABLE,
    ).all()

    if not agents:
        return None

    def workload(agent: User) -> int:
        return agent.assigned_tickets.filter(
            Ticket.status.notin_([TicketStatus.CLOSED, TicketStatus.RESOLVED])
        ).count()

    best_agent = min(agents, key=workload)
    _do_assign(ticket, best_agent, assigned_by)
    return best_agent


# ---------------------------------------------------------------------------
# FR-005, FR-009: manual assign / reassign
# ---------------------------------------------------------------------------

def assign_ticket(ticket: Ticket, agent: User, assigned_by: User) -> None:
    _do_assign(ticket, agent, assigned_by)


def _do_assign(ticket: Ticket, agent: User, assigned_by: User) -> None:
    ticket.assigned_to_id = agent.id
    ticket.updated_at = datetime.now(timezone.utc)

    # FR-008: status → assigned
    if ticket.status == TicketStatus.OPEN:
        ok, err = transition_status(ticket, TicketStatus.ASSIGNED, assigned_by,
                                    note=f"Assigned to {agent.name}")
        # transition_status flushes history — if for some reason it fails, set directly
        if not ok:
            ticket.status = TicketStatus.ASSIGNED

    # FR-010: record in assignment history
    record = Assignment(
        ticket_id=ticket.id,
        assigned_to_id=agent.id,
        assigned_by_id=assigned_by.id,
    )
    db.session.add(record)

    # FR-007: notify agent
    notification_service.ticket_assigned(ticket, agent)
