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
from fastapi.middleware.cors import CORSMiddleware

# load_dotenv must run before any import that reads os.getenv()
load_dotenv()

from routers import auth, tasks, teams

app = FastAPI(
    title="Task Management API",
    description="Teams, members, and tasks with role-based access control.",
    version="1.0.0",
)

# CORS: allow the Next.js dev server to call this API from the browser.
# Without this, the browser blocks every request with "CORS policy" error.
# In production, replace localhost:3000 with your real frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
