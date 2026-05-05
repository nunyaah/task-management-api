"""
FastAPI dependencies — reusable building blocks that are injected into routes.

The chain here is:
  get_db                  → opens a DB session
    └─ get_current_user   → decodes JWT, returns authenticated User
         └─ get_team_member → verifies the user is a member of a specific team

Each layer builds on the previous one. FastAPI resolves the full chain before
calling the route function, and caches each result so get_db is only called once
per request (even if multiple dependencies depend on it).

Why put this in a separate file?
- Routes import from here; separating it avoids circular imports.
- It keeps auth logic out of both the route files and the service files.
"""

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from auth import decode_token
from database import get_db
from models import TeamMember, User

# OAuth2PasswordBearer tells FastAPI:
# "Expect an Authorization: Bearer <token> header on protected routes."
# tokenUrl is where clients get a token — shown in the /docs UI.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency: decode the JWT and return the authenticated user.

    FastAPI automatically extracts the Bearer token from the Authorization header
    via the OAuth2PasswordBearer scheme, then injects it here as 'token'.
    """
    user_id = decode_token(token)  # raises 401 if token is bad
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user


def get_team_member(
    team_id: int,  # FastAPI reads this from the route path (e.g. /teams/{team_id}/...)
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency: verify the authenticated user is a member of the given team.

    Used on routes where you must be a team member to proceed.
    Returns the current user so the route can use it directly.

    'team_id' here is a path parameter. FastAPI sees it isn't wrapped in Depends(),
    so it treats it as a regular parameter and injects it from the URL path —
    the same way it would for a route function parameter.
    """
    membership = (
        db.query(TeamMember)
        .filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this team",
        )
    return current_user
