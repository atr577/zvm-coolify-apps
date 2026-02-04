"""Pydantic schemas for video moderation."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# --- Enums ---

class ApprovedGenerationStatus(str, Enum):
    APPROVED = "approved"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    PARTIALLY_PUBLISHED = "partially_published"
    FAILED = "failed"


# --- Moderation Queue Schemas ---

class ModerationQueueItem(BaseModel):
    """Item in the moderation queue (completed TemplateGeneration)."""
    id: int
    variant: Optional[Dict[str, Any]] = None  # {id, data}
    video_template: Optional[Dict[str, Any]] = None  # {id, name}
    preprocessing_result: Optional[Dict[str, Any]] = None
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    publishing_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ModerationQueueResponse(BaseModel):
    """Response for moderation queue list."""
    items: List[ModerationQueueItem]
    total: int


# --- Approved Generation Schemas ---

class PlatformMetadata(BaseModel):
    """Metadata for a single platform."""
    title: str
    description: str
    hashtags: Optional[str] = None


class ApprovedGenerationResponse(BaseModel):
    """Response for an approved generation."""
    id: int
    project_id: int
    template_generation_id: int
    position: int
    approved_at: datetime
    publishing_metadata: Optional[Dict[str, PlatformMetadata]] = None
    status: ApprovedGenerationStatus
    platform_statuses: Optional[Dict[str, str]] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Enriched data from template_generation
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ApproveRequest(BaseModel):
    """Optional request body for approve (with pre-edited metadata)."""
    publishing_metadata: Optional[Dict[str, PlatformMetadata]] = None


class ApproveResponse(BaseModel):
    """Response for approve action."""
    approved_generation: ApprovedGenerationResponse


# --- Pre-generate Metadata Schemas ---

class PreGenerateMetadataResponse(BaseModel):
    """Response for pre-generate metadata (without approving)."""
    metadata: Dict[str, PlatformMetadata]


# --- Rejection Schemas ---

class RejectRequest(BaseModel):
    """Request body for rejecting a generation."""
    reason: str = Field(..., min_length=1, max_length=255)
    comment: Optional[str] = Field(None, max_length=1000)


class RejectionResponse(BaseModel):
    """Response for a rejection."""
    id: int
    project_id: int
    template_generation_id: int
    reason: str
    comment: Optional[str] = None
    rejected_by: Optional[int] = None
    rejected_at: datetime
    created_at: datetime

    # Enriched data
    thumbnail_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RejectActionResponse(BaseModel):
    """Response for reject action."""
    rejection: RejectionResponse


# --- Rejection Archive Schemas ---

class RejectionArchiveItem(BaseModel):
    """Item in the rejection archive."""
    id: int
    template_generation_id: int
    reason: str
    comment: Optional[str] = None
    rejected_by: Optional[int] = None
    rejected_by_name: Optional[str] = None
    rejected_at: datetime

    # Enriched data from template_generation
    thumbnail_url: Optional[str] = None
    variant_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class RejectionArchiveResponse(BaseModel):
    """Response for rejection archive list."""
    items: List[RejectionArchiveItem]
    total: int


# --- Regenerate Schemas ---

class RegenerateRequest(BaseModel):
    """Request body for regenerating a generation."""
    feedback: Optional[str] = Field(None, max_length=2000, description="Feedback for prompt modification")


class RegenerateResponse(BaseModel):
    """Response for regenerate action."""
    new_generation: Dict[str, Any]  # GenerationResponse-like
