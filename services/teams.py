"""
Teams service — all business logic for team creation and membership.

The route functions in routers/teams.py only call these functions.
They do not contain any if-statements, DB queries, or business decisions.
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from models import Team, TeamMember, User
from schemas import MemberAdd, TeamCreate


def create_team(db: Session, data: TeamCreate, creator_id: int) -> Team:
    """
    Create a team and automatically add the creator as the first member.

    Why auto-add the creator?
    Domain rule: only team members can add other members or create tasks.
    If the creator weren't added automatically, they'd be locked out of their
    own team immediately after creating it.
    """
    team = Team(name=data.name, creator_id=creator_id)
    db.add(team)
    db.flush()  # get team.id so we can reference it in the membership row

    membership = TeamMember(team_id=team.id, user_id=creator_id)
    db.add(membership)
    db.flush()

    # Re-query with eager loading so the response includes the full members list.
    # Without this, accessing team.members would trigger lazy loads — which
    # can be unreliable once the session is closed or partially committed.
    return _load_team_with_members(db, team.id)


def add_member(db: Session, team_id: int, data: MemberAdd) -> TeamMember:
    """
    Add a user to a team.
    The caller (via the get_team_member dependency) has already verified that
    the requester is a team member — only members can add new members.
    """
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    already_member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == data.user_id)
        .first()
    )
    if already_member:
        raise HTTPException(status_code=400, detail="User is already a member of this team")

    membership = TeamMember(team_id=team_id, user_id=data.user_id)
    db.add(membership)
    db.flush()

    # Reload with user relationship so the response can include user details
    return (
        db.query(TeamMember)
        .options(joinedload(TeamMember.user))
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == data.user_id)
        .first()
    )


def get_team(db: Session, team_id: int) -> Team:
    """Return a team with its full member list, or raise 404."""
    team = _load_team_with_members(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


def get_user_teams(db: Session, user_id: int) -> list[Team]:
    """Return all teams the given user is a member of."""
    return (
        db.query(Team)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .options(joinedload(Team.members).joinedload(TeamMember.user))
        .filter(TeamMember.user_id == user_id)
        .all()
    )


def _load_team_with_members(db: Session, team_id: int):
    """
    Load a team and eagerly fetch members + their user details in one query.

    joinedload tells SQLAlchemy to use a SQL JOIN instead of separate queries.
    This avoids the N+1 problem: without it, SQLAlchemy would issue one query
    per member to load their user details.
    """
    return (
        db.query(Team)
        .options(
            joinedload(Team.members).joinedload(TeamMember.user)
        )
        .filter(Team.id == team_id)
        .first()
    )
