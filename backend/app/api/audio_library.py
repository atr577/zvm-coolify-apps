"""API endpoints for Audio Library."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.audio_library import AudioLibrarySearchResponse, AudioLibraryItemResponse
from app.services.audio_library_service import get_audio_library_service

router = APIRouter()


@router.get("", response_model=AudioLibrarySearchResponse)
async def search_audio_library(
    workspace_id: int = Query(...),
    mood: str | None = Query(None),
    source_type: str | None = Query(None),
    min_duration_ms: int | None = Query(None),
    max_duration_ms: int | None = Query(None),
    sort: str = Query("newest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search/list audio library for a workspace."""
    service = get_audio_library_service()
    result = await service.search(
        db=db,
        workspace_id=workspace_id,
        mood=mood,
        source_type=source_type,
        min_duration_ms=min_duration_ms,
        max_duration_ms=max_duration_ms,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return AudioLibrarySearchResponse(
        items=[AudioLibraryItemResponse.model_validate(item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
