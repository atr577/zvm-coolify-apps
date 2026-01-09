from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from app.db.base import get_db
from app.models.video import Video, WorkflowMode
from app.models.workflow_step import WorkflowStep, WorkflowStatus, StepType
from app.models.validation_result import ValidationResult, ValidationStatus
from app.models.user import User, WorkspaceMember
from app.core.deps import get_current_user
from app.schemas.workflow import (
    GenerateStoryRequest,
    GenerateDescriptionRequest,
    GeneratePromptRequest,
    GenerateImageRequest,
    GenerateScenarioRequest,
    GenerateVideoRequest,
    GenerateAudioRequest,
    SelectAudioVariantRequest,
    AdaptForPlatformsRequest,
    ApprovalRequest,
    AutoGenerateRequest,
    PreviewPromptRequest,
    PreviewPromptResponse,
    StepTypeEnum,
    CustomPrompt
)
from app.services.openai_service import openai_service
from app.services.kling_service import kling_service
from app.services.prompt_builders import (
    build_story_prompt,
    build_description_prompt,
    build_image_prompt_prompt,
    build_scenario_prompt,
    build_adaptation_prompt,
    PromptData
)
from app.services.workflow.steps import (
    StoryStep,
    DescriptionStep,
    PromptStep,
    ScenarioStep,
    AdaptationStep,
    ImageStep,
    VideoStep,
    AudioStep,
)
from app.core.deps import get_image_service, get_video_service, get_audio_service

router = APIRouter()


def build_camera_control(camera_movement: dict) -> dict | None:
    """
    Преобразует camera_movement из scenario в camera_control для KLING API.

    Args:
        camera_movement: Dict с полями type, speed, description из scenario

    Returns:
        camera_control dict для KLING или None если static
    """
    if not camera_movement or not isinstance(camera_movement, dict):
        return None

    camera_type = camera_movement.get("type", "static")
    if camera_type == "static":
        return None

    return {
        "type": camera_type,
        "config": {
            "horizontal": 0,
            "vertical": 0,
            "pan": -5 if camera_type == "pan_left" else 5 if camera_type == "pan_right" else 0,
            "tilt": 5 if camera_type == "tilt_up" else -5 if camera_type == "tilt_down" else 0,
            "zoom": 5 if camera_type == "zoom_in" else -5 if camera_type == "zoom_out" else 0,
            "roll": 0
        }
    }


def get_user_workspace_ids(db: Session, user_id: int) -> List[int]:
    """Get all workspace IDs the user is a member of"""
    memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).all()
    return [m.workspace_id for m in memberships]


def verify_video_ownership(db: Session, video: Video, current_user: User):
    """Проверка доступа к видео через workspace"""
    workspace_ids = get_user_workspace_ids(db, current_user.id)
    if video.project.workspace_id not in workspace_ids:
        raise HTTPException(status_code=403, detail="Access denied: you don't own this video")


def get_or_create_step(db: Session, video_id: int, step_type: StepType) -> WorkflowStep:
    """
    Get existing PENDING step or create a new one.
    This prevents duplicate steps when manually triggering generation.
    """
    # Check for existing PENDING step
    step = db.query(WorkflowStep).filter(
        WorkflowStep.video_id == video_id,
        WorkflowStep.step_type == step_type,
        WorkflowStep.status == WorkflowStatus.PENDING
    ).first()

    if step:
        # Update existing step
        step.status = WorkflowStatus.IN_PROGRESS
        step.started_at = datetime.utcnow()
    else:
        # Create new step only if no pending exists
        step = WorkflowStep(
            video_id=video_id,
            step_type=step_type,
            status=WorkflowStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        db.add(step)

    db.commit()
    db.refresh(step)
    return step


async def validate_and_save(
    db: Session,
    step: WorkflowStep,
    content: dict,
    step_type: str,
    previous_data: dict = None
):
    """Валидация контента и сохранение результата"""
    validation_result_data = await openai_service.validate_content(
        content=content,
        step_type=step_type,
        previous_data=previous_data
    )

    # Создаем запись валидации
    validation = ValidationResult(
        step_id=step.id,
        status=ValidationStatus(validation_result_data["status"]),
        score=validation_result_data.get("score"),
        criteria_results=validation_result_data.get("criteria_results"),
        warnings=validation_result_data.get("warnings"),
        errors=validation_result_data.get("errors"),
        recommendations=validation_result_data.get("recommendations")
    )
    db.add(validation)

    # Обновляем статус шага
    if validation_result_data["status"] == "fail":
        step.validation_attempts += 1
        if step.validation_attempts >= step.max_validation_attempts:
            step.status = WorkflowStatus.VALIDATION_FAILED
        else:
            step.status = WorkflowStatus.VALIDATING
    else:
        step.status = WorkflowStatus.AWAITING_APPROVAL

    db.commit()
    db.refresh(step)

    return validation


def get_effective_prompt(
    video: Video,
    step_type: str,
    prompt_data: PromptData,
    user_custom_prompt: CustomPrompt = None
) -> CustomPrompt:
    """
    Get the effective prompt to use for generation.
    Priority: user_custom_prompt > project.system_prompts > default
    """
    if user_custom_prompt:
        # User explicitly edited the prompt - use it as-is
        return user_custom_prompt

    # Use system_prompt from project if available
    project = video.project
    system_prompt = prompt_data.system_prompt  # default from builder

    if project and project.system_prompts:
        project_system_prompt = project.system_prompts.get(step_type)
        if project_system_prompt:
            system_prompt = project_system_prompt

    return CustomPrompt(
        system_prompt=system_prompt,
        user_prompt=prompt_data.user_prompt
    )


@router.post("/preview-prompt", response_model=PreviewPromptResponse)
async def preview_prompt(
    request: PreviewPromptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Preview the prompt that will be sent to AI for a specific step.
    User can view and optionally edit this before running generation.
    """
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    context = request.context or {}

    # Get system_prompt from project if available
    project = video.project
    project_prompts = project.system_prompts if project and project.system_prompts else {}

    # Build prompt based on step type
    if request.step_type == StepTypeEnum.STORY:
        prompt_data = build_story_prompt(
            theme=context.get("theme"),
            target_audience=context.get("target_audience"),
            mood=context.get("mood"),
            key_elements=context.get("key_elements"),
            duration=context.get("duration", 5),
            platforms=context.get("platforms"),
            additional_notes=context.get("additional_notes"),
            content_variables=context.get("content_variables") or video.content_variables,
            system_prompt=project_prompts.get("story")
        )
    elif request.step_type == StepTypeEnum.DESCRIPTION:
        story_data = context.get("story_data") or video.story_data
        if not story_data:
            raise HTTPException(status_code=400, detail="story_data required for description prompt")
        prompt_data = build_description_prompt(story_data, system_prompt=project_prompts.get("description"))
    elif request.step_type == StepTypeEnum.PROMPT:
        description_data = context.get("description_data") or video.description_data
        if not description_data:
            raise HTTPException(status_code=400, detail="description_data required for prompt generation")
        prompt_data = build_image_prompt_prompt(description_data, system_prompt=project_prompts.get("prompt"))
    elif request.step_type == StepTypeEnum.SCENARIO:
        image_url = context.get("image_url") or video.image_url
        description_data = context.get("description_data") or video.description_data
        if not image_url or not description_data:
            raise HTTPException(status_code=400, detail="image_url and description_data required for scenario")
        prompt_data = build_scenario_prompt(
            image_url=image_url,
            description_data=description_data,
            story_data=video.story_data,
            duration=video.project.duration if video.project else 5,
            system_prompt=project_prompts.get("scenario")
        )
    elif request.step_type == StepTypeEnum.ADAPTATION:
        platforms = context.get("platforms") or video.project.platforms if video.project else ["instagram"]
        full_context = {
            "story": video.story_data,
            "scenario": context.get("scenario_data") or video.scenario_data
        }
        prompt_data = build_adaptation_prompt(full_context, platforms, system_prompt=project_prompts.get("adaptation"))
    else:
        raise HTTPException(status_code=400, detail=f"Unknown step type: {request.step_type}")

    return PreviewPromptResponse(
        system_prompt=prompt_data.system_prompt,
        user_prompt=prompt_data.user_prompt,
        step_type=request.step_type.value,
        can_edit=True
    )


@router.post("/generate-story")
async def generate_story(
    request: GenerateStoryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Этап 1: Генерация сюжета"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    try:
        step = StoryStep(db, video)
        return await step.execute(request, request.custom_prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-description")
async def generate_description(
    request: GenerateDescriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Этап 2: Генерация детального описания"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    # Sync request data to video (in case frontend passed updated data)
    if request.story_data:
        video.story_data = request.story_data

    try:
        step = DescriptionStep(db, video)
        return await step.execute(request, request.custom_prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-prompt")
async def generate_prompt(
    request: GeneratePromptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Этап 3: Генерация промпта для KLING"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    # Sync request data to video
    if request.description_data:
        video.description_data = request.description_data

    try:
        step = PromptStep(db, video)
        return await step.execute(request, request.custom_prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-image")
async def generate_image(
    request: GenerateImageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Этап 4: Генерация изображения (provider-agnostic)"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    # Get prompt from request
    prompt_str = request.prompt
    negative_prompt = None
    style_suffix = None

    if request.prompt_data:
        if not prompt_str:
            prompt_str = request.prompt_data.get("main_prompt", "")
        negative_prompt = request.prompt_data.get("negative_prompt")
        style_suffix = request.prompt_data.get("style_suffix")

    if not prompt_str:
        raise HTTPException(status_code=400, detail="Either prompt or prompt_data.main_prompt is required")

    try:
        step = ImageStep(db, video, get_image_service())
        return await step.execute(
            prompt=prompt_str,
            aspect_ratio=request.aspect_ratio,
            negative_prompt=negative_prompt,
            style_suffix=style_suffix,
            mode=request.mode
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-scenario")
async def generate_scenario(
    request: GenerateScenarioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Этап 5: Генерация сценария видео"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    # Sync request data to video
    if request.image_url:
        video.image_url = request.image_url
    if request.description_data:
        video.description_data = request.description_data

    try:
        step = ScenarioStep(db, video)
        return await step.execute(request, request.custom_prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-video")
async def generate_video(
    request: GenerateVideoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Этап 6: Генерация видео (provider-agnostic)"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    # Get prompt from scenario
    prompt = request.scenario_data.get("motion_prompt", "") or request.scenario_data.get("scene_direction", "")

    # Build camera control from scenario
    camera_control = build_camera_control(request.scenario_data.get("camera_movement"))

    try:
        step = VideoStep(db, video, get_video_service())
        return await step.execute(
            image_url=request.image_url,
            prompt=prompt,
            duration=request.duration,
            camera_control=camera_control,
            mode=request.mode
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-audio")
async def generate_audio(
    request: GenerateAudioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Этап 7: Генерация аудио (provider-agnostic)"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    try:
        step = AudioStep(db, video, get_audio_service())
        result = await step.execute(video_task_id=video.video_task_id)

        # Add user-friendly message for non-skipped results
        if result.get("status") == "completed":
            result["message"] = "4 audio variants generated. Please select one."

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/select-audio-variant")
async def select_audio_variant(
    request: SelectAudioVariantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Выбор одного из 4 вариантов аудио"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    if not video.audio_variants:
        raise HTTPException(
            status_code=400,
            detail="No audio variants available. Generate audio first."
        )

    if request.variant_index >= len(video.audio_variants):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid variant index. Available: 0-{len(video.audio_variants)-1}"
        )

    # Select the variant
    selected_url = video.audio_variants[request.variant_index]
    video.video_with_audio_url = selected_url

    # Approve the audio step
    audio_step = db.query(WorkflowStep).filter(
        WorkflowStep.video_id == video.id,
        WorkflowStep.step_type == StepType.AUDIO
    ).first()

    if audio_step:
        audio_step.status = WorkflowStatus.APPROVED
        audio_step.user_approved = True
        audio_step.user_feedback = f"Selected variant {request.variant_index + 1}"

    db.commit()

    # Auto-generate Adaptation after audio selection
    project = video.project
    adaptation_step = WorkflowStep(
        video_id=video.id,
        step_type=StepType.ADAPTATION,
        status=WorkflowStatus.IN_PROGRESS,
        started_at=datetime.utcnow()
    )
    db.add(adaptation_step)
    db.commit()
    db.refresh(adaptation_step)

    # Собираем полный контекст для адаптации
    full_context = {
        "story": video.story_data,
        "scenario": video.scenario_data,
        "image_url": video.image_url,
        "video_url": selected_url  # Используем видео с выбранным аудио
    }

    adaptation_data = await openai_service.adapt_for_platforms(
        full_context,
        project.platforms
    )

    adaptation_step.content = adaptation_data
    adaptation_step.status = WorkflowStatus.AWAITING_APPROVAL
    adaptation_step.completed_at = datetime.utcnow()
    adaptation_step.generation_time_seconds = (datetime.utcnow() - adaptation_step.started_at).total_seconds()

    video.adaptation_data = adaptation_data
    video.current_step = StepType.ADAPTATION
    db.commit()

    return {
        "message": f"Selected audio variant {request.variant_index + 1}. Adaptation generated.",
        "video_with_audio_url": selected_url,
        "adaptation": adaptation_data
    }


@router.post("/adapt-for-platforms")
async def adapt_for_platforms(
    request: AdaptForPlatformsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Этап 7: Адаптация для платформ"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    # Sync request data to video
    if request.scenario_data:
        video.scenario_data = request.scenario_data

    # Override project platforms if specified in request
    project = video.project
    if project and request.platforms:
        project.platforms = request.platforms

    try:
        step = AdaptationStep(db, video)
        return await step.execute(request, request.custom_prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve-step")
async def approve_step(
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Одобрение/отклонение checkpoint"""
    step = db.query(WorkflowStep).filter(WorkflowStep.id == request.step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    verify_video_ownership(db, step.video, current_user)

    # Prevent double approval - check if step is already approved
    if request.approved and step.status == WorkflowStatus.APPROVED:
        return {
            "step_id": step.id,
            "status": step.status.value,
            "message": "Step already approved"
        }

    # Handle retry for FAILED or IN_PROGRESS steps
    if step.status in [WorkflowStatus.FAILED, WorkflowStatus.IN_PROGRESS] and request.regenerate:
        step.status = WorkflowStatus.PENDING
        step.user_approved = False
        step.validation_attempts = 0
        step.completed_at = None
        step.content = None  # Clear previous content
        db.commit()
        db.refresh(step)
        return {
            "step_id": step.id,
            "status": step.status.value,
            "message": "Step reset. Ready for retry."
        }

    step.user_approved = request.approved
    step.user_feedback = request.feedback

    if request.approved:
        step.status = WorkflowStatus.APPROVED
        step.completed_at = datetime.utcnow()

        # Update video current_step to next step after approval
        video = step.video

        # Special handling for VIDEO step approval
        if step.step_type == StepType.VIDEO:
            # Check project audio_mode
            project = video.project
            if project and project.audio_mode == "none":
                # Skip audio generation - go directly to ADAPTATION
                audio_step = WorkflowStep(
                    video_id=video.id,
                    step_type=StepType.AUDIO,
                    status=WorkflowStatus.APPROVED,
                    user_approved=True,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    content={"skipped": True, "reason": "audio_mode is none"}
                )
                db.add(audio_step)
                video.video_with_audio_url = video.video_url  # Use original video
                video.current_step = StepType.AUDIO
                db.commit()
            else:
                # После Video идёт Audio (генерация 4 вариантов)
                if not video.video_task_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Video task_id not found. Cannot generate audio."
                    )

                audio_step = WorkflowStep(
                    video_id=video.id,
                    step_type=StepType.AUDIO,
                    status=WorkflowStatus.IN_PROGRESS,
                    started_at=datetime.utcnow()
                )
                db.add(audio_step)
                db.commit()
                db.refresh(audio_step)

                # Генерируем 4 варианта аудио
                audio_variants = await kling_service.add_audio_to_video(video.video_task_id)

                audio_step.content = {"audio_variants": audio_variants}
                audio_step.status = WorkflowStatus.AWAITING_APPROVAL
                audio_step.completed_at = datetime.utcnow()
                audio_step.generation_time_seconds = (datetime.utcnow() - audio_step.started_at).total_seconds()

                video.audio_variants = audio_variants
                video.current_step = StepType.AUDIO
                db.commit()
        elif step.step_type == StepType.ADAPTATION:
            # После approve Adaptation - создаем Publishing step
            publishing_step = WorkflowStep(
                video_id=video.id,
                step_type=StepType.PUBLISHING,
                status=WorkflowStatus.AWAITING_APPROVAL,
                started_at=datetime.utcnow(),
                content={
                    "message": "Configure publishing settings and select platforms"
                }
            )
            db.add(publishing_step)
            video.current_step = StepType.PUBLISHING
            db.commit()
        elif step.step_type == StepType.PUBLISHING:
            # После approve Publishing - завершаем workflow
            video.status = WorkflowStatus.COMPLETED
            db.commit()
        elif step.step_type == StepType.IMAGE and video.workflow_mode == WorkflowMode.AUTO:
            # Special case: IMAGE approved in AUTO mode - continue with video generation
            # This happens when require_image_approval paused the workflow
            video.current_step = StepType.SCENARIO
            video.status = WorkflowStatus.IN_PROGRESS
            db.commit()
            db.refresh(step)

            # Return with flag to continue workflow
            return {
                "step_id": step.id,
                "status": step.status.value,
                "message": "Image approved. Call auto-generate-to-video to continue.",
                "continue_workflow": True
            }
        else:
            # For MANUAL mode: create next step as PENDING (user will click Generate)
            # For other modes: just update current_step marker
            next_step_map = {
                StepType.STORY: StepType.DESCRIPTION,
                StepType.DESCRIPTION: StepType.PROMPT,
                StepType.PROMPT: StepType.IMAGE,
                StepType.IMAGE: StepType.SCENARIO,
                StepType.SCENARIO: StepType.VIDEO,
                StepType.AUDIO: StepType.ADAPTATION,
                StepType.ADAPTATION: StepType.PUBLISHING,
            }

            if step.step_type in next_step_map:
                next_step_type = next_step_map[step.step_type]

                if video.workflow_mode == WorkflowMode.MANUAL:
                    # Create next step as PENDING - user will trigger generation manually
                    next_step = WorkflowStep(
                        video_id=video.id,
                        step_type=next_step_type,
                        status=WorkflowStatus.PENDING,
                        created_at=datetime.utcnow()
                    )
                    db.add(next_step)

                video.current_step = next_step_type
                db.commit()
    else:
        # Если reject с regenerate - возвращаем в PENDING, иначе REJECTED
        if request.regenerate:
            step.status = WorkflowStatus.PENDING
            step.user_approved = False
            step.validation_attempts = 0  # Сбрасываем счетчик попыток
            message = "Step rejected. Ready for regeneration."
        else:
            step.status = WorkflowStatus.REJECTED
            message = "Step rejected"

    db.commit()
    db.refresh(step)

    return {
        "step_id": step.id,
        "status": step.status.value,
        "message": "Step approved" if request.approved else message
    }


@router.post("/auto-generate-to-video")
async def auto_generate_to_video(
    request: AutoGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Автоматическая генерация видео с использованием WorkflowOrchestrator.

    Supports:
    - Discover mode: Story → Description → Prompt → Image → Scenario → Video → Audio
    - Remix mode: Template → Image → Video → Audio
    - Resume after image approval
    """
    from app.services.workflow.orchestrator import WorkflowOrchestrator, WorkflowResult

    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    try:
        orchestrator = WorkflowOrchestrator(db, video)
        result: WorkflowResult = await orchestrator.run()

        # Convert dataclass to dict for JSON response
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
