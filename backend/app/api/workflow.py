"""
Workflow API endpoints for video generation pipeline.
Handles 8-stage workflow: Story → Description → Prompt → Image → Scenario → Video → Audio → Adaptation
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.base import get_db
from app.models.video import Video, WorkflowMode
from app.models.workflow_step import WorkflowStep, WorkflowStatus, StepType
from app.models.user import User
from app.core.deps import get_current_user, get_image_service, get_video_service, get_audio_service

from app.schemas.workflow import (
    GenerateStoryRequest, GenerateDescriptionRequest, GeneratePromptRequest,
    GenerateImageRequest, GenerateScenarioRequest, GenerateVideoRequest,
    GenerateAudioRequest, SelectAudioVariantRequest, AdaptForPlatformsRequest,
    ApprovalRequest, AutoGenerateRequest, PreviewPromptRequest, PreviewPromptResponse
)

from app.services.openai_service import openai_service
from app.services.workflow.steps import (
    StoryStep, DescriptionStep, PromptStep, ScenarioStep,
    AdaptationStep, ImageStep, VideoStep, AudioStep,
)
from app.services.workflow.approval import ApprovalHandler
from app.services.workflow.prompt_preview import PromptPreviewBuilder
from app.api.workflow_helpers import (
    build_camera_control, get_video_with_auth, verify_video_ownership
)

router = APIRouter()


# -----------------------------------------------------------------------------
# Prompt Preview
# -----------------------------------------------------------------------------

@router.post("/preview-prompt", response_model=PreviewPromptResponse)
async def preview_prompt(
    request: PreviewPromptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Preview the prompt that will be sent to AI for a specific step."""
    video = get_video_with_auth(db, request.video_id, current_user)
    project = video.project
    project_prompts = project.system_prompts if project and project.system_prompts else {}

    builder = PromptPreviewBuilder(video, project_prompts)
    prompt_data = builder.build(request.step_type, request.context or {})

    return PreviewPromptResponse(
        system_prompt=prompt_data.system_prompt,
        user_prompt=prompt_data.user_prompt,
        step_type=request.step_type.value,
        can_edit=True
    )


# -----------------------------------------------------------------------------
# Text Generation Steps (Story, Description, Prompt, Scenario, Adaptation)
# -----------------------------------------------------------------------------

@router.post("/generate-story")
async def generate_story(
    request: GenerateStoryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stage 1: Generate story/concept."""
    video = get_video_with_auth(db, request.video_id, current_user)
    step = StoryStep(db, video)
    return await step.execute(request, request.custom_prompt)


@router.post("/generate-description")
async def generate_description(
    request: GenerateDescriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stage 2: Generate detailed visual description."""
    video = get_video_with_auth(db, request.video_id, current_user)
    if request.story_data:
        video.story_data = request.story_data
    step = DescriptionStep(db, video)
    return await step.execute(request, request.custom_prompt)


@router.post("/generate-prompt")
async def generate_prompt(
    request: GeneratePromptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stage 3: Generate image prompt."""
    video = get_video_with_auth(db, request.video_id, current_user)
    if request.description_data:
        video.description_data = request.description_data
    step = PromptStep(db, video)
    return await step.execute(request, request.custom_prompt)


@router.post("/generate-scenario")
async def generate_scenario(
    request: GenerateScenarioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stage 5: Generate video motion scenario."""
    video = get_video_with_auth(db, request.video_id, current_user)
    if request.image_url:
        video.image_url = request.image_url
    if request.description_data:
        video.description_data = request.description_data
    step = ScenarioStep(db, video)
    return await step.execute(request, request.custom_prompt)


@router.post("/adapt-for-platforms")
async def adapt_for_platforms(
    request: AdaptForPlatformsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stage 7: Adapt content for social platforms."""
    video = get_video_with_auth(db, request.video_id, current_user)
    if request.scenario_data:
        video.scenario_data = request.scenario_data
    if video.project and request.platforms:
        video.project.platforms = request.platforms
    step = AdaptationStep(db, video)
    return await step.execute(request, request.custom_prompt)


# -----------------------------------------------------------------------------
# Media Generation Steps (Image, Video, Audio)
# -----------------------------------------------------------------------------

@router.post("/generate-image")
async def generate_image(
    request: GenerateImageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stage 4: Generate image (provider-agnostic)."""
    video = get_video_with_auth(db, request.video_id, current_user)

    prompt_str = request.prompt
    negative_prompt = None
    style_suffix = None

    # Handle remix mode template refill
    if request.refill_from_template and video.project and video.project.project_type == "remix":
        filled_prompt = video.project.story_template or ""
        for key, value in (video.content_variables or {}).items():
            value_str = ", ".join(f"{k}: {v}" for k, v in value.items()) if isinstance(value, dict) else str(value)
            filled_prompt = filled_prompt.replace(f"{{{key}}}", value_str)
        prompt_str = filled_prompt
        video.image_prompt = filled_prompt
        db.commit()

    if request.prompt_data:
        prompt_str = prompt_str or request.prompt_data.get("main_prompt", "")
        negative_prompt = request.prompt_data.get("negative_prompt")
        style_suffix = request.prompt_data.get("style_suffix")

    if not prompt_str:
        raise HTTPException(status_code=400, detail="Either prompt or prompt_data.main_prompt is required")

    step = ImageStep(db, video, get_image_service())
    return await step.execute(
        prompt=prompt_str,
        aspect_ratio=request.aspect_ratio,
        negative_prompt=negative_prompt,
        style_suffix=style_suffix,
        mode=request.mode
    )


@router.post("/generate-video")
async def generate_video(
    request: GenerateVideoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stage 6: Generate video (provider-agnostic)."""
    video = get_video_with_auth(db, request.video_id, current_user)

    prompt = request.scenario_data.get("motion_prompt", "") or request.scenario_data.get("scene_direction", "")
    camera_control = build_camera_control(request.scenario_data.get("camera_movement"))

    step = VideoStep(db, video, get_video_service())
    return await step.execute(
        image_url=request.image_url,
        prompt=prompt,
        duration=request.duration,
        camera_control=camera_control,
        mode=request.mode
    )


@router.post("/generate-audio")
async def generate_audio(
    request: GenerateAudioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stage 7: Generate audio variants (provider-agnostic)."""
    video = get_video_with_auth(db, request.video_id, current_user)

    step = AudioStep(db, video, get_audio_service())
    result = await step.execute(video_task_id=video.video_task_id)

    if result.get("status") == "completed":
        result["message"] = "4 audio variants generated. Please select one."
    return result


@router.post("/select-audio-variant")
async def select_audio_variant(
    request: SelectAudioVariantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Select one of 4 audio variants and finalize video."""
    video = get_video_with_auth(db, request.video_id, current_user)

    if not video.audio_variants:
        raise HTTPException(status_code=400, detail="No audio variants available. Generate audio first.")
    if request.variant_index >= len(video.audio_variants):
        raise HTTPException(status_code=400, detail=f"Invalid variant index. Available: 0-{len(video.audio_variants)-1}")

    # Select variant and update video
    selected_url = video.audio_variants[request.variant_index]
    video.video_with_audio_url = selected_url

    # Approve audio step
    audio_step = db.query(WorkflowStep).filter(
        WorkflowStep.video_id == video.id,
        WorkflowStep.step_type == StepType.AUDIO
    ).first()
    if audio_step:
        audio_step.status = WorkflowStatus.APPROVED
        audio_step.user_approved = True
        audio_step.user_feedback = f"Selected variant {request.variant_index + 1}"

    db.commit()

    # Generate publishing metadata
    project = video.project
    platforms = project.platforms if project else ["youtube"]
    prompt_context = (
        video.image_prompt or
        (video.story_data.get("concept", "") if video.story_data else "") or
        (project.story_template if project else "") or
        "Video content"
    )

    try:
        meta = await openai_service.generate_publishing_meta(
            prompt_or_template=prompt_context,
            platforms=platforms,
            image_url=video.image_url
        )
        video.publishing_meta = meta
    except Exception:
        video.publishing_meta = {}

    video.status = WorkflowStatus.COMPLETED
    db.commit()

    return {
        "message": f"Selected audio variant {request.variant_index + 1}. Video ready for publishing.",
        "video_with_audio_url": selected_url,
        "publishing_meta": video.publishing_meta
    }


# -----------------------------------------------------------------------------
# Publishing Metadata
# -----------------------------------------------------------------------------

@router.post("/generate-meta")
async def generate_publishing_meta(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate publishing metadata (title, description, hashtags)."""
    video = get_video_with_auth(db, video_id, current_user)

    if not video.project:
        raise HTTPException(status_code=400, detail="Video has no project")

    platforms = video.project.platforms or ["youtube"]
    prompt_context = (
        video.image_prompt or
        video.story_data.get("concept", "") if video.story_data else "" or
        video.project.story_template or
        "Video content"
    )

    meta = await openai_service.generate_publishing_meta(
        prompt_or_template=prompt_context,
        platforms=platforms,
        image_url=video.image_url
    )

    video.publishing_meta = meta
    db.commit()

    return {"video_id": video_id, "publishing_meta": meta}


@router.patch("/update-meta")
async def update_publishing_meta(
    video_id: int,
    meta: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update publishing metadata (user edits)."""
    video = get_video_with_auth(db, video_id, current_user)
    video.publishing_meta = meta
    db.commit()
    return {"video_id": video_id, "publishing_meta": meta}


# -----------------------------------------------------------------------------
# Step Approval
# -----------------------------------------------------------------------------

@router.post("/approve-step")
async def approve_step(
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve or reject a workflow step."""
    step = db.query(WorkflowStep).filter(WorkflowStep.id == request.step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    verify_video_ownership(db, step.video, current_user)

    handler = ApprovalHandler(db, step)
    return await handler.handle_approval(
        approved=request.approved,
        feedback=request.feedback,
        regenerate=request.regenerate
    )


# -----------------------------------------------------------------------------
# Auto-Generation
# -----------------------------------------------------------------------------

@router.post("/auto-generate-to-video")
async def auto_generate_to_video(
    request: AutoGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Automatic video generation using WorkflowOrchestrator.

    Supports:
    - Discover mode: Story → Description → Prompt → Image → Scenario → Video → Audio
    - Remix mode: Template → Image → Video → Audio
    - Resume after image approval
    """
    from app.services.workflow.orchestrator import WorkflowOrchestrator, WorkflowResult

    video = get_video_with_auth(db, request.video_id, current_user)

    try:
        orchestrator = WorkflowOrchestrator(db, video)
        result: WorkflowResult = await orchestrator.run()

        response = {
            "video_id": result.video_id,
            "message": result.message,
            "total_time_seconds": result.total_time_seconds,
            "steps_completed": result.steps_completed,
            "mode": result.mode
        }

        if result.paused_for_approval:
            response["paused_for_approval"] = True
        if result.next_action:
            response["next_action"] = result.next_action
        if result.audio_variants:
            response["audio_variants"] = result.audio_variants
        if result.audio_skipped:
            response["audio_skipped"] = True

        return response

    except Exception as e:
        video.status = WorkflowStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# Approve and Continue (New Breakpoints System)
# -----------------------------------------------------------------------------

@router.post("/{video_id}/{step_type}/approve-and-continue")
async def approve_and_continue(
    video_id: int,
    step_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve current step and continue workflow to next step.

    Used with new breakpoints system (USE_NEW_BREAKPOINTS=true).
    In MANUAL mode, workflow pauses after each step for user approval.
    This endpoint approves the current step and continues execution.
    """
    from app.services.workflow.orchestrator import WorkflowOrchestrator, WorkflowResult

    video = get_video_with_auth(db, video_id, current_user)

    # Validate step type
    try:
        expected_step = StepType(step_type.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid step type: {step_type}")

    # Verify step matches current step
    if video.current_step != expected_step:
        raise HTTPException(
            status_code=400,
            detail=f"Expected step {video.current_step.value}, got {step_type}"
        )

    # Verify workflow is awaiting approval
    if video.status != WorkflowStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Workflow not awaiting approval (status: {video.status.value})"
        )

    try:
        orchestrator = WorkflowOrchestrator(db, video)
        result: WorkflowResult = await orchestrator.resume_workflow()

        response = {
            "video_id": result.video_id,
            "message": result.message,
            "total_time_seconds": result.total_time_seconds,
            "steps_completed": result.steps_completed,
            "mode": result.mode
        }

        if result.paused_for_approval:
            response["paused_for_approval"] = True
        if result.next_action:
            response["next_action"] = result.next_action
        if result.audio_variants:
            response["audio_variants"] = result.audio_variants
        if result.audio_skipped:
            response["audio_skipped"] = True

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error resuming workflow: {e}")
        video.status = WorkflowStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
