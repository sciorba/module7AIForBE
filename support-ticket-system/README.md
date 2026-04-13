# Customer Support Ticket System

A REST API for a customer support ticket management system built from the PRD.
Implements FR-001 through FR-035 core requirements.

## Stack

- **Flask** — web framework
- **Flask-SQLAlchemy** — ORM with SQLite (dev) / PostgreSQL (prod)
- **Flask-JWT-Extended** — JWT authentication (24-hour tokens, NFR-006)
- **Marshmallow** — serialization & validation
- **Flasgger** — Swagger UI documentation
- **pytest** — 30+ tests

## Setup

```bash
cd support-ticket-system
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py                   # http://localhost:5001
```

Swagger UI: `http://localhost:5001/docs/`

## Architecture

```
app/
├── models/         User, Ticket, Comment, Assignment, TicketHistory
├── routes/         auth, tickets (CRUD + status + assign + comments), users, admin
├── schemas/        Marshmallow input validation & output serialization
├── services/
│   ├── ticket_service.py       number gen, SLA calc, state-machine, auto-assign
│   └── notification_service.py email simulation (log / capture / off)
└── utils/
    ├── error_handlers.py       PRD-spec error format {status, message, code, errors}
    └── decorators.py           @require_role RBAC decorator
```

## API Endpoints

### Auth
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | No | Register user (customer/agent/admin) |
| POST | `/api/auth/login` | No | Login, returns JWT |
| GET | `/api/auth/me` | Yes | Current user profile |

### Tickets
| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| GET | `/api/tickets` | All | List tickets (scoped by role + filters) |
| POST | `/api/tickets` | All | Create ticket (FR-001, FR-002) |
| GET | `/api/tickets/:id` | All | Get ticket detail |
| PUT | `/api/tickets/:id` | All | Update subject/description/category |
| DELETE | `/api/tickets/:id` | Admin | Delete ticket |
| PUT | `/api/tickets/:id/status` | Agent, Admin | Status transition (FR-012) |
| PUT | `/api/tickets/:id/priority` | Agent, Admin | Change priority + reason (FR-024) |
| POST | `/api/tickets/:id/assign` | Admin | Assign/reassign ticket (FR-005, FR-006) |
| POST | `/api/tickets/:id/comments` | All | Add comment (FR-015, FR-016) |
| GET | `/api/tickets/:id/comments` | All | List comments (internal hidden from customers) |
| GET | `/api/tickets/:id/history` | All | Status change history (FR-013) |

### Users & Agents
| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| GET | `/api/users` | Admin | List all users |
| GET | `/api/agents` | Admin, Agent | List agents |
| PUT | `/api/agents/:id/availability` | Admin, Self | Update availability |

### Admin
| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| GET | `/api/admin/dashboard` | Admin | Ticket counts, SLA compliance, agent workload |

## Key Design Decisions

### Role-Based Access (FR-032, FR-033)
- **Customer** — sees only own tickets, public comments only, cannot change status/priority
- **Agent** — sees assigned tickets + unassigned queue, can add internal comments, update status
- **Admin** — full access, can assign/reassign tickets, delete tickets, view dashboard

### Status State Machine (FR-012)
```
open → assigned → in_progress → waiting → in_progress (loop)
                              ↘ resolved → closed
                                         ↘ reopened → in_progress
```
Invalid transitions return `400 INVALID_TRANSITION`.

### SLA (FR-020)
| Priority | Response | Resolution |
|----------|----------|------------|
| Urgent   | 2 hours  | 24 hours   |
| High     | 4 hours  | 48 hours   |
| Medium   | 8 hours  | 5 days     |
| Low      | 24 hours | 10 days    |

SLA status (`ok` / `warning` / `critical` / `breached`) is returned on every ticket response (FR-021).

### Ticket Numbering (FR-002)
Format: `TICK-YYYYMMDD-XXXX` (e.g. `TICK-20251016-0001`)

### Email Notifications (FR-035)
Simulated via `NotificationService`. Set `NOTIFICATION_MODE=log` in `.env` to print to stdout, `capture` for tests, `off` to disable.

## Running Tests

```bash
pytest tests/ -v
pytest tests/ --cov=app --cov-report=term-missing
```
