# Task Management API

A team task management application built with FastAPI, PostgreSQL, and Next.js. Users register, form teams, and manage tasks with role-based access control.

---

## What it does

- Users register and log in with JWT authentication
- A user creates a team and is automatically added as its first member
- Team members can add other users and create tasks
- Tasks have a status (`todo` / `in_progress` / `done`) and an optional assignee
- Only the task creator or assignee can update a task; only the creator can delete it
- Assigning a task to someone outside the team is rejected

---

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI + SQLAlchemy |
| Database | PostgreSQL 15 |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Frontend | Next.js 14 + Tailwind CSS |
| Containerisation | Docker (multi-stage) + Docker Compose |
| CI | GitHub Actions (lint → test → build) |
| Tests | pytest + SQLite via `dependency_overrides` |

---

## Project structure

```
├── main.py               # App entry point, CORS, router registration
├── database.py           # SQLAlchemy engine + get_db dependency
├── models.py             # ORM models (User, Team, TeamMember, Task)
├── schemas.py            # Pydantic request/response schemas
├── auth.py               # Password hashing + JWT encode/decode
├── dependencies.py       # get_current_user, get_team_member dependency chain
├── routers/
│   ├── auth.py           # POST /auth/register, POST /auth/login, GET /auth/me
│   ├── teams.py          # GET /teams, POST /teams, POST /teams/{id}/members, GET /teams/{id}
│   └── tasks.py          # POST /teams/{id}/tasks, GET /teams/{id}/tasks, PATCH /tasks/{id}, DELETE /tasks/{id}
├── services/
│   ├── auth.py           # Registration and login logic
│   ├── teams.py          # Team creation, membership, queries
│   └── tasks.py          # Task CRUD + ownership checks
├── tests/
│   └── test_api.py       # 8 integration tests using SQLite
├── frontend/
│   ├── app/              # Next.js App Router pages
│   │   ├── login/        # Login page
│   │   ├── register/     # Registration page
│   │   ├── dashboard/    # Teams overview
│   │   └── teams/[teamId]/ # Team detail: tasks + members
│   ├── lib/api.ts        # Typed fetch wrapper for all API calls
│   ├── types/index.ts    # TypeScript interfaces matching backend schemas
│   └── Dockerfile        # Multi-stage Next.js production build
├── init.sql              # PostgreSQL schema (tables, indexes, trigger)
├── Dockerfile            # Multi-stage Python production build
├── docker-compose.yml    # db + api + frontend, with healthchecks
├── .github/workflows/
│   └── ci.yml            # lint → test → build pipeline
├── pyproject.toml        # ruff linter config
└── requirements.txt
```

---

## Running with Docker (recommended)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| API | http://localhost:8000 |

On first start, Docker runs `init.sql` automatically to create all tables.

To stop and remove containers (database data is preserved in a volume):

```bash
docker compose down
```

To also wipe the database:

```bash
docker compose down -v
```

---

## Running locally (without Docker)

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL running locally

### Backend

```bash
# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://appuser:secret@localhost:5432/taskdb
SECRET_KEY=any-long-random-string
```

Apply the schema to your local database:

```bash
psql -U appuser -d taskdb -f init.sql
```

Start the API:

```bash
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3000` and expects the API at `http://localhost:8000`.

---

## Running tests

Tests use SQLite in-memory via FastAPI's `dependency_overrides` — no PostgreSQL needed.

```bash
pytest
```

### Test coverage

| # | Test |
|---|---|
| 1 | Register a user → 201, password not in response |
| 2 | Login → returns a bearer token |
| 3 | Create a team → 201, creator is in the member list |
| 4 | Add a member as a non-member → 403 |
| 5 | Create a task as a non-member → 403 |
| 6 | Assign a task to a non-member → 400 |
| 7 | Update a task as neither creator nor assignee → 403 |
| 8 | Filter tasks by status → only matching tasks returned |

---

## API endpoints

### Auth
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | — | Register. Returns user (no password). |
| `POST` | `/auth/login` | — | Login. Returns JWT token. |
| `GET` | `/auth/me` | ✓ | Returns the current user's profile. |

### Teams
| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/teams` | ✓ | List all teams the current user belongs to. |
| `POST` | `/teams` | ✓ | Create a team. Creator is auto-added as first member. |
| `GET` | `/teams/{team_id}` | ✓ member | Get team details and member list. |
| `POST` | `/teams/{team_id}/members` | ✓ member | Add a user to the team. |

### Tasks
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/teams/{team_id}/tasks` | ✓ member | Create a task. |
| `GET` | `/teams/{team_id}/tasks` | ✓ member | List tasks. Supports `?status=` and `?assignee_id=` filters. |
| `PATCH` | `/tasks/{task_id}` | ✓ creator/assignee | Partially update a task. |
| `DELETE` | `/tasks/{task_id}` | ✓ creator | Delete a task. |

---

## Key design decisions

**Services layer** — all business logic lives in `services/`. Route functions only parse the request, call a service, and return the result. This makes logic testable without spinning up an HTTP server.

**Dependency chain** — `get_db` → `get_current_user` → `get_team_member`. Each layer builds on the previous. FastAPI resolves the full chain before calling a route, and caches the DB session so only one connection is opened per request.

**Schema vs ORM model** — Pydantic schemas control what crosses the HTTP boundary. The `password` field exists on the SQLAlchemy model but not on `UserResponse`, so FastAPI never returns it, even if the ORM object has it.

**ON DELETE behaviour** — each foreign key has a deliberate strategy: `CASCADE` where the child row is meaningless without the parent, `RESTRICT` where deletion must be an explicit decision, `SET NULL` where the row remains valid without the reference (e.g. a task without an assignee).

**NEXT_PUBLIC_ env vars** — Next.js bakes `NEXT_PUBLIC_` variables into the JavaScript bundle at build time. The browser downloads this bundle; it cannot read Docker container environment variables. So the API URL is passed as a Docker build argument, not a runtime env var.
