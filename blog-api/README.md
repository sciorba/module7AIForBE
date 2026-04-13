# Blog API

A REST API for a blogging platform built with Flask, SQLAlchemy, Marshmallow, and JWT authentication.

## Stack

- **Flask** — web framework
- **Flask-SQLAlchemy** — ORM
- **Flask-JWT-Extended** — JWT authentication
- **Marshmallow** — serialization & validation
- **Flasgger** — Swagger UI docs
- **Flask-Caching** — response caching (Exercise 2)
- **pytest** — testing

## Setup

```bash
cd blog-api
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

The app will be available at `http://localhost:5000`.  
Swagger UI: `http://localhost:5000/docs/`

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | No | Register a new user |
| POST | `/api/auth/login` | No | Login, returns JWT |
| GET | `/api/posts` | No | List posts (paginated, 20/page) |
| POST | `/api/posts` | Yes | Create a post |
| GET | `/api/posts/<id>` | No | Get a single post |
| PUT | `/api/posts/<id>` | Yes | Update post (author only) |
| DELETE | `/api/posts/<id>` | Yes | Delete post (author only) |
| POST | `/api/posts/<id>/comments` | Yes | Add a comment |
| GET | `/api/posts/<id>/comments` | No | List comments |
| GET | `/api/categories` | No | List all categories |
| POST | `/api/categories` | Yes | Create a category |
| GET | `/api/search?q=keyword` | No | Search posts by keyword |

## Running Tests

```bash
pytest tests/ -v
```

## Authentication

All protected endpoints require a `Bearer` token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Get the token from `/api/auth/register` or `/api/auth/login`.
