"""
Application entry point.

This file:
1. Creates the FastAPI app instance
2. Registers all routers (which attach their routes to the app)
3. Provides a /health endpoint (used by Docker healthchecks)

Business logic belongs in services/, not here.
HTTP routing belongs in routers/, not here.
This file is just the wiring.
"""

from dotenv import load_dotenv
from fastapi import FastAPI

# Load variables from .env into the process environment.
# Must happen before any other import that reads os.getenv() — so it goes first.
# In Docker Compose, environment variables are already injected by the runtime,
# so load_dotenv() finds nothing new and is harmless there.
load_dotenv()

from routers import auth, tasks, teams

app = FastAPI(
    title="Task Management API",
    description="Teams, members, and tasks with role-based access control.",
    version="1.0.0",
)

# Register each router. FastAPI attaches the router's routes to the app.
# The prefix defined in each router (e.g. "/auth", "/teams") is applied here.
app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(tasks.router)


@app.get("/health", tags=["health"])
def health():
    """
    Health check endpoint.
    Docker Compose and load balancers poll this to know if the app is ready.
    Returns 200 immediately — if the app is running, it's healthy.
    """
    return {"status": "ok"}
