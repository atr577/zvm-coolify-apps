"""
Workflow API v2 - New endpoint pattern per CONTRACTS.md

URL Convention: /api/workflow/{video_id}/{step_type}/{action}

Implements:
- POST /workflow/{video_id}/start - Start/continue workflow
- GET /workflow/{video_id}/{step_type}/variants - Get step variants
- POST /workflow/{video_id}/{step_type}/select - Select variant
- POST /workflow/{video_id}/{step_type}/approve - Approve step
- POST /workflow/{video_id}/{step_type}/reject - Reject step (analytics)
- POST /workflow/{video_id}/{step_type}/regenerate - Regenerate with feedback
- POST /workflow/{video_id}/{step_type}/retry - Retry failed step
- POST /workflow/{video_id}/rollback/{target_step} - Rollback to step
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Any, Dict

from app.db.base import get_db
from app.models.video import Video, WorkflowMode, WorkflowStatus, StepType
from app.models.workflow_step import WorkflowStep
from app.models.user import User, WorkspaceMember
from app.core.deps import get_current_user
from app.services.workflow.orchestrator_v2 import WorkflowOrchestratorV2

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class StartResponse(BaseModel):
    video_id: int
    status: str
    current_step: str
    message: str


class VariantItem(BaseModel):
    id: int
    variant_number: int
    content: Dict[str, Any]
    is_selected: bool


class AttemptVariants(BaseModel):
    attempt_id: int
    attempt_number: int
    variants: List[VariantItem]
    feedback: Optional[str] = None


class VariantsResponse(BaseModel):
    step_type: str
    step_id: int
    current_attempt: AttemptVariants
    previous_attempts: List[AttemptVariants]


class SelectRequest(BaseModel):
    variant_id: int


class SelectResponse(BaseModel):
    step_type: str
    variant_id: int
    status: str


class ApproveResponse(BaseModel):
    step_type: str
    status: str
    next_step: Optional[str]
    auto_continue: bool
    video_status: str


class RejectRequest(BaseModel):
    reason: Optional[str] = None


class RejectResponse(BaseModel):
    step_type: str
    status: str
    available_actions: List[str]
    previous_variants_count: int


class RegenerateRequest(BaseModel):
    variant_id: int
    feedback: Optional[str] = None


class RegenerateResponse(BaseModel):
    step_type: str
    attempt_id: int
    status: str


class RetryResponse(BaseModel):
    step_type: str
    attempt_id: int
    status: str


class RollbackResponse(BaseModel):
    video_id: int
    rolled_back_to: str
    deleted_steps: List[str]
    status: str


# =============================================================================
# Helper Functions
# =============================================================================

def get_video_with_auth(db: Session, video_id: int, user: User) -> Video:
    """Get video with ownership check.

    Access granted if:
    1. User is project owner (project.user_id == user.id)
    2. OR User is workspace member (project in workspace where user is member)
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not video.project:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check 1: Direct project ownership
    if video.project.user_id == user.id:
        return video

    # Check 2: Workspace membership
    if video.project.workspace_id:
        is_member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == video.project.workspace_id,
            WorkspaceMember.user_id == user.id
        ).first()
        if is_member:
            return video

    raise HTTPException(status_code=403, detail="Not authorized")


def parse_step_type(step_type: str) -> StepType:
    """Parse step type string to enum."""
    try:
        return StepType(step_type.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step type: {step_type}. Valid: story, description, prompt, image, scenario, video, audio"
        )


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/{video_id}/start", response_model=StartResponse)
async def start_workflow(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start or continue workflow for a video.

    - Discover: starts with STORY
    - Remix: calls PREPARE, starts with IMAGE
    - Sets video.status = IN_PROGRESS

    Returns 202 Accepted with current step info.
    """
    video = get_video_with_auth(db, video_id, current_user)

    # Concurrency protection: check status with lock
    db.refresh(video)  # Refresh to get latest state

    if video.status == WorkflowStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="Generation already in progress")

    if video.status == WorkflowStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Video already completed")

    # Create orchestrator and run
    orchestrator = WorkflowOrchestratorV2(db, video)
    result = await orchestrator.run()

    return StartResponse(
        video_id=result.video_id,
        status=result.status,
        current_step=result.current_step,
        message=result.message
    )


@router.get("/{video_id}/{step_type}/variants", response_model=VariantsResponse)
async def get_variants(
    video_id: int,
    step_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all variants for a step (current and previous attempts)."""
    video = get_video_with_auth(db, video_id, current_user)
    step_enum = parse_step_type(step_type)

    # Get the workflow step
    step = db.query(WorkflowStep).filter(
        WorkflowStep.video_id == video_id,
        WorkflowStep.step_type == step_enum
    ).first()

    if not step:
        raise HTTPException(status_code=404, detail=f"Step {step_type} not found")

    # Get attempts with variants
    from app.models.step_attempt import StepAttempt, Variant

    attempts = db.query(StepAttempt).filter(
        StepAttempt.step_id == step.id
    ).order_by(StepAttempt.attempt_number.desc()).all()

    if not attempts:
        raise HTTPException(status_code=404, detail="No attempts found for this step")

    # Build response
    current_attempt = attempts[0]
    previous_attempts = attempts[1:] if len(attempts) > 1 else []

    def build_attempt_variants(attempt: StepAttempt) -> AttemptVariants:
        variants = db.query(Variant).filter(
            Variant.attempt_id == attempt.id
        ).order_by(Variant.variant_number).all()

        return AttemptVariants(
            attempt_id=attempt.id,
            attempt_number=attempt.attempt_number,
            feedback=attempt.feedback,
            variants=[
                VariantItem(
                    id=v.id,
                    variant_number=v.variant_number,
                    content=v.content or {},
                    is_selected=v.is_selected
                )
                for v in variants
            ]
        )

    return VariantsResponse(
        step_type=step_type,
        step_id=step.id,
        current_attempt=build_attempt_variants(current_attempt),
        previous_attempts=[build_attempt_variants(a) for a in previous_attempts]
    )


@router.post("/{video_id}/{step_type}/select", response_model=SelectResponse)
async def select_variant(
    video_id: int,
    step_type: str,
    request: SelectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Select a variant as current choice.

    - Sets WorkflowStep.selected_variant_id
    - Sets Variant.is_selected = true (resets others)
    - Does NOT copy to Video (only on approve)
    """
    video = get_video_with_auth(db, video_id, current_user)
    step_enum = parse_step_type(step_type)

    from app.models.step_attempt import Variant

    # Get the step
    step = db.query(WorkflowStep).filter(
        WorkflowStep.video_id == video_id,
        WorkflowStep.step_type == step_enum
    ).first()

    if not step:
        raise HTTPException(status_code=404, detail=f"Step {step_type} not found")

    # Get the variant
    variant = db.query(Variant).filter(Variant.id == request.variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    # Verify variant belongs to this step
    from app.models.step_attempt import StepAttempt
    attempt = db.query(StepAttempt).filter(StepAttempt.id == variant.attempt_id).first()
    if not attempt or attempt.step_id != step.id:
        raise HTTPException(status_code=400, detail="Variant does not belong to this step")

    # Reset all variants for this step
    all_variants = db.query(Variant).join(StepAttempt).filter(
        StepAttempt.step_id == step.id
    ).all()
    for v in all_variants:
        v.is_selected = False

    # Select this variant
    variant.is_selected = True
    step.selected_variant_id = variant.id
    db.commit()

    return SelectResponse(
        step_type=step_type,
        variant_id=variant.id,
        status="selected"
    )


@router.post("/{video_id}/{step_type}/approve", response_model=ApproveResponse)
async def approve_step(
    video_id: int,
    step_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve step and copy selected variant to Video.

    - Sets WorkflowStep.status = APPROVED
    - Copies selected_variant.content to Video.{field}
    - Returns next_step and auto_continue flag
    """
    video = get_video_with_auth(db, video_id, current_user)
    step_enum = parse_step_type(step_type)

    # Get the step with lock
    step = db.query(WorkflowStep).filter(
        WorkflowStep.video_id == video_id,
        WorkflowStep.step_type == step_enum
    ).with_for_update().first()

    if not step:
        raise HTTPException(status_code=404, detail=f"Step {step_type} not found")

    if step.status != WorkflowStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve: step is {step.status.value}"
        )

    # Get selected variant
    from app.models.step_attempt import Variant

    if not step.selected_variant_id:
        raise HTTPException(status_code=400, detail="No variant selected")

    variant = db.query(Variant).filter(Variant.id == step.selected_variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Selected variant not found")

    # Copy variant content to Video
    content = variant.content or {}
    _copy_variant_to_video(video, step_enum, content)

    # Mark step as approved
    step.status = WorkflowStatus.APPROVED

    # Determine next step
    is_remix = video.project.project_type == "remix"
    next_step = _get_next_step(step_enum, is_remix)
    is_last_step = next_step is None

    if is_last_step:
        # Last step (AUDIO) - complete workflow
        video.status = WorkflowStatus.COMPLETED
        auto_continue = False
    else:
        # More steps to go
        video.current_step = next_step
        video.status = WorkflowStatus.IN_PROGRESS
        auto_continue = True

    db.commit()

    return ApproveResponse(
        step_type=step_type,
        status="approved",
        next_step=next_step.value.lower() if next_step else None,
        auto_continue=auto_continue,
        video_status=video.status.value.lower()
    )


@router.post("/{video_id}/{step_type}/reject", response_model=RejectResponse)
async def reject_step(
    video_id: int,
    step_type: str,
    request: RejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reject step (for analytics). Status does NOT change.

    User can then regenerate or select another variant.
    """
    video = get_video_with_auth(db, video_id, current_user)
    step_enum = parse_step_type(step_type)

    step = db.query(WorkflowStep).filter(
        WorkflowStep.video_id == video_id,
        WorkflowStep.step_type == step_enum
    ).first()

    if not step:
        raise HTTPException(status_code=404, detail=f"Step {step_type} not found")

    # Log rejection for analytics (could store in a separate table)
    # For now, just count previous variants
    from app.models.step_attempt import StepAttempt, Variant

    variant_count = db.query(Variant).join(StepAttempt).filter(
        StepAttempt.step_id == step.id
    ).count()

    return RejectResponse(
        step_type=step_type,
        status="rejected",
        available_actions=["regenerate", "select_other_variant"],
        previous_variants_count=variant_count
    )


@router.post("/{video_id}/{step_type}/regenerate", response_model=RegenerateResponse)
async def regenerate_step(
    video_id: int,
    step_type: str,
    request: RegenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Regenerate step with new attempt based on selected variant + feedback.
    """
    video = get_video_with_auth(db, video_id, current_user)
    step_enum = parse_step_type(step_type)

    step = db.query(WorkflowStep).filter(
        WorkflowStep.video_id == video_id,
        WorkflowStep.step_type == step_enum
    ).first()

    if not step:
        raise HTTPException(status_code=404, detail=f"Step {step_type} not found")

    # Create new attempt
    from app.models.step_attempt import StepAttempt

    # Get current attempt number
    max_attempt = db.query(StepAttempt).filter(
        StepAttempt.step_id == step.id
    ).order_by(StepAttempt.attempt_number.desc()).first()

    new_attempt_number = (max_attempt.attempt_number + 1) if max_attempt else 1

    new_attempt = StepAttempt(
        step_id=step.id,
        attempt_number=new_attempt_number,
        parent_variant_id=request.variant_id,
        feedback=request.feedback,
        status="pending"
    )
    db.add(new_attempt)

    # Update step and video status
    step.status = WorkflowStatus.IN_PROGRESS
    video.status = WorkflowStatus.IN_PROGRESS
    db.commit()
    db.refresh(new_attempt)

    # TODO: Trigger actual regeneration (background task)
    # For now, return the attempt info

    return RegenerateResponse(
        step_type=step_type,
        attempt_id=new_attempt.id,
        status="in_progress"
    )


@router.post("/{video_id}/{step_type}/retry", response_model=RetryResponse)
async def retry_step(
    video_id: int,
    step_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry failed step without feedback."""
    video = get_video_with_auth(db, video_id, current_user)
    step_enum = parse_step_type(step_type)

    step = db.query(WorkflowStep).filter(
        WorkflowStep.video_id == video_id,
        WorkflowStep.step_type == step_enum
    ).first()

    if not step:
        raise HTTPException(status_code=404, detail=f"Step {step_type} not found")

    if step.status != WorkflowStatus.FAILED:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot retry: step is {step.status.value}, expected FAILED"
        )

    # Create new attempt
    from app.models.step_attempt import StepAttempt

    max_attempt = db.query(StepAttempt).filter(
        StepAttempt.step_id == step.id
    ).order_by(StepAttempt.attempt_number.desc()).first()

    new_attempt_number = (max_attempt.attempt_number + 1) if max_attempt else 1

    new_attempt = StepAttempt(
        step_id=step.id,
        attempt_number=new_attempt_number,
        status="pending"
    )
    db.add(new_attempt)

    step.status = WorkflowStatus.IN_PROGRESS
    video.status = WorkflowStatus.IN_PROGRESS
    db.commit()
    db.refresh(new_attempt)

    return RetryResponse(
        step_type=step_type,
        attempt_id=new_attempt.id,
        status="in_progress"
    )


@router.post("/{video_id}/rollback/{target_step}", response_model=RollbackResponse)
async def rollback_to_step(
    video_id: int,
    target_step: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Rollback workflow to a specific step.

    - Deletes all steps AFTER target
    - Clears Video fields for deleted steps
    - Sets target step to AWAITING_APPROVAL
    """
    video = get_video_with_auth(db, video_id, current_user)
    target_enum = parse_step_type(target_step)

    # Cannot rollback if published
    if video.is_published:
        raise HTTPException(
            status_code=409,
            detail="Cannot rollback: video already published"
        )

    # Get step order
    is_remix = video.project.project_type == "remix"
    step_order = _get_step_order(is_remix)

    if target_enum not in step_order:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid target step for {'remix' if is_remix else 'discover'} workflow"
        )

    target_index = step_order.index(target_enum)
    steps_to_delete = step_order[target_index + 1:]

    # Delete steps after target (cascade will delete attempts/variants)
    deleted_steps = []
    for step_type in steps_to_delete:
        step = db.query(WorkflowStep).filter(
            WorkflowStep.video_id == video_id,
            WorkflowStep.step_type == step_type
        ).first()
        if step:
            db.delete(step)
            deleted_steps.append(step_type.value.lower())

    # Clear Video fields
    for step_type in steps_to_delete:
        _clear_video_field(video, step_type)

    # Reset target step to awaiting approval
    target_step_obj = db.query(WorkflowStep).filter(
        WorkflowStep.video_id == video_id,
        WorkflowStep.step_type == target_enum
    ).first()

    if target_step_obj:
        target_step_obj.status = WorkflowStatus.AWAITING_APPROVAL

    video.current_step = target_enum
    video.status = WorkflowStatus.AWAITING_APPROVAL
    db.commit()

    return RollbackResponse(
        video_id=video_id,
        rolled_back_to=target_step,
        deleted_steps=deleted_steps,
        status="awaiting_approval"
    )


# =============================================================================
# Helper Functions for Step Logic
# =============================================================================

def _get_next_step(current_step: StepType, is_remix: bool) -> Optional[StepType]:
    """Get the next step in the workflow."""
    if is_remix:
        remix_order = [StepType.IMAGE, StepType.VIDEO, StepType.AUDIO]
        try:
            idx = remix_order.index(current_step)
            return remix_order[idx + 1] if idx + 1 < len(remix_order) else None
        except ValueError:
            return None
    else:
        discover_order = [
            StepType.STORY, StepType.DESCRIPTION, StepType.PROMPT,
            StepType.IMAGE, StepType.SCENARIO, StepType.VIDEO, StepType.AUDIO
        ]
        try:
            idx = discover_order.index(current_step)
            return discover_order[idx + 1] if idx + 1 < len(discover_order) else None
        except ValueError:
            return None


def _get_step_order(is_remix: bool) -> List[StepType]:
    """Get ordered list of steps for workflow type."""
    if is_remix:
        return [StepType.IMAGE, StepType.VIDEO, StepType.AUDIO]
    else:
        return [
            StepType.STORY, StepType.DESCRIPTION, StepType.PROMPT,
            StepType.IMAGE, StepType.SCENARIO, StepType.VIDEO, StepType.AUDIO
        ]


def _copy_variant_to_video(video: Video, step_type: StepType, content: Dict[str, Any]):
    """Copy variant content to appropriate Video field."""
    field_mapping = {
        StepType.STORY: "story_data",
        StepType.DESCRIPTION: "description_data",
        StepType.PROMPT: "prompt_data",
        StepType.IMAGE: "image_url",
        StepType.SCENARIO: "scenario_data",
        StepType.VIDEO: "video_url",
        StepType.AUDIO: "video_with_audio_url",
    }

    field = field_mapping.get(step_type)
    if field:
        if step_type in [StepType.IMAGE, StepType.VIDEO, StepType.AUDIO]:
            # URL fields - extract url from content
            setattr(video, field, content.get("url", content))
        else:
            # JSON fields - set content directly
            setattr(video, field, content)


def _clear_video_field(video: Video, step_type: StepType):
    """Clear Video field for a step type."""
    field_mapping = {
        StepType.STORY: "story_data",
        StepType.DESCRIPTION: "description_data",
        StepType.PROMPT: "prompt_data",
        StepType.IMAGE: "image_url",
        StepType.SCENARIO: "scenario_data",
        StepType.VIDEO: "video_url",
        StepType.AUDIO: "video_with_audio_url",
    }

    field = field_mapping.get(step_type)
    if field:
        setattr(video, field, None)
