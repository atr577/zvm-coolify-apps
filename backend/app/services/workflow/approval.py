"""
Step approval logic for workflow management.
Extracted from workflow.py API endpoint.
"""
import inspect
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.video import Video, WorkflowMode
from app.models.workflow_step import WorkflowStep, WorkflowStatus, StepType
from app.services.kling_service import kling_service


# Map current step to next step (Discover mode)
DISCOVER_NEXT_STEP = {
    StepType.STORY: StepType.DESCRIPTION,
    StepType.DESCRIPTION: StepType.PROMPT,
    StepType.PROMPT: StepType.IMAGE,
    StepType.IMAGE: StepType.SCENARIO,
    StepType.SCENARIO: StepType.VIDEO,
    StepType.VIDEO: StepType.AUDIO,
    StepType.AUDIO: StepType.ADAPTATION,
    StepType.ADAPTATION: StepType.PUBLISHING,
}

# Remix mode: IMAGE → VIDEO → AUDIO (no text steps, no scenario, no adaptation)
REMIX_NEXT_STEP = {
    StepType.IMAGE: StepType.VIDEO,
    StepType.VIDEO: StepType.AUDIO,
    # AUDIO is final for Remix
}

# Legacy alias
NEXT_STEP_MAP = DISCOVER_NEXT_STEP


class ApprovalHandler:
    """Handles step approval/rejection logic."""

    def __init__(self, db: Session, step: WorkflowStep):
        self.db = db
        self.step = step
        self.video = step.video

    async def handle_approval(
        self,
        approved: bool,
        feedback: str = None,
        regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Process step approval or rejection.

        Returns dict with step_id, status, message, and optional flags.
        """
        # Check for already approved
        if approved and self.step.status == WorkflowStatus.APPROVED:
            return self._response("Step already approved")

        # Handle retry for failed/in-progress steps
        if self.step.status in [WorkflowStatus.FAILED, WorkflowStatus.IN_PROGRESS] and regenerate:
            return self._reset_for_retry()

        self.step.user_approved = approved
        self.step.user_feedback = feedback

        if approved:
            return await self._process_approval()
        else:
            return self._process_rejection(regenerate)

    async def _process_approval(self) -> Dict[str, Any]:
        """Handle step approval and trigger next step."""
        self.step.status = WorkflowStatus.APPROVED
        self.step.completed_at = datetime.utcnow()

        handler = self._get_step_handler()
        if handler:
            # Handle both sync and async handlers
            if inspect.iscoroutinefunction(handler):
                result = await handler()
            else:
                result = handler()
            if result:
                return result

        self.db.commit()
        self.db.refresh(self.step)
        return self._response("Step approved")

    def _get_step_handler(self):
        """Get handler function for specific step type."""
        handlers = {
            StepType.VIDEO: self._handle_video_approval,
            StepType.ADAPTATION: self._handle_adaptation_approval,
            StepType.PUBLISHING: self._handle_publishing_approval,
            StepType.IMAGE: self._handle_image_approval,
        }
        return handlers.get(self.step.step_type, self._handle_default_approval)

    async def _handle_video_approval(self) -> Dict[str, Any] | None:
        """After VIDEO approval, handle audio generation."""
        project = self.video.project

        if project and project.audio_mode == "none":
            # Skip audio - go directly to ADAPTATION
            audio_step = WorkflowStep(
                video_id=self.video.id,
                step_type=StepType.AUDIO,
                status=WorkflowStatus.APPROVED,
                user_approved=True,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                content={"skipped": True, "reason": "audio_mode is none"}
            )
            self.db.add(audio_step)
            self.video.video_with_audio_url = self.video.video_url
            self.video.current_step = StepType.AUDIO
            self.db.commit()
            return None

        # Generate audio variants
        if not self.video.video_task_id:
            raise HTTPException(
                status_code=400,
                detail="Video task_id not found. Cannot generate audio."
            )

        audio_step = WorkflowStep(
            video_id=self.video.id,
            step_type=StepType.AUDIO,
            status=WorkflowStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        self.db.add(audio_step)
        self.db.commit()
        self.db.refresh(audio_step)

        audio_variants = await kling_service.add_audio_to_video(self.video.video_task_id)

        audio_step.content = {"audio_variants": audio_variants}
        audio_step.status = WorkflowStatus.AWAITING_APPROVAL
        audio_step.completed_at = datetime.utcnow()
        audio_step.generation_time_seconds = (datetime.utcnow() - audio_step.started_at).total_seconds()

        self.video.audio_variants = audio_variants
        self.video.current_step = StepType.AUDIO
        self.db.commit()
        return None

    def _handle_adaptation_approval(self) -> Dict[str, Any] | None:
        """After ADAPTATION approval, create publishing step."""
        publishing_step = WorkflowStep(
            video_id=self.video.id,
            step_type=StepType.PUBLISHING,
            status=WorkflowStatus.AWAITING_APPROVAL,
            started_at=datetime.utcnow(),
            content={"message": "Configure publishing settings and select platforms"}
        )
        self.db.add(publishing_step)
        self.video.current_step = StepType.PUBLISHING
        self.db.commit()
        return None

    def _handle_publishing_approval(self) -> Dict[str, Any] | None:
        """After PUBLISHING approval, complete workflow."""
        self.video.status = WorkflowStatus.COMPLETED
        self.db.commit()
        return None

    def _handle_image_approval(self) -> Dict[str, Any] | None:
        """Handle IMAGE approval - special case for AUTO mode."""
        if self.video.workflow_mode == WorkflowMode.AUTO:
            # Remix skips scenario, goes directly to video
            is_remix = self.video.project and self.video.project.project_type == "remix"
            self.video.current_step = StepType.VIDEO if is_remix else StepType.SCENARIO
            self.video.status = WorkflowStatus.IN_PROGRESS
            self.db.commit()
            self.db.refresh(self.step)
            return {
                "step_id": self.step.id,
                "status": self.step.status.value,
                "message": "Image approved. Call auto-generate-to-video to continue.",
                "continue_workflow": True
            }
        return self._handle_default_approval()

    def _handle_default_approval(self) -> Dict[str, Any] | None:
        """Default handler for steps with standard next-step transition."""
        # Use correct step map based on project type
        is_remix = self.video.project and self.video.project.project_type == "remix"
        step_map = REMIX_NEXT_STEP if is_remix else DISCOVER_NEXT_STEP

        if self.step.step_type not in step_map:
            # Final step for this workflow type
            return None

        next_step_type = step_map[self.step.step_type]

        if self.video.workflow_mode == WorkflowMode.MANUAL:
            next_step = WorkflowStep(
                video_id=self.video.id,
                step_type=next_step_type,
                status=WorkflowStatus.PENDING,
                created_at=datetime.utcnow()
            )
            self.db.add(next_step)

        self.video.current_step = next_step_type
        self.db.commit()
        return None

    def _process_rejection(self, regenerate: bool) -> Dict[str, Any]:
        """Handle step rejection."""
        if regenerate:
            self.step.status = WorkflowStatus.PENDING
            self.step.user_approved = False
            self.step.validation_attempts = 0
            message = "Step rejected. Ready for regeneration."
        else:
            self.step.status = WorkflowStatus.REJECTED
            message = "Step rejected"

        self.db.commit()
        self.db.refresh(self.step)
        return self._response(message)

    def _reset_for_retry(self) -> Dict[str, Any]:
        """Reset step for retry."""
        self.step.status = WorkflowStatus.PENDING
        self.step.user_approved = False
        self.step.validation_attempts = 0
        self.step.completed_at = None
        self.step.content = None
        self.db.commit()
        self.db.refresh(self.step)
        return self._response("Step reset. Ready for retry.")

    def _response(self, message: str) -> Dict[str, Any]:
        """Build standard response."""
        return {
            "step_id": self.step.id,
            "status": self.step.status.value,
            "message": message
        }
