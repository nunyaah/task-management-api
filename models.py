"""
SQLAlchemy ORM models — the Python representation of our database tables.

Each class maps to a table. Column types here should match init.sql.
The 'Base' object is shared across the whole app so SQLAlchemy knows
all models when creating/dropping tables (used in tests).
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    """Return the current UTC time. Used as a Python-side column default.

    Why a function instead of datetime.utcnow directly?
    - datetime.utcnow is deprecated in Python 3.12+
    - SQLAlchemy needs a callable (it calls it each time), not a fixed value
    """
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String, nullable=False)
    # index=True on email because we look users up by email on every login
    email      = Column(String, nullable=False, unique=True, index=True)
    password   = Column(String, nullable=False)  # bcrypt hash
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships let us do `user.created_teams` in Python without extra queries
    # (SQLAlchemy lazy-loads them on first access).
    created_teams    = relationship("Team", back_populates="creator")
    team_memberships = relationship("TeamMember", back_populates="user")
    # Two FK columns on Task both point to User, so we must tell SQLAlchemy
    # which FK each relationship uses via foreign_keys=[].
    created_tasks  = relationship(
        "Task", foreign_keys="Task.creator_id", back_populates="creator"
    )
    assigned_tasks = relationship(
        "Task", foreign_keys="Task.assignee_id", back_populates="assignee"
    )


class Team(Base):
    __tablename__ = "teams"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String, nullable=False)
    creator_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,  # manual index — see init.sql comment
    )
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    creator = relationship("User", back_populates="created_teams")
    members = relationship("TeamMember", back_populates="team")
    tasks   = relationship("Task", back_populates="team")


class TeamMember(Base):
    __tablename__ = "team_members"

    # Composite primary key — same as the composite PK in init.sql.
    # This is how SQLAlchemy knows the table has no surrogate id column.
    team_id   = Column(
        Integer,
        ForeignKey("teams.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id   = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,  # manual index so "teams for user X" queries are fast
    )
    joined_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")


class Task(Base):
    __tablename__ = "tasks"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status      = Column(String, nullable=False, default="todo")
    team_id     = Column(
        Integer,
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_id  = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assignee_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    # onupdate=_utcnow: SQLAlchemy automatically includes this column in every
    # UPDATE statement, setting it to now(). The DB trigger in init.sql does
    # the same thing server-side — they're redundant but both correct.
    updated_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    team     = relationship("Team", back_populates="tasks")
    creator  = relationship(
        "User", foreign_keys=[creator_id], back_populates="created_tasks"
    )
    assignee = relationship(
        "User", foreign_keys=[assignee_id], back_populates="assigned_tasks"
    )
