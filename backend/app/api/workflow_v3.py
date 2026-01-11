"""
Workflow API v3 - Simple, reliable step-by-step generation.

Endpoints:
- POST /v3/{video_id}/generate/{step} - Generate one step
- GET /v3/{video_id}/variants/{step} - Get all variants for a step
- POST /v3/{video_id}/select/{variant_id} - Select a variant
- POST /v3/{video_id}/run-auto - Run all steps (AUTO mode)
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

    if step == "story":
        return await openai_service.generate_story_from_template(
            story_template=project.story_template or "",
            content_variables=video.content_variables or {},
            duration=project.duration,
            platforms=project.platforms,
            system_prompt=project.system_prompts.get("story") if project.system_prompts else None
        )

    elif step == "description":
        if not video.story_data:
            raise HTTPException(status_code=400, detail="Story not generated yet")
        return await openai_service.generate_description(video.story_data)

    elif step == "scenario":
        # Scenario теперь генерируется ДО image, только на основе description
        if not video.description_data:
            raise HTTPException(status_code=400, detail="Description not generated yet")
        return await openai_service.generate_scenario_from_description(
            video.description_data
        )

    elif step == "prompt":
        if not video.description_data:
            raise HTTPException(status_code=400, detail="Description not generated yet")
        # Prompt теперь использует scenario для лучшей согласованности
        return await openai_service.generate_image_prompt(
            video.description_data,
            scenario_data=video.scenario_data  # Передаём scenario для учёта анимации
        )

    elif step == "image":
        # For Remix, use prompt from project template
        if project.project_type == "remix":
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
            # For Discover, use generated prompt_data
            if not video.prompt_data:
                raise HTTPException(status_code=400, detail="Prompt not generated yet")
            prompt_data = video.prompt_data
            image_url = await kling_service.generate_image(
                prompt=prompt_data.get("main_prompt", ""),
                negative_prompt=prompt_data.get("negative_prompt"),
                aspect_ratio=project.aspect_ratio or "9:16"
            )
        return {"image_url": image_url}

    elif step == "video":
        if not video.image_url:
            raise HTTPException(status_code=400, detail="Image not generated yet")

        # For Remix, use scenario from template
        if project.project_type == "remix" and project.scenario_template:
            scenario_data = dict(project.scenario_template)
            if video.content_variables:
                for key, value in video.content_variables.items():
                    for field in scenario_data:
                        if isinstance(scenario_data[field], str):
                            scenario_data[field] = scenario_data[field].replace(f"{{{key}}}", str(value))
        else:
            scenario_data = video.scenario_data

        if not scenario_data:
            raise HTTPException(status_code=400, detail="Scenario not generated yet")

        result = await kling_service.generate_video(
            image_url=video.image_url,
            prompt=scenario_data.get("motion_prompt", ""),
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

    # Get stale steps (dependent steps that need regeneration)
    stale_steps = STEP_DEPENDENCIES.get(step, [])

    # Clear stale step data from video
    for stale_step in stale_steps:
        video_field = STEP_TO_VIDEO_FIELD.get(stale_step)
        if video_field:
            setattr(video, video_field, None)

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
