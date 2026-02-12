"""API endpoints for Discover workflow."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.discover import (
    DiscoverProjectCreate,
    DiscoverProjectResponse,
    DiscoverProjectListResponse,
    DiscoverRoundResponse,
    DiscoverExtractionResponse,
    DiscoverAudioVariantResponse,
    GenerateRoundRequest,
    SelectionRequest,
    SelectionResponse,
    AdvanceRequest,
    AdvanceExtractionRequest,
    ExtractionUpdateRequest,
    CreateTemplateRequest,
    RefinementResponse,
    BlockUpdateRequest,
    PromptUpdateRequest,
    CompileResponse,
    AdvanceAudioRequest,
    GenerateSfxRequest,
    GenerateMusicRequest,
    SelectHookRequest,
    SelectLibraryRequest,
    ConfirmAudioRequest,
)
from app.services.discover_service import get_discover_service

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Project CRUD ---

@router.post("", response_model=DiscoverProjectResponse)
async def create_discover_project(
    data: DiscoverProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new Discover project."""
    service = get_discover_service()
    try:
        project = await service.create_project(
            db=db,
            user_id=current_user.id,
            workspace_id=data.workspace_id,
            concept=data.concept,
            name=data.name,
            image_model=data.image_model,
            video_model=data.video_model,
            image_aspect_ratio=data.image_aspect_ratio,
            video_duration=data.video_duration,
        )
        return project
    except Exception as e:
        logger.error(f"Create discover project failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=DiscoverProjectListResponse)
async def list_discover_projects(
    workspace_id: int | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List discover projects for a workspace."""
    service = get_discover_service()
    projects = await service.list_projects(
        db=db,
        user_id=current_user.id,
        workspace_id=workspace_id,
        status=status,
    )
    return DiscoverProjectListResponse(projects=projects, total=len(projects))


@router.get("/{project_id}", response_model=DiscoverProjectResponse)
async def get_discover_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a discover project with all rounds, items, and extraction."""
    service = get_discover_service()
    try:
        project = await service.get_project(db, project_id, current_user.id)
        return project
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{project_id}", status_code=204)
async def archive_discover_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archive (soft-delete) a discover project."""
    service = get_discover_service()
    try:
        await service.archive_project(db, project_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return None


# --- Rounds ---

@router.post("/{project_id}/rounds", response_model=dict)
async def generate_round(
    project_id: int,
    data: GenerateRoundRequest = GenerateRoundRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate the next round of exploration (image or video)."""
    service = get_discover_service()
    try:
        round_obj = await service.generate_round(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            feedback=data.feedback,
            model_override=data.model,
            count_override=data.count,
        )
        return {
            "round": DiscoverRoundResponse.model_validate(round_obj),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/rounds/{round_id}/select", response_model=SelectionResponse)
async def submit_selection(
    project_id: int,
    round_id: int,
    data: SelectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit user selections for a round."""
    service = get_discover_service()
    try:
        # Convert SelectionValue enum to string values
        selections = {k: v.value for k, v in data.selections.items()}
        result = await service.submit_selection(
            db=db,
            project_id=project_id,
            round_id=round_id,
            selections=selections,
            feedback=data.feedback,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/rounds/{round_id}/retry", response_model=dict)
async def retry_failed_items(
    project_id: int,
    round_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retry all failed items in a round."""
    service = get_discover_service()
    try:
        retried = await service.retry_failed_items(
            db=db,
            project_id=project_id,
            round_id=round_id,
            user_id=current_user.id,
        )
        return {"retried_count": retried}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Stage Management ---

@router.post("/{project_id}/advance", response_model=DiscoverProjectResponse)
async def advance_to_video(
    project_id: int,
    data: AdvanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Advance from images to video stage."""
    service = get_discover_service()
    try:
        project = await service.advance_to_video(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            finalist_item_id=data.finalist_image_item_id,
        )
        # Re-fetch with eager loading
        project = await service.get_project(db, project_id, current_user.id)
        return project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/advance-extraction", response_model=DiscoverProjectResponse)
async def advance_to_extraction(
    project_id: int,
    data: AdvanceExtractionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Advance from videos to extraction stage."""
    service = get_discover_service()
    try:
        project = await service.advance_to_extraction(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            finalist_video_item_id=data.finalist_video_item_id,
        )
        project = await service.get_project(db, project_id, current_user.id)
        return project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/rollback", response_model=dict)
async def rollback(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rollback to previous round."""
    service = get_discover_service()
    try:
        result = await service.rollback(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Extraction ---

@router.post("/{project_id}/extract", response_model=dict)
async def extract_template(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract template prompts from winning combo."""
    service = get_discover_service()
    try:
        extraction = await service.extract_template(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
        )
        return {
            "extraction": DiscoverExtractionResponse.model_validate(extraction),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{project_id}/extraction", response_model=DiscoverExtractionResponse)
async def update_extraction(
    project_id: int,
    data: ExtractionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user-edited extraction prompts."""
    service = get_discover_service()
    try:
        extraction = await service.update_extraction(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            edited_base_prompt=data.edited_base_prompt,
            edited_variation_prompt=data.edited_variation_prompt,
        )
        return extraction
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Template Creation ---

@router.post("/{project_id}/create-template", response_model=dict)
async def create_template(
    project_id: int,
    data: CreateTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create Template project from extraction. Auto-extracts if needed."""
    service = get_discover_service()
    try:
        # Auto-run extraction if not done yet
        project = await service.get_project(db, project_id, current_user.id)
        if not project.extraction:
            await service.extract_template(db, project_id, current_user.id)

        template_project_id = await service.create_template_project(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            name=data.name,
            platforms=data.platforms,
            video_template_prompt=data.video_template_prompt,
        )
        return {
            "project_id": template_project_id,
            "message": "Template project created from Discover",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/finalize", response_model=dict)
async def finalize_and_create_template(
    project_id: int,
    data: AdvanceExtractionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    One-click finalize: set video finalist → extract → create template.
    Returns the created template project ID.
    """
    service = get_discover_service()
    try:
        # 1. Advance to extraction (sets finalist_video_item_id)
        await service.advance_to_extraction(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            finalist_video_item_id=data.finalist_video_item_id,
        )

        # 2. Run extraction
        await service.extract_template(db, project_id, current_user.id)

        # 3. Get project for auto-naming and video prompt
        project = await service.get_project(db, project_id, current_user.id)
        extraction = project.extraction

        # Get winning video prompt
        finalist_video = next(
            (item for r in project.rounds if r.round_type == "video"
             for item in r.items if item.id == project.finalist_video_item_id),
            None
        )
        video_prompt = finalist_video.prompt if finalist_video else ""

        # 4. Create template project
        template_project_id = await service.create_template_project(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            name=f"{project.name} Template",
            platforms=["youtube", "instagram", "tiktok"],
            video_template_prompt=video_prompt,
        )

        return {
            "project_id": template_project_id,
            "message": "Template project created",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Audio Selection ---

@router.post("/{project_id}/advance-audio", response_model=DiscoverProjectResponse)
async def advance_to_audio(
    project_id: int,
    data: AdvanceAudioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Advance from videos to audio stage."""
    service = get_discover_service()
    try:
        await service.advance_to_audio(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            finalist_video_item_id=data.finalist_video_item_id,
        )
        project = await service.get_project(db, project_id, current_user.id)
        return project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/audio/generate-sfx", response_model=DiscoverAudioVariantResponse)
async def generate_sfx(
    project_id: int,
    data: GenerateSfxRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate Sound FX via MMAudio V2."""
    service = get_discover_service()
    try:
        variant = await service.generate_sfx(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            mode=data.mode,
            prompt=data.prompt,
        )
        return variant
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/audio/generate-music", response_model=DiscoverAudioVariantResponse)
async def generate_music(
    project_id: int,
    data: GenerateMusicRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate music via Lyria2."""
    service = get_discover_service()
    try:
        variant = await service.generate_music(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            mode=data.mode,
            prompt=data.prompt,
        )
        return variant
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/audio/select-hook", response_model=DiscoverAudioVariantResponse)
async def select_hook(
    project_id: int,
    data: SelectHookRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Select a hook segment from detected hooks."""
    service = get_discover_service()
    try:
        variant = await service.select_hook(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            variant_id=data.variant_id,
            hook_start_ms=data.hook_start_ms,
            hook_end_ms=data.hook_end_ms,
        )
        return variant
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/audio/select-library", response_model=DiscoverAudioVariantResponse)
async def select_library(
    project_id: int,
    data: SelectLibraryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Select track from audio library."""
    service = get_discover_service()
    try:
        variant = await service.select_from_library(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            library_item_id=data.library_item_id,
        )
        return variant
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/audio/confirm", response_model=DiscoverProjectResponse)
async def confirm_audio(
    project_id: int,
    data: ConfirmAudioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confirm audio selection. Merges video+audio, advances to extraction."""
    service = get_discover_service()
    try:
        await service.confirm_audio(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            variant_id=data.variant_id,
        )
        project = await service.get_project(db, project_id, current_user.id)
        return project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/audio/skip", response_model=DiscoverProjectResponse)
async def skip_audio(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Skip audio. Advances to extraction."""
    service = get_discover_service()
    try:
        await service.skip_audio(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
        )
        project = await service.get_project(db, project_id, current_user.id)
        return project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/extraction/rollback", response_model=dict)
async def rollback_extraction(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rollback from extraction/completed to audio stage."""
    service = get_discover_service()
    try:
        await service.rollback_from_extraction(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
        )
        return {"message": "Rolled back to audio stage"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/audio/rollback", response_model=dict)
async def rollback_audio(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rollback from audio to videos stage."""
    service = get_discover_service()
    try:
        await service.rollback_from_audio(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
        )
        return {"message": "Rolled back to videos stage"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Prompt Refinement ---

@router.get("/{project_id}/refine", response_model=RefinementResponse)
async def get_refinement(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get existing prompt refinement for a project."""
    service = get_discover_service()
    try:
        result = await service.get_refinement(db, project_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="No refinement found")
    return result


@router.post("/{project_id}/refine", response_model=RefinementResponse)
async def analyze_concept(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyze concept and create prompt refinement with blocks."""
    service = get_discover_service()
    try:
        return await service.analyze_concept(db, project_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.delete("/{project_id}/refine", status_code=204)
async def delete_refinement(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete refinement for re-analysis."""
    service = get_discover_service()
    try:
        await service.delete_refinement(db, project_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{project_id}/refine", response_model=RefinementResponse)
async def update_block(
    project_id: int,
    data: BlockUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a single block value (accept, edit, or answer)."""
    service = get_discover_service()
    try:
        return await service.update_block(
            db, project_id, current_user.id, data.block_name, data.value,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/refine/compile", response_model=CompileResponse)
async def compile_prompt(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compile final prompt from confirmed blocks. Score >= 80 required."""
    service = get_discover_service()
    try:
        result = await service.compile_prompt(db, project_id, current_user.id)
        return {
            "refined_prompt": result["refined_prompt"],
            "score": result["score"],
            "ready_to_generate": result["ready_to_generate"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.put("/{project_id}/refine/prompt", response_model=RefinementResponse)
async def update_prompt(
    project_id: int,
    data: PromptUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit the compiled prompt before generation."""
    service = get_discover_service()
    try:
        return await service.update_refined_prompt(
            db, project_id, current_user.id, data.refined_prompt,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
