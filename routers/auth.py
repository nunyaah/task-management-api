"""
Auth router — HTTP layer for registration and login.

Route functions here do exactly three things:
1. Receive the parsed/validated request body (Pydantic handles validation)
2. Call the service function with the data
3. Return the result (FastAPI serializes it using response_model)

No business logic lives here.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import services.auth as auth_service
from database import get_db
from dependencies import get_current_user
from models import User
from schemas import LoginRequest, TokenResponse, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user. Returns the user without the password.

    response_model=UserResponse is what strips the password field —
    FastAPI only includes fields declared in UserResponse when serializing.
    status_code=201 because we're creating a new resource.
    """
    return auth_service.register_user(db, body)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and return a JWT bearer token."""
    return auth_service.login_user(db, body)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user
