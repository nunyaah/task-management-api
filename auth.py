"""
Password hashing and JWT token utilities.

Why JWT (JSON Web Tokens)?
- The server doesn't need to store sessions. The token itself carries the user ID.
- Every protected request sends the token; we decode it to identify the user.
- If the token is tampered with, the signature check fails and we reject it.

Flow:
  Register → hash password and store hash (never store plain text)
  Login    → verify plain password against stored hash → return signed JWT
  Request  → client sends JWT in Authorization header → we decode it → get user ID
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext

# Read from environment — never hardcode a real secret in source code.
# The default here is only for local dev / tests. Docker Compose overrides it.
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-before-production")
ALGORITHM = "HS256"          # HMAC-SHA256 — symmetric signing
TOKEN_EXPIRE_HOURS = 24

# CryptContext handles bcrypt hashing. 'deprecated="auto"' means old hash
# formats are detected and marked for rehashing (future-proofing).
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plain text password."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if 'plain' matches the stored bcrypt hash."""
    return pwd_context.verify(plain, hashed)


def create_token(user_id: int) -> str:
    """Create a signed JWT containing the user's ID and an expiry timestamp."""
    payload = {
        "sub": str(user_id),  # 'sub' (subject) is the standard JWT claim for user identity
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> int:
    """
    Decode and verify a JWT. Returns the user_id stored in 'sub'.
    Raises HTTP 401 if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token missing subject claim")
        return int(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
