"""Pydantic schemas for Discover workflow."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum


# --- Enums ---

class SelectionValue(str, Enum):
    SELECTED = "selected"
    REJECTED = "rejected"


# --- Create ---

class DiscoverProjectCreate(BaseModel):
    concept: str = Field(..., min_length=10, max_length=2000)
    name: str = Field(..., min_length=1, max_length=255)
    workspace_id: int
    image_model: str = "fal-ai/flux-pro/v1.1"
    video_model: str = "fal-ai/veo3/fast/image-to-video"
    image_aspect_ratio: str = "9:16"
    video_duration: str = "6s"


# --- Responses ---

class DiscoverItemResponse(BaseModel):
    id: int
    position: int
    prompt: str
    source_image_item_id: Optional[int] = None
    status: str
    result_url: Optional[str] = None
    local_path: Optional[str] = None
    error_message: Optional[str] = None
    selection: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DiscoverRoundResponse(BaseModel):
    id: int
    round_number: int
    round_type: str
    status: str
    error_message: Optional[str] = None
    feedback_text: Optional[str] = None
    total_items: int
    selected_count: int
    rejected_count: int
    items: List[DiscoverItemResponse] = []
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DiscoverExtractionResponse(BaseModel):
    id: int
    winning_image_prompt: str
    winning_video_prompt: Optional[str] = None
    base_prompt: str
    variation_prompt: str
    video_template_prompt: Optional[str] = None
    slot_names: Optional[List[str]] = None
    slot_examples: Optional[Dict[str, List[str]]] = None
    edited_base_prompt: Optional[str] = None
    edited_variation_prompt: Optional[str] = None
    edited_video_template_prompt: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscoverProjectResponse(BaseModel):
    id: int
    concept: str
    name: str
    stage: str
    status: str
    current_image_round: int
    current_video_round: int
    image_model: str
    video_model: str
    image_aspect_ratio: str
    video_duration: str
    finalist_image_item_id: Optional[int] = None
    finalist_video_item_id: Optional[int] = None
    created_project_id: Optional[int] = None
    rounds: List[DiscoverRoundResponse] = []
    extraction: Optional[DiscoverExtractionResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscoverProjectListResponse(BaseModel):
    projects: List[DiscoverProjectResponse]
    total: int


# --- Requests ---

class GenerateRoundRequest(BaseModel):
    feedback: Optional[str] = None
    model: Optional[str] = None  # override image/video model for this round
    count: Optional[int] = Field(None, ge=1, le=7)  # number of items (1-7)


class SelectionRequest(BaseModel):
    selections: Dict[str, SelectionValue]  # item_id -> "selected" | "rejected"
    feedback: Optional[str] = None


class SelectionResponse(BaseModel):
    round_id: int
    selected_count: int
    rejected_count: int
    can_advance_to_video: bool
    can_generate_next_round: bool


class AdvanceRequest(BaseModel):
    finalist_image_item_id: int


class AdvanceExtractionRequest(BaseModel):
    finalist_video_item_id: int


class ExtractionUpdateRequest(BaseModel):
    edited_base_prompt: Optional[str] = None
    edited_variation_prompt: Optional[str] = None


class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    platforms: List[str] = ["youtube"]
    video_template_prompt: str


# --- Refinement ---

class RefinementBlockSchema(BaseModel):
    value: Optional[str] = None
    status: str  # auto_filled | needs_input | auto_generated | confirmed
    source: Optional[str] = None  # parsed | llm | user | settings
    question: Optional[str] = None
    options: Optional[List[str]] = None


class RefinementResponse(BaseModel):
    refinement_id: int
    original_concept: str
    score: int
    relevant_blocks: List[str]
    blocks: Dict[str, RefinementBlockSchema]
    refined_prompt: Optional[str] = None
    ready_to_generate: bool


class BlockUpdateRequest(BaseModel):
    block_name: str = Field(
        ...,
        pattern=r'^(subject|action|moment|environment|camera|lighting|style|details)$',
    )
    value: str = Field(..., min_length=1)


class PromptUpdateRequest(BaseModel):
    refined_prompt: str = Field(..., min_length=10)


class CompileResponse(BaseModel):
    refined_prompt: str
    score: int
    ready_to_generate: bool
