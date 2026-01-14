"""
TaskTracker schemas for API responses.
Used primarily for 409 Conflict responses when task is already running.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, Literal
from datetime import datetime


class TaskTrackerResponse(BaseModel):
    """Response for task status queries and 409 responses."""
    id: int
    video_id: int
    step_type: str
    provider: str
    external_task_id: Optional[str] = None
    status: Literal["pending", "running", "completed", "failed"]
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TaskRunningResponse(BaseModel):
    """409 Conflict response when task is already running."""
    task_id: int
    status: Literal["running"] = "running"
    message: str = "Task already running"
