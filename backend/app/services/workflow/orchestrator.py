"""
Workflow Orchestrator - manages 4-step workflow for video generation.

SCENARIO → IMAGE → VIDEO → AUDIO

Unified for both Discover and Remix projects (difference only in SCENARIO strategy).
"""
import time
import logging
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.db.base import get_db
from app.models.video import Video, WorkflowStatus, WorkflowMode
from app.models.step_history import StepHistory
from app.core.config import settings
from app.services.workflow.strategies import get_strategy

logger = logging.getLogger(__name__)

# Configure logging based on settings
if settings.LOG_LEVEL == "DEBUG":
    logger.setLevel(logging.DEBUG)

# Workflow configuration
WORKFLOW_STEPS = ['scenario', 'image', 'video', 'audio']

DEFAULT_VARIANTS = {
    'scenario': 1,
    'image': 3,
    'video': 1,
    'audio': 1,
}


def get_steps_for_project(project) -> List[str]:
    """
    Get workflow steps for a project.

    Returns 4 steps, or 3 if audio_mode is 'none'.
    """
    steps = ['scenario', 'image', 'video']
    if project.audio_mode != 'none':
        steps.append('audio')
    return steps


def get_next_step(current: str, project) -> Optional[str]:
    """
    Get next step after current, or None if last.
    """
    steps = get_steps_for_project(project)
    try:
        idx = steps.index(current)
        return steps[idx + 1] if idx + 1 < len(steps) else None
    except ValueError:
        return None


async def run_auto(video_id: int, db: Session) -> Dict[str, Any]:
    """
    AUTO mode: run all steps without pauses.

    Args:
        video_id: Video ID to process
        db: Database session

    Returns:
        Dict with final status and generated content
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    steps = get_steps_for_project(video.project)
    logger.info(f"run_auto: video {video_id}, steps: {steps}")

    for step in steps:
        result = await generate_step(video_id, step, db=db)
        if result.get("status") == "failed":
            return result

        # AUTO mode: auto-select first variant
        variants = result.get("variants", [])
        if variants:
            first_variant = variants[0]
            first_variant.is_selected = True
            db.commit()

    # Mark workflow as completed
    video.status = WorkflowStatus.COMPLETED
    db.commit()

    logger.info(f"run_auto: video {video_id} completed")
    return {"status": "completed", "video_id": video_id}


async def generate_step(
    video_id: int,
    step: str,
    feedback: Optional[str] = None,
    parent_id: Optional[int] = None,
    db: Session = None
) -> Dict[str, Any]:
    """
    Generate a single step with concurrent protection.

    Args:
        video_id: Video ID
        step: Step name (scenario, image, video, audio)
        feedback: Optional feedback for regeneration
        parent_id: Optional parent StepHistory ID for lineage
        db: Database session

    Returns:
        Dict with variants and status
    """
    if db is None:
        db = next(get_db())

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Concurrent protection
    if video.status == WorkflowStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="Generation already in progress")

    video.status = WorkflowStatus.IN_PROGRESS
    db.commit()

    try:
        start_time = time.time()
        logger.info(f"Step {step} started for video {video_id}")

        # Get strategy for project type
        strategy = get_strategy(video.project.project_type)

        # Determine variant count
        count = 1 if video.workflow_mode == WorkflowMode.AUTO else DEFAULT_VARIANTS.get(step, 1)

        # Generate variants
        variants = []
        for i in range(count):
            try:
                content = await strategy.generate(step, video, video.project)

                # Create StepHistory entry
                sh = StepHistory(
                    video_id=video.id,
                    step_type=step,
                    content=content,
                    status="success",
                    generation_time_seconds=time.time() - start_time,
                    parent_id=parent_id,
                    feedback=feedback if i == 0 else None,  # Only first variant gets feedback
                )
                db.add(sh)
                db.flush()  # Get ID before commit
                variants.append(sh)

                # Update video with generated content
                _update_video_content(video, step, content)

                logger.debug(f"Generated variant {i+1}/{count} for {step}")

            except Exception as e:
                # Create failed entry
                sh = StepHistory(
                    video_id=video.id,
                    step_type=step,
                    content={"error": str(e)},
                    status="failed",
                    error_message=str(e),
                    generation_time_seconds=time.time() - start_time,
                    parent_id=parent_id,
                    feedback=feedback if i == 0 else None,
                )
                db.add(sh)
                logger.error(f"Step {step} variant {i+1} failed: {e}")
                raise

        elapsed = time.time() - start_time
        logger.info(f"Step {step} completed in {elapsed:.1f}s, {len(variants)} variants")

        # Update video status
        if video.workflow_mode == WorkflowMode.AUTO:
            # AUTO: auto-select first variant
            if variants:
                variants[0].is_selected = True
            video.current_step = get_next_step(step, video.project) or step
        else:
            # MANUAL: await approval
            video.status = WorkflowStatus.AWAITING_APPROVAL

        db.commit()

        return {
            "variants": variants,
            "status": "success",
            "step": step,
            "video_id": video_id,
        }

    except Exception as e:
        logger.error(f"Step {step} failed: {e}")
        video.status = WorkflowStatus.FAILED
        db.commit()
        raise


async def select_variant(video_id: int, variant_id: int, db: Session) -> Dict[str, Any]:
    """
    Select a variant and auto-continue to next step.

    Args:
        video_id: Video ID
        variant_id: StepHistory ID to select
        db: Database session

    Returns:
        Dict with next step result or completion status
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    variant = db.query(StepHistory).filter(StepHistory.id == variant_id).first()
    if not variant or variant.video_id != video_id:
        raise HTTPException(status_code=404, detail="Variant not found")

    step_type = variant.step_type

    # Deselect all variants of this step
    db.query(StepHistory).filter(
        StepHistory.video_id == video_id,
        StepHistory.step_type == step_type
    ).update({"is_selected": False})

    # Select this variant
    variant.is_selected = True

    # Update video content from selected variant
    _update_video_content(video, step_type, variant.content)

    db.commit()

    logger.info(f"Selected variant {variant_id} for step {step_type}, video {video_id}")

    # Auto-continue to next step
    next_step = get_next_step(step_type, video.project)
    if next_step:
        video.current_step = next_step
        db.commit()
        return await generate_step(video_id, next_step, parent_id=variant_id, db=db)
    else:
        # Last step - mark as completed
        video.status = WorkflowStatus.COMPLETED
        db.commit()
        return {"status": "completed", "video_id": video_id}


async def get_step_history(video_id: int, step: str, db: Session) -> List[StepHistory]:
    """
    Get all variants for a step from history.

    Args:
        video_id: Video ID
        step: Step name
        db: Database session

    Returns:
        List of StepHistory entries for this step
    """
    return db.query(StepHistory).filter(
        StepHistory.video_id == video_id,
        StepHistory.step_type == step
    ).order_by(StepHistory.created_at.desc()).all()


def _update_video_content(video: Video, step: str, content: Dict[str, Any]) -> None:
    """
    Update video fields from generated content.

    Args:
        video: Video model
        step: Step name
        content: Generated content dict
    """
    if step == "scenario":
        video.scenario_data = content.get("scenario_data")
        if content.get("image_prompt"):
            video.image_prompt = content["image_prompt"]

    elif step == "image":
        if content.get("image_url"):
            video.image_url = content["image_url"]

    elif step == "video":
        if content.get("video_url"):
            video.video_url = content["video_url"]
        if content.get("task_id"):
            video.video_task_id = content["task_id"]

    elif step == "audio":
        if content.get("audio_variants"):
            video.audio_variants = content["audio_variants"]
        if content.get("video_with_audio_url"):
            video.video_with_audio_url = content["video_with_audio_url"]
