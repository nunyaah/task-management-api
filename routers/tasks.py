"""
Tasks router — HTTP layer for task endpoints.

Task routes span two different path prefixes:
  /teams/{team_id}/tasks  — list and create tasks within a team
  /tasks/{task_id}        — update or delete a specific task

Because of this, we don't set a prefix on this router. We write the full
path in each decorator instead.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import services.tasks as tasks_service
from database import get_db
from dependencies import get_current_user, get_team_member
from models import User
from schemas import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(tags=["tasks"])


@router.post("/teams/{team_id}/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    team_id: int,
    body: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_team_member),  # enforces team membership
):
    """Create a task in a team. Must be a team member."""
    return tasks_service.create_task(db, team_id, body, current_user.id)


@router.get("/teams/{team_id}/tasks", response_model=List[TaskResponse])
def list_tasks(
    team_id: int,
    status: Optional[str] = None,       # ?status=todo
    assignee_id: Optional[int] = None,  # ?assignee_id=5
    db: Session = Depends(get_db),
    current_user: User = Depends(get_team_member),  # enforces team membership
):
    """
    List tasks for a team. Must be a team member.
    Supports optional query param filters: ?status=todo and ?assignee_id=5
    """
    return tasks_service.list_tasks(db, team_id, status, assignee_id)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    body: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Partially update a task (PATCH = only the fields you send are changed).
    Must be the task creator or the current assignee.
    Auth is via get_current_user; the ownership check is in the service layer.
    """
    return tasks_service.update_task(db, task_id, body, current_user.id)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a task. Only the task creator can do this.
    Returns 204 No Content on success — no body, just the status code.
    """
    tasks_service.delete_task(db, task_id, current_user.id)
    # Returning None with status_code=204 gives an empty response — correct for DELETE
