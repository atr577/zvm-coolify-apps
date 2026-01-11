"""
Workflow schemas for 4-step video generation pipeline.

SCENARIO → IMAGE → VIDEO → AUDIO
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class StepTypeEnum(str, Enum):
    """Valid workflow steps."""
    SCENARIO = "scenario"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class CustomPrompt(BaseModel):
    """Custom prompt provided by user."""
    system_prompt: str
    user_prompt: str


# Request schemas for specific endpoints

class GenerateImageRequest(BaseModel):
    """Request to generate image step."""
    video_id: int
    prompt: Optional[str] = None
    aspect_ratio: str = Field(default="9:16", pattern="^(16:9|9:16|1:1)$")


class GenerateVideoRequest(BaseModel):
    """Request to generate video step."""
    video_id: int
    duration: int = Field(default=5, ge=5, le=10)


class GenerateAudioRequest(BaseModel):
    """Request to generate audio step."""
    video_id: int


class SelectAudioVariantRequest(BaseModel):
    """Request to select audio variant."""
    video_id: int
    variant_index: int = Field(..., ge=0, le=3)


# Prompt preview (kept for backwards compatibility)

class PreviewPromptRequest(BaseModel):
    """Request to preview prompt before generation."""
    video_id: int
    step_type: StepTypeEnum
    context: Optional[Dict[str, Any]] = None


class PreviewPromptResponse(BaseModel):
    """Response with prompt preview."""
    system_prompt: str
    user_prompt: str
    step_type: str
    can_edit: bool = True
