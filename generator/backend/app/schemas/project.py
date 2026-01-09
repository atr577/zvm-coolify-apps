from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Literal, Dict
from datetime import datetime

# Audio mode options
AudioMode = Literal["none", "scene", "music", "voiceover", "auto"]

# System prompts for each workflow step
class SystemPrompts(BaseModel):
    story: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    scenario: Optional[str] = None
    adaptation: Optional[str] = None


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    story_template: str
    platforms: List[str]
    duration: int
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    audio_mode: AudioMode = "auto"
    system_prompts: Optional[Dict[str, str]] = None


class ProjectCreate(ProjectBase):
    workspace_id: Optional[int] = None  # If not specified, uses user's first workspace


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    story_template: Optional[str] = None
    platforms: Optional[List[str]] = None
    duration: Optional[int] = None
    aspect_ratio: Optional[Literal["9:16", "16:9", "1:1"]] = None
    audio_mode: Optional[AudioMode] = None
    system_prompts: Optional[Dict[str, str]] = None


class ProjectResponse(ProjectBase):
    id: int
    workspace_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
