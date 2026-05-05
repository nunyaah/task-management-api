"""
Auth service — business logic for registration and login.

Why a service layer instead of putting this in the router?
- Routers should only handle HTTP concerns: parse the request, call a service,
  return the response. They should not contain business logic.
- Services contain the actual decisions: "does this email already exist?",
  "is this password correct?". This makes logic testable in isolation.
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from auth import create_token, hash_password, verify_password
from models import User
from schemas import LoginRequest, TokenResponse, UserCreate


def register_user(db: Session, data: UserCreate) -> User:
    """
    Create a new user. Raises 400 if the email is already registered.
    Returns the User ORM object (the router maps it to UserResponse, which
    strips the password field automatically).
    """
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        password=hash_password(data.password),  # NEVER store plain text
    )
    db.add(user)
    # flush() sends the INSERT to the DB and gets back the generated id,
    # but keeps it inside the current transaction (no commit yet).
    # The get_db dependency commits after the route returns successfully.
    db.flush()
    return user


def login_user(db: Session, data: LoginRequest) -> TokenResponse:
    """
    Verify credentials and return a JWT token.
    We return the same vague error for both "user not found" and "wrong password"
    — this prevents user enumeration attacks (telling an attacker which emails exist).
    """
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return TokenResponse(access_token=create_token(user.id))
