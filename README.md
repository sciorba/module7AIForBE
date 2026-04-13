# Backend Exercises — ByGrid University · Module 5

Flask / SQLAlchemy / Marshmallow / JWT · Python 3.12

---

## Repository structure

```
cursorCourseBE/
├── blog-api/               # Exercises 1 & 2 — same codebase, Ex2 builds on Ex1
│   ├── app/
│   │   ├── models/         User, Post, Category, Comment
│   │   ├── routes/         auth, posts (+ comments), categories, search
│   │   ├── schemas/        Marshmallow schemas
│   │   ├── services/       (placeholder for Ex2 service layer)
│   │   └── utils/          error handlers, cache key builders
│   ├── tests/              68 tests · 94% coverage
│   ├── config.py
│   ├── requirements.txt
│   └── run.py
│
└── support-ticket-system/  # Exercise 3 — standalone app built from PRD
    ├── app/
    │   ├── models/         User, Ticket, Comment, Assignment, TicketHistory
    │   ├── routes/         auth, tickets (CRUD + status + assign + comments), users, admin
    │   ├── schemas/        Marshmallow schemas
    │   ├── services/       TicketService, NotificationService
    │   └── utils/          PRD-format error handlers, @require_role decorator
    ├── tests/              64 tests · 90% coverage
    ├── config.py
    ├── requirements.txt
    └── run.py
```

---

## Exercise 1 — Blog API

> Build a REST API for a blogging platform.

### Features implemented

| Requirement | Status | Detail |
|---|---|---|
| User authentication (register, login) | ✅ | JWT via Flask-JWT-Extended |
| Post CRUD operations | ✅ | Full create / read / update / delete |
| Comment system (create, read, delete) | ✅ | Author or post owner can delete |
| Category management | ✅ | Auto-slugged, unique names |
| Search posts by keyword | ✅ | Case-insensitive, title + content |
| Pagination — 20 posts per page | ✅ | `?page=` query param |
| Swagger documentation | ✅ | `/docs/` |
| Proper error handling & validation | ✅ | Marshmallow, 400/401/403/404 handlers |

### API endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | No | Register a new user |
| POST | `/api/auth/login` | No | Login, returns JWT |
| GET | `/api/posts` | No | List posts (paginated, 20/page) |
| POST | `/api/posts` | Yes | Create a post |
| GET | `/api/posts/<id>` | No | Get a single post |
| PUT | `/api/posts/<id>` | Yes | Update post (author only) |
| DELETE | `/api/posts/<id>` | Yes | Delete post (author only) |
| POST | `/api/posts/<id>/comments` | Yes | Add a comment |
| GET | `/api/posts/<id>/comments` | No | List comments |
| DELETE | `/api/posts/<id>/comments/<id>` | Yes | Delete comment (author or post owner) |
| GET | `/api/categories` | No | List all categories |
| POST | `/api/categories` | Yes | Create a category |
| GET | `/api/search?q=keyword` | No | Search posts by keyword |

### Setup

```bash
cd blog-api
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py                  # → http://localhost:5000
```

Swagger UI: `http://localhost:5000/docs/`

---

## Exercise 2 — Caching & Testing

> Enhance the Blog API with Redis caching and comprehensive tests.

### Features implemented

| Requirement | Status | Detail |
|---|---|---|
| Redis caching configured | ✅ | `CACHE_TYPE=RedisCache` via `.env`; falls back to `SimpleCache` in dev |
| Cache post listings | ✅ | `posts:list:{page}:{per_page}` key |
| Cache individual posts | ✅ | `posts:detail:{id}` key |
| Cache search results | ✅ | `posts:search:{q}:{page}` key |
| Cache categories | ✅ | `categories:all` key |
| Cache invalidation on writes | ✅ | `cache.delete(key)` on update, `cache.clear()` on create/delete |
| 15+ pytest test cases | ✅ | **68 total** (39 original + 25 added in Ex2 + 4 comment delete) |
| 85%+ test coverage | ✅ | **94%** |
| Database indexes for optimization | ✅ | `ix_posts_published_created`, `ix_posts_user_id`, `ix_comments_post_id` |

### Caching strategy

Dicts (not Flask Response objects) are stored in the cache — this keeps values pickle-safe and makes cache state directly inspectable in tests via `cache.get(key)`.

Write-path invalidation:

| Event | Invalidation |
|-------|-------------|
| `POST /api/posts` | `cache.clear()` — new post affects all list pages |
| `PUT /api/posts/<id>` | `cache.delete("posts:detail:<id>")` + `cache.clear()` |
| `DELETE /api/posts/<id>` | `cache.clear()` |
| `POST /api/posts/<id>/comments` | `cache.delete("posts:detail:<id>")` (comment count changed) |
| `POST /api/categories` | `cache.delete("categories:all")` |

### Running tests & coverage

```bash
cd blog-api
source venv/bin/activate
pytest tests/ -v
pytest tests/ --cov=app --cov-report=term-missing
```

---

## Exercise 3 — Support Ticket System (from PRD)

> Implement the customer support ticket system from `PRD_Customer_Support_System.txt`.

### PRD requirements implemented

| Req | Description | Status |
|-----|-------------|--------|
| FR-001 | Ticket creation with field validation | ✅ |
| FR-002 | Auto-generate `TICK-YYYYMMDD-XXXX` ticket numbers | ✅ |
| FR-003 | Email confirmation to customer on creation | ✅ simulated |
| FR-005 | Admin manually assigns tickets to agents | ✅ |
| FR-006 | Auto-assign to least-loaded available agent | ✅ |
| FR-007 | Agent notified on assignment | ✅ simulated |
| FR-008 | Status → `assigned` on assignment | ✅ |
| FR-009 | Admin can reassign to different agent | ✅ |
| FR-010 | Assignment history tracked with timestamp | ✅ |
| FR-011 | 7-status ticket lifecycle | ✅ |
| FR-012 | State-machine transition rules enforced | ✅ |
| FR-013 | Status changes logged in `TicketHistory` | ✅ |
| FR-014 | Customer + agent notified on status changes | ✅ simulated |
| FR-015 | Comments system (create, read) | ✅ |
| FR-016 | Public vs internal comments; customers see public only | ✅ |
| FR-018 | Comment notification sent to relevant parties | ✅ simulated |
| FR-020 | Priority-based SLA deadlines (response + resolution) | ✅ |
| FR-021 | `sla_status` flag on every ticket response | ✅ `ok/warning/critical/breached` |
| FR-023 | Priority changes by agents/admins only | ✅ |
| FR-024 | Priority change requires a reason | ✅ |
| FR-032 | Three user roles: customer, agent, admin | ✅ |
| FR-033 | Role-based access control (RBAC) | ✅ |
| FR-035 | Email notifications (6 event types) | ✅ simulated |

### API endpoints

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| POST | `/api/auth/register` | Public | Register (customer / agent / admin) |
| POST | `/api/auth/login` | Public | Login, returns JWT |
| GET | `/api/auth/me` | Any | Current user profile |
| GET | `/api/tickets` | Any | List tickets (role-scoped + filters) |
| POST | `/api/tickets` | Any | Create ticket |
| GET | `/api/tickets/<id>` | Any | Get ticket detail + SLA status |
| PUT | `/api/tickets/<id>` | Any | Update subject / description / category |
| DELETE | `/api/tickets/<id>` | Admin | Delete ticket |
| PUT | `/api/tickets/<id>/status` | Agent, Admin | Status transition (state-machine enforced) |
| PUT | `/api/tickets/<id>/priority` | Agent, Admin | Change priority (reason required) |
| POST | `/api/tickets/<id>/assign` | Admin | Manual or auto-assign |
| POST | `/api/tickets/<id>/comments` | Any | Add public or internal comment |
| GET | `/api/tickets/<id>/comments` | Any | List comments (internal filtered for customers) |
| GET | `/api/tickets/<id>/history` | Any | Full status-change history |
| GET | `/api/users` | Admin | List all users |
| GET | `/api/agents` | Admin, Agent | List agents |
| PUT | `/api/agents/<id>/availability` | Admin, Self | Update availability status |
| GET | `/api/admin/dashboard` | Admin | Metrics: counts, SLA compliance, agent workload |

### Status state machine (FR-012)

```
open ──→ assigned ──→ in_progress ──→ waiting
  └──→ closed           ↓    ↑──────────┘
                      resolved ──→ closed
                         └──→ reopened ──→ in_progress
```

Invalid transitions return `400 INVALID_TRANSITION`.

### SLA deadlines (FR-020)

| Priority | First response | Resolution |
|----------|---------------|------------|
| Urgent | 2 hours | 24 hours |
| High | 4 hours | 48 hours |
| Medium | 8 hours | 5 days |
| Low | 24 hours | 10 days |

### Error response format (PRD §8)

```json
{
  "status": "error",
  "message": "Human-readable message",
  "code": "ERROR_CODE",
  "errors": { "field": ["detail"] }
}
```

### Setup

```bash
cd support-ticket-system
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py                   # → http://localhost:5001
```

Swagger UI: `http://localhost:5001/docs/`

### Running tests & coverage

```bash
cd support-ticket-system
source venv/bin/activate
pytest tests/ -v
pytest tests/ --cov=app --cov-report=term-missing
```

---

## Test summary

| Project | Tests | Coverage | Notes |
|---------|-------|----------|-------|
| `blog-api` (Ex 1 + 2) | **68 passed** | **94%** | auth, posts, comments (incl. delete), categories, search, caching |
| `support-ticket-system` (Ex 3) | **64 passed** · 1 skipped | **90%** | auth, tickets, status transitions, comments, assignment, SLA, admin |

---

## Shared tech stack

```
Flask 3.0          Flask-SQLAlchemy 3.1    Flask-Migrate 4.0
Flask-JWT-Extended 4.6    Marshmallow 3.21    Flasgger 0.9
Flask-Caching 2.3 (Ex2)   pytest 8.2          pytest-cov 5.0
```

## Authentication

All protected endpoints require a `Bearer` token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Tokens are obtained from `/api/auth/register` or `/api/auth/login`.
