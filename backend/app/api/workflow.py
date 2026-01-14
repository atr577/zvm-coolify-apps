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

class GenerateRequest(BaseModel):
    feedback: Optional[str] = None


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
    feedback: Optional[str] = None


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


class UpdateContentRequest(BaseModel):
    content: Dict[str, Any]


class UpdateContentResponse(BaseModel):
    variant_id: int
    step_type: str
    content: Dict[str, Any]
    is_selected: bool


class GoToStepResponse(BaseModel):
    step: str
    has_data: bool


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


async def generate_step_content(step: str, video: Video, db: Session, feedback: Optional[str] = None) -> Dict[str, Any]:
    """Generate content for a specific step.

    Args:
        step: Step type to generate
        video: Video model
        db: Database session
        feedback: Optional user feedback for regeneration
    """
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
                aspect_ratio=project.aspect_ratio or "9:16",
                feedback=feedback,
                previous_scenario=video.scenario_data
            )

    elif step == "image":
        # For Remix, use prompt from project template
        if is_remix:
            # Fill template with variables
            prompt = project.story_template or ""
            if video.content_variables:
                for key, value in video.content_variables.items():
                    prompt = prompt.replace(f"{{{key}}}", str(value))
        else:
            # For Discover, use image_prompt from scenario_data
            if not video.scenario_data:
                raise HTTPException(status_code=400, detail="Scenario not generated yet")
            prompt = video.scenario_data.get("image_prompt", "")

        # Refine prompt if feedback provided
        if feedback and prompt:
            prompt = await openai_service.refine_prompt(prompt, feedback, prompt_type="image")

        image_url = await kling_service.generate_image(
            prompt=prompt,
            negative_prompt=video.scenario_data.get("negative_prompt") if video.scenario_data else None,
            aspect_ratio=project.aspect_ratio or "9:16"
        )
        return {
            "image_url": image_url,
            "image_prompt": prompt,
            "source_scenario": video.scenario_data  # snapshot for lineage
        }

    elif step == "video":
        if not video.image_url:
            raise HTTPException(status_code=400, detail="Image not generated yet")

        # Get motion prompt and scenario data
        if is_remix:
            # Remix: use motion_template from project
            if not project.motion_template:
                raise HTTPException(status_code=400, detail="Project has no motion_template")
            motion_prompt = project.motion_template
            # Fill placeholders in motion prompt
            if video.content_variables:
                for key, value in video.content_variables.items():
                    motion_prompt = motion_prompt.replace(f"{{{key}}}", str(value))
            # Build scenario_data for lineage
            scenario_data = {"motion_prompt": motion_prompt}
        else:
            # Discover: use scenario_data from previous step
            if not video.scenario_data:
                raise HTTPException(status_code=400, detail="Scenario not generated yet")
            scenario_data = video.scenario_data
            motion_prompt = scenario_data.get("motion_prompt", "")

        # Refine motion prompt if feedback provided
        if feedback and motion_prompt:
            motion_prompt = await openai_service.refine_prompt(motion_prompt, feedback, prompt_type="motion")

        result = await kling_service.generate_video(
            image_url=video.image_url,
            prompt=motion_prompt,
            duration=project.duration or 5,
            return_task_id=True
        )
        video_url, task_id = result
        return {
            "video_url": video_url,
            "video_task_id": task_id,
            "motion_prompt": motion_prompt,
            "source_image_url": video.image_url,  # snapshot for lineage
            "source_scenario": scenario_data  # use resolved scenario_data
        }

    elif step == "audio":
        if not video.video_url:
            raise HTTPException(status_code=400, detail="Video not generated yet")

        # Get provider from project settings (default: kling)
        provider_name = project.audio_provider if project else None

        # Get scenario data for lineage
        if is_remix:
            # Build scenario_data from motion_template
            motion_prompt = project.motion_template or ""
            if video.content_variables:
                for key, value in video.content_variables.items():
                    motion_prompt = motion_prompt.replace(f"{{{key}}}", str(value))
            scenario_data = {"motion_prompt": motion_prompt}
        else:
            scenario_data = video.scenario_data

        # Use provider factory to generate audio
        from app.providers.factory import get_audio_provider
        provider = get_audio_provider(provider_name)
        result = await provider.generate(video, feedback=feedback)

        # Build response with lineage data
        response = {
            **result,
            "source_video_url": video.video_url,
            "source_image_url": video.image_url,
            "source_scenario": scenario_data
        }

        # For kling provider, use first variant as main audio_url
        if result.get("provider") == "kling":
            response["audio_url"] = result.get("video_with_audio_url")
            response["audio_variants"] = result.get("audio_variants", [])
        # For ai_music provider, no audio_url until user selects hook
        elif result.get("provider") == "ai_music":
            response["audio_url"] = None  # Will be set after hook selection + merge

        return response

    else:
        raise HTTPException(status_code=400, detail=f"Unknown step: {step}")


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/{video_id}/generate/{step}", response_model=GenerateResponse)
async def generate_step(
    video_id: int,
    step: str,
    request: GenerateRequest = GenerateRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a single step variant."""
    video = get_video_with_auth(db, video_id, current_user)
    validate_step(step, video)

    # Prevent concurrent generation for the same step
    if video.status == WorkflowStatus.IN_PROGRESS and video.current_step == step:
        raise HTTPException(
            status_code=409,
            detail=f"Generation already in progress for step {step}"
        )

    # Update status
    video.status = WorkflowStatus.IN_PROGRESS
    video.current_step = step
    db.commit()

    try:
        # Find current selected variant (parent for regeneration)
        current_variant = db.query(StepHistory).filter(
            StepHistory.video_id == video_id,
            StepHistory.step_type == step,
            StepHistory.is_selected == True
        ).first()

        # Generate content (with optional feedback)
        content = await generate_step_content(step, video, db, feedback=request.feedback)

        # Deselect current variant if exists
        if current_variant:
            current_variant.is_selected = False

        # ai_music: 1 StepHistory with all hooks in content.variants (like image/video)
        # Each generation = 1 variant containing 4 hooks to choose from
        if content.get('provider') == 'ai_music' and content.get('variants'):
            # Content already has variants array, selected_hook defaults to 0
            content['selected_hook'] = 0

            history = StepHistory(
                video_id=video_id,
                step_type=step,
                content=content,
                is_selected=True,
                feedback=request.feedback,
                parent_id=current_variant.id if current_variant else None
            )
            db.add(history)
            db.commit()
            db.refresh(history)

            # Copy to video
            _copy_to_video(video, step, content)
            db.commit()

            logger.info(f"Generated {step} for video {video_id}, variant_id={history.id} with {len(content.get('variants', []))} hooks")

            return GenerateResponse(
                variant_id=history.id,
                step_type=step,
                content=content,
                is_selected=history.is_selected
            )

        # Standard handling for other steps
        history = StepHistory(
            video_id=video_id,
            step_type=step,
            content=content,
            is_selected=True,
            feedback=request.feedback,
            parent_id=current_variant.id if current_variant else None
        )
        db.add(history)

        # Copy to video
        _copy_to_video(video, step, content)
        db.commit()
        db.refresh(history)

        # Download media locally (non-blocking, best-effort)
        await _download_media_for_step(video, step)

        logger.info(f"Generated {step} for video {video_id}, variant_id={history.id}")

        return GenerateResponse(
            variant_id=history.id,
            step_type=step,
            content=content,
            is_selected=history.is_selected
        )

    except TimeoutError as e:
        # Timeout is retriable - don't mark as FAILED
        logger.warning(f"Timeout generating {step}: {e}")
        video.status = WorkflowStatus.PENDING  # Allow retry
        db.commit()
        raise HTTPException(status_code=504, detail=str(e))
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
                created_at=v.created_at,
                feedback=v.feedback
            )
            for v in variants
        ],
        selected_id=selected_id
    )


@router.patch("/{video_id}/update/{step}", response_model=UpdateContentResponse)
async def update_step_content(
    video_id: int,
    step: str,
    request: UpdateContentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update step content (manual edit). Creates new variant with edited content."""
    video = get_video_with_auth(db, video_id, current_user)
    validate_step(step, video)

    # Find current selected variant (parent)
    current_variant = db.query(StepHistory).filter(
        StepHistory.video_id == video_id,
        StepHistory.step_type == step,
        StepHistory.is_selected == True
    ).first()

    # Create new variant with edited content
    history = StepHistory(
        video_id=video_id,
        step_type=step,
        content=request.content,
        is_selected=True,
        feedback="[manual edit]",
        parent_id=current_variant.id if current_variant else None
    )

    # Deselect old variant
    if current_variant:
        current_variant.is_selected = False

    db.add(history)
    db.commit()
    db.refresh(history)

    # Update video with new content
    _copy_to_video(video, step, request.content)
    db.commit()

    logger.info(f"Updated {step} content for video {video_id}, variant_id={history.id}")

    return UpdateContentResponse(
        variant_id=history.id,
        step_type=step,
        content=request.content,
        is_selected=True
    )


class SwitchResponse(BaseModel):
    variant_id: int
    step_type: str
    content: Dict[str, Any]


@router.post("/{video_id}/switch/{variant_id}", response_model=SwitchResponse)
async def switch_variant(
    video_id: int,
    variant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Switch to a variant (for preview). Does NOT clear dependent steps."""
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

    db.commit()

    logger.info(f"Switched to variant {variant_id} for {step}")

    return SwitchResponse(
        variant_id=variant_id,
        step_type=step,
        content=variant.content
    )


class SelectHookRequest(BaseModel):
    hook_index: int


class SelectHookResponse(BaseModel):
    variant_id: int
    selected_hook: int


@router.post("/{video_id}/variant/{variant_id}/select-hook", response_model=SelectHookResponse)
async def select_hook(
    video_id: int,
    variant_id: int,
    request: SelectHookRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Select a specific hook within an ai_music variant."""
    video = get_video_with_auth(db, video_id, current_user)

    # Get variant
    variant = db.query(StepHistory).filter(
        StepHistory.id == variant_id,
        StepHistory.video_id == video_id
    ).first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    content = variant.content or {}
    variants_list = content.get("variants", [])

    if request.hook_index < 0 or request.hook_index >= len(variants_list):
        raise HTTPException(status_code=400, detail=f"Invalid hook_index: {request.hook_index}")

    # Update selected_hook in content
    content["selected_hook"] = request.hook_index
    variant.content = content

    # Flag the variant as modified for SQLAlchemy
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(variant, "content")

    db.commit()

    logger.info(f"Selected hook {request.hook_index} for variant {variant_id}")

    return SelectHookResponse(
        variant_id=variant_id,
        selected_hook=request.hook_index
    )


@router.post("/{video_id}/approve/{variant_id}", response_model=SelectResponse)
async def approve_variant(
    video_id: int,
    variant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a variant and move to next step. Clears dependent steps."""
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

    # Special handling for ai_music provider: merge video + selected hook
    if step == "audio" and variant.content.get("provider") == "ai_music":
        await _merge_audio_for_ai_music(video, variant, db)

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

    # Move to next step
    steps = get_steps_for_video(video)
    current_index = steps.index(step) if step in steps else -1
    if current_index < len(steps) - 1:
        video.current_step = steps[current_index + 1]
        # Reset to PENDING so frontend can trigger next step generation
        video.status = WorkflowStatus.PENDING
    else:
        # Last step - mark as completed
        video.status = WorkflowStatus.COMPLETED
        video.current_step = None

        # Generate publishing metadata
        await _generate_publishing_meta(video, db)

    db.commit()

    logger.info(f"Approved variant {variant_id} for {step}, next_step={video.current_step}, stale_steps={stale_steps}")

    return SelectResponse(
        variant_id=variant_id,
        step_type=step,
        stale_steps=stale_steps
    )


# Legacy endpoint - redirect to approve
@router.post("/{video_id}/select/{variant_id}", response_model=SelectResponse)
async def select_variant(
    video_id: int,
    variant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """DEPRECATED: Use /approve/{variant_id} instead. This now calls approve."""
    return await approve_variant(video_id, variant_id, db, current_user)


@router.post("/{video_id}/goto/{step}", response_model=GoToStepResponse)
async def goto_step(
    video_id: int,
    step: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Navigate to a specific step (for MANUAL mode back navigation)."""
    video = get_video_with_auth(db, video_id, current_user)
    validate_step(step, video)

    # Check if step has data (variants exist)
    has_variants = db.query(StepHistory).filter(
        StepHistory.video_id == video_id,
        StepHistory.step_type == step
    ).count() > 0

    # Update current step
    video.current_step = step
    video.status = WorkflowStatus.IN_PROGRESS
    db.commit()

    logger.info(f"Navigated to step {step} for video {video_id}")

    return GoToStepResponse(
        step=step,
        has_data=has_variants
    )


@router.post("/{video_id}/run-auto", response_model=RunAutoResponse)
async def run_auto(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Run all steps automatically (AUTO mode). Can resume from in_progress."""
    video = get_video_with_auth(db, video_id, current_user)

    # Allow pending or in_progress (resume after interruption)
    # Block if already completed or failed
    if video.status not in [WorkflowStatus.PENDING, WorkflowStatus.IN_PROGRESS]:
        logger.warning(f"run_auto called but video {video_id} status is {video.status}, skipping")
        return RunAutoResponse(
            video_id=video_id,
            status=video.status.value if video.status else "unknown",
            completed_steps=[],
            current_step=video.current_step if isinstance(video.current_step, str) else None,
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

            # For ai_music: auto-select first hook (index 0)
            if step == "audio" and content.get("provider") == "ai_music":
                content["selected_hook"] = 0

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

            # For ai_music: merge video + selected hook audio
            if step == "audio" and content.get("provider") == "ai_music":
                db.flush()  # Ensure history has ID
                await _merge_audio_for_ai_music(video, history, db)

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

        # Generate publishing metadata
        await _generate_publishing_meta(video, db)

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
    """Copy step content to appropriate Video field.

    Also restores source chain data (lineage) when selecting variants.
    """
    field = STEP_TO_VIDEO_FIELD.get(step)
    if not field:
        return

    if step in ["story", "description", "prompt", "scenario"]:
        # JSON fields
        setattr(video, field, content)
    elif step == "image":
        video.image_url = content.get("image_url")
        # Restore source chain
        if content.get("source_scenario"):
            video.scenario_data = content["source_scenario"]
    elif step == "video":
        video.video_url = content.get("video_url")
        video.video_task_id = content.get("video_task_id")
        # Restore source chain
        if content.get("source_image_url"):
            video.image_url = content["source_image_url"]
        if content.get("source_scenario"):
            video.scenario_data = content["source_scenario"]
    elif step == "audio":
        # For ai_music: set audio_data (final URL set after approve/merge)
        # For kling: set video_with_audio_url directly
        if content.get("provider") == "ai_music":
            video.audio_data = {
                "provider": "ai_music",
                "preview_url": content.get("preview_url"),
                "music_prompt": content.get("music_prompt"),
                "full_track_url": content.get("full_track_url"),
                "hook": content.get("hook"),
            }
        else:
            video.video_with_audio_url = content.get("audio_url")
            video.audio_variants = content.get("audio_variants")
        # Restore source chain
        if content.get("source_video_url"):
            video.video_url = content["source_video_url"]
        if content.get("source_image_url"):
            video.image_url = content["source_image_url"]
        if content.get("source_scenario"):
            video.scenario_data = content["source_scenario"]


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


async def _generate_publishing_meta(video: Video, db: Session):
    """Generate publishing metadata when workflow completes."""
    try:
        project = video.project
        if not project or not project.platforms:
            logger.info(f"Skipping publishing_meta: no project or platforms for video {video.id}")
            return

        # Get scenario data for context
        scenario_data = video.scenario_data or {}

        # Add story_template and content_variables if available
        if project.story_template and "story_template" not in scenario_data:
            scenario_data["story_template"] = project.story_template
        if video.content_variables and "content_variables" not in scenario_data:
            scenario_data["content_variables"] = video.content_variables

        # Generate publishing meta
        publishing_meta = await openai_service.generate_publishing_meta(
            platforms=project.platforms,
            scenario_data=scenario_data,
            fallback_text=scenario_data.get("image_prompt", project.story_template or "")
        )

        video.publishing_meta = publishing_meta
        logger.info(f"Generated publishing_meta for video {video.id}: {list(publishing_meta.keys())}")

    except Exception as e:
        # Non-blocking: log error but don't fail the workflow
        logger.error(f"Failed to generate publishing_meta for video {video.id}: {e}")


async def _merge_audio_for_ai_music(video: Video, variant, db: Session):
    """
    Merge video + selected audio hook for ai_music provider.

    Called when user approves an ai_music audio variant.
    Downloads video if needed, merges with selected hook audio.
    """
    from app.core.media_processor import media_processor
    from pathlib import Path

    try:
        content = variant.content

        # Get selected hook from variants array
        variants = content.get("variants", [])
        selected_hook_index = content.get("selected_hook", 0)

        if not variants or selected_hook_index >= len(variants):
            logger.error(f"ai_music merge: invalid variants or selected_hook in variant {variant.id}")
            return

        selected_variant = variants[selected_hook_index]
        hook = selected_variant.get("hook")
        local_audio_path = selected_variant.get("local_path")

        if not local_audio_path:
            logger.error(f"ai_music merge: no local_path in variant {variant.id}")
            return

        if not Path(local_audio_path).exists():
            logger.error(f"ai_music merge: audio file not found: {local_audio_path}")
            return

        # Get video path (download if needed)
        video_path = video.local_video_path
        if not video_path or not Path(video_path).exists():
            if not video.video_url:
                logger.error(f"ai_music merge: no video_url for video {video.id}")
                return
            logger.info(f"ai_music merge: downloading video for video {video.id}")
            video_path = await media_processor.download_file(video.video_url)

        # Merge video + audio
        logger.info(f"ai_music merge: merging video {video.id} with hook")
        merged_path = await media_processor.merge_video_audio(
            video_path=video_path,
            audio_path=local_audio_path,
        )

        # Move merged file to media directory for permanent storage
        import shutil
        from app.services.media_downloader import VIDEOS_DIR

        final_filename = f"video_{video.id}_with_audio.mp4"
        final_path = VIDEOS_DIR / final_filename
        shutil.move(merged_path, final_path)

        # Update video with merged URL and relative path
        video.video_with_audio_url = f"/api/files/videos/{final_filename}"
        video.local_audio_path = f"videos/{final_filename}"  # Relative path for frontend

        logger.info(f"ai_music merge: completed for video {video.id} -> {final_path}")

    except Exception as e:
        logger.error(f"ai_music merge failed for video {video.id}: {e}")
        # Don't fail the approval, just log the error
