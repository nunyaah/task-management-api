"""
Tasks service — all business logic for task creation, listing, updating, deleting.

The authorization rules enforced here:
- Only a team member can create a task in that team.
  (enforced upstream by the get_team_member dependency, not repeated here)
- Only the task creator OR the assignee can update a task.
- Only the task creator can delete a task.
- Assigning a task to someone who is not a team member is rejected with 400.
"""

from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Task, TeamMember
from schemas import TaskCreate, TaskUpdate

VALID_STATUSES = {"todo", "in_progress", "done"}


def create_task(
    db: Session,
    team_id: int,
    data: TaskCreate,
    creator_id: int,
) -> Task:
    """Create a task in a team. Validates the assignee is a team member if provided."""
    if data.assignee_id is not None:
        _assert_is_team_member(db, team_id, data.assignee_id)

    task = Task(
        title=data.title,
        description=data.description,
        team_id=team_id,
        creator_id=creator_id,
        assignee_id=data.assignee_id,
    )
    db.add(task)
    db.flush()  # get task.id without committing
    return task


def list_tasks(
    db: Session,
    team_id: int,
    status: Optional[str] = None,
    assignee_id: Optional[int] = None,
) -> List[Task]:
    """
    Return all tasks for a team, with optional filters.

    We build the query incrementally: start with all tasks for the team,
    then add WHERE clauses only for the filters the caller provided.
    This avoids duplicating the base query for each filter combination.
    """
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}",
        )

    query = db.query(Task).filter(Task.team_id == team_id)

    if status is not None:
        query = query.filter(Task.status == status)

    if assignee_id is not None:
        query = query.filter(Task.assignee_id == assignee_id)

    return query.all()


def update_task(
    db: Session,
    task_id: int,
    data: TaskUpdate,
    current_user_id: int,
) -> Task:
    """
    Update a task. Only the creator or current assignee may do this.

    We apply each field only if the caller supplied it (PATCH semantics).
    If a field is None in the request body, we leave the existing value alone.
    """
    task = _get_task_or_404(db, task_id)

    if task.creator_id != current_user_id and task.assignee_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the task creator or assignee can update this task",
        )

    if data.title is not None:
        task.title = data.title

    if data.description is not None:
        task.description = data.description

    if data.status is not None:
        if data.status not in VALID_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{data.status}'. Must be one of: {', '.join(VALID_STATUSES)}",
            )
        task.status = data.status

    if data.assignee_id is not None:
        # Even when updating, the new assignee must be a team member
        _assert_is_team_member(db, task.team_id, data.assignee_id)
        task.assignee_id = data.assignee_id

    # SQLAlchemy tracks which attributes changed. db.flush() sends the UPDATE
    # to the DB. The onupdate=_utcnow on the model column updates updated_at.
    db.flush()
    return task


def delete_task(db: Session, task_id: int, current_user_id: int) -> None:
    """Delete a task. Only the creator may do this."""
    task = _get_task_or_404(db, task_id)

    if task.creator_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the task creator can delete this task",
        )

    db.delete(task)


def _get_task_or_404(db: Session, task_id: int) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _assert_is_team_member(db: Session, team_id: int, user_id: int) -> None:
    """Raise HTTP 400 if user_id is not a member of team_id."""
    membership = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=400,
            detail="Assignee is not a member of this team",
        )
