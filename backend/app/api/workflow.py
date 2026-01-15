"""
Workflow API - 4-step video generation pipeline.

SCENARIO → IMAGE → VIDEO → AUDIO

Endpoints:
- POST /{video_id}/generate/{step} - Generate one step
- GET /{video_id}/variants/{step} - Get all variants for a step
- POST /{video_id}/select/{variant_id} - Select a variant
- POST /{video_id}/run-auto - Run all steps (AUTO mode)

TaskTracker integration (T9):
- Before calling external provider, check for active TaskTracker
- If task already RUNNING → return 409 Conflict
- If task COMPLETED → return cached result
- Store external_task_id for resume after page refresh
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime

import asyncio
from app.db.base import get_db
from app.models.video import Video, WorkflowStatus
from app.models.step_history import StepHistory, STEP_TO_VIDEO_FIELD, DISCOVER_STEPS, REMIX_STEPS, STEP_DEPENDENCIES
from app.models.task_tracker import TaskTracker, TaskStatus
from app.models.user import User, WorkspaceMember
from app.core.deps import get_current_user
from app.core.config import settings
from app.services.openai_service import openai_service
from app.services.kling_service import kling_service
from app.services.piapi_client import piapi_client, PiAPIError
from app.services import media_downloader
from app.services.mock_data import MOCK_IMAGE_URL, MOCK_VIDEO_URL
from app.schemas.task_tracker import TaskRunningResponse
from app.core.hook_analyzer import hook_analyzer
from app.core.media_processor import media_processor
from app.core.music_generator import music_generator
from pathlib import Path
import os

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# Video Lock (T9 - Prevent concurrent generation for same video)
# =============================================================================
_video_locks: Dict[int, asyncio.Lock] = {}


def get_video_lock(video_id: int) -> asyncio.Lock:
    """Get or create asyncio lock for a specific video.

    Prevents multiple concurrent requests from generating the same step.
    """
    if video_id not in _video_locks:
        _video_locks[video_id] = asyncio.Lock()
    return _video_locks[video_id]


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


# =============================================================================
# TaskTracker Helpers (T9 - Idempotent Generation)
# =============================================================================

def get_active_task_tracker(db: Session, video_id: int, step_type: str) -> Optional[TaskTracker]:
    """Find active (PENDING or RUNNING) TaskTracker for this video/step."""
    return db.query(TaskTracker).filter(
        TaskTracker.video_id == video_id,
        TaskTracker.step_type == step_type,
        TaskTracker.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING])
    ).first()


def get_completed_task_tracker(db: Session, video_id: int, step_type: str) -> Optional[TaskTracker]:
    """Find most recent COMPLETED TaskTracker for this video/step.

    Used to resume from completed external task without re-generating.
    """
    return db.query(TaskTracker).filter(
        TaskTracker.video_id == video_id,
        TaskTracker.step_type == step_type,
        TaskTracker.status == TaskStatus.COMPLETED
    ).order_by(TaskTracker.completed_at.desc()).first()


def create_task_tracker(db: Session, video_id: int, step_type: str, provider: str) -> TaskTracker:
    """Create new TaskTracker in PENDING state."""
    tracker = TaskTracker(
        video_id=video_id,
        step_type=step_type,
        provider=provider,
        status=TaskStatus.PENDING,
    )
    db.add(tracker)
    db.commit()
    db.refresh(tracker)
    logger.info(f"Created TaskTracker {tracker.id} for video {video_id}, step={step_type}")
    return tracker


async def check_external_task_status(tracker: TaskTracker) -> Dict[str, Any]:
    """
    Check status of external task via PiAPI.

    Returns dict with:
    - status: "running" | "completed" | "failed" | "unknown"
    - result: result data if completed
    - error: error message if failed
    """
    if not tracker.external_task_id:
        return {"status": "unknown", "error": "No external_task_id"}

    # Mock mode: check tracker status directly (no external call)
    if settings.MOCK_MODE:
        if tracker.external_task_id.startswith("mock_"):
            # In mock mode, task is "running" until completed in our DB
            if tracker.status == TaskStatus.COMPLETED:
                return {"status": "completed", "result": tracker.result}
            elif tracker.status == TaskStatus.FAILED:
                return {"status": "failed", "error": tracker.error_message}
            else:
                return {"status": "running"}

    try:
        response = await piapi_client.get_task_status(tracker.external_task_id)
        data = response.get("data", response)
        status = data.get("status", "").lower()

        if status in ["completed", "succeeded", "success"]:
            return {"status": "completed", "result": data}
        elif status in ["failed", "error"]:
            error_msg = data.get("error", {}).get("message", str(data))
            return {"status": "failed", "error": error_msg}
        else:
            return {"status": "running"}
    except Exception as e:
        logger.error(f"Failed to check task status {tracker.external_task_id}: {e}")
        return {"status": "unknown", "error": str(e)}


def raise_task_running(tracker: TaskTracker):
    """Raise 409 HTTPException for already running task."""
    raise HTTPException(
        status_code=409,
        detail=TaskRunningResponse(
            task_id=tracker.id,
            status="running",
            message=f"Task already running for step {tracker.step_type}"
        ).model_dump()
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

        # Add negative prompt suffix if provided
        negative_prompt = video.scenario_data.get("negative_prompt") if video.scenario_data else None
        full_prompt = prompt
        if negative_prompt:
            full_prompt = f"{prompt} --no {negative_prompt}"

        # T9: Create TaskTracker and call piapi_client directly
        tracker = create_task_tracker(db, video.id, "image", "kling")
        try:
            if settings.MOCK_MODE:
                # Mock mode: simulate async task with delay
                logger.info("MOCK MODE: Simulating image generation (10s delay)")
                tracker.external_task_id = f"mock_image_{video.id}"
                tracker.status = TaskStatus.RUNNING
                tracker.started_at = datetime.utcnow()
                db.commit()
                await asyncio.sleep(2)  # 10 sec delay for manual testing
                image_url = MOCK_IMAGE_URL
            else:
                # Real mode: call piapi_client
                task_id = await piapi_client.create_image_task(
                    prompt=full_prompt,
                    aspect_ratio=project.aspect_ratio or "9:16",
                )
                tracker.external_task_id = task_id
                tracker.status = TaskStatus.RUNNING
                tracker.started_at = datetime.utcnow()
                db.commit()
                image_url = await piapi_client.wait_for_image(task_id)

            # Update tracker
            tracker.status = TaskStatus.COMPLETED
            tracker.completed_at = datetime.utcnow()
            tracker.result = {"image_url": image_url}
            db.commit()

        except (PiAPIError, TimeoutError) as e:
            tracker.status = TaskStatus.FAILED
            tracker.error_message = str(e)
            tracker.completed_at = datetime.utcnow()
            db.commit()
            raise

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

        # T9: Create TaskTracker and call piapi_client directly
        tracker = create_task_tracker(db, video.id, "video", "kling")
        try:
            if settings.MOCK_MODE:
                # Mock mode: simulate async task with delay
                logger.info("MOCK MODE: Simulating video generation (15s delay)")
                task_id = f"mock_video_{video.id}"
                tracker.external_task_id = task_id
                tracker.status = TaskStatus.RUNNING
                tracker.started_at = datetime.utcnow()
                db.commit()
                await asyncio.sleep(3)  # 15 sec delay for manual testing
                video_url = MOCK_VIDEO_URL
            else:
                # Real mode: call piapi_client
                task_id = await piapi_client.create_video_task(
                    prompt=motion_prompt,
                    image_url=video.image_url,
                    duration=project.duration or 5,
                    aspect_ratio=project.aspect_ratio or "9:16",
                )
                tracker.external_task_id = task_id
                tracker.status = TaskStatus.RUNNING
                tracker.started_at = datetime.utcnow()
                db.commit()
                video_url = await piapi_client.wait_for_video(task_id)

            # Update tracker
            tracker.status = TaskStatus.COMPLETED
            tracker.completed_at = datetime.utcnow()
            tracker.result = {"video_url": video_url, "task_id": task_id}
            db.commit()

        except (PiAPIError, TimeoutError) as e:
            tracker.status = TaskStatus.FAILED
            tracker.error_message = str(e)
            tracker.completed_at = datetime.utcnow()
            db.commit()
            raise

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

        # Check if audio should be skipped
        if project and project.audio_mode == "none":
            return {
                "audio_variants": [],
                "video_with_audio_url": video.video_url,
                "provider": "skip",
                "skipped": True,
                "source_video_url": video.video_url,
                "source_image_url": video.image_url,
                "source_scenario": scenario_data
            }

        # T9: Handle different providers with TaskTracker
        if provider_name == "ai_music":
            # ai_music: call piapi_client directly (like image/video)
            # 1. Generate prompt (fast)
            previous_prompt = video.audio_data.get("music_prompt") if video.audio_data else None
            music_prompt, tags = await music_generator.generate_prompt(
                video, feedback=feedback, previous_prompt=previous_prompt
            )

            tracker = create_task_tracker(db, video.id, "audio", "ai_music")
            try:
                if settings.MOCK_MODE:
                    # Mock mode: simulate with delay
                    logger.info("MOCK MODE: Simulating ai_music generation")
                    task_id = f"mock_music_{video.id}"
                    tracker.external_task_id = task_id
                    tracker.status = TaskStatus.RUNNING
                    tracker.started_at = datetime.utcnow()
                    db.commit()
                    await asyncio.sleep(2)
                    # Mock tracks (use real URLs in prod)
                    tracks = [{"audio_url": MOCK_VIDEO_URL, "title": "Mock Track", "duration": 60}]
                else:
                    # 2. Create Suno task and SAVE task_id BEFORE polling
                    task_id = await piapi_client.create_music_task(
                        prompt=music_prompt,
                        tags=tags,
                    )
                    tracker.external_task_id = task_id  # ← Crash recovery possible!
                    tracker.status = TaskStatus.RUNNING
                    tracker.started_at = datetime.utcnow()
                    db.commit()

                    # 3. Poll for completion (long, ~3-5 min)
                    tracks = await piapi_client.wait_for_music(task_id)

                # 4. Process tracks: download, hook analysis, trim (fast, ~30 sec)
                variants = await _process_music_tracks(video, tracks)

                tracker.status = TaskStatus.COMPLETED
                tracker.completed_at = datetime.utcnow()
                tracker.result = {
                    "provider": "ai_music",
                    "variant_count": len(variants),
                    "tracks": tracks,  # For crash recovery
                    "music_prompt": music_prompt,
                    "tags": tags,
                }
                db.commit()

                result = {
                    "variants": variants,
                    "tracks": tracks,
                    "music_prompt": music_prompt,
                    "tags": tags,
                    "provider": "ai_music",
                }

            except Exception as e:
                tracker.status = TaskStatus.FAILED
                tracker.error_message = str(e)
                tracker.completed_at = datetime.utcnow()
                db.commit()
                raise

        elif provider_name == "kling":
            # kling: call piapi_client directly
            video_task_id = video.video_task_id
            if not video_task_id and not settings.MOCK_MODE:
                raise HTTPException(status_code=400, detail="video_task_id not found. Run video step first.")

            tracker = create_task_tracker(db, video.id, "audio", "kling")
            try:
                if settings.MOCK_MODE:
                    # Mock mode: simulate async task with delay
                    logger.info("MOCK MODE: Simulating audio generation (10s delay)")
                    task_id = f"mock_audio_{video.id}"
                    tracker.external_task_id = task_id
                    tracker.status = TaskStatus.RUNNING
                    tracker.started_at = datetime.utcnow()
                    db.commit()
                    await asyncio.sleep(2)  # 10 sec delay for manual testing
                    audio_variants = [MOCK_VIDEO_URL] * 4  # 4 variants
                else:
                    # Real mode: call piapi_client
                    task_id = await piapi_client.create_sound_task(origin_task_id=video_task_id)
                    tracker.external_task_id = task_id
                    tracker.status = TaskStatus.RUNNING
                    tracker.started_at = datetime.utcnow()
                    db.commit()
                    audio_variants = await piapi_client.wait_for_sound(task_id)

                tracker.status = TaskStatus.COMPLETED
                tracker.completed_at = datetime.utcnow()
                tracker.result = {"audio_variants": audio_variants}
                db.commit()

                result = {
                    "audio_variants": audio_variants,
                    "video_with_audio_url": audio_variants[0] if audio_variants else video.video_url,
                    "provider": "kling",
                }

            except (PiAPIError, TimeoutError) as e:
                tracker.status = TaskStatus.FAILED
                tracker.error_message = str(e)
                tracker.completed_at = datetime.utcnow()
                db.commit()
                raise

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

    # T9: Check TaskTracker for async steps (image, video, audio)
    # These steps use external APIs that take minutes to complete
    async_steps = ["image", "video", "audio"]
    completed_content = None  # Content from completed tracker (if exists)

    if step in async_steps:
        tracker = get_active_task_tracker(db, video.id, step)
        if tracker:
            # Active tracker exists (PENDING or RUNNING) - handle accordingly
            if tracker.status == TaskStatus.PENDING:
                # Task created but not started yet - return 409
                logger.info(f"Task {tracker.id} is PENDING for video {video.id}, step={step}")
                raise_task_running(tracker)

            elif tracker.status == TaskStatus.RUNNING:
                # Check external task status
                ext_status = await check_external_task_status(tracker)

                if ext_status["status"] == "running":
                    # Task still running - return 409
                    logger.info(f"Task {tracker.id} still running for video {video.id}, step={step}")
                    raise_task_running(tracker)

                elif ext_status["status"] == "completed":
                    # Task completed externally - update tracker and use result
                    logger.info(f"Task {tracker.id} completed externally, using result")
                    tracker.status = TaskStatus.COMPLETED
                    tracker.completed_at = datetime.utcnow()
                    db.commit()
                    # Use result from tracker
                    if tracker.result:
                        completed_content = tracker.result

                elif ext_status["status"] == "failed":
                    # Task failed - mark tracker and allow retry
                    logger.info(f"Task {tracker.id} failed externally: {ext_status.get('error')}")
                    tracker.status = TaskStatus.FAILED
                    tracker.error_message = ext_status.get("error", "External task failed")
                    tracker.completed_at = datetime.utcnow()
                    db.commit()
                    # Fall through to create new tracker

        # T9: Check for completed tracker with result (avoid duplicate generation)
        if not tracker or tracker.status != TaskStatus.RUNNING:
            completed_tracker = get_completed_task_tracker(db, video.id, step)
            if completed_tracker and completed_tracker.result and not completed_content:
                logger.info(f"Using result from completed tracker {completed_tracker.id} for step {step}")
                completed_content = completed_tracker.result

    # Legacy check for non-async steps (scenario)
    if step not in async_steps and video.status == WorkflowStatus.IN_PROGRESS and video.current_step == step:
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

        # Generate content (with optional feedback) or use completed tracker result
        if completed_content:
            content = completed_content
            logger.info(f"Using content from completed tracker for step {step}")

            # T9: If using completed tracker content, check if StepHistory already exists
            # (prevents duplicate creation from race conditions)
            existing_history = db.query(StepHistory).filter(
                StepHistory.video_id == video_id,
                StepHistory.step_type == step,
                StepHistory.is_selected == True
            ).first()

            if existing_history:
                # StepHistory already exists - just return it
                logger.info(f"StepHistory already exists for step {step}, returning existing")
                _copy_to_video(video, step, existing_history.content)
                db.commit()
                return GenerateResponse(
                    variant_id=existing_history.id,
                    step_type=step,
                    content=existing_history.content,
                    is_selected=existing_history.is_selected
                )
        else:
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

    # T9: Try to acquire lock - if already locked, return in_progress immediately
    lock = get_video_lock(video_id)
    if lock.locked():
        logger.info(f"run_auto: Video {video_id} is locked, returning in_progress")
        return RunAutoResponse(
            video_id=video_id,
            status="in_progress",
            completed_steps=[],
            current_step=video.current_step.value if video.current_step else None,
            error=None
        )

    async with lock:
        # Re-fetch video after acquiring lock (state might have changed)
        db.refresh(video)

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

                # T9: Check for active TaskTracker before generating
                async_steps = ["image", "video", "audio"]
                content = None  # Will be set by generation or from completed tracker

                if step in async_steps:
                    tracker = get_active_task_tracker(db, video.id, step)
                    if tracker:
                        # Active tracker exists (PENDING or RUNNING) - check status
                        if tracker.status == TaskStatus.PENDING:
                            # Task created but not started yet - return in_progress
                            logger.info(f"run-auto: Task {tracker.id} is PENDING for step {step}, returning in_progress")
                            return RunAutoResponse(
                                video_id=video_id,
                                status="in_progress",
                                completed_steps=completed_steps,
                                current_step=step,
                                error=None
                            )
                        elif tracker.status == TaskStatus.RUNNING:
                            # Check external status
                            ext_status = await check_external_task_status(tracker)
                            if ext_status["status"] == "running":
                                # Task still running - return in_progress so frontend keeps polling
                                logger.info(f"run-auto: Task {tracker.id} still running for step {step}, returning in_progress")
                                return RunAutoResponse(
                                    video_id=video_id,
                                    status="in_progress",
                                    completed_steps=completed_steps,
                                    current_step=step,
                                    error=None
                                )
                            elif ext_status["status"] == "completed":
                                # Resume completed task
                                tracker.status = TaskStatus.COMPLETED
                                tracker.completed_at = datetime.utcnow()

                                # ai_music: need to process tracks after Suno completed
                                if step == "audio" and tracker.provider == "ai_music":
                                    ext_result = ext_status.get("result", {})
                                    # Extract tracks from Suno output
                                    output = ext_result.get("output", [])
                                    if isinstance(output, list):
                                        tracks = [{"audio_url": t.get("audio_url"), "title": t.get("title", "Track"), "duration": t.get("metadata", {}).get("duration", 0)} for t in output if t.get("audio_url")]
                                        if tracks:
                                            logger.info(f"run-auto: Resuming ai_music - processing {len(tracks)} tracks")
                                            variants = await _process_music_tracks(video, tracks)
                                            content = {
                                                "variants": variants,
                                                "tracks": tracks,
                                                "provider": "ai_music",
                                            }
                                            tracker.result = {"provider": "ai_music", "variant_count": len(variants), "tracks": tracks}
                                db.commit()
                            elif ext_status["status"] == "failed":
                                # Mark as failed, allow retry
                                tracker.status = TaskStatus.FAILED
                                tracker.error_message = ext_status.get("error")
                                db.commit()

                    # T9: Check for completed tracker with result (avoid duplicate generation)
                    if not tracker or tracker.status != TaskStatus.RUNNING:
                        completed_tracker = get_completed_task_tracker(db, video.id, step)
                        if completed_tracker and completed_tracker.result:
                            # Use result from completed tracker instead of re-generating
                            logger.info(f"run-auto: Using result from completed tracker {completed_tracker.id} for step {step}")
                            tracker_result = completed_tracker.result

                            # ai_music: if result has tracks but no variants, generate variants
                            if step == "audio" and tracker_result.get("provider") == "ai_music":
                                if tracker_result.get("tracks") and not tracker_result.get("variants"):
                                    logger.info(f"run-auto: Generating variants from stored tracks")
                                    variants = await _process_music_tracks(video, tracker_result["tracks"])
                                    content = {
                                        "variants": variants,
                                        "tracks": tracker_result["tracks"],
                                        "music_prompt": tracker_result.get("music_prompt"),
                                        "tags": tracker_result.get("tags"),
                                        "provider": "ai_music",
                                    }
                                else:
                                    content = tracker_result
                            else:
                                content = tracker_result

                # Generate only if no content from completed tracker
                if content is None:
                    content = await generate_step_content(step, video, db)

                # For ai_music: auto-select first hook (index 0)
                if step == "audio" and content.get("provider") == "ai_music":
                    content["selected_hook"] = 0

                # T9: Re-check for existing StepHistory before creating (prevent race condition duplicates)
                existing_now = db.query(StepHistory).filter(
                    StepHistory.video_id == video_id,
                    StepHistory.step_type == step,
                    StepHistory.is_selected == True
                ).first()

                if existing_now:
                    # Another request already created StepHistory - use it, skip creation
                    logger.info(f"run-auto: StepHistory already exists for step {step}, skipping creation")
                    _copy_to_video(video, step, existing_now.content)
                    history = existing_now
                else:
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


async def _process_music_tracks(video: Video, tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process music tracks: download, analyze hooks, trim.

    Args:
        video: Video model
        tracks: List of track dicts from Suno with audio_url, title, duration

    Returns:
        List of variant dicts with preview URLs for hook selection
    """
    hook_duration = video.project.duration if video.project else 5.0

    # Directories
    temp_dir = Path(settings.TEMP_DIR)
    audio_dir = Path(settings.MEDIA_AUDIO_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    all_variants = []
    global_index = 0

    for track_index, track in enumerate(tracks):
        track_url = track.get("audio_url")
        track_title = track.get("title", f"Track {track_index + 1}")

        if not track_url:
            logger.warning(f"Track {track_index} has no audio_url, skipping")
            continue

        logger.info(f"Processing track {track_index + 1}/{len(tracks)}: {track_title}")

        # Download track to temp storage
        local_track_path = await media_processor.download_file(
            url=track_url,
            dest_path=str(temp_dir / f"track_{video.id}_{track_index}_{os.urandom(4).hex()}.mp3"),
        )

        # Find hooks using GPT-4o-audio-preview
        logger.info(f"Analyzing track {track_index + 1} for hooks...")
        hooks = await hook_analyzer.find_hooks(
            audio_path=local_track_path,
            video=video,
            num_hooks=4,
            hook_duration=float(hook_duration),
        )

        # Trim each hook with fade in/out
        logger.info(f"Trimming {len(hooks)} hooks from track {track_index + 1}...")
        for i, hook in enumerate(hooks):
            global_idx = global_index + i
            output_filename = f"{video.id}_t{track_index}_hook_{i}_{int(hook.start)}_{int(hook.end)}.mp3"
            output_path = str(audio_dir / output_filename)

            try:
                trimmed_path = await media_processor.trim_audio(
                    audio_path=local_track_path,
                    start=hook.start,
                    end=hook.end,
                    fade_in=0.5,
                    fade_out=0.5,
                    output_path=output_path,
                )

                preview_url = f"/api/files/audio/{output_filename}"
                all_variants.append({
                    "hook": hook.to_dict(),
                    "preview_url": preview_url,
                    "local_path": trimmed_path,
                    "video_id": video.id,
                    "index": global_idx,
                    "track_index": track_index,
                    "track_title": track_title,
                    "hook_index": i,
                })

            except Exception as e:
                logger.error(f"Failed to trim track {track_index} hook {i}: {e}")

        global_index += len(hooks)

        # Cleanup temp track
        try:
            os.remove(local_track_path)
        except OSError:
            pass

    logger.info(f"Generated {len(all_variants)} variants from {len(tracks)} tracks for video {video.id}")
    return all_variants


async def _download_media_for_step(video: Video, step: str):
    """Download media files locally after generation (non-blocking, best-effort).

    Skips download if file already exists locally.
    """
    try:
        if step == "image" and video.image_url:
            # Skip if already downloaded
            if video.local_image_path:
                logger.info(f"Image already downloaded for video {video.id}, skipping")
                return
            local_path = await media_downloader.download_image(video.image_url, video.id)
            if local_path:
                video.local_image_path = local_path
                logger.info(f"Downloaded image for video {video.id}: {local_path}")

        elif step == "video" and video.video_url:
            # Skip if already downloaded
            if video.local_video_path:
                logger.info(f"Video already downloaded for video {video.id}, skipping")
                return
            local_path = await media_downloader.download_video(video.video_url, video.id, "video")
            if local_path:
                video.local_video_path = local_path
                logger.info(f"Downloaded video for video {video.id}: {local_path}")

        elif step == "audio" and video.video_with_audio_url:
            # Skip if already downloaded
            if video.local_audio_path:
                logger.info(f"Audio already downloaded for video {video.id}, skipping")
                return
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
