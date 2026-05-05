## What you're building

A **task management API** for teams. Teams have members. Members create tasks. Tasks are assigned to members.

---

## Domain rules

- A **user** has a name, email, and password
- A **team** has a name and a creator (a user)
- A user can belong to **multiple teams** (many-to-many)
- A **task** belongs to a team, has a title, description, status (`todo` / `in_progress` / `done`), and an optional assignee (a user who is a member of that team)
- Only a **team member** can create tasks in that team
- Only the **task creator or the assignee** can update a task
- Assigning a task to someone who is **not a team member** must be rejected with 400

---

## Schema requirements

Write raw SQL (`init.sql`) and SQLAlchemy models (`models.py`):

- Correct normalization — no redundancy
- All foreign keys indexed manually
- Right `ON DELETE` behavior on every FK — justify each in a comment
- `CHECK` constraint on task status — only the three valid values allowed
- `created_at` and `updated_at` on tasks — `updated_at` must update automatically on change

---

## Endpoints to implement

**Auth**
| Method | Path | Rule |
|---|---|---|
| `POST` | `/auth/register` | Hash password, return user (no password in response) |
| `POST` | `/auth/login` | Return JWT token |

**Teams**
| Method | Path | Rule |
|---|---|---|
| `POST` | `/teams` | Auth required. Creator is auto-added as first member |
| `POST` | `/teams/{team_id}/members` | Auth required. Only existing team members can add new members |
| `GET` | `/teams/{team_id}` | Auth required. Returns team + member list |

**Tasks**
| Method | Path | Rule |
|---|---|---|
| `POST` | `/teams/{team_id}/tasks` | Auth required. Must be team member |
| `GET` | `/teams/{team_id}/tasks` | Auth required. Must be team member. Supports `?status=` filter and `?assignee_id=` filter |
| `PATCH` | `/tasks/{task_id}` | Auth required. Only creator or assignee can update |
| `DELETE` | `/tasks/{task_id}` | Auth required. Only creator can delete |

---

## Technical requirements

**Project structure — non-negotiable:**
```
├── main.py
├── database.py
├── models.py
├── schemas.py
├── auth.py
├── dependencies.py        # get_db, get_current_user, get_team_member
├── routers/
│   ├── auth.py
│   ├── teams.py
│   └── tasks.py
├── services/
│   ├── teams.py           # business logic — not in route functions
│   └── tasks.py
├── tests/
│   └── test_api.py
├── init.sql
├── Dockerfile             # multi-stage
├── docker-compose.yml     # api + postgres with healthcheck
├── .github/
│   └── workflows/
│       └── ci.yml         # lint → test → build
├── .gitignore
├── .env                   # not committed
├── pyproject.toml         # ruff config
└── requirements.txt
```

**Non-negotiables:**
- Every route has a `response_model`
- `get_db` uses `yield` with commit / rollback / close
- No business logic inside route functions — it lives in `services/`
- `SECRET_KEY` and `DATABASE_URL` come from environment variables only
- Multi-stage Dockerfile with non-root user
- `depends_on: condition: service_healthy` in Compose
- Service name (`db`) in `DATABASE_URL`, not `localhost`

---

## Tests to write

All using `dependency_overrides` + SQLite:

1. Register a user → 201, no password in response
2. Login → returns a token
3. Create a team → 201, creator is in the member list
4. Add a member to a team as a non-member → 403
5. Create a task as a non-member → 403
6. Assign a task to a non-member → 400
7. Update a task as someone who is neither creator nor assignee → 403
8. Filter tasks by status → only correct tasks returned

---

## CI pipeline requirements

Three jobs, each `needs` the previous:

1. **lint** — `ruff check .` fails the pipeline on any error
2. **test** — `pytest` with a real PostgreSQL service container
3. **build** — `docker build` succeeds

---

## What I'll assess

| Area | What I'm looking for |
|---|---|
| Schema | Normalization, indexes, constraints, ON DELETE justification |
| Services layer | Business logic is not in route functions |
| Dependency chain | `get_team_member` built on `get_current_user` built on `get_db` |
| Auth | Password hashed, JWT verified, ownership correctly checked |
| Error codes | 400 / 401 / 403 / 404 used correctly and consistently |
| Tests | All 8 cases, `dependency_overrides`, no real DB in tests |
| Docker | Multi-stage, non-root, healthcheck, service name networking |
| CI | Three jobs with `needs`, secrets via env, real PG service in test job |
| Commit history | Logical commits, not one giant "done" commit |
| Time | Note how long it took |

---

When you're done, paste your files one by one. Start with `init.sql`, then `models.py`, then work outward. Note your time. I'll review everything.