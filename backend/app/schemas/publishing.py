from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import re


# --- Legacy schemas (for manual publishing) ---

class PublishRequest(BaseModel):
    video_id: int
    platform: str = Field(..., pattern="^(instagram|tiktok|youtube)$")
    video_url: str
    title: str
    description: str
    hashtags: Optional[str] = None
    schedule_time: Optional[str] = None  # ISO format datetime for scheduling
    privacy_status: Optional[str] = "public"  # public, private, unlisted (YouTube only)


class PublishResponse(BaseModel):
    success: bool
    platform: str
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error_message: Optional[str] = None
    status: str


# --- Publishing Config (T21: Scheduled Publishing) ---

class PublishingConfigBase(BaseModel):
    """Base schema for publishing config."""
    enabled: bool = False
    is_paused: bool = False
    days: List[str] = Field(default_factory=list, description="Days of week: mon, tue, wed, thu, fri, sat, sun")
    preferred_times: List[str] = Field(default_factory=lambda: ["18:00"], description="Times in HH:MM format")
    depth_days: int = Field(default=7, ge=1, le=30, description="Days to show in schedule")

    @field_validator('days')
    @classmethod
    def validate_days(cls, v):
        valid_days = {'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'}
        for day in v:
            if day.lower() not in valid_days:
                raise ValueError(f"Invalid day: {day}. Must be one of: {', '.join(valid_days)}")
        return [d.lower() for d in v]

    @field_validator('preferred_times')
    @classmethod
    def validate_times(cls, v):
        if not v:
            raise ValueError("At least one time must be specified")
        for time_str in v:
            if not re.match(r'^([01]?\d|2[0-3]):([0-5]\d)$', time_str):
                raise ValueError(f"Invalid time format: {time_str}. Must be HH:MM (00:00 - 23:59)")
        return sorted(set(v))  # Remove duplicates and sort


class PublishingConfigCreate(PublishingConfigBase):
    """Schema for creating publishing config."""
    pass


class PublishingConfigUpdate(PublishingConfigBase):
    """Schema for updating publishing config."""
    pass


class PublishingConfigResponse(PublishingConfigBase):
    """Response schema for publishing config."""
    id: int
    project_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Publishing Queue Item ---

class PlatformMetadata(BaseModel):
    """Metadata for a single platform."""
    title: str = ""
    description: str = ""
    hashtags: str = ""


class PublishingQueueItemUpdate(BaseModel):
    """Schema for updating queue item."""
    publishing_metadata: Dict[str, Dict[str, str]] = Field(
        ...,
        description="Platform metadata: {platform: {title, description, hashtags}}"
    )

    @field_validator('publishing_metadata')
    @classmethod
    def validate_metadata(cls, v):
        if not v:
            raise ValueError("At least one platform must be specified")
        valid_platforms = {'instagram', 'tiktok', 'youtube'}
        for platform in v.keys():
            if platform.lower() not in valid_platforms:
                raise ValueError(f"Invalid platform: {platform}. Must be one of: {', '.join(valid_platforms)}")
        return v


class PublishingQueueItemResponse(BaseModel):
    """Response schema for queue item."""
    id: int
    project_id: int
    template_generation_id: int
    position: int
    approved_at: datetime
    publishing_metadata: Optional[Dict[str, Any]] = None
    status: str
    platform_statuses: Optional[Dict[str, str]] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # From related TemplateGeneration
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None

    class Config:
        from_attributes = True


class PublishingQueueResponse(BaseModel):
    """Response schema for publishing queue list."""
    items: List[PublishingQueueItemResponse]
    total: int


# --- Publishing Schedule ---

class ScheduleSlotItem(BaseModel):
    """Item in a schedule slot."""
    id: int
    generation_id: int
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    publishing_metadata: Optional[Dict[str, Any]] = None
    status: str
    platform_statuses: Optional[Dict[str, str]] = None


class ScheduleSlot(BaseModel):
    """A single schedule slot."""
    scheduled_at: datetime
    item: Optional[ScheduleSlotItem] = None


class ScheduleWarning(BaseModel):
    """Warning for schedule view."""
    type: str  # queue_low, no_platforms, config_disabled
    message: str


class PublishingScheduleConfig(BaseModel):
    """Config info for schedule response."""
    enabled: bool
    is_paused: bool = False
    days: List[str]
    preferred_times: List[str]
    timezone: str
    depth_days: int


class PublishingScheduleResponse(BaseModel):
    """Response schema for computed schedule."""
    config: PublishingScheduleConfig
    slots: List[ScheduleSlot]
    warnings: List[ScheduleWarning] = Field(default_factory=list)


# --- Queue Management (T51) ---

class ReturnToModerationResponse(BaseModel):
    """Response for return-to-moderation action."""
    returned_generation_id: int
    message: str = "Returned to moderation queue"


class ReorderQueueRequest(BaseModel):
    """Request to reorder publishing queue."""
    item_ids: List[int] = Field(
        ...,
        min_length=1,
        description="Ordered list of approved queue item IDs"
    )


class ReorderQueueResponse(BaseModel):
    """Response for queue reorder."""
    reordered_count: int


# --- Pipeline Stats ---

class PipelineStatsResponse(BaseModel):
    """Response schema for pipeline funnel counters."""
    generating_count: int = 0
    review_count: int = 0
    approved_count: int = 0
    scheduled_count: int = 0
    total_schedule_slots: int = 0
    published_count: int = 0
    variants_count: int = 0
    templates_count: int = 0
