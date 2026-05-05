"""
Database connection and session management.

The key pattern here is the 'get_db' generator function used as a FastAPI
dependency. It follows the context manager pattern:
  1. Open a session
  2. yield it to the route function
  3. Commit if the route succeeded, rollback if it raised an exception
  4. Always close the session (the 'finally' block)

Tests override 'get_db' entirely via FastAPI's dependency_overrides, swapping
in a SQLite session. The engine created here is never used during testing.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# In Docker Compose: set via the 'environment' block using the service name 'db'.
# In local development: set in .env (loaded by python-dotenv in main.py).
# Tests: dependency_overrides replaces get_db, so this URL is never used.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://appuser:secret@db:5432/taskdb")

engine = create_engine(DATABASE_URL)

# autocommit=False: we control transactions manually (commit in get_db, not automatically)
# autoflush=False: we call db.flush() explicitly when we need the DB to assign IDs
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """
    FastAPI dependency that provides a database session per request.

    'yield' turns this into a generator — FastAPI calls it before the route,
    uses the yielded session, then resumes here after the route finishes.
    This guarantees cleanup even if the route raises an exception.
    """
    db: Session = SessionLocal()
    try:
        yield db          # route function runs here, receiving 'db'
        db.commit()       # only commits if no exception was raised
    except Exception:
        db.rollback()     # undo any partial changes on error
        raise             # re-raise so FastAPI returns the correct error response
    finally:
        db.close()        # always runs — releases the connection back to the pool
