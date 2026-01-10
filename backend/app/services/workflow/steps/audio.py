"""
AudioStep - Adds AI-generated audio to video using media service.

Step 7 in the workflow pipeline (after Video generation).
"""
from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session

from app.models.video import Video, StepType, WorkflowStatus
from app.models.workflow_step import WorkflowStep
from app.services.media.base import AudioServiceProtocol


class AudioStep:
    """
    Audio generation step using injected service.

    Unlike text generation steps, this:
    - Does NOT use AI validation (audio content)
    - Uses dependency injection for the audio service
    - Returns multiple variants for user selection
    - Can be skipped if project.audio_mode is "none"
    """

    step_type = StepType.AUDIO
    step_name = "audio"

    def __init__(
        self,
        db: Session,
        video: Video,
        audio_service: AudioServiceProtocol
    ):
        self.db = db
        self.video = video
        self.project = video.project
        self.audio_service = audio_service
        self.step: Optional[WorkflowStep] = None

    async def execute(
        self,
        video_task_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Add audio to video.

        Args:
            video_task_id: Task ID from video generation (uses video.video_task_id if not provided)

        Returns:
            Dict with step_id, content (audio_variants), status
            Or skipped status if audio_mode is "none"
        """
        # Check if audio should be skipped
        if self.project and self.project.audio_mode == "none":
            return self._skip_audio()

        # Get task_id
        task_id = video_task_id or self.video.video_task_id
        if not task_id:
            raise ValueError("Video task_id not found. Please regenerate video first.")

        self.step = self._get_or_create_step()

        try:
            # Generate audio variants
            audio_variants = await self.audio_service.add_to_video(
                video_task_id=task_id,
                **kwargs
            )

            # Save to step and video
            self.step.content = {"audio_variants": audio_variants}
            self.video.audio_variants = audio_variants
            self.video.current_step = self.step_type
            self.step.status = WorkflowStatus.AWAITING_APPROVAL
            self.step.completed_at = datetime.utcnow()
            self.db.commit()

            return {
                "step_id": self.step.id,
                "content": {"audio_variants": audio_variants},
                "status": "completed"
            }

        except Exception as e:
            self._handle_failure(e)
            raise

    def _skip_audio(self) -> Dict[str, Any]:
        """Skip audio generation when audio_mode is none."""
        self.step = self._get_or_create_step()

        self.step.content = {"skipped": True, "reason": "audio_mode is none"}
        self.step.status = WorkflowStatus.APPROVED
        self.step.user_approved = True
        self.step.completed_at = datetime.utcnow()

        # Use original video without audio
        self.video.video_with_audio_url = self.video.video_url
        self.video.current_step = self.step_type
        self.db.commit()

        return {
            "step_id": self.step.id,
            "content": {"skipped": True},
            "status": "skipped",
            "message": "Audio generation skipped (audio_mode: none)"
        }

    def _get_or_create_step(self) -> WorkflowStep:
        """Get existing PENDING step or create new one."""
        step = self.db.query(WorkflowStep).filter(
            WorkflowStep.video_id == self.video.id,
            WorkflowStep.step_type == self.step_type,
            WorkflowStep.status == WorkflowStatus.PENDING
        ).first()

        if step:
            step.status = WorkflowStatus.IN_PROGRESS
            step.started_at = datetime.utcnow()
        else:
            step = WorkflowStep(
                video_id=self.video.id,
                step_type=self.step_type,
                status=WorkflowStatus.IN_PROGRESS,
                started_at=datetime.utcnow()
            )
            self.db.add(step)

        self.db.commit()
        self.db.refresh(step)
        return step

    def _handle_failure(self, error: Exception):
        """Handle step failure."""
        if self.step:
            self.step.status = WorkflowStatus.FAILED
            self.step.completed_at = datetime.utcnow()
            self.db.commit()
