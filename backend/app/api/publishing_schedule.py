"""API endpoints for scheduled publishing (Template projects)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List
import pytz
import logging

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.publishing_config import PublishingConfig
from app.models.approved_generation import ApprovedGeneration
from app.models.template_generation import TemplateGeneration
from app.models.variant import Variant
from app.models.video_template import VideoTemplate
from app.models.rejection_archive import RejectionArchive
from app.api.projects import user_has_workspace_access
from app.schemas.publishing import (
    PublishingConfigCreate,
    PublishingConfigUpdate,
    PublishingConfigResponse,
    PublishingQueueItemUpdate,
    PublishingQueueItemResponse,
    PublishingQueueResponse,
    PublishingScheduleResponse,
    PublishingScheduleConfig,
    ScheduleSlot,
    ScheduleSlotItem,
    ScheduleWarning,
    PipelineStatsResponse,
)

from app.utils.urls import get_local_url

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Helper Functions ---

def get_template_project(db: Session, project_id: int, user: User) -> Project:
    """Get project and verify it's template type with user access."""
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.project_type != "template":
        raise HTTPException(status_code=400, detail="Project is not template type")

    # Verify workspace access
    if project.workspace_id and not user_has_workspace_access(db, user.id, project.workspace_id):
        raise HTTPException(status_code=403, detail="No access to workspace")

    return project


def get_or_create_config(db: Session, project_id: int) -> PublishingConfig:
    """Get existing config or create default one."""
    config = db.query(PublishingConfig).filter(
        PublishingConfig.project_id == project_id
    ).first()

    if not config:
        config = PublishingConfig(
            project_id=project_id,
            enabled=False,
            is_paused=False,
            days=[],
            preferred_times=["18:00"],
            depth_days=7
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return config


def calculate_schedule_slots(
    config: PublishingConfig,
    timezone: str,
    depth_days: int
) -> List[datetime]:
    """Calculate schedule slots for depth_days ahead.

    Supports multiple times per day (e.g., ["09:00", "18:00"]).
    """
    DAY_MAP = {
        'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6
    }

    if not config.days:
        return []

    # Parse preferred times
    times = []
    preferred_times = config.preferred_times or ["18:00"]
    for time_str in preferred_times:
        try:
            hour, minute = map(int, time_str.split(':'))
            times.append((hour, minute))
        except (ValueError, AttributeError):
            continue

    if not times:
        times = [(18, 0)]  # Default fallback

    # Get timezone
    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        tz = pytz.UTC

    # Get current time in project timezone
    now = datetime.now(tz)
    today = now.date()

    # Convert config days to weekday numbers
    target_weekdays = set()
    for day in config.days:
        if day.lower() in DAY_MAP:
            target_weekdays.add(DAY_MAP[day.lower()])

    # Find all slots in the next depth_days
    slots = []
    for i in range(depth_days):
        check_date = today + timedelta(days=i)
        if check_date.weekday() in target_weekdays:
            # Create slots for each preferred time
            for hour, minute in times:
                slot_dt = tz.localize(datetime(
                    check_date.year, check_date.month, check_date.day,
                    hour, minute
                ))
                # Skip if this slot is in the past
                if slot_dt > now:
                    slots.append(slot_dt)

    # Sort by datetime
    slots.sort()
    return slots


# --- Publishing Config ---

@router.get("/projects/{project_id}/publishing-config", response_model=PublishingConfigResponse, tags=["publishing-schedule"])
async def get_publishing_config(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get publishing config for a template project."""
    project = get_template_project(db, project_id, current_user)
    config = get_or_create_config(db, project_id)
    return config


@router.put("/projects/{project_id}/publishing-config", response_model=PublishingConfigResponse, tags=["publishing-schedule"])
async def update_publishing_config(
    project_id: int,
    request: PublishingConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update publishing config for a template project."""
    project = get_template_project(db, project_id, current_user)
    config = get_or_create_config(db, project_id)

    # Update config
    config.enabled = request.enabled
    config.is_paused = request.is_paused
    config.days = request.days
    config.preferred_times = request.preferred_times
    config.depth_days = request.depth_days
    config.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(config)

    logger.info(f"Updated publishing config for project {project_id}: enabled={config.enabled}, days={config.days}")

    return config


# --- Publishing Queue ---

@router.get("/projects/{project_id}/publishing-queue", response_model=PublishingQueueResponse, tags=["publishing-schedule"])
async def get_publishing_queue(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get publishing queue (approved generations) for a template project."""
    project = get_template_project(db, project_id, current_user)

    # Get all approved generations ordered by position
    items = db.query(ApprovedGeneration).options(
        joinedload(ApprovedGeneration.template_generation)
    ).filter(
        ApprovedGeneration.project_id == project_id,
        ApprovedGeneration.status == "approved"
    ).order_by(ApprovedGeneration.position.asc()).all()

    # Build response
    response_items = []
    for item in items:
        gen = item.template_generation
        response_items.append(PublishingQueueItemResponse(
            id=item.id,
            project_id=item.project_id,
            template_generation_id=item.template_generation_id,
            position=item.position,
            approved_at=item.approved_at,
            publishing_metadata=item.publishing_metadata,
            status=item.status,
            platform_statuses=item.platform_statuses,
            retry_count=item.retry_count,
            last_error=item.last_error,
            published_at=item.published_at,
            created_at=item.created_at,
            updated_at=item.updated_at,
            thumbnail_url=get_local_url(gen.image_path, gen.image_url) if gen else None,
            video_url=get_local_url(gen.video_with_audio_path or gen.video_path, gen.video_url) if gen else None
        ))

    return PublishingQueueResponse(items=response_items, total=len(response_items))


@router.put("/projects/{project_id}/publishing-queue/{item_id}", response_model=PublishingQueueItemResponse, tags=["publishing-schedule"])
async def update_queue_item(
    project_id: int,
    item_id: int,
    request: PublishingQueueItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update publishing metadata for a queue item."""
    project = get_template_project(db, project_id, current_user)

    item = db.query(ApprovedGeneration).options(
        joinedload(ApprovedGeneration.template_generation)
    ).filter(
        ApprovedGeneration.id == item_id,
        ApprovedGeneration.project_id == project_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    if item.status != "approved":
        raise HTTPException(status_code=400, detail="Can only edit items with status 'approved'")

    # Update metadata
    item.publishing_metadata = request.publishing_metadata
    item.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(item)

    gen = item.template_generation
    return PublishingQueueItemResponse(
        id=item.id,
        project_id=item.project_id,
        template_generation_id=item.template_generation_id,
        position=item.position,
        approved_at=item.approved_at,
        publishing_metadata=item.publishing_metadata,
        status=item.status,
        platform_statuses=item.platform_statuses,
        retry_count=item.retry_count,
        last_error=item.last_error,
        published_at=item.published_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        thumbnail_url=get_local_url(gen.image_path, gen.image_url) if gen else None,
        video_url=get_local_url(gen.video_with_audio_path or gen.video_path, gen.video_url) if gen else None
    )


@router.delete("/projects/{project_id}/publishing-queue/{item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["publishing-schedule"])
async def delete_queue_item(
    project_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove item from publishing queue."""
    project = get_template_project(db, project_id, current_user)

    item = db.query(ApprovedGeneration).filter(
        ApprovedGeneration.id == item_id,
        ApprovedGeneration.project_id == project_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    if item.status not in ("approved", "failed"):
        raise HTTPException(status_code=400, detail="Can only delete items with status 'approved' or 'failed'")

    deleted_position = item.position

    # Delete item
    db.delete(item)

    # Reorder remaining items
    db.query(ApprovedGeneration).filter(
        ApprovedGeneration.project_id == project_id,
        ApprovedGeneration.status == "approved",
        ApprovedGeneration.position > deleted_position
    ).update(
        {ApprovedGeneration.position: ApprovedGeneration.position - 1},
        synchronize_session=False
    )

    db.commit()

    logger.info(f"Deleted queue item {item_id} from project {project_id}, reordered positions")

    return None


# --- Publishing Schedule ---

@router.get("/projects/{project_id}/publishing-schedule", response_model=PublishingScheduleResponse, tags=["publishing-schedule"])
async def get_publishing_schedule(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get computed publishing schedule.

    Calculates slots based on config (days, time) and assigns queue items (FIFO).
    Returns warnings if queue is low, platforms not configured, etc.
    """
    project = get_template_project(db, project_id, current_user)
    config = get_or_create_config(db, project_id)

    # Get approved items from queue
    queue_items = db.query(ApprovedGeneration).options(
        joinedload(ApprovedGeneration.template_generation)
    ).filter(
        ApprovedGeneration.project_id == project_id,
        ApprovedGeneration.status == "approved"
    ).order_by(ApprovedGeneration.position.asc()).all()

    # Calculate schedule slots
    slots = calculate_schedule_slots(config, project.timezone, config.depth_days)

    # Build response slots with assigned items
    response_slots = []
    for i, slot_time in enumerate(slots):
        item = None
        if i < len(queue_items):
            q_item = queue_items[i]
            gen = q_item.template_generation
            item = ScheduleSlotItem(
                id=q_item.id,
                generation_id=q_item.template_generation_id,
                thumbnail_url=get_local_url(gen.image_path, gen.image_url) if gen else None,
                video_url=get_local_url(gen.video_with_audio_path or gen.video_path, gen.video_url) if gen else None,
                publishing_metadata=q_item.publishing_metadata,
                status=q_item.status,
                platform_statuses=q_item.platform_statuses
            )

        response_slots.append(ScheduleSlot(
            scheduled_at=slot_time,
            item=item
        ))

    # Build warnings
    warnings = []

    if not config.enabled:
        warnings.append(ScheduleWarning(
            type="config_disabled",
            message="Publishing schedule is disabled"
        ))

    if not project.platforms:
        warnings.append(ScheduleWarning(
            type="no_platforms",
            message="No platforms configured for this project"
        ))

    if len(queue_items) < len(slots):
        missing = len(slots) - len(queue_items)
        warnings.append(ScheduleWarning(
            type="queue_low",
            message=f"Queue has {len(queue_items)} videos, but {len(slots)} slots available. {missing} slots will be empty."
        ))

    # Build config response
    config_response = PublishingScheduleConfig(
        enabled=config.enabled,
        is_paused=config.is_paused,
        days=config.days,
        preferred_times=config.preferred_times or ["18:00"],
        timezone=project.timezone,
        depth_days=config.depth_days
    )

    return PublishingScheduleResponse(
        config=config_response,
        slots=response_slots,
        warnings=warnings
    )


# --- Pipeline Stats ---

@router.get("/projects/{project_id}/pipeline-stats", response_model=PipelineStatsResponse, tags=["publishing-schedule"])
async def get_pipeline_stats(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get pipeline funnel statistics for a template project.

    Returns counts for: generating, pending review, approved (queue), scheduled slots.
    Also returns variants_count and templates_count for smart default screen logic.
    """
    project = get_template_project(db, project_id, current_user)

    # Generating count: active generation statuses
    generating_count = db.query(func.count(TemplateGeneration.id)).filter(
        TemplateGeneration.project_id == project_id,
        TemplateGeneration.status.in_(['pending', 'preprocessing', 'generating_image', 'generating_video']),
        TemplateGeneration.is_deleted == False
    ).scalar()

    # Review count: completed + not approved + not rejected + not regenerated + not deleted
    approved_ids = db.query(ApprovedGeneration.template_generation_id).filter(
        ApprovedGeneration.project_id == project_id
    ).subquery()

    rejected_ids = db.query(RejectionArchive.template_generation_id).filter(
        RejectionArchive.project_id == project_id
    ).subquery()

    review_count = db.query(func.count(TemplateGeneration.id)).filter(
        TemplateGeneration.project_id == project_id,
        TemplateGeneration.status == "completed",
        TemplateGeneration.regenerated == False,
        TemplateGeneration.is_deleted == False,
        ~TemplateGeneration.id.in_(approved_ids),
        ~TemplateGeneration.id.in_(rejected_ids)
    ).scalar()

    # Approved count: items in queue with status 'approved'
    approved_count = db.query(func.count(ApprovedGeneration.id)).filter(
        ApprovedGeneration.project_id == project_id,
        ApprovedGeneration.status == "approved"
    ).scalar()

    # Schedule slots
    config = get_or_create_config(db, project_id)
    slots = calculate_schedule_slots(config, project.timezone or 'UTC', config.depth_days)
    total_schedule_slots = len(slots)
    scheduled_count = min(approved_count, total_schedule_slots)

    # Variants count
    variants_count = db.query(func.count(Variant.id)).filter(
        Variant.project_id == project_id
    ).scalar()

    # Templates count (non-deleted)
    templates_count = db.query(func.count(VideoTemplate.id)).filter(
        VideoTemplate.project_id == project_id,
        VideoTemplate.is_deleted == False
    ).scalar()

    return PipelineStatsResponse(
        generating_count=generating_count,
        review_count=review_count,
        approved_count=approved_count,
        scheduled_count=scheduled_count,
        total_schedule_slots=total_schedule_slots,
        variants_count=variants_count,
        templates_count=templates_count
    )
