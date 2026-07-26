# ed-eval-service

[![CI](https://github.com/Pavithra8805/ed-eval-service/actions/workflows/ci.yml/badge.svg)](https://github.com/Pavithra8805/ed-eval-service/actions)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![Redis](https://img.shields.io/badge/Redis-7-red)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)

A FastAPI-based education evaluation service built for the **Bodhrik Full Stack Engineer assessment**.

Models the core of an EdTech platform: users with roles, tutoring sessions, and an async evaluation pipeline backed by Redis.

---

## Features

- **PostgreSQL schema** — `users` (admin/teacher/parent), `students`, `sessions`, `evaluations`
- **JWT Auth + RBAC** — teachers see only their own sessions; parents see only their child's data; admin sees everything
- **Redis dual usage** — hot-read caching for session GET (5 min TTL) + Redis LIST queue for evaluation jobs
- **Background worker** — polls `eval_queue` via blocking pop, processes jobs asynchronously
- **Dockerized end-to-end** — single `docker compose up --build` brings up API + PostgreSQL + Redis + worker
- **GitHub Actions CI** — lint (ruff + black) and pytest on every push/PR

---

## Quick Start (Docker)

```bash
git clone https://github.com/Pavithra8805/ed-eval-service.git
cd ed-eval-service
cp .env.example .env
docker compose up --build -d
```

| URL | Description |
|-----|-------------|
| http://localhost:8000/docs | Swagger UI (interactive API docs) |
| http://localhost:8000/health | Health check |

---

## Local Development (without Docker)

```bash
# Create and activate virtualenv
python -m venv .venv
.\.venv\Scripts\activate          # Windows
# source .venv/bin/activate       # Linux/macOS

pip install -r requirements.txt
cp .env.example .env

# Start DB + Redis via Docker (only the services, not the app)
docker compose up db redis -d

# Run database migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000

# In a second terminal — start the background evaluation worker
python -m app.worker.evaluation_worker
```

---

## Running Tests

Tests use **SQLite in-memory** (no Postgres needed) + **FakeRedis** (no Redis needed):

```bash
pytest -v tests/
```

## Lint & Format

```bash
ruff check app tests
black --check app tests
```

---

## API Reference

| Method | Endpoint | Description | Role Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/register` | Register a new user | Public |
| POST | `/api/v1/auth/login` | Login → JWT access token | Public |
| GET | `/api/v1/auth/me` | Get current user profile | Any authenticated |
| POST | `/api/v1/auth/students` | Create a student record | Admin or Teacher |
| POST | `/api/v1/sessions` | Create a tutoring session | Teacher or Admin |
| GET | `/api/v1/sessions` | List sessions (RBAC filtered) | Any authenticated |
| GET | `/api/v1/sessions/{id}` | Get session (Redis cached) | Teacher(own)/Parent(child)/Admin |
| PUT | `/api/v1/sessions/{id}` | Update session | Teacher(own) or Admin |
| DELETE | `/api/v1/sessions/{id}` | Delete session | Teacher(own) or Admin |
| POST | `/api/v1/evaluations/trigger` | Enqueue evaluation job (202) | Teacher/Parent/Admin |
| GET | `/api/v1/evaluations/{id}` | Poll evaluation status/result | Teacher/Parent/Admin |

---

## RBAC Rules Summary

| Role | Sessions | Evaluations |
|------|----------|-------------|
| **admin** | Full CRUD on all sessions | Trigger + view all |
| **teacher** | CRUD only own sessions | Trigger + view own sessions' evals |
| **parent** | Read-only, only child's sessions | Trigger + view child's session evals |

---

## Architecture

```
ed-eval-service/
├── .github/workflows/ci.yml   # CI: lint → test
├── app/
│   ├── api/                   # Route handlers (auth, sessions, evaluations)
│   ├── core/                  # JWT security + RBAC FastAPI deps
│   ├── models/                # SQLAlchemy ORM models (Uuid-compatible)
│   ├── schemas/               # Pydantic v2 schemas
│   ├── worker/                # Redis-backed background evaluation worker
│   ├── config.py              # Settings (pydantic-settings + .env)
│   ├── database.py            # Async SQLAlchemy engine + session factory
│   ├── main.py                # FastAPI app + lifespan (startup/shutdown)
│   └── redis_client.py        # Session cache + eval queue helpers
├── alembic/                   # Alembic DB migration scripts
├── tests/                     # pytest async test suite (SQLite + FakeRedis)
│   ├── conftest.py            # Shared fixtures
│   ├── test_auth.py           # Auth endpoint tests
│   ├── test_sessions.py       # Sessions CRUD + RBAC tests
│   └── test_evaluations.py    # Evaluation trigger + retrieval tests
├── generate_note.py           # Script to generate submission PDF
├── Dockerfile                 # Multi-stage build (builder → runtime)
├── docker-compose.yml         # api + db + redis + worker
├── requirements.txt
├── pyproject.toml             # pytest / ruff / black config
└── .env.example
```

---

## Design Decisions

### Schema Shape
- `users` table stores all authenticated actors (admin/teacher/parent) with role as a Postgres ENUM
- `students` is separate from users — students are learners, not auth actors
- `sessions` are 1:1 between teacher and student; evaluation results live in a separate `evaluations` table to support retries and status tracking
- UUIDs as primary keys across all tables — prevents enumerable IDs in URLs, enables distributed generation

### Redis Usage
1. **Session cache** (`session:<id>` → JSON, TTL 5 min) — avoids DB hit on hot GET requests; invalidated on every write/delete
2. **Eval queue** (`eval_queue` Redis LIST) — `RPUSH` on trigger, `BLPOP` in the worker for blocking, low-latency job pickup

### RBAC Approach
RBAC is enforced at the query level (not just at the router). Each endpoint applies WHERE clauses based on the current user's role before returning data.
