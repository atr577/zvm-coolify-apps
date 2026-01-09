from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


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
