"""Task Manager API — flask-apcore v0.1.0 demo application.

Demonstrates:
- Flask CRUD routes with Pydantic schemas
- Automatic route scanning and annotation inference
- @module decorator for standalone modules
- Observability (tracing, metrics, structured logging)
- MCP server via streamable-http transport
"""
from __future__ import annotations

from flask import Flask
from pydantic import BaseModel

from flask_apcore import Apcore, module


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    done: bool = False


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    done: bool | None = None


class Task(BaseModel):
    id: int
    title: str
    description: str
    done: bool


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

_tasks: dict[int, dict] = {
    1: {"id": 1, "title": "Try flask-apcore", "description": "Run the demo", "done": False},
    2: {"id": 2, "title": "Connect MCP client", "description": "Use Claude Desktop", "done": False},
}
_next_id: int = 3


# ---------------------------------------------------------------------------
# Flask app + config (Apcore init deferred to end of file)
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config.update(
    APCORE_AUTO_DISCOVER=True,
    APCORE_MODULE_DIR="apcore_modules/",
    APCORE_MODULE_PACKAGES=["app"],
    APCORE_SERVE_TRANSPORT="streamable-http",
    APCORE_SERVE_HOST="0.0.0.0",
    APCORE_SERVE_PORT=9100,
    APCORE_SERVER_NAME="task-manager-mcp",
    APCORE_TRACING_ENABLED=True,
    APCORE_TRACING_EXPORTER="stdout",
    APCORE_METRICS_ENABLED=True,
    APCORE_LOGGING_ENABLED=True,
    APCORE_LOGGING_FORMAT="json",
    APCORE_SERVE_VALIDATE_INPUTS=True,
    # Explorer: dev/staging only. Exposes module schemas and execution via HTTP.
    # Do NOT enable in production — there is no auth on these endpoints.
    APCORE_EXPLORER_ENABLED=True,            # browse modules at /apcore/
    APCORE_EXPLORER_ALLOW_EXECUTE=True,      # allow Try-it execution (calls Executor)
)


# ---------------------------------------------------------------------------
# Standalone @module example
# ---------------------------------------------------------------------------

@module(id="task_stats.v1")
def task_stats() -> dict:
    """Return summary statistics about all tasks."""
    total = len(_tasks)
    done = sum(1 for t in _tasks.values() if t["done"])
    return {"total": total, "done": done, "pending": total - done}


# ---------------------------------------------------------------------------
# CRUD routes
# ---------------------------------------------------------------------------

@app.route("/tasks", methods=["GET"])
def list_tasks() -> list[Task]:
    """List all tasks."""
    return [Task(**t) for t in _tasks.values()]


@app.route("/tasks", methods=["POST"])
def create_task(body: TaskCreate) -> Task:
    """Create a new task."""
    global _next_id
    task = {"id": _next_id, "title": body.title, "description": body.description, "done": body.done}
    _tasks[_next_id] = task
    _next_id += 1
    return Task(**task)


@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id: int) -> Task:
    """Get a task by its ID."""
    task = _tasks.get(task_id)
    if task is None:
        return {"error": "not found"}, 404
    return Task(**task)


@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id: int, body: TaskUpdate) -> Task:
    """Update an existing task."""
    task = _tasks.get(task_id)
    if task is None:
        return {"error": "not found"}, 404
    if body.title is not None:
        task["title"] = body.title
    if body.description is not None:
        task["description"] = body.description
    if body.done is not None:
        task["done"] = body.done
    return Task(**task)


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id: int) -> dict:
    """Delete a task permanently."""
    if task_id not in _tasks:
        return {"error": "not found"}, 404
    del _tasks[task_id]
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Initialize Apcore AFTER all routes and @module functions are defined,
# so that auto-discover can resolve binding targets.
# ---------------------------------------------------------------------------

Apcore(app)
