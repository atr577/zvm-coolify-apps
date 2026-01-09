"""
VideoStep - Generates video from image using media service.

Step 6 in the workflow pipeline (after Scenario generation).
"""
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.models.video import Video, StepType, WorkflowStatus
from app.models.workflow_step import WorkflowStep
from app.services.media.base import VideoServiceProtocol


class VideoStep:
    """
    Video generation step using injected service.

    Unlike text generation steps, this:
    - Does NOT use AI validation (visual content)
    - Uses dependency injection for the video service
    - Returns task_id needed for audio generation
    """

    step_type = StepType.VIDEO
    step_name = "video"

    def __init__(
        self,
        db: Session,
        video: Video,
        video_service: VideoServiceProtocol
    ):
        self.db = db
        self.video = video
        self.project = video.project
        self.video_service = video_service
        self.step: Optional[WorkflowStep] = None

    async def execute(
        self,
        image_url: str,
        prompt: str,
        duration: int = 5,
        camera_control: Optional[Dict[str, Any]] = None,
        negative_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate video from image.

        Args:
            image_url: Source image URL
            prompt: Motion/scenario prompt
            duration: Video duration in seconds
            camera_control: Camera movement settings
            negative_prompt: What should NOT appear

        Returns:
            Dict with step_id, content (video_url, task_id), status
        """
        self.step = self._get_or_create_step()

        try:
            # Generate video
            video_url, task_id = await self.video_service.generate(
                image_url=image_url,
                prompt=prompt,
                duration=duration,
                camera_control=camera_control,
                negative_prompt=negative_prompt,
                **kwargs
            )

            # Save to step and video
            self.step.content = {"video_url": video_url, "task_id": task_id}
            self.video.video_url = video_url
            self.video.video_task_id = task_id
            self.video.current_step = self.step_type
            self.step.status = WorkflowStatus.AWAITING_APPROVAL
            self.step.completed_at = datetime.utcnow()
            self.db.commit()

            return {
                "step_id": self.step.id,
                "content": {"video_url": video_url, "task_id": task_id},
                "status": "completed"
            }

        except Exception as e:
            self._handle_failure(e)
            raise

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
