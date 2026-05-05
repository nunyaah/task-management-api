"""
API integration tests — all 8 required test cases.

Key decisions:
- We use SQLite (in-memory via a file) instead of real PostgreSQL.
  This means no DB setup/teardown between CI runs.
- We use FastAPI's dependency_overrides to swap the production get_db
  (which talks to PostgreSQL) for a test version (which talks to SQLite).
  No mocking library is needed — FastAPI gives us this mechanism for free.
- Each test gets a fresh database via the reset_db fixture (autouse=True),
  so tests are fully isolated and can't interfere with each other.

How dependency_overrides works:
  app.dependency_overrides[get_db] = override_get_db
  This tells FastAPI: "whenever a route or dependency asks for get_db,
  call override_get_db instead." The entire dependency chain
  (get_current_user → get_db, get_team_member → get_db, etc.) automatically
  uses the test DB because they all ultimately depend on get_db.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import get_db
from main import app
from models import Base

# SQLite for tests — no PostgreSQL required, no external process to manage.
# connect_args: SQLite by default only allows one thread. We disable that check
# because FastAPI's TestClient may use the connection from different threads.
SQLITE_URL = "sqlite:///./test.db"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    """Test replacement for the production get_db dependency."""
    db = TestingSession()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Swap the real DB for the test DB for the entire test module.
# This affects every route and every dependency in the chain.
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_db():
    """
    Create all tables before each test, drop them after.
    autouse=True means this runs for every test automatically —
    no need to explicitly include it in each test function signature.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ── Helper functions ───────────────────────────────────────────────────────────
# These reduce repetition in tests. Each helper is a thin wrapper around the
# API call, returning only the data we care about.

def register(name: str, email: str, password: str = "password123") -> dict:
    r = client.post("/auth/register", json={"name": name, "email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()


def login(email: str, password: str = "password123") -> str:
    """Returns just the bearer token string."""
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth_headers(token: str) -> dict:
    """Format the token as an Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}


def create_team(token: str, name: str = "Test Team") -> dict:
    r = client.post("/teams", json={"name": name}, headers=auth_headers(token))
    assert r.status_code == 201, r.text
    return r.json()


def add_member(token: str, team_id: int, user_id: int) -> dict:
    r = client.post(
        f"/teams/{team_id}/members",
        json={"user_id": user_id},
        headers=auth_headers(token),
    )
    return r  # return the full response so callers can check the status code


def create_task(token: str, team_id: int, title: str = "Test Task", assignee_id=None) -> dict:
    body = {"title": title}
    if assignee_id is not None:
        body["assignee_id"] = assignee_id
    r = client.post(f"/teams/{team_id}/tasks", json=body, headers=auth_headers(token))
    return r  # return full response so callers can check status code


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_register_returns_201_without_password():
    """
    Test 1: Registering a user returns 201 and the response must NOT include
    the password (not even the hash — that would be a security leak).
    """
    response = client.post(
        "/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "secret123"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["name"] == "Alice"
    assert "id" in data
    # This is the core security check — password must never appear in the response
    assert "password" not in data


def test_login_returns_token():
    """
    Test 2: Logging in with valid credentials returns a JWT bearer token.
    The token must be a non-empty string.
    """
    client.post(
        "/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "secret123"},
    )

    response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "secret123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0
    assert data["token_type"] == "bearer"


def test_create_team_creator_is_in_member_list():
    """
    Test 3: Creating a team automatically adds the creator as a member.
    The response should include the creator in the members array.
    """
    alice = register("Alice", "alice@example.com")
    token = login("alice@example.com")

    response = client.post(
        "/teams",
        json={"name": "Team Alpha"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Team Alpha"

    member_user_ids = [m["user_id"] for m in data["members"]]
    # Alice (the creator) must be in the member list
    assert alice["id"] in member_user_ids


def test_add_member_as_non_member_returns_403():
    """
    Test 4: A user who is not a team member cannot add members to that team.
    Expecting 403 Forbidden.
    """
    alice = register("Alice", "alice@example.com")
    alice_token = login("alice@example.com")

    bob = register("Bob", "bob@example.com")
    bob_token = login("bob@example.com")

    # Alice creates a team (Bob is NOT a member)
    team = create_team(alice_token, "Alice's Team")

    # Charlie is a third user we want Bob to try adding
    charlie = register("Charlie", "charlie@example.com")

    # Bob tries to add Charlie — he should be rejected because he's not in the team
    response = add_member(bob_token, team["id"], charlie["id"])
    assert response.status_code == 403


def test_create_task_as_non_member_returns_403():
    """
    Test 5: A user who is not a team member cannot create tasks in that team.
    Expecting 403 Forbidden.
    """
    register("Alice", "alice@example.com")
    alice_token = login("alice@example.com")

    register("Bob", "bob@example.com")
    bob_token = login("bob@example.com")

    # Alice creates a team (Bob is not a member)
    team = create_team(alice_token)

    # Bob tries to create a task in Alice's team
    response = create_task(bob_token, team["id"], "Bob's Task")
    assert response.status_code == 403


def test_assign_task_to_non_member_returns_400():
    """
    Test 6: Assigning a task to someone who is not a team member must be rejected.
    Expecting 400 Bad Request (domain rule violation, not an auth error).
    """
    register("Alice", "alice@example.com")
    alice_token = login("alice@example.com")

    # Bob is registered but NOT added to Alice's team
    bob = register("Bob", "bob@example.com")

    team = create_team(alice_token)

    # Alice tries to assign a task to Bob, but Bob is not a team member
    response = create_task(alice_token, team["id"], "Task for Bob", assignee_id=bob["id"])
    assert response.status_code == 400


def test_update_task_as_unrelated_user_returns_403():
    """
    Test 7: A user who is neither the task creator nor the assignee cannot update the task.
    Expecting 403 Forbidden.

    Setup: Alice and Bob are both team members. Alice creates a task (not assigned to Bob).
    Bob tries to update it — he should be rejected.
    """
    alice = register("Alice", "alice@example.com")
    alice_token = login("alice@example.com")

    bob = register("Bob", "bob@example.com")
    bob_token = login("bob@example.com")

    team = create_team(alice_token)

    # Add Bob as a team member (so the 403 isn't just from non-membership)
    add_member(alice_token, team["id"], bob["id"])

    # Alice creates a task — not assigned to Bob
    task_response = create_task(alice_token, team["id"], "Alice's Task")
    assert task_response.status_code == 201
    task = task_response.json()

    # Bob (team member, but not creator or assignee) tries to update the task
    response = client.patch(
        f"/tasks/{task['id']}",
        json={"title": "Bob's hijacked title"},
        headers=auth_headers(bob_token),
    )
    assert response.status_code == 403


def test_filter_tasks_by_status_returns_only_matching():
    """
    Test 8: The ?status= query parameter filters tasks correctly.
    Only tasks with the requested status should be returned.
    """
    register("Alice", "alice@example.com")
    alice_token = login("alice@example.com")
    team = create_team(alice_token)

    # Create three tasks
    t1 = create_task(alice_token, team["id"], "Todo task").json()
    t2 = create_task(alice_token, team["id"], "In progress task").json()
    t3 = create_task(alice_token, team["id"], "Done task").json()

    # Move t2 to in_progress and t3 to done
    alice_token_h = auth_headers(alice_token)
    client.patch(f"/tasks/{t2['id']}", json={"status": "in_progress"}, headers=alice_token_h)
    client.patch(f"/tasks/{t3['id']}", json={"status": "done"}, headers=alice_token_h)

    # Filter for only 'todo' tasks
    response = client.get(
        f"/teams/{team['id']}/tasks?status=todo",
        headers=alice_token_h,
    )
    assert response.status_code == 200
    tasks = response.json()

    # Only t1 should appear
    assert len(tasks) == 1
    assert tasks[0]["id"] == t1["id"]
    assert tasks[0]["status"] == "todo"

    # Sanity check: filter for 'done' returns only t3
    response_done = client.get(
        f"/teams/{team['id']}/tasks?status=done",
        headers=alice_token_h,
    )
    assert len(response_done.json()) == 1
    assert response_done.json()[0]["id"] == t3["id"]
