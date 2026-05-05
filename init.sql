-- =============================================================================
-- Task Management API — PostgreSQL Schema
-- =============================================================================
-- Run once at first container start (mounted into docker-entrypoint-initdb.d/).
-- =============================================================================

-- ── Users ─────────────────────────────────────────────────────────────────────
-- Stores everyone who can log in. email is the natural login identifier,
-- so it needs a UNIQUE constraint enforced at the DB level (not just Python).
-- We store the bcrypt hash in 'password', never the plain text.

CREATE TABLE users (
    id         SERIAL      PRIMARY KEY,
    name       TEXT        NOT NULL,
    email      TEXT        NOT NULL UNIQUE,
    password   TEXT        NOT NULL,                 -- bcrypt hash
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- No manual index on id — PRIMARY KEY auto-creates one.
-- No manual index on email — UNIQUE auto-creates one.

-- ── Teams ─────────────────────────────────────────────────────────────────────
-- A team has a creator (the user who created it).
-- ON DELETE RESTRICT on creator_id: we never want a team to silently lose its
-- creator reference. If you want to delete a user who created teams, you must
-- reassign or delete those teams first. RESTRICT makes this an explicit decision.

CREATE TABLE teams (
    id         SERIAL      PRIMARY KEY,
    name       TEXT        NOT NULL,
    creator_id INTEGER     NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- PostgreSQL does NOT auto-index foreign keys. Without this index, any query
-- that filters or joins on creator_id (e.g. "find all teams by this user")
-- does a full table scan. We add it manually.
CREATE INDEX idx_teams_creator_id ON teams(creator_id);

-- ── Team Members ──────────────────────────────────────────────────────────────
-- Many-to-many junction table: a user can be in many teams, a team has many users.
-- The composite PRIMARY KEY (team_id, user_id) does two things at once:
--   1. Prevents the same user from being added to the same team twice.
--   2. Creates a composite index that makes "is user X in team Y?" lookups fast.
--
-- ON DELETE CASCADE on team_id: if a team is deleted, all its memberships go
--   with it. A membership without a team makes no sense.
-- ON DELETE CASCADE on user_id: if a user is deleted, their memberships go
--   with them. A membership without a user makes no sense.

CREATE TABLE team_members (
    team_id   INTEGER     NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id   INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (team_id, user_id)
);

-- The composite PK already covers searches starting with team_id.
-- We add a separate index on user_id alone so "which teams does user X belong to?"
-- is also fast (the composite PK index won't help for that query).
CREATE INDEX idx_team_members_user_id ON team_members(user_id);

-- ── Tasks ─────────────────────────────────────────────────────────────────────
-- A task belongs to a team, has a creator, and optionally an assignee.
--
-- ON DELETE CASCADE on team_id: if a team is deleted, all its tasks go with it.
--   A task without a team is meaningless.
-- ON DELETE RESTRICT on creator_id: we keep task records for audit/history even
--   if the creator leaves. But we require an explicit decision — you must handle
--   the task before deleting the creator. RESTRICT enforces that.
-- ON DELETE SET NULL on assignee_id: if the assignee's account is deleted, the
--   task stays but becomes unassigned. This is the least disruptive option —
--   the task still exists and can be reassigned. NULL is a valid state for assignee.
--
-- CHECK constraint on status: the DB is the last line of defense. Even if Python
-- has a bug that writes a bad status, the DB will reject it outright.

CREATE TABLE tasks (
    id          SERIAL      PRIMARY KEY,
    title       TEXT        NOT NULL,
    description TEXT,                                -- optional, so no NOT NULL
    status      TEXT        NOT NULL DEFAULT 'todo'
                    CHECK (status IN ('todo', 'in_progress', 'done')),
    team_id     INTEGER     NOT NULL REFERENCES teams(id)  ON DELETE CASCADE,
    creator_id  INTEGER     NOT NULL REFERENCES users(id)  ON DELETE RESTRICT,
    assignee_id INTEGER              REFERENCES users(id)  ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Every FK column needs a manual index. These are the join/filter columns.
CREATE INDEX idx_tasks_team_id     ON tasks(team_id);
CREATE INDEX idx_tasks_creator_id  ON tasks(creator_id);
CREATE INDEX idx_tasks_assignee_id ON tasks(assignee_id);

-- ── Auto-update trigger for tasks.updated_at ──────────────────────────────────
-- We put this at the DB level so it fires regardless of which application,
-- script, or admin tool modifies the row. A Python-only solution would miss
-- direct SQL updates.

CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    -- NEW is the row being written. We overwrite updated_at before the row is saved.
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION fn_set_updated_at();
