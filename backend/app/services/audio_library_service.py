"""Audio Library service — search, add, manage workspace audio tracks."""

from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import Optional

from app.models.audio_library import AudioLibrary

import logging

logger = logging.getLogger(__name__)


class AudioLibraryService:
    """Service for per-workspace audio library operations."""

    async def search(
        self,
        db: Session,
        workspace_id: int,
        mood: Optional[str] = None,
        source_type: Optional[str] = None,
        min_duration_ms: Optional[int] = None,
        max_duration_ms: Optional[int] = None,
        sort: str = "newest",
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Search audio library with filters and pagination."""
        query = db.query(AudioLibrary).filter(
            AudioLibrary.workspace_id == workspace_id
        )

        if mood:
            query = query.filter(AudioLibrary.mood == mood)
        if source_type:
            query = query.filter(AudioLibrary.source_type == source_type)
        if min_duration_ms is not None:
            query = query.filter(AudioLibrary.duration_ms >= min_duration_ms)
        if max_duration_ms is not None:
            query = query.filter(AudioLibrary.duration_ms <= max_duration_ms)

        total = query.count()

        # Sorting
        if sort == "duration":
            query = query.order_by(asc(AudioLibrary.duration_ms))
        elif sort == "most_used":
            query = query.order_by(desc(AudioLibrary.use_count))
        else:  # newest
            query = query.order_by(desc(AudioLibrary.created_at))

        # Pagination
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def add_from_variant(
        self,
        db: Session,
        workspace_id: int,
        source_type: str,
        file_path: str,
        file_url: Optional[str],
        duration_ms: int,
        prompt: Optional[str] = None,
        mood: Optional[str] = None,
        source_discover_project_id: Optional[int] = None,
    ) -> AudioLibrary:
        """Add a new audio track to the library from a Discover variant."""
        item = AudioLibrary(
            workspace_id=workspace_id,
            source_type=source_type,
            file_path=file_path,
            file_url=file_url,
            duration_ms=duration_ms,
            prompt=prompt,
            mood=mood,
            source_discover_project_id=source_discover_project_id,
        )
        db.add(item)
        db.flush()
        logger.info(f"Added audio to library: id={item.id}, type={source_type}, workspace={workspace_id}")
        return item

    async def get_item(self, db: Session, item_id: int) -> Optional[AudioLibrary]:
        """Get a single library item by ID."""
        return db.query(AudioLibrary).filter(AudioLibrary.id == item_id).first()

    async def increment_use_count(self, db: Session, item_id: int):
        """Increment use_count when track is used in a Template."""
        item = db.query(AudioLibrary).filter(AudioLibrary.id == item_id).first()
        if item:
            item.use_count = (item.use_count or 0) + 1
            db.flush()


def get_audio_library_service() -> AudioLibraryService:
    return AudioLibraryService()
