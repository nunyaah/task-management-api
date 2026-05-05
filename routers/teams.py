"""
Teams router — HTTP layer for team and membership endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import services.teams as teams_service
from database import get_db
from dependencies import get_current_user, get_team_member
from models import User
from schemas import MemberAdd, TeamCreate, TeamMemberResponse, TeamResponse

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("", response_model=TeamResponse, status_code=201)
def create_team(
    body: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a team. The authenticated user becomes the creator and first member.
    Auth required — Depends(get_current_user) raises 401 if no valid token.
    """
    return teams_service.create_team(db, body, current_user.id)


@router.post("/{team_id}/members", response_model=TeamMemberResponse, status_code=201)
def add_member(
    team_id: int,
    body: MemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_team_member),  # raises 403 if not a member
):
    """
    Add a user to a team. Only existing team members can do this.

    get_team_member receives team_id from the URL path automatically —
    FastAPI sees it's declared as a regular int parameter (not Depends()),
    so it extracts it from the path, just like it would in a route function.
    """
    return teams_service.add_member(db, team_id, body)


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_team_member),  # raises 403 if not a member
):
    """Get a team's details and member list. Only team members can view it."""
    return teams_service.get_team(db, team_id)
