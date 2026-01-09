"""
ImageStep - Generates image from prompt using media service.

Step 4 in the workflow pipeline (after Prompt generation).
"""
from datetime import datetime
from typing import Dict, Any, Optional, List

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
    - Supports feedback accumulation for regeneration
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
        self._feedback_history: List[str] = []

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

        # Apply feedback if available (modifies prompt)
        effective_prompt = self._apply_feedback_to_prompt(prompt)

        try:
            # Generate image
            image_url = await self.image_service.generate(
                prompt=effective_prompt,
                aspect_ratio=aspect_ratio,
                negative_prompt=negative_prompt,
                style_suffix=style_suffix,
                **kwargs
            )

            # Build content with meta
            content = {"image_url": image_url}
            meta = {
                "original_prompt": prompt,
                "effective_prompt": effective_prompt,
                "generated_at": datetime.utcnow().isoformat()
            }
            if self._feedback_history:
                meta["feedback_history"] = self._feedback_history
            content["_meta"] = meta

            # Save to step and video
            self.step.content = content
            self.video.image_url = image_url
            self.video.current_step = self.step_type
            self.step.status = WorkflowStatus.AWAITING_APPROVAL
            self.step.completed_at = datetime.utcnow()
            self.db.commit()

            return {
                "step_id": self.step.id,
                "content": content,
                "status": "completed",
                "feedback_applied": bool(self._feedback_history)
            }

        except Exception as e:
            self._handle_failure(e)
            raise

    def _apply_feedback_to_prompt(self, prompt: str) -> str:
        """Apply accumulated feedback to the image prompt."""
        feedback = self._get_feedback_with_history()
        if not feedback:
            return prompt

        # For image generation, append feedback as style/composition guidance
        if len(self._feedback_history) == 1:
            return f"{prompt}. User feedback: {feedback}"
        else:
            feedback_parts = [f"#{i+1}: {fb}" for i, fb in enumerate(self._feedback_history)]
            return f"{prompt}. User feedback history: {'; '.join(feedback_parts)}"

    def _get_feedback_with_history(self) -> Optional[str]:
        """Get feedback from current step and build history."""
        new_feedback = None

        # Check current step for feedback
        if self.step and self.step.user_feedback:
            new_feedback = self.step.user_feedback
            self.step.user_feedback = None  # Clear after reading

        if not new_feedback:
            return None

        # Get previous feedback history from video's image content
        previous_content = getattr(self.video, 'image_url', None)
        # Check step content for history
        last_image_step = self.db.query(WorkflowStep).filter(
            WorkflowStep.video_id == self.video.id,
            WorkflowStep.step_type == self.step_type,
            WorkflowStep.content.isnot(None)
        ).order_by(WorkflowStep.created_at.desc()).first()

        previous_history: List[str] = []
        if last_image_step and last_image_step.content:
            meta = last_image_step.content.get("_meta", {})
            previous_history = meta.get("feedback_history", [])

        self._feedback_history = previous_history + [new_feedback]
        return new_feedback

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
