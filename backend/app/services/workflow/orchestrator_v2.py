"""
WorkflowOrchestratorV2 - New orchestrator per CONTRACTS.md

Key differences from v1:
- Creates full hierarchy: WorkflowStep → StepAttempt → Variant
- AUTO mode: 1 variant, auto-select, auto-approve
- MANUAL mode: N variants, pause for user selection
- Proper state transitions per spec
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session

from app.models.video import Video, StepType, WorkflowStatus, WorkflowMode
from app.models.workflow_step import WorkflowStep
from app.models.step_attempt import StepAttempt, Variant, AttemptStatus
from app.models.project import Project
from app.core.config import settings

from app.services.openai_service import openai_service
from app.services.workflow.steps.image import ImageStep
from app.services.workflow.steps.video import VideoStep
from app.services.workflow.steps.audio import AudioStep
from app.services.media.base import ImageServiceProtocol, VideoServiceProtocol, AudioServiceProtocol
from app.core.deps import get_image_service, get_video_service, get_audio_service

logger = logging.getLogger(__name__)

# Variants config per CONTRACTS.md
DEFAULT_VARIANTS_CONFIG = {
    StepType.STORY: 1,
    StepType.DESCRIPTION: 1,
    StepType.PROMPT: 1,
    StepType.IMAGE: 3,      # MANUAL: 3 variants
    StepType.SCENARIO: 1,
    StepType.VIDEO: 1,
    StepType.AUDIO: 3       # MANUAL: 3 variants
}


@dataclass
class OrchestratorResult:
    """Result from orchestrator run."""
    video_id: int
    status: str
    current_step: str
    message: str


class ServiceContainer:
    """Container for media services with lazy initialization."""

    def __init__(
        self,
        image_service: Optional[ImageServiceProtocol] = None,
        video_service: Optional[VideoServiceProtocol] = None,
        audio_service: Optional[AudioServiceProtocol] = None
    ):
        self._image_service = image_service
        self._video_service = video_service
        self._audio_service = audio_service

    @property
    def image(self) -> ImageServiceProtocol:
        if self._image_service is None:
            self._image_service = get_image_service()
        return self._image_service

    @property
    def video(self) -> VideoServiceProtocol:
        if self._video_service is None:
            self._video_service = get_video_service()
        return self._video_service

    @property
    def audio(self) -> AudioServiceProtocol:
        if self._audio_service is None:
            self._audio_service = get_audio_service()
        return self._audio_service


class WorkflowOrchestratorV2:
    """
    Orchestrates workflow execution with full variant support.

    Supports:
    - Discover: Full workflow (Story → Description → Prompt → Image → Scenario → Video → Audio)
    - Remix: Simplified workflow (PREPARE → Image → Video → Audio)

    Creates WorkflowStep → StepAttempt → Variant hierarchy for each step.
    """

    def __init__(
        self,
        db: Session,
        video: Video,
        services: Optional[ServiceContainer] = None
    ):
        self.db = db
        self.video = video
        self.project = video.project
        self.services = services or ServiceContainer()
        self.start_time = datetime.utcnow()
        self.is_remix = self.project.project_type == "remix"
        self.is_auto = video.workflow_mode == WorkflowMode.AUTO

    def _get_variant_count(self, step_type: StepType) -> int:
        """Get number of variants to generate for a step."""
        if self.is_auto:
            return 1  # AUTO always generates 1 variant
        return DEFAULT_VARIANTS_CONFIG.get(step_type, 1)

    async def run(self) -> OrchestratorResult:
        """Run workflow based on project type and current state."""
        # Set status to IN_PROGRESS
        self.video.status = WorkflowStatus.IN_PROGRESS
        self.db.commit()

        if self.is_remix:
            return await self._run_remix_workflow()
        else:
            return await self._run_discover_workflow()

    async def _run_discover_workflow(self) -> OrchestratorResult:
        """
        Run full Discover workflow: 7 steps.

        AUTO mode: runs all steps without pausing
        MANUAL mode: pauses after each step for approval
        """
        steps = [
            (StepType.STORY, self._generate_story),
            (StepType.DESCRIPTION, self._generate_description),
            (StepType.PROMPT, self._generate_prompt),
            (StepType.IMAGE, self._generate_image),
            (StepType.SCENARIO, self._generate_scenario),
            (StepType.VIDEO, self._generate_video),
        ]

        # Add audio step only if audio_mode is not 'none'
        if self.project.audio_mode != 'none':
            steps.append((StepType.AUDIO, self._generate_audio))

        # Determine starting point
        current_step = self.video.current_step
        start_index = 0

        if current_step:
            step_types = [s[0] for s in steps]
            if current_step in step_types:
                # Resume from next step after current
                start_index = step_types.index(current_step) + 1

        # Run steps
        for i, (step_type, generator) in enumerate(steps):
            if i < start_index:
                continue

            self.video.current_step = step_type
            self.db.commit()
            self.db.refresh(self.video)

            # Generate step content
            logger.info(f"Generating step {step_type}, video.story_data={self.video.story_data is not None}")
            await generator()

            # In AUTO mode, auto-approve and continue
            # In MANUAL mode, pause for approval
            if not self.is_auto:
                return self._pause_result(step_type)

        # All steps completed (AUTO mode)
        self.video.status = WorkflowStatus.COMPLETED
        self.db.commit()

        return OrchestratorResult(
            video_id=self.video.id,
            status="completed",
            current_step="audio",
            message="Workflow completed"
        )

    async def _run_remix_workflow(self) -> OrchestratorResult:
        """
        Run Remix workflow: PREPARE → IMAGE → VIDEO → AUDIO
        """
        from app.services.workflow.remix_prepare import prepare_remix

        # PREPARE phase (sync, not a WorkflowStep)
        prepare_remix(self.project, self.video)
        self.db.commit()

        steps = [
            (StepType.IMAGE, self._generate_image),
            (StepType.VIDEO, self._generate_video),
        ]

        # Add audio step only if audio_mode is not 'none'
        if self.project.audio_mode != 'none':
            steps.append((StepType.AUDIO, self._generate_audio))

        # Determine starting point
        current_step = self.video.current_step
        start_index = 0

        if current_step:
            step_types = [s[0] for s in steps]
            if current_step in step_types:
                start_index = step_types.index(current_step) + 1

        # Run steps
        for i, (step_type, generator) in enumerate(steps):
            if i < start_index:
                continue

            self.video.current_step = step_type
            self.db.commit()

            await generator()

            if not self.is_auto:
                return self._pause_result(step_type)

        # All steps completed
        self.video.status = WorkflowStatus.COMPLETED
        self.db.commit()

        return OrchestratorResult(
            video_id=self.video.id,
            status="completed",
            current_step="audio",
            message="Remix workflow completed"
        )

    def _pause_result(self, step_type: StepType) -> OrchestratorResult:
        """Create pause result for MANUAL mode."""
        self.video.status = WorkflowStatus.AWAITING_APPROVAL
        self.db.commit()

        return OrchestratorResult(
            video_id=self.video.id,
            status="awaiting_approval",
            current_step=step_type.value.lower(),
            message=f"{step_type.value.capitalize()} generated, awaiting approval"
        )

    # =========================================================================
    # Step Generators
    # =========================================================================

    async def _generate_story(self):
        """Generate story step with variant hierarchy."""
        step = self._create_step(StepType.STORY)
        attempt = self._create_attempt(step)

        try:
            # Generate story content
            story_data = await openai_service.generate_story_from_template(
                story_template=self.project.story_template or "",
                content_variables=self.video.content_variables or {},
                duration=self.project.duration,
                platforms=self.project.platforms,
                system_prompt=self.project.system_prompts.get("story") if self.project.system_prompts else None
            )

            # Create variant
            variant = self._create_variant(attempt, 1, story_data)

            # AUTO: auto-select and auto-approve
            if self.is_auto:
                self._auto_approve(step, variant, "story_data", story_data)
            else:
                self._mark_awaiting_approval(step, attempt, variant)

        except Exception as e:
            self._mark_failed(step, attempt, str(e))
            raise

    async def _generate_description(self):
        """Generate description step."""
        step = self._create_step(StepType.DESCRIPTION)
        attempt = self._create_attempt(step)

        try:
            description_data = await openai_service.generate_description(
                self.video.story_data
            )

            variant = self._create_variant(attempt, 1, description_data)

            if self.is_auto:
                self._auto_approve(step, variant, "description_data", description_data)
            else:
                self._mark_awaiting_approval(step, attempt, variant)

        except Exception as e:
            self._mark_failed(step, attempt, str(e))
            raise

    async def _generate_prompt(self):
        """Generate prompt step."""
        step = self._create_step(StepType.PROMPT)
        attempt = self._create_attempt(step)

        try:
            prompt_data = await openai_service.generate_image_prompt(
                self.video.description_data
            )

            variant = self._create_variant(attempt, 1, prompt_data)

            if self.is_auto:
                self._auto_approve(step, variant, "prompt_data", prompt_data)
                # Also set image_prompt for convenience
                self.video.image_prompt = prompt_data.get("main_prompt", "")
            else:
                self._mark_awaiting_approval(step, attempt, variant)

        except Exception as e:
            self._mark_failed(step, attempt, str(e))
            raise

    async def _generate_image(self):
        """Generate image step with potential multiple variants."""
        step = self._create_step(StepType.IMAGE)
        attempt = self._create_attempt(step)

        variant_count = self._get_variant_count(StepType.IMAGE)

        try:
            prompt_data = self.video.prompt_data or {}
            image_prompt = prompt_data.get("main_prompt") or self.video.image_prompt
            negative_prompt = prompt_data.get("negative_prompt")
            style_suffix = prompt_data.get("style_suffix")

            # Generate N variants
            for i in range(variant_count):
                image_step = ImageStep(self.db, self.video, self.services.image)
                result = await image_step.execute(
                    prompt=image_prompt,
                    aspect_ratio=self.project.aspect_ratio,
                    negative_prompt=negative_prompt,
                    style_suffix=style_suffix
                )

                content = {
                    "url": self.video.image_url,
                    "prompt": image_prompt
                }
                self._create_variant(attempt, i + 1, content)

            # Get first variant for auto mode
            first_variant = self.db.query(Variant).filter(
                Variant.attempt_id == attempt.id,
                Variant.variant_number == 1
            ).first()

            if self.is_auto and first_variant:
                self._auto_approve(step, first_variant, "image_url", first_variant.content.get("url"))
            else:
                self._mark_awaiting_approval(step, attempt, first_variant)

        except Exception as e:
            self._mark_failed(step, attempt, str(e))
            raise

    async def _generate_scenario(self):
        """Generate scenario step."""
        step = self._create_step(StepType.SCENARIO)
        attempt = self._create_attempt(step)

        try:
            scenario_data = await openai_service.generate_scenario(
                image_url=self.video.image_url,
                description_data=self.video.description_data,
                story_data=self.video.story_data,
                duration=self.project.duration
            )

            variant = self._create_variant(attempt, 1, scenario_data)

            if self.is_auto:
                self._auto_approve(step, variant, "scenario_data", scenario_data)
            else:
                self._mark_awaiting_approval(step, attempt, variant)

        except Exception as e:
            self._mark_failed(step, attempt, str(e))
            raise

    async def _generate_video(self):
        """Generate video step."""
        step = self._create_step(StepType.VIDEO)
        attempt = self._create_attempt(step)

        try:
            scenario_data = self.video.scenario_data or {}
            motion_prompt = (
                scenario_data.get("motion_prompt") or
                scenario_data.get("scene_direction") or
                "Subtle natural movement, cinematic atmosphere"
            )

            camera_control = self._build_camera_control(scenario_data.get("camera_movement"))

            video_step = VideoStep(self.db, self.video, self.services.video)
            result = await video_step.execute(
                image_url=self.video.image_url,
                prompt=motion_prompt,
                duration=self.project.duration,
                camera_control=camera_control
            )

            content = {
                "url": self.video.video_url,
                "motion_prompt": motion_prompt
            }
            variant = self._create_variant(attempt, 1, content)

            if self.is_auto:
                self._auto_approve(step, variant, "video_url", self.video.video_url)
            else:
                self._mark_awaiting_approval(step, attempt, variant)

        except Exception as e:
            self._mark_failed(step, attempt, str(e))
            raise

    async def _generate_audio(self):
        """Generate audio step with multiple variants."""
        step = self._create_step(StepType.AUDIO)
        attempt = self._create_attempt(step)

        variant_count = self._get_variant_count(StepType.AUDIO)

        try:
            audio_step = AudioStep(self.db, self.video, self.services.audio)
            result = await audio_step.execute()

            if result.get("status") == "skipped":
                # Audio skipped - mark as approved with no content
                variant = self._create_variant(attempt, 1, {"status": "skipped"})
                self._auto_approve(step, variant, None, None)
                return

            # Audio variants are in video.audio_variants
            audio_variants = self.video.audio_variants or []

            for i, audio_url in enumerate(audio_variants[:variant_count]):
                content = {"url": audio_url}
                self._create_variant(attempt, i + 1, content)

            first_variant = self.db.query(Variant).filter(
                Variant.attempt_id == attempt.id,
                Variant.variant_number == 1
            ).first()

            if self.is_auto and first_variant:
                # Auto-select first audio variant
                audio_url = first_variant.content.get("url")
                self._auto_approve(step, first_variant, "video_with_audio_url", audio_url)
            else:
                self._mark_awaiting_approval(step, attempt, first_variant)

        except Exception as e:
            self._mark_failed(step, attempt, str(e))
            raise

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _create_step(self, step_type: StepType) -> WorkflowStep:
        """Create or get existing WorkflowStep."""
        # Check if step already exists
        existing = self.db.query(WorkflowStep).filter(
            WorkflowStep.video_id == self.video.id,
            WorkflowStep.step_type == step_type
        ).first()

        if existing:
            existing.status = WorkflowStatus.IN_PROGRESS
            existing.started_at = datetime.utcnow()
            self.db.commit()
            return existing

        step = WorkflowStep(
            video_id=self.video.id,
            step_type=step_type,
            status=WorkflowStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def _create_attempt(self, step: WorkflowStep) -> StepAttempt:
        """Create new StepAttempt."""
        # Get next attempt number
        max_attempt = self.db.query(StepAttempt).filter(
            StepAttempt.step_id == step.id
        ).order_by(StepAttempt.attempt_number.desc()).first()

        attempt_number = (max_attempt.attempt_number + 1) if max_attempt else 1

        attempt = StepAttempt(
            step_id=step.id,
            attempt_number=attempt_number,
            status=AttemptStatus.PENDING,
            started_at=datetime.utcnow()
        )
        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)
        return attempt

    def _create_variant(self, attempt: StepAttempt, variant_number: int, content: Dict[str, Any]) -> Variant:
        """Create new Variant."""
        variant = Variant(
            attempt_id=attempt.id,
            variant_number=variant_number,
            content=content,
            is_selected=False
        )
        self.db.add(variant)
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def _auto_approve(self, step: WorkflowStep, variant: Variant, video_field: Optional[str], value: Any):
        """Auto-select and auto-approve for AUTO mode."""
        variant.is_selected = True
        step.selected_variant_id = variant.id
        step.status = WorkflowStatus.APPROVED
        step.completed_at = datetime.utcnow()

        # Update attempt status
        attempt = self.db.query(StepAttempt).filter(StepAttempt.id == variant.attempt_id).first()
        if attempt:
            attempt.status = AttemptStatus.SUCCESS
            attempt.completed_at = datetime.utcnow()

        # Copy to video field
        if video_field and value is not None:
            setattr(self.video, video_field, value)

        self.db.commit()
        self.db.refresh(self.video)  # Refresh to ensure video object is up-to-date

    def _mark_awaiting_approval(self, step: WorkflowStep, attempt: StepAttempt, variant: Optional[Variant]):
        """Mark step as awaiting approval for MANUAL mode."""
        attempt.status = AttemptStatus.SUCCESS
        attempt.completed_at = datetime.utcnow()

        # Pre-select first variant
        if variant:
            variant.is_selected = True
            step.selected_variant_id = variant.id

        step.status = WorkflowStatus.AWAITING_APPROVAL
        step.completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(self.video)

    def _mark_failed(self, step: WorkflowStep, attempt: StepAttempt, error: str):
        """Mark step and attempt as failed."""
        attempt.status = AttemptStatus.FAILED
        attempt.completed_at = datetime.utcnow()
        attempt.error_message = error

        step.status = WorkflowStatus.FAILED
        step.completed_at = datetime.utcnow()

        self.video.status = WorkflowStatus.FAILED
        self.db.commit()
        self.db.refresh(self.video)

    def _build_camera_control(self, camera_movement: Optional[Dict]) -> Optional[Dict]:
        """Build camera control config from scenario data."""
        if not camera_movement:
            return None

        movement_type = camera_movement.get("type", "").lower()

        type_mapping = {
            "static": "static",
            "dolly_in": "move_forward",
            "dolly_out": "move_backward",
            "pan_left": "move_left",
            "pan_right": "move_right",
            "tilt_up": "move_up",
            "tilt_down": "move_down",
            "zoom_in": "zoom_in",
            "zoom_out": "zoom_out"
        }

        kling_type = type_mapping.get(movement_type, "static")

        return {
            "type": "simple",
            "config": {"type": kling_type}
        }
