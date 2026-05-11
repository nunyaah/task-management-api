"""
Pydantic schemas — the shape of data coming IN and going OUT of our API.

Separate from SQLAlchemy models on purpose:
- SQLAlchemy models describe what the DB stores.
- Pydantic schemas describe what the API accepts and returns.
- Keeping them separate lets us control exactly what data crosses the HTTP boundary.
  (e.g. we never return the hashed password, even though it's in the DB model)

'from_attributes = True' in model_config tells Pydantic it can read data from
ORM objects (like a SQLAlchemy User row), not just from plain dicts.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr

# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    """What the client sends when registering."""
    name: str
    email: EmailStr   # Pydantic validates the email format automatically
    password: str


class UserResponse(BaseModel):
    """What we send back — note: no 'password' field here.
    FastAPI strips any field not declared in the response_model schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime


class LoginRequest(BaseModel):
    """What the client sends when logging in."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """What we return after a successful login."""
    access_token: str
    token_type: str = "bearer"


# ── Teams ─────────────────────────────────────────────────────────────────────

class TeamCreate(BaseModel):
    name: str


class MemberAdd(BaseModel):
    """Request body when adding a user to a team."""
    user_id: int


class TeamMemberResponse(BaseModel):
    """A single row from team_members, with the user's details nested in."""
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    joined_at: datetime
    user: UserResponse   # nested — FastAPI serializes this from the relationship


class TeamResponse(BaseModel):
    """Full team detail: metadata + the list of current members."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    creator_id: int
    created_at: datetime
    members: List[TeamMemberResponse]


# ── Tasks ─────────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int] = None  # optional at creation time


class TaskUpdate(BaseModel):
    """All fields optional — only supplied fields are changed (PATCH semantics)."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[int] = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str]
    status: str
    team_id: int
    creator_id: int
    assignee_id: Optional[int]
    created_at: datetime
    updated_at: datetime
