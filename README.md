# ed-eval-service

[![CI](https://github.com/Pavithra8805/ed-eval-service/actions/workflows/ci.yml/badge.svg)](https://github.com/Pavithra8805/ed-eval-service/actions)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![Redis](https://img.shields.io/badge/Redis-7-red)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)

A FastAPI-based education evaluation service built for the Bodhrik Full Stack Engineer assessment.

---

## Features

- **PostgreSQL schema**: Users (admin/teacher/parent), Students, Sessions, Evaluations
- **JWT Auth + RBAC**: Role-based access control — teachers see only their sessions, parents see only their child's data
- **Redis dual usage**: Session caching (hot-read) + evaluation job queue
- **Docker Compose**: Single command to run the full stack
- **GitHub Actions CI**: lint + tests on every push

---

## Quick Start

```bash
# Clone & run everything
git clone https://github.com/Pavithra8805/ed-eval-service.git
cd ed-eval-service
cp .env.example .env
docker compose up --build -d
```

- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## Local Development

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Start DB + Redis via Docker
docker compose up db redis -d

# Run migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload --port 8000

# Start background worker (separate terminal)
python -m app.worker.evaluation_worker
```

---

## Running Tests

```bash
pytest -v tests/
```

## Lint & Format

```bash
ruff check app tests
black --check app tests
```

---

## API Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/api/v1/auth/register` | Register user | Public |
| POST | `/api/v1/auth/login` | Login → JWT | Public |
| GET | `/api/v1/auth/me` | Current user | Authenticated |
| POST | `/api/v1/auth/students` | Create student | Admin/Teacher |
| POST | `/api/v1/sessions` | Create session | Teacher/Admin |
| GET | `/api/v1/sessions` | List sessions (RBAC) | Authenticated |
| GET | `/api/v1/sessions/{id}` | Get session (cached) | Teacher(owner)/Parent(child)/Admin |
| PUT | `/api/v1/sessions/{id}` | Update session | Teacher(owner)/Admin |
| DELETE | `/api/v1/sessions/{id}` | Delete session | Teacher(owner)/Admin |
| POST | `/api/v1/evaluations/trigger` | Enqueue eval job | Teacher/Parent/Admin |
| GET | `/api/v1/evaluations/{id}` | Get eval result | Teacher/Parent/Admin |

---

## Directory Structure

```
ed-eval-service/
├── .github/workflows/ci.yml
├── app/
│   ├── api/           # Route handlers
│   ├── core/          # JWT security + RBAC deps
│   ├── models/        # SQLAlchemy ORM models
│   ├── schemas/       # Pydantic V2 schemas
│   ├── worker/        # Redis background eval worker
│   ├── config.py      # Settings via pydantic-settings
│   ├── database.py    # Async SQLAlchemy engine
│   ├── main.py        # FastAPI app + lifespan
│   └── redis_client.py
├── alembic/           # DB migrations
├── scripts/           # PDF generation
├── tests/             # pytest async suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── WRITTEN_NOTE.md
```
