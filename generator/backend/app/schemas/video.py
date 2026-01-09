from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime


class VideoBase(BaseModel):
    title: str
    workflow_mode: Literal["MANUAL", "AUTO"] = "AUTO"
    content_variables: Optional[Dict[str, Any]] = None


class VideoCreate(VideoBase):
    project_id: int


class VideoUpdate(BaseModel):
    title: Optional[str] = None
    workflow_mode: Optional[Literal["MANUAL", "AUTO"]] = None
    content_variables: Optional[Dict[str, Any]] = None


class ProjectBrief(BaseModel):
    """Brief project info for video response"""
    id: int
    name: str
    platforms: List[str]
    duration: int

    model_config = ConfigDict(from_attributes=True)


class WorkflowStepResponse(BaseModel):
    id: int
    video_id: int
    step_type: str
    status: str
    content: Optional[Dict[str, Any]] = None
    user_approved: Optional[bool] = None
    user_feedback: Optional[str] = None
    prompt_used: Optional[str] = None
    generation_time_seconds: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VideoResponse(BaseModel):
    id: int
    project_id: int
    title: str
    workflow_mode: str

    content_variables: Optional[Dict[str, Any]] = None
    story_data: Optional[Dict[str, Any]] = None
    description_data: Optional[Dict[str, Any]] = None
    prompt_data: Optional[Dict[str, Any]] = None
    image_prompt: Optional[str] = None
    image_url: Optional[str] = None
    scenario_data: Optional[Dict[str, Any]] = None
    video_url: Optional[str] = None
    video_task_id: Optional[str] = None
    audio_variants: Optional[List[str]] = None
    video_with_audio_url: Optional[str] = None
    adaptation_data: Optional[Dict[str, Any]] = None

    current_step: str
    status: str

    created_at: datetime
    updated_at: datetime

    workflow_steps: List[WorkflowStepResponse] = []
    project: Optional[ProjectBrief] = None

    model_config = ConfigDict(from_attributes=True)
