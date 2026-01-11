from __future__ import annotations

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
    author_rating: Optional[int] = None  # 1-5


class ProjectBrief(BaseModel):
    """Brief project info for video response"""
    id: int
    name: str
    platforms: List[str]
    duration: int
    project_type: str = "discover"
    audio_mode: str = "auto"  # none, scene, music, voiceover, auto
    require_image_approval: bool = False

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


# --- Metrics Schemas (must be before VideoResponse due to forward reference) ---

class VideoMetricsCreate(BaseModel):
    """Create metrics for a specific period"""
    platform: str  # instagram, tiktok, youtube
    period: Literal["30m", "6h", "24h", "7d"]
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0


class VideoMetricsUpdate(BaseModel):
    """Update existing metrics"""
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None


class VideoMetricsResponse(BaseModel):
    id: int
    video_id: int
    platform: str
    period: str
    views: int
    likes: int
    comments: int
    shares: int
    engagement_rate: Optional[float] = None  # percentage (e.g., 5.5 = 5.5%)
    recorded_at: datetime
    is_manual: bool

    model_config = ConfigDict(from_attributes=True)


class VideoMetricsSummary(BaseModel):
    """Summary of all metrics for a video across platforms and periods"""
    video_id: int
    author_rating: Optional[int] = None
    platforms: Dict[str, Dict[str, VideoMetricsResponse]] = {}
    # Structure: {"instagram": {"30m": {...}, "6h": {...}}, "tiktok": {...}}

    # Aggregated totals (sum across all platforms for latest period)
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    avg_engagement_rate: Optional[float] = None


# --- Video Response (uses VideoMetricsResponse) ---

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

    # Local file paths (served via /api/files)
    local_image_path: Optional[str] = None
    local_video_path: Optional[str] = None
    local_audio_path: Optional[str] = None
    adaptation_data: Optional[Dict[str, Any]] = None
    publishing_meta: Optional[Dict[str, Any]] = None

    current_step: Optional[str] = None
    status: str
    author_rating: Optional[int] = None

    # Publishing - computed from publish_results relationship
    is_published: bool = False
    published_at: Optional[datetime] = None
    published_platforms: List[str] = []  # ["youtube", "instagram"]
    publish_urls: Dict[str, str] = {}  # {"youtube": "https://..."}

    created_at: datetime
    updated_at: datetime

    workflow_steps: List[WorkflowStepResponse] = []
    project: Optional[ProjectBrief] = None
    metrics: List[VideoMetricsResponse] = []

    model_config = ConfigDict(from_attributes=True)
