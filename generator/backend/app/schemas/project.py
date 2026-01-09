from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    story_template: str
    platforms: List[str]
    duration: int
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"


class ProjectCreate(ProjectBase):
    workspace_id: Optional[int] = None  # If not specified, uses user's first workspace


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    story_template: Optional[str] = None
    platforms: Optional[List[str]] = None
    duration: Optional[int] = None
    aspect_ratio: Optional[Literal["9:16", "16:9", "1:1"]] = None


class ProjectResponse(ProjectBase):
    id: int
    workspace_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
