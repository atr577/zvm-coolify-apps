"""API endpoints for Template project type."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User, SocialAccount
from app.models.project import Project
from app.models.template_settings import TemplateSettings
from app.models.video_template import VideoTemplate
from app.models.variant import Variant
from app.models.template_generation import TemplateGeneration
from app.models.approved_generation import ApprovedGeneration
from app.models.rejection_archive import RejectionArchive
from app.schemas.template import (
    TemplateSettingsResponse,
    TemplateSettingsUpdate,
    TemplateProjectCreate,
    VariantResponse,
    VariantListResponse,
    VariantUpdate,
    CSVUploadResponse,
    VideoTemplateCreate,
    VideoTemplateUpdate,
    VideoTemplateResponse,
    GenerateRequest,
    GenerationResponse,
    GenerationListResponse,
    BatchGenerateRequest,
    BatchGenerateResponse,
    GenerateVariantPromptResponse,
    GenerateVariantsRequest,
    GenerateVariantsPreviewResponse,
    SaveGeneratedVariantsRequest,
    SaveGeneratedVariantsResponse,
)
from app.api.projects import user_has_workspace_access, get_user_workspace_ids
from app.services.csv_parser import parse_csv, validate_csv_for_project, CSVParseError
from app.services.template_generation_service import get_template_generation_service
from app.services.openai_client import openai_client, OpenAIClientError

import logging
import json
import os
import random
import string

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


# --- Template Project Creation ---

@router.post("/projects/template", response_model=dict, tags=["template"])
async def create_template_project(
    data: TemplateProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new template project with settings and first video template.

    Creates:
    - Project (type=template)
    - TemplateSettings (with prompts and models)
    - VideoTemplate (first template, is_default=true)
    """
    # Validate workspace access
    workspace_ids = get_user_workspace_ids(db, current_user.id)
    workspace_id = data.workspace_id

    if workspace_id:
        if workspace_id not in workspace_ids:
            raise HTTPException(status_code=403, detail="No access to workspace")
    elif workspace_ids:
        workspace_id = workspace_ids[0]

    # Create Project
    project = Project(
        user_id=current_user.id,
        workspace_id=workspace_id,
        name=data.name,
        description=data.description,
        project_type="template",
        story_template="",  # Not used for template type
        platforms=data.platforms,
        duration=10,  # Default, not used for template type (video_duration is in settings)
        aspect_ratio=data.image_aspect_ratio.value,
    )
    db.add(project)
    db.flush()  # Get project.id

    # Create TemplateSettings
    settings = TemplateSettings(
        project_id=project.id,
        preprocessing_prompt=data.preprocessing_prompt,
        image_prompt_template=data.image_prompt_template,
        llm_model=data.llm_model.value,
        image_model=data.image_model.value,
        video_model=data.video_model.value,
        image_aspect_ratio=data.image_aspect_ratio.value,
        video_duration=data.video_duration,
    )
    db.add(settings)

    # Create first VideoTemplate (default)
    video_template = VideoTemplate(
        project_id=project.id,
        name=data.video_template_name,
        prompt=data.video_template_prompt,
        is_default=True,
    )
    db.add(video_template)

    # Bind social accounts if provided
    if data.social_account_ids:
        for account_id in data.social_account_ids:
            account = db.query(SocialAccount).filter(
                SocialAccount.id == account_id,
                SocialAccount.user_id == current_user.id
            ).first()
            if account:
                project.social_accounts.append(account)

    db.commit()
    db.refresh(project)
    db.refresh(settings)

    # Auto-generate variant_generation_prompt and music_prompt from pipeline prompts
    if settings.preprocessing_prompt and settings.image_prompt_template:
        auto_gen_tasks = []
        if not settings.variant_generation_prompt:
            auto_gen_tasks.append(("variant", _generate_variant_prompt_from_pipeline(
                settings.preprocessing_prompt, settings.image_prompt_template
            )))
        if not settings.music_prompt:
            auto_gen_tasks.append(("music", _generate_music_prompt_from_pipeline(
                settings.preprocessing_prompt, settings.image_prompt_template
            )))

        import asyncio
        for name, coro in auto_gen_tasks:
            try:
                result = await coro
                if name == "variant":
                    settings.variant_generation_prompt = result
                elif name == "music":
                    settings.music_prompt = result
            except Exception as e:
                logger.warning(f"Auto-generate {name} prompt on create failed: {e}")

        db.commit()

    return {
        "id": project.id,
        "name": project.name,
        "project_type": project.project_type,
        "message": "Template project created successfully"
    }


def _enrich_settings(db: Session, settings: TemplateSettings, project: Project) -> TemplateSettings:
    """Enrich settings with audio_hook_url and re-trim info from project's audio_source."""
    if project.audio_source_id:
        from app.models.audio_library import AudioLibrary
        lib_item = db.query(AudioLibrary).filter(
            AudioLibrary.id == project.audio_source_id
        ).first()
        if lib_item and lib_item.file_path:
            from pathlib import Path
            p = Path(lib_item.file_path)
            settings.audio_hook_url = f"/api/files/{p.parent.name}/{p.name}"
            settings.audio_hook_duration_ms = lib_item.duration_ms

            # Check if hook will be re-trimmed at batch time
            duration_str = settings.video_duration or "5"
            hook_duration_ms = int(float(duration_str.rstrip("s")) * 1000)
            settings.audio_hook_retrim = (
                lib_item.duration_ms < hook_duration_ms
                and lib_item.track_path is not None
            )
    return settings


@router.get(
    "/projects/{project_id}/audio-hook-preview",
    tags=["template"],
)
async def get_audio_hook_preview(
    project_id: int,
    duration: str = Query(..., description="Target video duration, e.g. '10'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a trimmed audio hook preview matching the target video duration."""
    project = get_template_project(db, project_id, current_user)
    if not project.audio_source_id:
        raise HTTPException(status_code=404, detail="No audio source configured")

    from app.models.audio_library import AudioLibrary
    lib_item = db.query(AudioLibrary).filter(
        AudioLibrary.id == project.audio_source_id
    ).first()
    if not lib_item or not lib_item.file_path:
        raise HTTPException(status_code=404, detail="Audio library item not found")

    hook_duration = float(duration.rstrip("s"))
    hook_duration_ms = int(hook_duration * 1000)

    # If hook already long enough, return original
    if lib_item.duration_ms >= hook_duration_ms:
        return FileResponse(lib_item.file_path, media_type="audio/mpeg")

    # Need re-trim from full track
    if not lib_item.track_path or not os.path.exists(lib_item.track_path):
        # No full track — return original hook as fallback
        return FileResponse(lib_item.file_path, media_type="audio/mpeg")

    from app.core.media_processor import media_processor
    from app.core.hook_analyzer import hook_analyzer
    from app.core.config import settings as app_settings

    if lib_item.hook_start_ms is not None and lib_item.hook_end_ms is not None:
        start_s = lib_item.hook_start_ms / 1000.0
        end_s = start_s + hook_duration
    else:
        hooks = await hook_analyzer.find_hooks(
            audio_path=lib_item.track_path,
            video=None,
            num_hooks=4,
            hook_duration=hook_duration,
        )
        if not hooks:
            track_duration = await media_processor.get_audio_duration(lib_item.track_path)
            hooks = hook_analyzer._create_fallback_hooks(
                total_duration=track_duration,
                hook_duration=hook_duration,
                num_hooks=1,
            )
        start_s = hooks[0].start
        end_s = hooks[0].end

    audio_dir = os.path.join(app_settings.MEDIA_DIR, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    preview_path = os.path.join(audio_dir, f"project_{project_id}_hook_preview.mp3")

    await media_processor.trim_audio(
        audio_path=lib_item.track_path,
        start=start_s,
        end=end_s,
        fade_in=0.5,
        fade_out=0.5,
        output_path=preview_path,
    )

    return FileResponse(preview_path, media_type="audio/mpeg")


# --- Template Settings Endpoints ---

@router.get(
    "/projects/{project_id}/template-settings",
    response_model=TemplateSettingsResponse,
    tags=["template"]
)
async def get_template_settings(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get template settings for a project."""
    project = get_template_project(db, project_id, current_user)

    settings = db.query(TemplateSettings).filter(
        TemplateSettings.project_id == project_id
    ).first()

    if not settings:
        raise HTTPException(status_code=404, detail="Template settings not found")

    return _enrich_settings(db, settings, project)


@router.put(
    "/projects/{project_id}/template-settings",
    response_model=TemplateSettingsResponse,
    tags=["template"]
)
async def update_template_settings(
    project_id: int,
    data: TemplateSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update template settings for a project."""
    project = get_template_project(db, project_id, current_user)

    settings = db.query(TemplateSettings).filter(
        TemplateSettings.project_id == project_id
    ).first()

    if not settings:
        raise HTTPException(status_code=404, detail="Template settings not found")

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    # Normalize empty strings to None for meta prompts
    for key in ('meta_title_prompt', 'meta_description_prompt', 'meta_hashtags_prompt'):
        if key in update_data and not update_data[key]:
            update_data[key] = None
    for field, value in update_data.items():
        if hasattr(value, 'value'):  # Enum
            setattr(settings, field, value.value)
        else:
            setattr(settings, field, value)

    db.commit()
    db.refresh(settings)

    # Auto-generate prompts if empty and pipeline prompts are set
    if settings.preprocessing_prompt and settings.image_prompt_template:
        changed = False
        if not settings.variant_generation_prompt:
            try:
                settings.variant_generation_prompt = await _generate_variant_prompt_from_pipeline(
                    settings.preprocessing_prompt, settings.image_prompt_template
                )
                changed = True
            except Exception as e:
                logger.warning(f"Auto-generate variant prompt failed: {e}")

        if not settings.music_prompt:
            try:
                settings.music_prompt = await _generate_music_prompt_from_pipeline(
                    settings.preprocessing_prompt, settings.image_prompt_template
                )
                changed = True
            except Exception as e:
                logger.warning(f"Auto-generate music prompt failed: {e}")

        if changed:
            db.commit()
            db.refresh(settings)

    return _enrich_settings(db, settings, project)


# --- Variants Endpoints ---

@router.post(
    "/projects/{project_id}/variants/upload",
    response_model=CSVUploadResponse,
    tags=["template"]
)
async def upload_variants_csv(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload CSV file to create variants for a template project.

    - Replaces all existing variants for this project
    - Updates csv_columns in TemplateSettings
    - Returns preview of first 5 rows
    """
    project = get_template_project(db, project_id, current_user)

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    # Read and parse CSV
    try:
        content = await file.read()
        columns, rows = parse_csv(content)
        validate_csv_for_project(columns, rows)
    except CSVParseError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Delete existing variants for this project
    db.query(Variant).filter(Variant.project_id == project_id).delete()

    # Create new variants
    for row_num, row_data in enumerate(rows, start=1):
        variant = Variant(
            project_id=project_id,
            row_number=row_num,
            data=row_data,
            usage_count=0,
        )
        db.add(variant)

    # Update csv_columns in TemplateSettings
    settings = db.query(TemplateSettings).filter(
        TemplateSettings.project_id == project_id
    ).first()
    if settings:
        settings.csv_columns = columns

    db.commit()

    # Return response with preview
    preview = rows[:5]
    return CSVUploadResponse(
        variants_created=len(rows),
        csv_columns=columns,
        preview=preview
    )


@router.get(
    "/projects/{project_id}/variants",
    response_model=VariantListResponse,
    tags=["template"]
)
async def list_variants(
    project_id: int,
    search: Optional[str] = Query(None, description="Search in variant data"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List variants for a template project with optional search and pagination.
    """
    project = get_template_project(db, project_id, current_user)

    # Base query
    query = db.query(Variant).filter(Variant.project_id == project_id)

    # Search in JSON data (PostgreSQL: cast to text and search)
    if search:
        from sqlalchemy import text
        # PostgreSQL: data::text ILIKE '%search%'
        query = query.filter(
            text("data::text ILIKE :search").bindparams(search=f"%{search}%")
        )

    # Get total count
    total = query.count()

    # Get variants with pagination, ordered by row_number
    variants = query.order_by(Variant.row_number).offset(offset).limit(limit).all()

    # Get csv_columns from settings
    settings = db.query(TemplateSettings).filter(
        TemplateSettings.project_id == project_id
    ).first()
    csv_columns = settings.csv_columns if settings else None

    return VariantListResponse(
        variants=[VariantResponse.model_validate(v) for v in variants],
        total=total,
        csv_columns=csv_columns
    )


@router.put(
    "/projects/{project_id}/variants/{variant_id}",
    response_model=VariantResponse,
    tags=["template"]
)
async def update_variant(
    project_id: int,
    variant_id: int,
    data: VariantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update variant data (inline edit)."""
    project = get_template_project(db, project_id, current_user)

    variant = db.query(Variant).filter(
        Variant.id == variant_id,
        Variant.project_id == project_id
    ).first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    if data.data is not None:
        variant.data = data.data

    db.commit()
    db.refresh(variant)
    return variant


@router.delete(
    "/projects/{project_id}/variants/{variant_id}",
    response_model=dict,
    tags=["template"]
)
async def delete_variant(
    project_id: int,
    variant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a single variant."""
    project = get_template_project(db, project_id, current_user)

    variant = db.query(Variant).filter(
        Variant.id == variant_id,
        Variant.project_id == project_id
    ).first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    db.delete(variant)
    db.commit()

    return {"message": "Variant deleted", "id": variant_id}


@router.delete(
    "/projects/{project_id}/variants",
    response_model=dict,
    tags=["template"]
)
async def delete_all_variants(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete all variants for a project."""
    project = get_template_project(db, project_id, current_user)

    deleted_count = db.query(Variant).filter(
        Variant.project_id == project_id
    ).delete()

    # Clear csv_columns in settings
    settings = db.query(TemplateSettings).filter(
        TemplateSettings.project_id == project_id
    ).first()
    if settings:
        settings.csv_columns = None

    db.commit()

    return {"message": "All variants deleted", "deleted_count": deleted_count}


# --- Variant Generation (LLM) Endpoints ---

async def _generate_batch_music(project_id: int) -> Optional[str]:
    """
    Generate a music track and return path to trimmed hook audio.

    Returns None if project has no music_prompt set (music disabled).
    If project has audio_source_id (pre-selected hook from Discover), uses that directly.
    """
    from app.db.base import SessionLocal
    from app.core.music_generator import MusicGenerator, sanitize_prompt
    from app.core.hook_analyzer import hook_analyzer
    from app.core.media_processor import media_processor
    from app.services.media_service import media_service
    from app.models.audio_library import AudioLibrary

    db_session = SessionLocal()
    try:
        settings = db_session.query(TemplateSettings).filter(
            TemplateSettings.project_id == project_id
        ).first()

        if not settings:
            return None

        music_mode = settings.music_mode or "none"

        # "none" — no music
        if music_mode == "none":
            return None

        # "library" — use pre-selected audio from library
        if music_mode == "library":
            project = db_session.query(Project).filter(
                Project.id == project_id
            ).first()
            if project and project.audio_source_id:
                lib_item = db_session.query(AudioLibrary).filter(
                    AudioLibrary.id == project.audio_source_id
                ).first()
                if lib_item and lib_item.file_path:
                    # Check if hook needs re-trimming for longer video
                    duration_str = settings.video_duration or "5"
                    hook_duration = float(duration_str.rstrip("s"))
                    hook_duration_ms = int(hook_duration * 1000)

                    if lib_item.duration_ms < hook_duration_ms and lib_item.track_path:
                        if os.path.exists(lib_item.track_path):
                            logger.info(
                                f"Project {project_id}: library hook {lib_item.duration_ms}ms < "
                                f"video {hook_duration_ms}ms, re-trimming from full track"
                            )

                            # Use saved coordinates if available, otherwise analyze
                            if lib_item.hook_start_ms is not None and lib_item.hook_end_ms is not None:
                                # Scale coordinates to match target duration
                                start_s = lib_item.hook_start_ms / 1000.0
                                end_s = start_s + hook_duration
                            else:
                                hooks = await hook_analyzer.find_hooks(
                                    audio_path=lib_item.track_path,
                                    video=None,
                                    num_hooks=4,
                                    hook_duration=hook_duration,
                                )
                                if not hooks:
                                    track_duration = await media_processor.get_audio_duration(
                                        lib_item.track_path
                                    )
                                    hooks = hook_analyzer._create_fallback_hooks(
                                        total_duration=track_duration,
                                        hook_duration=hook_duration,
                                        num_hooks=1,
                                    )
                                start_s = hooks[0].start
                                end_s = hooks[0].end

                            from app.core.config import settings as app_settings
                            audio_dir = os.path.join(app_settings.MEDIA_DIR, "audio")
                            os.makedirs(audio_dir, exist_ok=True)
                            hook_filename = f"project_{project_id}_hook.mp3"
                            hook_output_path = os.path.join(audio_dir, hook_filename)

                            trimmed_path = await media_processor.trim_audio(
                                audio_path=lib_item.track_path,
                                start=start_s,
                                end=end_s,
                                fade_in=0.5,
                                fade_out=0.5,
                                output_path=hook_output_path,
                            )
                            logger.info(
                                f"Project {project_id}: re-trimmed hook "
                                f"{start_s:.1f}-{end_s:.1f}s → {trimmed_path}"
                            )
                            return trimmed_path
                        else:
                            logger.error(
                                f"Project {project_id}: track_path not found on disk: "
                                f"{lib_item.track_path}"
                            )
                    elif lib_item.duration_ms < hook_duration_ms:
                        logger.warning(
                            f"Project {project_id}: hook {lib_item.duration_ms}ms < "
                            f"video {hook_duration_ms}ms but no track_path, using hook as-is"
                        )

                    logger.info(
                        f"Project {project_id}: using library audio "
                        f"(id={lib_item.id}, {lib_item.file_path})"
                    )
                    return lib_item.file_path
            logger.warning(f"Project {project_id}: music_mode=library but no audio_source found")
            return None

        # "generate" — generate from prompt
        if not settings.music_prompt:
            return None

        music_prompt = settings.music_prompt

        # Parse video duration for hook length
        duration_str = settings.video_duration or "5"
        hook_duration = float(duration_str.rstrip("s"))

        logger.info(f"Project {project_id}: generating batch music track")

        # Sanitize and generate track via Lyria2
        full_prompt = sanitize_prompt(music_prompt)
        audio_url = await media_service.generate_music(
            prompt=full_prompt,
            negative_prompt="low quality, distorted"
        )

        # Download track
        track_path = await media_processor.download_file(audio_url)
        logger.info(f"Project {project_id}: track downloaded to {track_path}")

        # Find hooks (video param unused in implementation)
        hooks = await hook_analyzer.find_hooks(
            audio_path=track_path,
            video=None,
            num_hooks=4,
            hook_duration=hook_duration,
        )

        if not hooks:
            logger.warning(f"Project {project_id}: no hooks found, using full track start")
            # Fallback: use first N seconds of track
            hooks = hook_analyzer._create_fallback_hooks(
                total_duration=30.0,
                hook_duration=hook_duration,
                num_hooks=1,
            )

        # Auto-select best hook (highest energy, first in sorted list)
        best_hook = hooks[0]
        logger.info(
            f"Project {project_id}: selected hook {best_hook.start:.1f}-{best_hook.end:.1f}s "
            f"({best_hook.energy} energy, {best_hook.type})"
        )

        # Trim hook with fade
        from app.core.config import settings as app_settings
        audio_dir = os.path.join(app_settings.MEDIA_DIR, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        hook_filename = f"project_{project_id}_hook.mp3"
        hook_output_path = os.path.join(audio_dir, hook_filename)

        trimmed_path = await media_processor.trim_audio(
            audio_path=track_path,
            start=best_hook.start,
            end=best_hook.end,
            fade_in=0.5,
            fade_out=0.5,
            output_path=hook_output_path,
        )

        logger.info(f"Project {project_id}: hook trimmed to {trimmed_path}")

        # Cleanup full track temp file
        try:
            os.remove(track_path)
        except OSError:
            pass

        return trimmed_path

    except Exception as e:
        logger.error(f"Project {project_id}: batch music generation failed: {e}")
        return None
    finally:
        db_session.close()


async def _generate_music_prompt_from_pipeline(
    preprocessing_prompt: str,
    image_prompt_template: str,
) -> str:
    """Generate a music_prompt by analyzing pipeline prompts."""
    system = (
        "You are a music director for short-form viral videos. "
        "Analyze the given video pipeline prompts and create a concise music style description "
        "for AI music generation. Output ONLY the music description (1-2 sentences), nothing else."
    )
    user_prompt = f"""Analyze these prompts from a video generation pipeline and suggest appropriate music:

PREPROCESSING PROMPT (processes raw data):
{preprocessing_prompt}

IMAGE PROMPT TEMPLATE (generates image descriptions):
{image_prompt_template}

Based on the visual style and mood of these videos, describe the ideal background music.
Include: genre, tempo, mood, instruments. Keep it concise (1-2 sentences).
Example: "Upbeat electronic lo-fi beat with soft synth pads and a catchy melody, energetic but not overwhelming"
"""

    return await openai_client.generate_text(
        prompt=user_prompt,
        system_prompt=system,
        temperature=0.7
    )


async def _generate_variant_prompt_from_pipeline(
    preprocessing_prompt: str,
    image_prompt_template: str
) -> str:
    """Generate a variant_generation_prompt by analyzing pipeline prompts."""
    system = (
        "You are a data analyst. Analyze the given prompts and create a concise instruction "
        "for generating diverse data rows (variants) as FLAT JSON objects (no nesting). "
        "Each variant is like a CSV row — simple string values only. "
        "Identify the KEY INPUT variables that the preprocessing prompt expects. "
        "Return ONLY the instruction text, nothing else."
    )
    user_prompt = f"""Analyze these two prompts from a video generation pipeline:

PREPROCESSING PROMPT (processes raw data into structured format):
{preprocessing_prompt}

IMAGE PROMPT TEMPLATE (generates image description from data):
{image_prompt_template}

The preprocessing prompt takes SHORT input descriptions and expands them into detailed JSON.
Your job: write an instruction for generating those SHORT input descriptions as FLAT JSON objects.

CRITICAL RULES:
- Each variant must be a FLAT object with simple string values — NO nested objects, NO arrays
- Think of it as CSV data: each key is a column name, each value is a RICH text description (10-30 words)
- Column names should be in the same language as the preprocessing prompt
- Values should be detailed and vivid, not generic (e.g. "Токио — Синдзюку / неоновая улица" not just "Tokyo")

The instruction should:
1. List exactly 3-6 required columns with clear names (e.g. "Место", "Мотоцикл", "модель", "одежда")
2. For each column, give an example value showing the expected detail level
3. Emphasize diversity and uniqueness
4. State that fields must vary independently (e.g. location must NOT determine character appearance)
5. Specify that values should be written in the same language as the prompts
6. Be concise (4-6 sentences)"""

    return await openai_client.generate_text(
        prompt=user_prompt,
        system_prompt=system,
        temperature=0.5
    )


@router.post(
    "/projects/{project_id}/variants/generate-prompt",
    response_model=GenerateVariantPromptResponse,
    tags=["template"]
)
async def generate_variant_prompt(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate variant_generation_prompt from pipeline prompts (preprocessing + image_prompt).

    Analyzes the pipeline prompts and creates an instruction for variant generation.
    Saves the result to settings.variant_generation_prompt.
    """
    project = get_template_project(db, project_id, current_user)

    settings = db.query(TemplateSettings).filter(
        TemplateSettings.project_id == project_id
    ).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Template settings not found")

    if not settings.preprocessing_prompt or not settings.image_prompt_template:
        raise HTTPException(
            status_code=400,
            detail="Both preprocessing_prompt and image_prompt_template must be set"
        )

    try:
        prompt = await _generate_variant_prompt_from_pipeline(
            settings.preprocessing_prompt,
            settings.image_prompt_template
        )
    except OpenAIClientError as e:
        raise HTTPException(status_code=503, detail=f"Generation failed: {e}")

    settings.variant_generation_prompt = prompt
    db.commit()
    db.refresh(settings)

    return GenerateVariantPromptResponse(prompt=prompt)


@router.post(
    "/projects/{project_id}/variants/generate",
    response_model=GenerateVariantsPreviewResponse,
    tags=["template"]
)
async def generate_variants_preview(
    project_id: int,
    data: GenerateVariantsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate variant preview using LLM. Does NOT save to database.

    Returns a preview of generated variants for user to review before saving.
    """
    project = get_template_project(db, project_id, current_user)

    settings = db.query(TemplateSettings).filter(
        TemplateSettings.project_id == project_id
    ).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Template settings not found")

    if not settings.variant_generation_prompt:
        raise HTTPException(
            status_code=400,
            detail="variant_generation_prompt is not set. Generate or set it first."
        )

    # Gather context: existing columns + sample variants
    columns = settings.csv_columns or []
    existing_variants = db.query(Variant).filter(
        Variant.project_id == project_id
    ).order_by(Variant.row_number).limit(10).all()

    examples = [v.data for v in existing_variants]

    # Build LLM prompt
    system = (
        "You are a data generator. Generate unique data rows as a JSON object with key \"variants\" "
        "containing an array of FLAT objects. Each object represents one data row. "
        "FLAT means: all values must be simple strings, NO nested objects, NO arrays. "
        "Think of each object as a CSV row with string values only. "
        "All objects MUST have the same keys. "
        "IMPORTANT: Each field must vary INDEPENDENTLY. Do not create stereotypical correlations "
        "between fields (e.g. location should NOT determine character appearance, ethnicity, or name). "
        "Mix combinations freely and unexpectedly. "
        "Return valid JSON only."
    )

    context_parts = [f"INSTRUCTION:\n{settings.variant_generation_prompt}"]

    if columns:
        context_parts.append(f"\nREQUIRED COLUMNS (use exactly these keys): {json.dumps(columns)}")

    if examples:
        context_parts.append(
            f"\nEXISTING EXAMPLES (generate different values, keep same structure):\n"
            + json.dumps(examples[:5], ensure_ascii=False, indent=2)
        )

    # Random seed to avoid similar results on repeated generations
    seed = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
    context_parts.append(
        f"\nGenerate exactly {data.count} unique variants. "
        f"DIVERSITY SEED: {seed} — use this as creative inspiration to produce COMPLETELY DIFFERENT results each time. "
        f"Avoid repeating the same cities, names, brands, or patterns. Be surprising and global. "
        f"Return JSON: {{\"variants\": [...]}}"
    )

    user_prompt = "\n".join(context_parts)

    try:
        result = await openai_client.generate_json(
            prompt=user_prompt,
            system_prompt=system,
            temperature=1.0
        )
    except OpenAIClientError as e:
        raise HTTPException(status_code=503, detail=f"Generation failed: {e}")

    variants = result.get("variants", [])
    if not variants or not isinstance(variants, list):
        raise HTTPException(status_code=503, detail="Generation failed: invalid LLM response format")

    # Extract columns from generated data
    generated_columns = list(variants[0].keys()) if variants else columns

    return GenerateVariantsPreviewResponse(
        variants=variants,
        columns=generated_columns
    )


@router.post(
    "/projects/{project_id}/variants/save-generated",
    response_model=SaveGeneratedVariantsResponse,
    tags=["template"]
)
async def save_generated_variants(
    project_id: int,
    data: SaveGeneratedVariantsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save generated variants from preview. Deduplicates against existing variants.
    """
    project = get_template_project(db, project_id, current_user)

    if not data.variants:
        raise HTTPException(status_code=400, detail="No variants to save")

    # Get existing variant data for deduplication
    existing = db.query(Variant).filter(Variant.project_id == project_id).all()
    existing_data_set = {json.dumps(v.data, sort_keys=True) for v in existing}

    # Get max row_number
    max_row = db.query(func.max(Variant.row_number)).filter(
        Variant.project_id == project_id
    ).scalar() or 0

    created = 0
    skipped = 0

    for variant_data in data.variants:
        data_key = json.dumps(variant_data, sort_keys=True)
        if data_key in existing_data_set:
            skipped += 1
            continue

        max_row += 1
        variant = Variant(
            project_id=project_id,
            row_number=max_row,
            data=variant_data,
            usage_count=0,
        )
        db.add(variant)
        existing_data_set.add(data_key)
        created += 1

    # Update csv_columns if not set
    settings = db.query(TemplateSettings).filter(
        TemplateSettings.project_id == project_id
    ).first()
    if settings and not settings.csv_columns and data.variants:
        settings.csv_columns = list(data.variants[0].keys())

    db.commit()

    return SaveGeneratedVariantsResponse(
        variants_created=created,
        duplicates_skipped=skipped
    )


# --- Video Templates Endpoints ---

@router.get(
    "/projects/{project_id}/video-templates",
    response_model=List[VideoTemplateResponse],
    tags=["template"]
)
async def list_video_templates(
    project_id: int,
    include_deleted: bool = Query(False, description="Include soft-deleted templates"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all video templates for a project."""
    project = get_template_project(db, project_id, current_user)

    query = db.query(VideoTemplate).filter(VideoTemplate.project_id == project_id)

    if not include_deleted:
        query = query.filter(VideoTemplate.is_deleted == False)

    templates = query.order_by(VideoTemplate.created_at).all()
    return templates


@router.post(
    "/projects/{project_id}/video-templates",
    response_model=VideoTemplateResponse,
    tags=["template"]
)
async def create_video_template(
    project_id: int,
    data: VideoTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new video template for a project."""
    project = get_template_project(db, project_id, current_user)

    # If this is set as default, unset other defaults
    if data.is_default:
        db.query(VideoTemplate).filter(
            VideoTemplate.project_id == project_id,
            VideoTemplate.is_deleted == False
        ).update({"is_default": False})

    template = VideoTemplate(
        project_id=project_id,
        name=data.name,
        prompt=data.prompt,
        is_default=data.is_default,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get(
    "/projects/{project_id}/video-templates/{template_id}",
    response_model=VideoTemplateResponse,
    tags=["template"]
)
async def get_video_template(
    project_id: int,
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific video template."""
    project = get_template_project(db, project_id, current_user)

    template = db.query(VideoTemplate).filter(
        VideoTemplate.id == template_id,
        VideoTemplate.project_id == project_id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Video template not found")

    return template


@router.put(
    "/projects/{project_id}/video-templates/{template_id}",
    response_model=VideoTemplateResponse,
    tags=["template"]
)
async def update_video_template(
    project_id: int,
    template_id: int,
    data: VideoTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a video template."""
    project = get_template_project(db, project_id, current_user)

    template = db.query(VideoTemplate).filter(
        VideoTemplate.id == template_id,
        VideoTemplate.project_id == project_id,
        VideoTemplate.is_deleted == False
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Video template not found")

    # If setting as default, unset other defaults
    if data.is_default:
        db.query(VideoTemplate).filter(
            VideoTemplate.project_id == project_id,
            VideoTemplate.is_deleted == False,
            VideoTemplate.id != template_id
        ).update({"is_default": False})

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    db.commit()
    db.refresh(template)
    return template


@router.delete(
    "/projects/{project_id}/video-templates/{template_id}",
    response_model=dict,
    tags=["template"]
)
async def delete_video_template(
    project_id: int,
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft-delete a video template.

    If deleting the default template, another template becomes default.
    Cannot delete if it's the only non-deleted template.
    """
    project = get_template_project(db, project_id, current_user)

    template = db.query(VideoTemplate).filter(
        VideoTemplate.id == template_id,
        VideoTemplate.project_id == project_id,
        VideoTemplate.is_deleted == False
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Video template not found")

    # Check if this is the only template
    active_count = db.query(VideoTemplate).filter(
        VideoTemplate.project_id == project_id,
        VideoTemplate.is_deleted == False
    ).count()

    if active_count <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the only video template. Create another template first."
        )

    # Soft delete
    template.is_deleted = True

    # If was default, make another template default
    if template.is_default:
        template.is_default = False
        next_default = db.query(VideoTemplate).filter(
            VideoTemplate.project_id == project_id,
            VideoTemplate.is_deleted == False,
            VideoTemplate.id != template_id
        ).first()
        if next_default:
            next_default.is_default = True

    db.commit()

    return {"message": "Video template deleted", "id": template_id}


# --- Generation Endpoints ---

@router.post(
    "/projects/{project_id}/generate",
    response_model=GenerationResponse,
    tags=["template"]
)
async def start_generation(
    project_id: int,
    data: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start a new generation for a template project.

    - variant_id: If not specified, picks least-used variant
    - video_template_id: If not specified, uses default template
    """
    from datetime import datetime

    project = get_template_project(db, project_id, current_user)

    # Get template settings
    settings = db.query(TemplateSettings).filter(
        TemplateSettings.project_id == project_id
    ).first()
    if not settings:
        raise HTTPException(status_code=400, detail="Template settings not found")

    # Get or auto-select variant
    if data.variant_id:
        variant = db.query(Variant).filter(
            Variant.id == data.variant_id,
            Variant.project_id == project_id
        ).first()
        if not variant:
            raise HTTPException(status_code=404, detail="Variant not found")
    else:
        # Auto-select least used variant
        variant = db.query(Variant).filter(
            Variant.project_id == project_id
        ).order_by(Variant.usage_count, Variant.id).first()
        if not variant:
            raise HTTPException(status_code=400, detail="No variants available. Upload a CSV first.")

    # Get or auto-select video template
    if data.video_template_id:
        video_template = db.query(VideoTemplate).filter(
            VideoTemplate.id == data.video_template_id,
            VideoTemplate.project_id == project_id,
            VideoTemplate.is_deleted == False
        ).first()
        if not video_template:
            raise HTTPException(status_code=404, detail="Video template not found")
    else:
        # Auto-select default template
        video_template = db.query(VideoTemplate).filter(
            VideoTemplate.project_id == project_id,
            VideoTemplate.is_deleted == False,
            VideoTemplate.is_default == True
        ).first()
        if not video_template:
            # Fallback to any template
            video_template = db.query(VideoTemplate).filter(
                VideoTemplate.project_id == project_id,
                VideoTemplate.is_deleted == False
            ).first()
        if not video_template:
            raise HTTPException(status_code=400, detail="No video template available")

    # Update variant usage
    variant.usage_count += 1
    variant.last_used_at = datetime.utcnow()

    # Create generation record
    generation = TemplateGeneration(
        project_id=project_id,
        variant_id=variant.id,
        video_template_id=video_template.id,
        llm_model=settings.llm_model,
        image_model=settings.image_model,
        video_model=settings.video_model,
        status="pending"
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)

    # Start background task
    async def run_generation_task(gen_id: int, proj_id: int):
        from app.db.base import SessionLocal
        db_session = SessionLocal()
        try:
            service = get_template_generation_service()
            hook_audio_path = await _generate_batch_music(proj_id)
            await service.run_generation(
                db_session, gen_id,
                hook_audio_path=hook_audio_path,
            )
        finally:
            db_session.close()

    import asyncio
    asyncio.create_task(run_generation_task(generation.id, project_id))

    # Return response with variant data
    response = GenerationResponse.model_validate(generation)
    response.variant_data = variant.data
    return response


@router.post(
    "/projects/{project_id}/generate/batch",
    response_model=BatchGenerateResponse,
    tags=["template"]
)
async def start_batch_generation(
    project_id: int,
    data: BatchGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start a batch generation for a template project.

    Modes:
    - all_unused: Generate for all variants with usage_count=0
    - least_used: Generate for the N least-used variants
    - specific: Generate for specific variant IDs
    """
    import uuid
    from datetime import datetime

    project = get_template_project(db, project_id, current_user)

    # Get template settings
    settings = db.query(TemplateSettings).filter(
        TemplateSettings.project_id == project_id
    ).first()
    if not settings:
        raise HTTPException(status_code=400, detail="Template settings not found")

    # Get or auto-select video template
    if data.video_template_id:
        video_template = db.query(VideoTemplate).filter(
            VideoTemplate.id == data.video_template_id,
            VideoTemplate.project_id == project_id,
            VideoTemplate.is_deleted == False
        ).first()
        if not video_template:
            raise HTTPException(status_code=404, detail="Video template not found")
    else:
        video_template = db.query(VideoTemplate).filter(
            VideoTemplate.project_id == project_id,
            VideoTemplate.is_deleted == False,
            VideoTemplate.is_default == True
        ).first()
        if not video_template:
            video_template = db.query(VideoTemplate).filter(
                VideoTemplate.project_id == project_id,
                VideoTemplate.is_deleted == False
            ).first()
        if not video_template:
            raise HTTPException(status_code=400, detail="No video template available")

    # Select variants based on mode
    if data.mode == "all_unused":
        variants = db.query(Variant).filter(
            Variant.project_id == project_id,
            Variant.usage_count == 0
        ).order_by(Variant.row_number).all()
        if not variants:
            raise HTTPException(status_code=400, detail="No unused variants available")

    elif data.mode == "least_used":
        count = data.count or 10
        variants = db.query(Variant).filter(
            Variant.project_id == project_id
        ).order_by(Variant.usage_count, Variant.row_number).limit(count).all()
        if not variants:
            raise HTTPException(status_code=400, detail="No variants available")

    elif data.mode == "specific":
        if not data.variant_ids:
            raise HTTPException(status_code=400, detail="variant_ids required for specific mode")
        variants = db.query(Variant).filter(
            Variant.id.in_(data.variant_ids),
            Variant.project_id == project_id
        ).all()
        if not variants:
            raise HTTPException(status_code=400, detail="No matching variants found")
        if len(variants) != len(data.variant_ids):
            raise HTTPException(
                status_code=400,
                detail=f"Found {len(variants)} of {len(data.variant_ids)} requested variants"
            )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {data.mode}")

    # Create batch
    batch_id = str(uuid.uuid4())
    generations = []

    for variant in variants:
        # Update variant usage
        variant.usage_count += 1
        variant.last_used_at = datetime.utcnow()

        generation = TemplateGeneration(
            project_id=project_id,
            variant_id=variant.id,
            video_template_id=video_template.id,
            llm_model=settings.llm_model,
            image_model=settings.image_model,
            video_model=settings.video_model,
            batch_id=batch_id,
            status="pending"
        )
        db.add(generation)
        generations.append((generation, variant))

    db.commit()

    # Refresh all generations
    for gen, _ in generations:
        db.refresh(gen)

    # Start sequential background processing
    gen_ids = [gen.id for gen, _ in generations]

    async def run_batch_task(generation_ids: list[int], project_id: int):
        from app.db.base import SessionLocal
        service = get_template_generation_service()

        # Generate music track for the batch (if music_prompt is set)
        hook_audio_path = await _generate_batch_music(project_id)

        for gen_id in generation_ids:
            db_session = SessionLocal()
            try:
                # Check if cancelled before starting
                gen = db_session.query(TemplateGeneration).filter(
                    TemplateGeneration.id == gen_id
                ).first()
                if gen and gen.status == "cancelled":
                    logger.info(f"Generation {gen_id} cancelled, skipping")
                    continue

                await service.run_generation(
                    db_session, gen_id,
                    hook_audio_path=hook_audio_path,
                )
            except Exception as e:
                # Mark as failed but continue — PROTECT cancelled status
                try:
                    gen = db_session.query(TemplateGeneration).filter(
                        TemplateGeneration.id == gen_id
                    ).first()
                    if gen and gen.status not in ("completed", "cancelled"):
                        gen.status = "failed"
                        gen.error_message = str(e)[:500]
                        db_session.commit()
                except Exception:
                    pass
            finally:
                db_session.close()

    import asyncio
    asyncio.create_task(run_batch_task(gen_ids, project_id))

    # Build response
    result = []
    for gen, variant in generations:
        response = GenerationResponse.model_validate(gen)
        response.variant_data = variant.data
        result.append(response)

    return BatchGenerateResponse(
        batch_id=batch_id,
        count=len(generations),
        generations=result
    )


@router.get(
    "/projects/{project_id}/generations",
    response_model=GenerationListResponse,
    tags=["template"]
)
async def list_generations(
    project_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List generations for a template project."""
    project = get_template_project(db, project_id, current_user)

    # Query generations (exclude soft-deleted)
    query = db.query(TemplateGeneration).filter(
        TemplateGeneration.project_id == project_id,
        TemplateGeneration.is_deleted == False
    )

    total = query.count()
    generations = query.order_by(TemplateGeneration.created_at.desc()).offset(offset).limit(limit).all()

    # Batch-load moderation statuses
    gen_ids = [g.id for g in generations]

    approved_set = set()
    rejected_set = set()
    if gen_ids:
        approved_set = {
            row[0] for row in db.query(ApprovedGeneration.template_generation_id).filter(
                ApprovedGeneration.template_generation_id.in_(gen_ids)
            ).all()
        }
        rejected_set = {
            row[0] for row in db.query(RejectionArchive.template_generation_id).filter(
                RejectionArchive.template_generation_id.in_(gen_ids)
            ).all()
        }

    # Enrich with variant data and moderation status
    result = []
    for gen in generations:
        response = GenerationResponse.model_validate(gen)
        if gen.variant_id:
            variant = db.query(Variant).filter(Variant.id == gen.variant_id).first()
            if variant:
                response.variant_data = variant.data
        # Moderation status
        if gen.id in approved_set:
            response.moderation_status = "approved"
        elif gen.id in rejected_set:
            response.moderation_status = "rejected"
        elif gen.regenerated:
            response.moderation_status = "regenerated"
        result.append(response)

    return GenerationListResponse(generations=result, total=total)


@router.get(
    "/projects/{project_id}/generations/{generation_id}",
    response_model=GenerationResponse,
    tags=["template"]
)
async def get_generation(
    project_id: int,
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific generation."""
    project = get_template_project(db, project_id, current_user)

    generation = db.query(TemplateGeneration).filter(
        TemplateGeneration.id == generation_id,
        TemplateGeneration.project_id == project_id
    ).first()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    response = GenerationResponse.model_validate(generation)
    if generation.variant_id:
        variant = db.query(Variant).filter(Variant.id == generation.variant_id).first()
        if variant:
            response.variant_data = variant.data

    return response


@router.post(
    "/projects/{project_id}/generations/{generation_id}/retry",
    response_model=GenerationResponse,
    tags=["template"]
)
async def retry_generation(
    project_id: int,
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retry a failed generation from its failed step.
    """
    project = get_template_project(db, project_id, current_user)

    generation = db.query(TemplateGeneration).filter(
        TemplateGeneration.id == generation_id,
        TemplateGeneration.project_id == project_id
    ).first()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation.status != "failed":
        raise HTTPException(status_code=400, detail="Can only retry failed generations")

    # Reset status
    generation.status = "pending"
    generation.error_message = None
    db.commit()

    # Start background task from failed step
    async def run_retry_task(gen_id: int, resume_step: str):
        from app.db.base import SessionLocal
        db_session = SessionLocal()
        try:
            service = get_template_generation_service()
            await service.run_generation(db_session, gen_id, resume_from_step=resume_step)
        finally:
            db_session.close()

    import asyncio
    asyncio.create_task(run_retry_task(generation.id, generation.failed_at_step or "preprocessing"))

    db.refresh(generation)
    response = GenerationResponse.model_validate(generation)
    if generation.variant_id:
        variant = db.query(Variant).filter(Variant.id == generation.variant_id).first()
        if variant:
            response.variant_data = variant.data

    return response


@router.delete(
    "/projects/{project_id}/generations/{generation_id}",
    status_code=204,
    tags=["template"]
)
async def delete_generation(
    project_id: int,
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft-delete a generation.
    """
    project = get_template_project(db, project_id, current_user)

    generation = db.query(TemplateGeneration).filter(
        TemplateGeneration.id == generation_id,
        TemplateGeneration.project_id == project_id,
        TemplateGeneration.is_deleted == False
    ).first()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    generation.is_deleted = True
    db.commit()

    return None


@router.post(
    "/projects/{project_id}/batches/{batch_id}/cancel",
    response_model=dict,
    tags=["template"]
)
async def cancel_batch(
    project_id: int,
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel an active batch. Marks pending/in-progress generations as cancelled.
    Completed and failed generations are not affected.
    """
    project = get_template_project(db, project_id, current_user)

    generations = db.query(TemplateGeneration).filter(
        TemplateGeneration.project_id == project_id,
        TemplateGeneration.batch_id == batch_id,
        TemplateGeneration.is_deleted == False
    ).all()

    if not generations:
        raise HTTPException(status_code=404, detail="Batch not found")

    terminal_statuses = {"completed", "failed", "cancelled"}
    cancelled_count = 0
    already_completed = 0
    already_failed = 0
    already_cancelled = 0

    for gen in generations:
        if gen.status == "completed":
            already_completed += 1
        elif gen.status == "failed":
            already_failed += 1
        elif gen.status == "cancelled":
            already_cancelled += 1
        else:
            gen.status = "cancelled"
            cancelled_count += 1

    db.commit()

    logger.info(
        f"Batch {batch_id} cancelled: {cancelled_count} cancelled, "
        f"{already_completed} completed, {already_failed} failed"
    )

    return {
        "batch_id": batch_id,
        "cancelled_count": cancelled_count,
        "already_completed": already_completed,
        "already_failed": already_failed,
        "already_cancelled": already_cancelled,
    }
