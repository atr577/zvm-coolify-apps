"""Pydantic schemas for Audio Library."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime


class AudioLibraryItemResponse(BaseModel):
    id: int
    source_type: str  # 'sfx' | 'music'
    duration_ms: int
    file_url: Optional[str] = None
    prompt: Optional[str] = None
    mood: Optional[str] = None
    use_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AudioLibrarySearchResponse(BaseModel):
    items: List[AudioLibraryItemResponse]
    total: int
    page: int
    page_size: int
