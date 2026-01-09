"""
ImageStep - Generates image from prompt using media service.

Step 4 in the workflow pipeline (after Prompt generation).
"""
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.models.video import Video, StepType, WorkflowStatus
from app.models.workflow_step import WorkflowStep
from app.services.media.base import ImageServiceProtocol


class ImageStep:
    """
    Image generation step using injected service.

    Unlike text generation steps, this:
    - Does NOT use AI validation (visual content)
    - Does NOT use prompt building (uses image_prompt directly)
    - Uses dependency injection for the image service
    """

    step_type = StepType.IMAGE
    step_name = "image"

    def __init__(
        self,
        db: Session,
        video: Video,
        image_service: ImageServiceProtocol
    ):
        self.db = db
        self.video = video
        self.project = video.project
        self.image_service = image_service
        self.step: Optional[WorkflowStep] = None

    async def execute(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        negative_prompt: Optional[str] = None,
        style_suffix: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate image and save to video.

        Args:
            prompt: Image generation prompt
            aspect_ratio: Image aspect ratio
            negative_prompt: What should NOT appear
            style_suffix: Style modifiers

        Returns:
            Dict with step_id, content, status
        """
        self.step = self._get_or_create_step()

        try:
            # Generate image
            image_url = await self.image_service.generate(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                negative_prompt=negative_prompt,
                style_suffix=style_suffix,
                **kwargs
            )

            # Save to step and video
            self.step.content = {"image_url": image_url}
            self.video.image_url = image_url
            self.video.current_step = self.step_type
            self.step.status = WorkflowStatus.AWAITING_APPROVAL
            self.step.completed_at = datetime.utcnow()
            self.db.commit()

            return {
                "step_id": self.step.id,
                "content": {"image_url": image_url},
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
