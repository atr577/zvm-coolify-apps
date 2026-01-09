from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.base import get_db
from app.models.video import Video, WorkflowMode
from app.models.workflow_step import WorkflowStep, WorkflowStatus, StepType
from app.models.validation_result import ValidationResult, ValidationStatus
from app.models.user import User
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
    AutoGenerateRequest
)
from app.services.openai_service import openai_service
from app.services.kling_service import kling_service

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


def verify_video_ownership(video: Video, current_user: User):
    """Проверка владения видео через проект"""
    if video.project.user_id != current_user.id:
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

    verify_video_ownership(video, current_user)

    step = get_or_create_step(db, video.id, StepType.STORY)

    # Берём content_variables из запроса или из video
    content_variables = request.content_variables or video.content_variables

    try:
        # Генерируем сюжет
        story_data = await openai_service.generate_story(
            theme=request.theme,
            target_audience=request.target_audience,
            mood=request.mood,
            key_elements=request.key_elements,
            duration=request.duration,
            platforms=request.platforms,
            additional_notes=request.additional_notes,
            content_variables=content_variables
        )
        step.content = story_data
        video.story_data = story_data
        video.current_step = StepType.STORY
        video.status = WorkflowStatus.IN_PROGRESS

        # Валидация
        validation = await validate_and_save(db, step, story_data, "story")

        return {
            "step_id": step.id,
            "content": story_data,
            "validation": {
                "status": validation.status.value,
                "score": validation.score,
                "warnings": validation.warnings,
                "errors": validation.errors,
                "recommendations": validation.recommendations
            }
        }
    except Exception as e:
        step.status = WorkflowStatus.FAILED
        step.completed_at = datetime.utcnow()
        db.commit()
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

    verify_video_ownership(video, current_user)

    step = get_or_create_step(db, video.id, StepType.DESCRIPTION)

    try:
        # Генерируем описание
        description_data = await openai_service.generate_description(request.story_data)
        step.content = description_data
        video.description_data = description_data
        video.current_step = StepType.DESCRIPTION

        # Валидация
        validation = await validate_and_save(
            db, step, description_data, "description", request.story_data
        )

        return {
            "step_id": step.id,
            "content": description_data,
            "validation": {
                "status": validation.status.value,
                "score": validation.score,
                "warnings": validation.warnings,
                "recommendations": validation.recommendations
            }
        }
    except Exception as e:
        step.status = WorkflowStatus.FAILED
        step.completed_at = datetime.utcnow()
        db.commit()
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

    verify_video_ownership(video, current_user)

    step = get_or_create_step(db, video.id, StepType.PROMPT)

    try:
        # Генерируем промпт (теперь возвращает dict с main_prompt, negative_prompt, etc.)
        prompt_data = await openai_service.generate_image_prompt(request.description_data)
        step.content = prompt_data
        video.prompt_data = prompt_data
        video.image_prompt = prompt_data.get("main_prompt", "")  # legacy field
        video.current_step = StepType.PROMPT

        # Валидация
        validation = await validate_and_save(
            db, step, prompt_data, "prompt", request.description_data
        )

        return {
            "step_id": step.id,
            "content": prompt_data,
            "validation": {
                "status": validation.status.value,
                "score": validation.score,
                "recommendations": validation.recommendations
            }
        }
    except Exception as e:
        step.status = WorkflowStatus.FAILED
        step.completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-image")
async def generate_image(
    request: GenerateImageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Этап 4: Генерация изображения через KLING"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(video, current_user)

    step = get_or_create_step(db, video.id, StepType.IMAGE)

    try:
        # Определяем промпт - либо простая строка, либо из структурированного объекта
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

        # Генерируем изображение с negative_prompt и style_suffix
        image_url = await kling_service.generate_image(
            prompt=prompt_str,
            aspect_ratio=request.aspect_ratio,
            mode=request.mode,
            negative_prompt=negative_prompt,
            style_suffix=style_suffix
        )

        step.content = {"image_url": image_url}
        video.image_url = image_url
        video.current_step = StepType.IMAGE
        step.status = WorkflowStatus.AWAITING_APPROVAL
        step.completed_at = datetime.utcnow()
        db.commit()

        return {
            "step_id": step.id,
            "content": {"image_url": image_url},
            "status": "completed"
        }

    except Exception as e:
        step.status = WorkflowStatus.FAILED
        db.commit()
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

    verify_video_ownership(video, current_user)

    step = get_or_create_step(db, video.id, StepType.SCENARIO)

    try:
        # Получаем duration из проекта
        project = video.project

        # Генерируем сценарий с vision и полным контекстом
        scenario_data = await openai_service.generate_scenario(
            image_url=request.image_url,
            description_data=request.description_data,
            story_data=video.story_data,  # Передаем story для контекста
            duration=project.duration  # Используем duration из проекта
        )
        step.content = scenario_data
        video.scenario_data = scenario_data
        video.current_step = StepType.SCENARIO

        # Валидация
        validation = await validate_and_save(
            db, step, scenario_data, "scenario", request.description_data
        )

        return {
            "step_id": step.id,
            "content": scenario_data,
            "validation": {
                "status": validation.status.value,
                "score": validation.score,
                "recommendations": validation.recommendations
            }
        }
    except Exception as e:
        step.status = WorkflowStatus.FAILED
        step.completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-video")
async def generate_video(
    request: GenerateVideoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Этап 6: Генерация видео через KLING"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(video, current_user)

    step = get_or_create_step(db, video.id, StepType.VIDEO)

    try:
        # Генерируем видео (используем motion_prompt из scenario)
        prompt = request.scenario_data.get("motion_prompt", "") or request.scenario_data.get("scene_direction", "")

        # Преобразуем camera_movement в camera_control для KLING
        camera_control = build_camera_control(request.scenario_data.get("camera_movement"))

        video_url, task_id = await kling_service.generate_video(
            image_url=request.image_url,
            prompt=prompt,
            duration=request.duration,
            mode=request.mode,
            version=request.version,
            camera_control=camera_control,
            return_task_id=True
        )

        step.content = {"video_url": video_url, "task_id": task_id}
        video.video_url = video_url
        video.video_task_id = task_id  # Save task_id for audio generation
        video.current_step = StepType.VIDEO
        step.status = WorkflowStatus.AWAITING_APPROVAL
        step.completed_at = datetime.utcnow()
        db.commit()

        return {
            "step_id": step.id,
            "content": {"video_url": video_url, "task_id": task_id},
            "status": "completed"
        }

    except Exception as e:
        step.status = WorkflowStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-audio")
async def generate_audio(
    request: GenerateAudioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Этап 7: Генерация аудио через Kling Sound API (4 варианта)"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(video, current_user)

    if not video.video_task_id:
        raise HTTPException(
            status_code=400,
            detail="Video task_id not found. Please regenerate video first."
        )

    step = get_or_create_step(db, video.id, StepType.AUDIO)

    try:
        # Generate 4 audio variants using Kling Sound API
        audio_variants = await kling_service.add_audio_to_video(video.video_task_id)

        step.content = {"audio_variants": audio_variants}
        video.audio_variants = audio_variants
        video.current_step = StepType.AUDIO
        step.status = WorkflowStatus.AWAITING_APPROVAL
        step.completed_at = datetime.utcnow()
        db.commit()

        return {
            "step_id": step.id,
            "content": {"audio_variants": audio_variants},
            "status": "completed",
            "message": "4 audio variants generated. Please select one."
        }

    except Exception as e:
        step.status = WorkflowStatus.FAILED
        db.commit()
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

    verify_video_ownership(video, current_user)

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

    verify_video_ownership(video, current_user)

    step = get_or_create_step(db, video.id, StepType.ADAPTATION)

    try:
        # Собираем полный контекст для адаптации
        full_context = {
            "story": video.story_data,
            "scenario": request.scenario_data,
            "image_url": video.image_url,
            "video_url": video.video_url
        }

        # Адаптируем контент с полным контекстом
        adaptation_data = await openai_service.adapt_for_platforms(
            full_context,
            request.platforms
        )
        step.content = adaptation_data
        video.adaptation_data = adaptation_data
        video.current_step = StepType.ADAPTATION

        # Валидация
        validation = await validate_and_save(
            db, step, adaptation_data, "adaptation"
        )

        return {
            "step_id": step.id,
            "content": adaptation_data,
            "validation": {
                "status": validation.status.value,
                "score": validation.score
            }
        }
    except Exception as e:
        step.status = WorkflowStatus.FAILED
        step.completed_at = datetime.utcnow()
        db.commit()
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

    verify_video_ownership(step.video, current_user)

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
        else:
            # For manual mode, auto-generate next step after approval
            if video.workflow_mode == WorkflowMode.MANUAL:
                # Auto-generate next step after approval
                if step.step_type == StepType.STORY:
                    # Generate Description
                    desc_step = WorkflowStep(
                        video_id=video.id,
                        step_type=StepType.DESCRIPTION,
                        status=WorkflowStatus.IN_PROGRESS,
                        started_at=datetime.utcnow()
                    )
                    db.add(desc_step)
                    db.commit()
                    db.refresh(desc_step)

                    description_data = await openai_service.generate_description(video.story_data)
                    desc_step.content = description_data
                    desc_step.status = WorkflowStatus.AWAITING_APPROVAL
                    desc_step.completed_at = datetime.utcnow()
                    desc_step.generation_time_seconds = (datetime.utcnow() - desc_step.started_at).total_seconds()

                    video.description_data = description_data
                    video.current_step = StepType.DESCRIPTION
                    db.commit()

                elif step.step_type == StepType.DESCRIPTION:
                    # Generate Prompt
                    prompt_step = WorkflowStep(
                        video_id=video.id,
                        step_type=StepType.PROMPT,
                        status=WorkflowStatus.IN_PROGRESS,
                        started_at=datetime.utcnow()
                    )
                    db.add(prompt_step)
                    db.commit()
                    db.refresh(prompt_step)

                    prompt_data = await openai_service.generate_image_prompt(video.description_data)
                    prompt_step.content = prompt_data
                    prompt_step.status = WorkflowStatus.AWAITING_APPROVAL
                    prompt_step.completed_at = datetime.utcnow()
                    prompt_step.generation_time_seconds = (datetime.utcnow() - prompt_step.started_at).total_seconds()

                    video.prompt_data = prompt_data
                    video.current_step = StepType.PROMPT
                    db.commit()

                elif step.step_type == StepType.PROMPT:
                    # Generate Image
                    image_step = WorkflowStep(
                        video_id=video.id,
                        step_type=StepType.IMAGE,
                        status=WorkflowStatus.IN_PROGRESS,
                        started_at=datetime.utcnow()
                    )
                    db.add(image_step)
                    db.commit()
                    db.refresh(image_step)

                    # Используем style_suffix и negative_prompt из prompt_data
                    # aspect_ratio берем из проекта
                    project = video.project
                    prompt_data = video.prompt_data or {}
                    image_url = await kling_service.generate_image(
                        prompt=prompt_data.get("main_prompt", ""),
                        aspect_ratio=project.aspect_ratio,
                        mode="std",
                        negative_prompt=prompt_data.get("negative_prompt"),
                        style_suffix=prompt_data.get("style_suffix")
                    )
                    image_step.content = {"image_url": image_url}
                    image_step.status = WorkflowStatus.AWAITING_APPROVAL
                    image_step.completed_at = datetime.utcnow()
                    image_step.generation_time_seconds = (datetime.utcnow() - image_step.started_at).total_seconds()

                    video.image_url = image_url
                    video.current_step = StepType.IMAGE
                    db.commit()

                elif step.step_type == StepType.IMAGE:
                    # Generate Scenario
                    scenario_step = WorkflowStep(
                        video_id=video.id,
                        step_type=StepType.SCENARIO,
                        status=WorkflowStatus.IN_PROGRESS,
                        started_at=datetime.utcnow()
                    )
                    db.add(scenario_step)
                    db.commit()
                    db.refresh(scenario_step)

                    project = video.project
                    # Используем vision и передаем полный контекст
                    scenario_data = await openai_service.generate_scenario(
                        image_url=video.image_url,
                        description_data=video.description_data,
                        story_data=video.story_data,
                        duration=project.duration
                    )
                    scenario_step.content = scenario_data
                    scenario_step.status = WorkflowStatus.AWAITING_APPROVAL
                    scenario_step.completed_at = datetime.utcnow()
                    scenario_step.generation_time_seconds = (datetime.utcnow() - scenario_step.started_at).total_seconds()

                    video.scenario_data = scenario_data
                    video.current_step = StepType.SCENARIO
                    db.commit()

                elif step.step_type == StepType.SCENARIO:
                    # Generate Video
                    video_step = WorkflowStep(
                        video_id=video.id,
                        step_type=StepType.VIDEO,
                        status=WorkflowStatus.IN_PROGRESS,
                        started_at=datetime.utcnow()
                    )
                    db.add(video_step)
                    db.commit()
                    db.refresh(video_step)

                    project = video.project
                    # Use scenario motion_prompt for video generation
                    video_prompt = (video.scenario_data.get("motion_prompt", "") or
                                   video.scenario_data.get("scene_direction", "")) if video.scenario_data else ""

                    # Преобразуем camera_movement в camera_control для KLING
                    camera_control = build_camera_control(
                        video.scenario_data.get("camera_movement") if video.scenario_data else None
                    )

                    video_url = await kling_service.generate_video(
                        image_url=video.image_url,
                        prompt=video_prompt,
                        duration=project.duration,
                        mode="standard",
                        camera_control=camera_control
                    )
                    video_step.content = {"video_url": video_url}
                    video_step.status = WorkflowStatus.AWAITING_APPROVAL
                    video_step.completed_at = datetime.utcnow()
                    video_step.generation_time_seconds = (datetime.utcnow() - video_step.started_at).total_seconds()

                    video.video_url = video_url
                    video.current_step = StepType.VIDEO
                    db.commit()

                elif step.step_type == StepType.ADAPTATION:
                    # После Adaptation создаем Publishing step
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
            else:
                # For non-template videos, just move to next step marker
                next_step_map = {
                    StepType.STORY: StepType.DESCRIPTION,
                    StepType.DESCRIPTION: StepType.PROMPT,
                    StepType.PROMPT: StepType.IMAGE,
                    StepType.IMAGE: StepType.SCENARIO,
                    StepType.SCENARIO: StepType.VIDEO,
                    StepType.ADAPTATION: StepType.PUBLISHING,
                }
                if step.step_type in next_step_map:
                    video.current_step = next_step_map[step.step_type]
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
    Автоматическая генерация Steps 1-6 для обычных роликов
    Без checkpoints, последовательно
    """
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(video, current_user)

    project = video.project
    start_time = datetime.utcnow()

    try:
        # Step 1: Story
        story_step = WorkflowStep(
            video_id=video.id,
            step_type=StepType.STORY,
            status=WorkflowStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        db.add(story_step)
        db.commit()
        db.refresh(story_step)

        story_data = await openai_service.generate_story_from_template(
            story_template=project.story_template,
            content_variables=video.content_variables or {},
            duration=project.duration,
            platforms=project.platforms
        )

        story_step.content = story_data
        story_step.status = WorkflowStatus.APPROVED
        story_step.completed_at = datetime.utcnow()
        story_step.generation_time_seconds = (datetime.utcnow() - story_step.started_at).total_seconds()

        video.story_data = story_data
        video.current_step = StepType.DESCRIPTION
        db.commit()

        # Step 2: Description
        desc_step = WorkflowStep(
            video_id=video.id,
            step_type=StepType.DESCRIPTION,
            status=WorkflowStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        db.add(desc_step)
        db.commit()
        db.refresh(desc_step)

        description_data = await openai_service.generate_description(story_data)
        desc_step.content = description_data
        desc_step.status = WorkflowStatus.APPROVED
        desc_step.completed_at = datetime.utcnow()
        desc_step.generation_time_seconds = (datetime.utcnow() - desc_step.started_at).total_seconds()

        video.description_data = description_data
        video.current_step = StepType.PROMPT
        db.commit()

        # Step 3: Prompt
        prompt_step = WorkflowStep(
            video_id=video.id,
            step_type=StepType.PROMPT,
            status=WorkflowStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        db.add(prompt_step)
        db.commit()
        db.refresh(prompt_step)

        prompt_data = await openai_service.generate_image_prompt(description_data)
        prompt_step.content = prompt_data
        prompt_step.status = WorkflowStatus.APPROVED
        prompt_step.completed_at = datetime.utcnow()
        prompt_step.generation_time_seconds = (datetime.utcnow() - prompt_step.started_at).total_seconds()

        video.prompt_data = prompt_data
        video.image_prompt = prompt_data.get("main_prompt", "")
        video.current_step = StepType.IMAGE
        db.commit()

        # Step 4: Image
        image_step = WorkflowStep(
            video_id=video.id,
            step_type=StepType.IMAGE,
            status=WorkflowStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        db.add(image_step)
        db.commit()
        db.refresh(image_step)

        # Используем style_suffix и negative_prompt из prompt_data
        # aspect_ratio берем из проекта
        image_url = await kling_service.generate_image(
            prompt=prompt_data.get("main_prompt", ""),
            aspect_ratio=project.aspect_ratio,
            mode="std",
            negative_prompt=prompt_data.get("negative_prompt"),
            style_suffix=prompt_data.get("style_suffix")
        )

        image_step.content = {"image_url": image_url}
        image_step.status = WorkflowStatus.APPROVED
        image_step.completed_at = datetime.utcnow()
        image_step.generation_time_seconds = (datetime.utcnow() - image_step.started_at).total_seconds()

        video.image_url = image_url
        video.current_step = StepType.SCENARIO
        db.commit()

        # Step 5: Scenario
        scenario_step = WorkflowStep(
            video_id=video.id,
            step_type=StepType.SCENARIO,
            status=WorkflowStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        db.add(scenario_step)
        db.commit()
        db.refresh(scenario_step)

        # Используем vision и передаем полный контекст
        scenario_data = await openai_service.generate_scenario(
            image_url=image_url,
            description_data=description_data,
            story_data=story_data,
            duration=project.duration
        )
        scenario_step.content = scenario_data
        scenario_step.status = WorkflowStatus.APPROVED
        scenario_step.completed_at = datetime.utcnow()
        scenario_step.generation_time_seconds = (datetime.utcnow() - scenario_step.started_at).total_seconds()

        video.scenario_data = scenario_data
        video.current_step = StepType.VIDEO
        db.commit()

        # Step 6: Video
        video_step = WorkflowStep(
            video_id=video.id,
            step_type=StepType.VIDEO,
            status=WorkflowStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        db.add(video_step)
        db.commit()
        db.refresh(video_step)

        # Преобразуем camera_movement в camera_control для KLING
        camera_control = build_camera_control(scenario_data.get("camera_movement"))

        video_url, task_id = await kling_service.generate_video(
            image_url=image_url,
            prompt=scenario_data.get("motion_prompt", "") or scenario_data.get("scene_direction", ""),
            duration=project.duration,
            mode="std",
            version="2.1",
            camera_control=camera_control,
            return_task_id=True
        )

        video_step.content = {"video_url": video_url, "task_id": task_id}
        video.video_task_id = task_id  # Save for audio generation
        video_step.status = WorkflowStatus.APPROVED
        video_step.completed_at = datetime.utcnow()
        video_step.generation_time_seconds = (datetime.utcnow() - video_step.started_at).total_seconds()

        video.video_url = video_url
        video.current_step = StepType.AUDIO
        db.commit()

        # Step 7: Audio (генерируем 4 варианта, юзер выберет)
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
        audio_variants = await kling_service.add_audio_to_video(task_id)

        audio_step.content = {"audio_variants": audio_variants}
        audio_step.status = WorkflowStatus.AWAITING_APPROVAL
        audio_step.completed_at = datetime.utcnow()
        audio_step.generation_time_seconds = (datetime.utcnow() - audio_step.started_at).total_seconds()

        video.audio_variants = audio_variants
        video.status = WorkflowStatus.AWAITING_APPROVAL
        db.commit()

        total_time = (datetime.utcnow() - start_time).total_seconds()

        return {
            "video_id": video.id,
            "message": "Video generated. Please select audio variant to continue.",
            "total_time_seconds": total_time,
            "steps_completed": 7,
            "audio_variants": audio_variants,
            "next_action": "select_audio_variant"
        }

    except Exception as e:
        video.status = WorkflowStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
