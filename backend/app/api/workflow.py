"""
Workflow API - 4-step video generation pipeline.

SCENARIO → IMAGE → VIDEO → AUDIO

Endpoints:
- POST /{video_id}/generate/{step} - Generate one step
- GET /{video_id}/variants/{step} - Get all variants for a step
- POST /{video_id}/select/{variant_id} - Select a variant
- POST /{video_id}/run-auto - Run all steps (AUTO mode)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime

from app.db.base import get_db
from app.models.video import Video, WorkflowStatus
from app.models.step_history import StepHistory, STEP_TO_VIDEO_FIELD, DISCOVER_STEPS, REMIX_STEPS, STEP_DEPENDENCIES
from app.models.user import User, WorkspaceMember
from app.core.deps import get_current_user
from app.services.openai_service import openai_service
from app.services.kling_service import kling_service
from app.services import media_downloader

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class GenerateResponse(BaseModel):
    variant_id: int
    step_type: str
    content: Dict[str, Any]
    is_selected: bool


class VariantResponse(BaseModel):
    id: int
    step_type: str
    content: Dict[str, Any]
    is_selected: bool
    created_at: datetime


class VariantsListResponse(BaseModel):
    step_type: str
    variants: List[VariantResponse]
    selected_id: Optional[int]


class SelectResponse(BaseModel):
    variant_id: int
    step_type: str
    stale_steps: List[str]


class RunAutoResponse(BaseModel):
    video_id: int
    status: str
    completed_steps: List[str]
    current_step: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# Helpers
# =============================================================================

def get_video_with_auth(db: Session, video_id: int, user: User) -> Video:
    """Get video with ownership check."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    logger.info(f"Auth check: video_id={video_id}, user_id={user.id}, project_id={video.project_id}")

    if not video.project:
        logger.warning(f"Video {video_id} has no project (project_id={video.project_id})")
        raise HTTPException(status_code=403, detail="Not authorized - no project")

    # Check direct ownership
    if video.project.user_id == user.id:
        logger.info(f"Auth OK: direct ownership")
        return video

    # Check workspace membership
    if video.project.workspace_id:
        is_member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == video.project.workspace_id,
            WorkspaceMember.user_id == user.id
        ).first()
        if is_member:
            logger.info(f"Auth OK: workspace member")
            return video

    logger.warning(f"Auth FAIL: project.user_id={video.project.user_id}, user_id={user.id}, workspace_id={video.project.workspace_id}")
    raise HTTPException(status_code=403, detail="Not authorized")


def get_steps_for_video(video: Video) -> List[str]:
    """Get step list based on project type and settings."""
    is_remix = video.project and video.project.project_type == "remix"
    steps = list(REMIX_STEPS if is_remix else DISCOVER_STEPS)

    # Skip audio step if audio_mode is 'none'
    if video.project and video.project.audio_mode == 'none':
        steps = [s for s in steps if s != 'audio']

    return steps


def validate_step(step: str, video: Video):
    """Validate step is valid for this video."""
    valid_steps = get_steps_for_video(video)
    if step not in valid_steps:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step '{step}'. Valid: {valid_steps}"
        )


async def generate_step_content(step: str, video: Video, db: Session) -> Dict[str, Any]:
    """Generate content for a specific step."""
    project = video.project
    is_remix = project and project.project_type == "remix"

    if step == "scenario":
        if is_remix:
            # Remix: use scenario_template from project
            if not project.scenario_template:
                raise HTTPException(status_code=400, detail="Project has no scenario template")
            scenario_data = dict(project.scenario_template)
            # Fill placeholders with content_variables
            if video.content_variables:
                for key, value in video.content_variables.items():
                    for field in scenario_data:
                        if isinstance(scenario_data[field], str):
                            scenario_data[field] = scenario_data[field].replace(f"{{{key}}}", str(value))
            return scenario_data
        else:
            # Discover: generate scenario from story_template + content_variables
            return await openai_service.generate_scenario_from_template(
                story_template=project.story_template or "",
                content_variables=video.content_variables or {},
                duration=project.duration or 5,
                aspect_ratio=project.aspect_ratio or "9:16"
            )

    elif step == "image":
        # For Remix, use prompt from project template
        if is_remix:
            # Fill template with variables
            prompt = project.story_template or ""
            if video.content_variables:
                for key, value in video.content_variables.items():
                    prompt = prompt.replace(f"{{{key}}}", str(value))
            image_url = await kling_service.generate_image(
                prompt=prompt,
                aspect_ratio=project.aspect_ratio or "9:16"
            )
        else:
            # For Discover, use image_prompt from scenario_data
            if not video.scenario_data:
                raise HTTPException(status_code=400, detail="Scenario not generated yet")
            scenario_data = video.scenario_data
            image_url = await kling_service.generate_image(
                prompt=scenario_data.get("image_prompt", ""),
                negative_prompt=scenario_data.get("negative_prompt"),
                aspect_ratio=project.aspect_ratio or "9:16"
            )
        return {"image_url": image_url}

    elif step == "video":
        if not video.image_url:
            raise HTTPException(status_code=400, detail="Image not generated yet")
        if not video.scenario_data:
            raise HTTPException(status_code=400, detail="Scenario not generated yet")

        result = await kling_service.generate_video(
            image_url=video.image_url,
            prompt=video.scenario_data.get("motion_prompt", ""),
            duration=project.duration or 5,
            return_task_id=True
        )
        video_url, task_id = result
        return {"video_url": video_url, "video_task_id": task_id}

    elif step == "audio":
        if not video.video_url:
            raise HTTPException(status_code=400, detail="Video not generated yet")
        if not video.video_task_id:
            raise HTTPException(status_code=400, detail="Video task ID not found")
        audio_urls = await kling_service.add_audio_to_video(video.video_task_id)
        # Return first audio variant as main
        return {"audio_url": audio_urls[0] if audio_urls else None, "audio_variants": audio_urls}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown step: {step}")


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/{video_id}/generate/{step}", response_model=GenerateResponse)
async def generate_step(
    video_id: int,
    step: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a single step variant."""
    video = get_video_with_auth(db, video_id, current_user)
    validate_step(step, video)

    # Update status
    video.status = WorkflowStatus.IN_PROGRESS
    video.current_step = step
    db.commit()

    try:
        # Generate content
        content = await generate_step_content(step, video, db)

        # Save to history
        history = StepHistory(
            video_id=video_id,
            step_type=step,
            content=content,
            is_selected=False
        )
        db.add(history)
        db.commit()
        db.refresh(history)

        # Auto-select if first variant
        existing_count = db.query(StepHistory).filter(
            StepHistory.video_id == video_id,
            StepHistory.step_type == step
        ).count()

        if existing_count == 1:
            # First variant - auto-select
            history.is_selected = True
            _copy_to_video(video, step, content)
            # Download media locally (non-blocking, best-effort)
            await _download_media_for_step(video, step)
            db.commit()

        logger.info(f"Generated {step} for video {video_id}, variant_id={history.id}")

        return GenerateResponse(
            variant_id=history.id,
            step_type=step,
            content=content,
            is_selected=history.is_selected
        )

    except Exception as e:
        logger.error(f"Failed to generate {step}: {e}")
        video.status = WorkflowStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}/variants/{step}", response_model=VariantsListResponse)
async def get_variants(
    video_id: int,
    step: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all variants for a step."""
    video = get_video_with_auth(db, video_id, current_user)
    validate_step(step, video)

    variants = db.query(StepHistory).filter(
        StepHistory.video_id == video_id,
        StepHistory.step_type == step
    ).order_by(StepHistory.created_at.desc()).all()

    selected_id = None
    for v in variants:
        if v.is_selected:
            selected_id = v.id
            break

    return VariantsListResponse(
        step_type=step,
        variants=[
            VariantResponse(
                id=v.id,
                step_type=v.step_type,
                content=v.content,
                is_selected=v.is_selected,
                created_at=v.created_at
            )
            for v in variants
        ],
        selected_id=selected_id
    )


@router.post("/{video_id}/select/{variant_id}", response_model=SelectResponse)
async def select_variant(
    video_id: int,
    variant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Select a variant, mark dependent steps as stale."""
    video = get_video_with_auth(db, video_id, current_user)

    # Get variant
    variant = db.query(StepHistory).filter(
        StepHistory.id == variant_id,
        StepHistory.video_id == video_id
    ).first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    step = variant.step_type

    # Deselect all other variants of this step
    db.query(StepHistory).filter(
        StepHistory.video_id == video_id,
        StepHistory.step_type == step
    ).update({"is_selected": False})

    # Select this variant
    variant.is_selected = True

    # Copy to video
    _copy_to_video(video, step, variant.content)

    # Download media locally for the selected variant
    await _download_media_for_step(video, step)

    # Get stale steps (dependent steps that need regeneration)
    stale_steps = STEP_DEPENDENCIES.get(step, [])

    # Clear stale step data and local paths from video
    for stale_step in stale_steps:
        video_field = STEP_TO_VIDEO_FIELD.get(stale_step)
        if video_field:
            setattr(video, video_field, None)
        # Also clear local paths
        if stale_step == "image":
            video.local_image_path = None
        elif stale_step == "video":
            video.local_video_path = None
        elif stale_step == "audio":
            video.local_audio_path = None

    db.commit()

    logger.info(f"Selected variant {variant_id} for {step}, stale_steps={stale_steps}")

    return SelectResponse(
        variant_id=variant_id,
        step_type=step,
        stale_steps=stale_steps
    )


@router.post("/{video_id}/run-auto", response_model=RunAutoResponse)
async def run_auto(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Run all steps automatically (AUTO mode)."""
    video = get_video_with_auth(db, video_id, current_user)

    # Prevent duplicate runs - only start if pending
    if video.status != WorkflowStatus.PENDING:
        logger.warning(f"run_auto called but video {video_id} status is {video.status}, skipping")
        return RunAutoResponse(
            video_id=video_id,
            status=video.status.value if video.status else "unknown",
            completed_steps=[],
            current_step=video.current_step.value if video.current_step else None,
            error=None
        )

    steps = get_steps_for_video(video)

    video.status = WorkflowStatus.IN_PROGRESS
    db.commit()

    completed_steps = []
    current_step = None
    error = None

    for step in steps:
        current_step = step
        video.current_step = step
        db.commit()

        try:
            # Check if step already has selected variant
            existing = db.query(StepHistory).filter(
                StepHistory.video_id == video_id,
                StepHistory.step_type == step,
                StepHistory.is_selected == True
            ).first()

            if existing:
                # Already done - ensure data is copied to video
                _copy_to_video(video, step, existing.content)
                # Download media if not already downloaded
                if step in ["image", "video", "audio"]:
                    await _download_media_for_step(video, step)
                db.commit()
                db.refresh(video)
                completed_steps.append(step)
                continue

            # Generate
            content = await generate_step_content(step, video, db)

            # Save and auto-select
            history = StepHistory(
                video_id=video_id,
                step_type=step,
                content=content,
                is_selected=True
            )
            db.add(history)
            _copy_to_video(video, step, content)
            # Download media locally (non-blocking, best-effort)
            await _download_media_for_step(video, step)
            db.commit()
            db.refresh(video)  # Refresh to get updated data

            completed_steps.append(step)
            logger.info(f"AUTO: Completed {step} for video {video_id}")

        except Exception as e:
            logger.error(f"AUTO: Failed at {step}: {e}")
            error = str(e)
            video.status = WorkflowStatus.FAILED
            db.commit()
            break

    # All done?
    if not error and len(completed_steps) == len(steps):
        video.status = WorkflowStatus.COMPLETED
        current_step = None
        db.commit()

    return RunAutoResponse(
        video_id=video_id,
        status=video.status.value,
        completed_steps=completed_steps,
        current_step=current_step,
        error=error
    )


# =============================================================================
# Internal Helpers
# =============================================================================

def _copy_to_video(video: Video, step: str, content: Dict[str, Any]):
    """Copy step content to appropriate Video field."""
    field = STEP_TO_VIDEO_FIELD.get(step)
    if not field:
        return

    if step in ["story", "description", "prompt", "scenario"]:
        # JSON fields
        setattr(video, field, content)
    elif step == "image":
        video.image_url = content.get("image_url")
    elif step == "video":
        video.video_url = content.get("video_url")
        video.video_task_id = content.get("video_task_id")
    elif step == "audio":
        video.video_with_audio_url = content.get("audio_url")
        video.audio_variants = content.get("audio_variants")


async def _download_media_for_step(video: Video, step: str):
    """Download media files locally after generation (non-blocking, best-effort)."""
    try:
        if step == "image" and video.image_url:
            local_path = await media_downloader.download_image(video.image_url, video.id)
            if local_path:
                video.local_image_path = local_path
                logger.info(f"Downloaded image for video {video.id}: {local_path}")

        elif step == "video" and video.video_url:
            local_path = await media_downloader.download_video(video.video_url, video.id, "video")
            if local_path:
                video.local_video_path = local_path
                logger.info(f"Downloaded video for video {video.id}: {local_path}")

        elif step == "audio" and video.video_with_audio_url:
            local_path = await media_downloader.download_video(video.video_with_audio_url, video.id, "audio")
            if local_path:
                video.local_audio_path = local_path
                logger.info(f"Downloaded audio for video {video.id}: {local_path}")

    except Exception as e:
        # Non-blocking: log error but don't fail the workflow
        logger.error(f"Failed to download media for step {step}, video {video.id}: {e}")
