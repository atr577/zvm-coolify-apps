"""API endpoints for video moderation (Template projects)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from typing import Optional
from datetime import datetime

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.template_generation import TemplateGeneration
from app.models.template_settings import TemplateSettings
from app.models.approved_generation import ApprovedGeneration
from app.models.rejection_archive import RejectionArchive
from app.schemas.moderation import (
    ModerationQueueItem,
    ModerationQueueResponse,
    ApprovedGenerationResponse,
    ApproveRequest,
    ApproveResponse,
    PreGenerateMetadataResponse,
    RejectRequest,
    RejectionResponse,
    RejectActionResponse,
    RejectionArchiveItem,
    RejectionArchiveResponse,
    RegenerateRequest,
    RegenerateResponse,
)
from app.api.projects import user_has_workspace_access
from app.services.openai_service import openai_service
from app.services.template_generation_service import get_template_generation_service
from app.utils.urls import get_local_url

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


def get_generation_for_moderation(db: Session, project_id: int, generation_id: int) -> TemplateGeneration:
    """Get generation and verify it's pending moderation."""
    generation = db.query(TemplateGeneration).filter(
        TemplateGeneration.id == generation_id,
        TemplateGeneration.project_id == project_id
    ).first()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation.status != "completed":
        raise HTTPException(status_code=400, detail="Generation is not completed")

    if generation.regenerated:
        raise HTTPException(status_code=400, detail="Generation was regenerated")

    if generation.is_deleted:
        raise HTTPException(status_code=400, detail="Generation is deleted")

    return generation


# --- Moderation Queue ---

@router.get("/projects/{project_id}/moderation-queue", response_model=ModerationQueueResponse, tags=["moderation"])
async def get_moderation_queue(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of generations pending moderation.

    Returns completed generations that are:
    - status = completed
    - regenerated = false
    - is_deleted = false
    - NOT in approved_generations
    - NOT in rejection_archive
    """
    project = get_template_project(db, project_id, current_user)

    # Subqueries for exclusion
    approved_ids = db.query(ApprovedGeneration.template_generation_id).filter(
        ApprovedGeneration.project_id == project_id
    ).subquery()

    rejected_ids = db.query(RejectionArchive.template_generation_id).filter(
        RejectionArchive.project_id == project_id
    ).subquery()

    # Query pending generations
    generations = db.query(TemplateGeneration).options(
        joinedload(TemplateGeneration.variant),
        joinedload(TemplateGeneration.video_template)
    ).filter(
        TemplateGeneration.project_id == project_id,
        TemplateGeneration.status == "completed",
        TemplateGeneration.regenerated == False,
        TemplateGeneration.is_deleted == False,
        ~TemplateGeneration.id.in_(approved_ids),
        ~TemplateGeneration.id.in_(rejected_ids)
    ).order_by(TemplateGeneration.completed_at.asc()).all()

    # Build response
    items = []
    for gen in generations:
        item = ModerationQueueItem(
            id=gen.id,
            variant={
                "id": gen.variant.id,
                "data": gen.variant.data
            } if gen.variant else None,
            video_template={
                "id": gen.video_template.id,
                "name": gen.video_template.name
            } if gen.video_template else None,
            preprocessing_result=gen.preprocessing_result,
            image_prompt=gen.image_prompt,
            video_prompt=gen.video_prompt,
            image_url=get_local_url(gen.image_path, gen.image_url),
            video_url=get_local_url(gen.video_path, gen.video_url),
            created_at=gen.created_at,
            completed_at=gen.completed_at
        )
        items.append(item)

    return ModerationQueueResponse(items=items, total=len(items))


# --- Pre-generate Metadata ---

@router.post("/projects/{project_id}/moderation-queue/{generation_id}/pre-generate-metadata", response_model=PreGenerateMetadataResponse, tags=["moderation"])
async def pre_generate_metadata(
    project_id: int,
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Pre-generate publishing metadata for a generation WITHOUT approving it.

    Returns metadata that user can review and edit before calling approve.
    """
    project = get_template_project(db, project_id, current_user)
    generation = get_generation_for_moderation(db, project_id, generation_id)

    scenario_data = {
        "preprocessing_result": generation.preprocessing_result,
        "image_prompt": generation.image_prompt,
        "video_prompt": generation.video_prompt,
    }

    try:
        metadata = await openai_service.generate_publishing_meta(
            platforms=project.platforms or ["youtube"],
            scenario_data=scenario_data,
            fallback_text=generation.image_prompt[:500] if generation.image_prompt else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Metadata generation failed: {str(e)}. Please retry."
        )

    return PreGenerateMetadataResponse(metadata=metadata)


# --- Approve ---

@router.post("/projects/{project_id}/moderation-queue/{generation_id}/approve", response_model=ApproveResponse, tags=["moderation"])
async def approve_generation(
    project_id: int,
    generation_id: int,
    request: Optional[ApproveRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve a generation for publishing.

    1. Check for duplicate approve (409 Conflict)
    2. Use provided metadata or generate via LLM
    3. Create ApprovedGeneration with position = MAX(position) + 1
    4. Return the created ApprovedGeneration
    """
    project = get_template_project(db, project_id, current_user)
    generation = get_generation_for_moderation(db, project_id, generation_id)

    # Check for duplicate approve (CRITICAL: prevent duplicates)
    existing = db.query(ApprovedGeneration).filter(
        ApprovedGeneration.template_generation_id == generation_id
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Generation already approved")

    # Use provided metadata or generate via LLM
    if request and request.publishing_metadata:
        publishing_metadata = {
            platform: meta.model_dump() for platform, meta in request.publishing_metadata.items()
        }
    else:
        scenario_data = {
            "preprocessing_result": generation.preprocessing_result,
            "image_prompt": generation.image_prompt,
            "video_prompt": generation.video_prompt,
        }

        try:
            publishing_metadata = await openai_service.generate_publishing_meta(
                platforms=project.platforms or ["youtube"],
                scenario_data=scenario_data,
                fallback_text=generation.image_prompt[:500] if generation.image_prompt else None
            )
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Metadata generation failed: {str(e)}. Please retry."
            )

    # Get next position with FOR UPDATE to prevent race conditions
    max_position = db.query(func.max(ApprovedGeneration.position)).filter(
        ApprovedGeneration.project_id == project_id
    ).with_for_update().scalar()

    next_position = (max_position or 0) + 1

    # Create ApprovedGeneration
    approved = ApprovedGeneration(
        project_id=project_id,
        template_generation_id=generation_id,
        position=next_position,
        approved_at=datetime.utcnow(),
        publishing_metadata=publishing_metadata,
        status="approved"
    )
    db.add(approved)
    db.commit()
    db.refresh(approved)

    # Build response
    response = ApprovedGenerationResponse(
        id=approved.id,
        project_id=approved.project_id,
        template_generation_id=approved.template_generation_id,
        position=approved.position,
        approved_at=approved.approved_at,
        publishing_metadata=approved.publishing_metadata,
        status=approved.status,
        platform_statuses=approved.platform_statuses,
        retry_count=approved.retry_count,
        last_error=approved.last_error,
        published_at=approved.published_at,
        created_at=approved.created_at,
        updated_at=approved.updated_at,
        thumbnail_url=get_local_url(generation.image_path, generation.image_url),
        video_url=get_local_url(generation.video_path, generation.video_url)
    )

    return ApproveResponse(approved_generation=response)


# --- Reject ---

@router.post("/projects/{project_id}/moderation-queue/{generation_id}/reject", response_model=RejectActionResponse, tags=["moderation"])
async def reject_generation(
    project_id: int,
    generation_id: int,
    request: RejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reject a generation with reason.

    1. Create RejectionArchive entry
    2. Return the rejection record
    """
    project = get_template_project(db, project_id, current_user)
    generation = get_generation_for_moderation(db, project_id, generation_id)

    # Check for duplicate rejection
    existing = db.query(RejectionArchive).filter(
        RejectionArchive.template_generation_id == generation_id
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Generation already rejected")

    # Also check if already approved
    approved = db.query(ApprovedGeneration).filter(
        ApprovedGeneration.template_generation_id == generation_id
    ).first()

    if approved:
        raise HTTPException(status_code=409, detail="Generation already approved")

    # Create rejection
    rejection = RejectionArchive(
        project_id=project_id,
        template_generation_id=generation_id,
        reason=request.reason,
        comment=request.comment,
        rejected_by=current_user.id,
        rejected_at=datetime.utcnow()
    )
    db.add(rejection)
    db.commit()
    db.refresh(rejection)

    # Build response
    response = RejectionResponse(
        id=rejection.id,
        project_id=rejection.project_id,
        template_generation_id=rejection.template_generation_id,
        reason=rejection.reason,
        comment=rejection.comment,
        rejected_by=rejection.rejected_by,
        rejected_at=rejection.rejected_at,
        created_at=rejection.created_at,
        thumbnail_url=get_local_url(generation.image_path, generation.image_url)
    )

    return RejectActionResponse(rejection=response)


# --- Regenerate ---

@router.post("/projects/{project_id}/moderation-queue/{generation_id}/regenerate", response_model=RegenerateResponse, tags=["moderation"])
async def regenerate_generation(
    project_id: int,
    generation_id: int,
    request: Optional[RegenerateRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Regenerate a video with optional feedback.

    If feedback provided:
    1. LLM modifies prompts based on feedback
    2. New generation uses modified prompts (skips preprocessing)

    If no feedback:
    1. Full regeneration from scratch

    In both cases:
    - Mark old generation as regenerated=true
    - Create new generation
    - Start background task
    """
    project = get_template_project(db, project_id, current_user)
    generation = get_generation_for_moderation(db, project_id, generation_id)

    # Get project settings for model config
    settings = db.query(TemplateSettings).filter(
        TemplateSettings.project_id == project_id
    ).first()

    if not settings:
        raise HTTPException(status_code=400, detail="Template settings not found")

    # Process feedback if provided
    modified_prompts = None
    resume_from_step = None

    if request and request.feedback and request.feedback.strip():
        # Modify prompts based on feedback
        try:
            modified_prompts = await openai_service.modify_prompts_with_feedback(
                original_image_prompt=generation.image_prompt or "",
                original_video_prompt=generation.video_prompt,
                feedback=request.feedback.strip()
            )
            resume_from_step = "image"  # Skip preprocessing and image_prompt steps
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to modify prompts: {str(e)}. Please retry."
            )

    # Mark old generation as regenerated
    generation.regenerated = True
    db.flush()

    # Create new generation record
    new_generation = TemplateGeneration(
        project_id=project_id,
        variant_id=generation.variant_id,
        video_template_id=generation.video_template_id,
        llm_model=settings.llm_model,
        image_model=settings.image_model,
        video_model=settings.video_model,
        status="pending"
    )

    # If feedback was provided, pre-fill prompts
    if modified_prompts:
        new_generation.preprocessing_result = generation.preprocessing_result  # Copy original
        new_generation.image_prompt = modified_prompts["image_prompt"]
        new_generation.video_prompt = modified_prompts["video_prompt"]

    db.add(new_generation)
    db.commit()
    db.refresh(new_generation)

    # Start background task
    import asyncio
    async def run_generation_task(gen_id: int, resume_step: Optional[str] = None):
        from app.db.base import SessionLocal
        db_session = SessionLocal()
        try:
            service = get_template_generation_service()
            await service.run_generation(db_session, gen_id, resume_from_step=resume_step)
        finally:
            db_session.close()

    asyncio.create_task(run_generation_task(new_generation.id, resume_from_step))

    return RegenerateResponse(
        new_generation={
            "id": new_generation.id,
            "status": new_generation.status,
            "variant_id": new_generation.variant_id,
            "video_template_id": new_generation.video_template_id,
            "created_at": new_generation.created_at.isoformat() if new_generation.created_at else None,
            "feedback_applied": modified_prompts is not None,
            "changes_summary": modified_prompts.get("changes_summary") if modified_prompts else None
        }
    )


# --- Rejection Archive ---

@router.get("/projects/{project_id}/rejection-archive", response_model=RejectionArchiveResponse, tags=["moderation"])
async def get_rejection_archive(
    project_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of rejected generations.
    """
    project = get_template_project(db, project_id, current_user)

    # Query rejections with generation data
    rejections = db.query(RejectionArchive).options(
        joinedload(RejectionArchive.template_generation).joinedload(TemplateGeneration.variant),
        joinedload(RejectionArchive.rejected_by_user)
    ).filter(
        RejectionArchive.project_id == project_id
    ).order_by(RejectionArchive.rejected_at.desc()).offset(offset).limit(limit).all()

    total = db.query(func.count(RejectionArchive.id)).filter(
        RejectionArchive.project_id == project_id
    ).scalar()

    # Build response
    items = []
    for rej in rejections:
        gen = rej.template_generation
        item = RejectionArchiveItem(
            id=rej.id,
            template_generation_id=rej.template_generation_id,
            reason=rej.reason,
            comment=rej.comment,
            rejected_by=rej.rejected_by,
            rejected_by_name=rej.rejected_by_user.full_name or rej.rejected_by_user.email if rej.rejected_by_user else None,
            rejected_at=rej.rejected_at,
            thumbnail_url=get_local_url(gen.image_path, gen.image_url) if gen else None,
            variant_data=gen.variant.data if gen and gen.variant else None
        )
        items.append(item)

    return RejectionArchiveResponse(items=items, total=total)
