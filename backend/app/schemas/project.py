from pydantic import BaseModel, ConfigDict, model_validator
from typing import Optional, List, Literal, Dict
from datetime import datetime

# Audio mode options
AudioMode = Literal["none", "scene", "music", "voiceover", "auto"]

# Audio provider options
AudioProvider = Literal["kling", "ai_music"]

# Project type options
ProjectType = Literal["discover", "remix"]

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
    story_template: str  # Image prompt template with {placeholders}
    motion_template: Optional[str] = None  # Motion prompt template with {placeholders} (for remix)
    platforms: List[str]
    duration: int
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    audio_mode: AudioMode = "auto"
    audio_provider: Optional[AudioProvider] = None  # None = use default for audio_mode
    project_type: ProjectType = "discover"
    require_image_approval: bool = False  # Pause after image for approval
    system_prompts: Optional[Dict[str, str]] = None

    # Remix-specific fields (optional for discover projects)
    source_video_ids: Optional[List[int]] = None  # Discover videos used as basis
    scenario_template: Optional[Dict[str, str]] = None  # Legacy: Template for video motion
    placeholders: Optional[List[str]] = None  # ["dress_color", "car_model"]
    placeholder_suggestions: Optional[Dict[str, List[str]]] = None  # {dress_color: ["red", "blue"]}

    @model_validator(mode="after")
    def validate_audio_provider(self):
        """Validate that audio_provider is valid for audio_mode."""
        if self.audio_provider:
            from app.core.audio_config import is_valid_combination

            if not is_valid_combination(self.audio_mode, self.audio_provider):
                raise ValueError(
                    f"audio_provider '{self.audio_provider}' is not valid for audio_mode '{self.audio_mode}'"
                )
        return self


class ProjectCreate(ProjectBase):
    workspace_id: Optional[int] = None  # If not specified, uses user's first workspace


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    story_template: Optional[str] = None
    motion_template: Optional[str] = None  # Motion prompt template (for remix)
    platforms: Optional[List[str]] = None
    duration: Optional[int] = None
    aspect_ratio: Optional[Literal["9:16", "16:9", "1:1"]] = None
    audio_mode: Optional[AudioMode] = None
    audio_provider: Optional[AudioProvider] = None
    project_type: Optional[ProjectType] = None
    require_image_approval: Optional[bool] = None
    system_prompts: Optional[Dict[str, str]] = None

    # Remix-specific fields
    source_video_ids: Optional[List[int]] = None
    scenario_template: Optional[Dict[str, str]] = None  # Legacy
    placeholders: Optional[List[str]] = None
    placeholder_suggestions: Optional[Dict[str, List[str]]] = None


class ProjectResponse(ProjectBase):
    id: int
    workspace_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
