"""API endpoints for Template project type."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
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
)
from app.api.projects import user_has_workspace_access, get_user_workspace_ids
from app.services.csv_parser import parse_csv, validate_csv_for_project, CSVParseError
from app.services.template_generation_service import get_template_generation_service

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

    return {
        "id": project.id,
        "name": project.name,
        "project_type": project.project_type,
        "message": "Template project created successfully"
    }


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

    return settings


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
    for field, value in update_data.items():
        if hasattr(value, 'value'):  # Enum
            setattr(settings, field, value.value)
        else:
            setattr(settings, field, value)

    db.commit()
    db.refresh(settings)
    return settings


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
    async def run_generation_task(gen_id: int):
        from app.db.base import SessionLocal
        db_session = SessionLocal()
        try:
            service = get_template_generation_service()
            await service.run_generation(db_session, gen_id)
        finally:
            db_session.close()

    import asyncio
    asyncio.create_task(run_generation_task(generation.id))

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

    async def run_batch_task(generation_ids: list[int]):
        from app.db.base import SessionLocal
        service = get_template_generation_service()
        for gen_id in generation_ids:
            db_session = SessionLocal()
            try:
                await service.run_generation(db_session, gen_id)
            except Exception as e:
                # Mark as failed but continue with the rest
                try:
                    gen = db_session.query(TemplateGeneration).filter(
                        TemplateGeneration.id == gen_id
                    ).first()
                    if gen and gen.status != "completed":
                        gen.status = "failed"
                        gen.error_message = str(e)[:500]
                        db_session.commit()
                except Exception:
                    pass
            finally:
                db_session.close()

    import asyncio
    asyncio.create_task(run_batch_task(gen_ids))

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

    # Enrich with variant data
    result = []
    for gen in generations:
        response = GenerationResponse.model_validate(gen)
        if gen.variant_id:
            variant = db.query(Variant).filter(Variant.id == gen.variant_id).first()
            if variant:
                response.variant_data = variant.data
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
