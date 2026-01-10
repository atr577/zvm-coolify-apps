"""
WorkflowOrchestrator - Coordinates workflow execution.

Encapsulates the logic for running Discover and Remix workflows,
using step classes instead of direct service calls.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.models.video import Video, StepType, WorkflowStatus, WorkflowMode
from app.models.workflow_step import WorkflowStep
from app.models.project import Project
from app.core.config import settings

# Breakpoints for each project type (MANUAL mode stops after each)
DISCOVER_BREAKPOINTS = [
    StepType.STORY,
    StepType.DESCRIPTION,
    StepType.PROMPT,
    StepType.IMAGE,
    StepType.SCENARIO,
    StepType.VIDEO,
    StepType.AUDIO,
]

REMIX_BREAKPOINTS = [
    StepType.IMAGE,
    StepType.VIDEO,
    StepType.AUDIO,
]
from app.services.openai_service import openai_service
from app.services.kling_service import kling_service
from app.services.workflow.steps.image import ImageStep
from app.services.workflow.steps.video import VideoStep
from app.services.workflow.steps.audio import AudioStep
from app.services.media.base import ImageServiceProtocol, VideoServiceProtocol, AudioServiceProtocol
from app.core.deps import get_image_service, get_video_service, get_audio_service


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    video_id: int
    steps_completed: int
    message: str
    mode: str
    total_time_seconds: float
    paused_for_approval: bool = False
    next_action: Optional[str] = None
    audio_variants: Optional[List[str]] = None
    audio_skipped: bool = False


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


def build_camera_control(camera_movement: Optional[Dict]) -> Optional[Dict]:
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


class WorkflowOrchestrator:
    """
    Orchestrates workflow execution for video generation.

    Supports two modes:
    - Discover: Full workflow (Story → Description → Prompt → Image → Scenario → Video → Audio)
    - Remix: Simplified workflow (Template → Image → Video → Audio)
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
        self.steps_completed = 0
        self.is_remix = self.project.project_type == "remix"

    def _should_pause(self, step_type: StepType) -> bool:
        """Check if workflow should pause at this step."""
        if not settings.USE_NEW_BREAKPOINTS:
            # Old behavior: only pause at image if require_image_approval
            return (step_type == StepType.IMAGE and
                    getattr(self.project, 'require_image_approval', False))

        # New behavior: breakpoints system
        if self.video.workflow_mode == WorkflowMode.AUTO:
            return False  # AUTO never pauses

        breakpoints = REMIX_BREAKPOINTS if self.is_remix else DISCOVER_BREAKPOINTS
        return step_type in breakpoints

    def _pause_result(self, message: str, current_step: StepType) -> WorkflowResult:
        """Create a pause result for MANUAL mode."""
        self.video.status = WorkflowStatus.AWAITING_APPROVAL
        self.video.current_step = current_step
        self.db.commit()

        return WorkflowResult(
            video_id=self.video.id,
            steps_completed=self.steps_completed,
            message=message,
            mode="remix" if self.is_remix else "discover",
            total_time_seconds=self._elapsed_time(),
            paused_for_approval=True,
            next_action=f"approve_{current_step.value.lower()}"
        )

    async def run(self) -> WorkflowResult:
        """
        Run appropriate workflow based on project type.

        Handles:
        - Resume after image approval
        - Remix mode
        - Discover mode
        """
        resume_from_image = (
            self.video.image_url and
            self.video.current_step in [StepType.SCENARIO, StepType.VIDEO]
        )

        if resume_from_image:
            return await self.resume_after_image_approval(self.is_remix)
        elif self.is_remix:
            return await self.run_remix_workflow()
        else:
            return await self.run_discover_workflow()

    async def run_discover_workflow(self) -> WorkflowResult:
        """
        Run full Discover workflow:
        Story → Description → Prompt → Image → Scenario → Video → Audio

        In MANUAL mode, pauses after each step for approval.
        In AUTO mode, runs all steps without pausing.
        """
        # Step 1: Story
        await self._generate_story()
        self.steps_completed += 1
        if self._should_pause(StepType.STORY):
            return self._pause_result("Story generated", StepType.STORY)

        # Step 2: Description
        await self._generate_description()
        self.steps_completed += 1
        if self._should_pause(StepType.DESCRIPTION):
            return self._pause_result("Description generated", StepType.DESCRIPTION)

        # Step 3: Prompt
        await self._generate_prompt()
        self.steps_completed += 1
        if self._should_pause(StepType.PROMPT):
            return self._pause_result("Prompt generated", StepType.PROMPT)

        # Step 4: Image
        await self._generate_image()
        self.steps_completed += 1
        if self._should_pause(StepType.IMAGE):
            return self._pause_result("Image generated", StepType.IMAGE)

        # Step 5: Scenario
        await self._generate_scenario()
        self.steps_completed += 1
        if self._should_pause(StepType.SCENARIO):
            return self._pause_result("Scenario generated", StepType.SCENARIO)

        # Step 6: Video
        await self._generate_video()
        self.steps_completed += 1
        if self._should_pause(StepType.VIDEO):
            return self._pause_result("Video generated", StepType.VIDEO)

        # Step 7: Audio
        audio_result = await self._generate_audio()
        self.steps_completed += 1
        if self._should_pause(StepType.AUDIO):
            return self._pause_result("Audio generated", StepType.AUDIO)

        # Complete
        return self._complete_workflow(audio_result)

    async def run_remix_workflow(self) -> WorkflowResult:
        """
        Run Remix workflow:
        Template → Image → Video → Audio

        In MANUAL mode, pauses after Image, Video, Audio.
        In AUTO mode, runs all steps without pausing.
        """
        # Fill template
        filled_prompt = self._fill_template()
        self.video.story_data = {"filled_template": filled_prompt}
        self.video.image_prompt = filled_prompt
        self.video.current_step = StepType.IMAGE  # Remix starts at IMAGE
        self.video.status = WorkflowStatus.IN_PROGRESS
        self.db.commit()

        # Step 1: Image
        await self._generate_image(prompt=filled_prompt)
        self.steps_completed += 1
        if self._should_pause(StepType.IMAGE):
            return self._pause_result("Image generated", StepType.IMAGE)

        # Step 2: Video
        await self._generate_video(motion_prompt="Subtle natural movement, cinematic atmosphere")
        self.steps_completed += 1
        if self._should_pause(StepType.VIDEO):
            return self._pause_result("Video generated", StepType.VIDEO)

        # Step 3: Audio
        audio_result = await self._generate_audio()
        self.steps_completed += 1
        if self._should_pause(StepType.AUDIO):
            return self._pause_result("Audio generated", StepType.AUDIO)

        # Complete
        return self._complete_workflow(audio_result)

    def _complete_workflow(self, audio_result: Dict[str, Any]) -> WorkflowResult:
        """Create completion result based on audio status."""
        if audio_result.get("status") == "skipped":
            return WorkflowResult(
                video_id=self.video.id,
                steps_completed=self.steps_completed,
                message="Video completed. Audio skipped. Generate meta manually.",
                mode="remix" if self.is_remix else "discover",
                total_time_seconds=self._elapsed_time(),
                audio_skipped=True,
                next_action="generate_meta"
            )
        else:
            return WorkflowResult(
                video_id=self.video.id,
                steps_completed=self.steps_completed,
                message="Video generated. Select audio variant.",
                mode="remix" if self.is_remix else "discover",
                total_time_seconds=self._elapsed_time(),
                audio_variants=audio_result.get("content", {}).get("audio_variants", []),
                next_action="select_audio_variant"
            )

    async def resume_workflow(self) -> WorkflowResult:
        """
        Resume workflow from current step after approval.

        Used when workflow is paused at a breakpoint in MANUAL mode.
        """
        current_step = self.video.current_step

        if not current_step:
            raise ValueError("No current step to resume from")

        if self.video.status != WorkflowStatus.AWAITING_APPROVAL:
            raise ValueError("Workflow not awaiting approval")

        # Mark as in progress
        self.video.status = WorkflowStatus.IN_PROGRESS
        self.db.commit()

        # Define step handlers
        discover_steps = [
            (StepType.STORY, self._generate_story),
            (StepType.DESCRIPTION, self._generate_description),
            (StepType.PROMPT, self._generate_prompt),
            (StepType.IMAGE, self._generate_image),
            (StepType.SCENARIO, self._generate_scenario),
            (StepType.VIDEO, self._generate_video),
            (StepType.AUDIO, self._generate_audio),
        ]

        remix_steps = [
            (StepType.IMAGE, lambda: self._generate_image(prompt=self.video.image_prompt)),
            (StepType.VIDEO, lambda: self._generate_video(motion_prompt="Subtle natural movement, cinematic atmosphere")),
            (StepType.AUDIO, self._generate_audio),
        ]

        steps = remix_steps if self.is_remix else discover_steps

        # Find current step index
        step_types = [s[0] for s in steps]
        try:
            current_index = step_types.index(current_step)
        except ValueError:
            raise ValueError(f"Current step {current_step} not in workflow")

        # Run from next step
        audio_result = None
        for i, (step_type, handler) in enumerate(steps):
            if i <= current_index:
                continue  # Skip already completed steps

            result = await handler()
            self.steps_completed += 1

            if step_type == StepType.AUDIO:
                audio_result = result

            if self._should_pause(step_type):
                return self._pause_result(f"{step_type.value.capitalize()} generated", step_type)

        # Complete workflow
        if audio_result:
            return self._complete_workflow(audio_result)
        else:
            # No audio step ran (shouldn't happen normally)
            return WorkflowResult(
                video_id=self.video.id,
                steps_completed=self.steps_completed,
                message="Workflow resumed and completed",
                mode="remix" if self.is_remix else "discover",
                total_time_seconds=self._elapsed_time()
            )

    # Legacy method for old require_image_approval flow
    async def run_remix_workflow_legacy(self) -> WorkflowResult:
        """
        Legacy Remix workflow (kept for backwards compatibility).
        """
        filled_prompt = self._fill_template()
        self.video.story_data = {"filled_template": filled_prompt}
        self.video.image_prompt = filled_prompt
        self.video.current_step = StepType.IMAGE
        self.video.status = WorkflowStatus.IN_PROGRESS
        self.db.commit()

        await self._generate_image(prompt=filled_prompt)
        self.steps_completed += 1

        if getattr(self.project, 'require_image_approval', False):
            return WorkflowResult(
                video_id=self.video.id,
                steps_completed=self.steps_completed,
                message="Image generated. Approve to continue to video.",
                mode="remix",
                total_time_seconds=self._elapsed_time(),
                paused_for_approval=True,
                next_action="approve_image"
            )

        # Continue with remaining steps
        return await self._complete_video_generation(mode="remix")

    async def resume_after_image_approval(self, is_remix: bool) -> WorkflowResult:
        """
        Resume workflow after image has been approved.

        For Remix: continue with Video → Audio
        For Discover: continue with Scenario → Video → Audio
        """
        if is_remix:
            # Remix: Video → Audio
            return await self._complete_video_generation(
                mode="remix",
                skip_scenario=True,
                is_resume=True
            )
        else:
            # Discover: Scenario → Video → Audio
            return await self._complete_video_generation(
                mode="discover",
                is_resume=True
            )

    async def _generate_story(self) -> Dict[str, Any]:
        """Generate story from template."""
        step = self._create_step(StepType.STORY)

        story_data = await openai_service.generate_story_from_template(
            story_template=self.project.story_template,
            content_variables=self.video.content_variables or {},
            duration=self.project.duration,
            platforms=self.project.platforms,
            system_prompt=self.project.system_prompts.get("story") if self.project.system_prompts else None
        )

        self._complete_step(step, story_data)
        self.video.story_data = story_data
        self.video.current_step = StepType.DESCRIPTION
        self.db.commit()

        return story_data

    async def _generate_description(self) -> Dict[str, Any]:
        """Generate scene description from story."""
        step = self._create_step(StepType.DESCRIPTION)

        description_data = await openai_service.generate_description(
            self.video.story_data
        )

        self._complete_step(step, description_data)
        self.video.description_data = description_data
        self.video.current_step = StepType.PROMPT
        self.db.commit()

        return description_data

    async def _generate_prompt(self) -> Dict[str, Any]:
        """Generate image prompt from description."""
        step = self._create_step(StepType.PROMPT)

        prompt_data = await openai_service.generate_image_prompt(
            self.video.description_data
        )

        self._complete_step(step, prompt_data)
        self.video.prompt_data = prompt_data
        self.video.image_prompt = prompt_data.get("main_prompt", "")
        self.video.current_step = StepType.IMAGE
        self.db.commit()

        return prompt_data

    async def _generate_image(self, prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate image using ImageStep."""
        prompt_data = self.video.prompt_data or {}
        image_prompt = prompt or prompt_data.get("main_prompt", self.video.image_prompt)
        negative_prompt = prompt_data.get("negative_prompt")
        style_suffix = prompt_data.get("style_suffix")

        image_step = ImageStep(self.db, self.video, self.services.image)
        result = await image_step.execute(
            prompt=image_prompt,
            aspect_ratio=self.project.aspect_ratio,
            negative_prompt=negative_prompt,
            style_suffix=style_suffix
        )

        # Update step status based on approval requirement
        if self.project.require_image_approval:
            self.video.current_step = StepType.IMAGE
            self.video.status = WorkflowStatus.AWAITING_APPROVAL
        else:
            # Mark step as approved
            step = self.db.query(WorkflowStep).filter(
                WorkflowStep.id == result["step_id"]
            ).first()
            if step:
                step.status = WorkflowStatus.APPROVED
            self.video.current_step = StepType.SCENARIO

        self.db.commit()
        return result

    async def _generate_scenario(self) -> Dict[str, Any]:
        """Generate scenario from image and description."""
        step = self._create_step(StepType.SCENARIO)

        scenario_data = await openai_service.generate_scenario(
            image_url=self.video.image_url,
            description_data=self.video.description_data,
            story_data=self.video.story_data,
            duration=self.project.duration
        )

        self._complete_step(step, scenario_data)
        self.video.scenario_data = scenario_data
        self.video.current_step = StepType.VIDEO
        self.db.commit()

        return scenario_data

    async def _generate_video(self, motion_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate video using VideoStep."""
        scenario_data = self.video.scenario_data or {}
        prompt = motion_prompt or scenario_data.get("motion_prompt", "") or scenario_data.get("scene_direction", "Subtle natural movement")
        camera_control = build_camera_control(scenario_data.get("camera_movement"))

        video_step = VideoStep(self.db, self.video, self.services.video)
        result = await video_step.execute(
            image_url=self.video.image_url,
            prompt=prompt,
            duration=self.project.duration,
            camera_control=camera_control
        )

        # Mark as approved (auto-generated)
        step = self.db.query(WorkflowStep).filter(
            WorkflowStep.id == result["step_id"]
        ).first()
        if step:
            step.status = WorkflowStatus.APPROVED

        self.video.current_step = StepType.AUDIO
        self.db.commit()

        return result

    async def _generate_audio(self) -> Dict[str, Any]:
        """Generate audio using AudioStep."""
        audio_step = AudioStep(self.db, self.video, self.services.audio)
        result = await audio_step.execute()

        if result.get("status") == "skipped":
            self.video.status = WorkflowStatus.COMPLETED
        else:
            self.video.status = WorkflowStatus.AWAITING_APPROVAL

        self.db.commit()
        return result

    async def _complete_video_generation(
        self,
        mode: str,
        skip_scenario: bool = False,
        is_resume: bool = False
    ) -> WorkflowResult:
        """
        Complete video generation after image step.

        Handles Scenario → Video → Audio pipeline.
        """
        if not skip_scenario and mode == "discover":
            await self._generate_scenario()
            self.steps_completed += 1

        # Generate video
        motion_prompt = "Subtle natural movement, cinematic atmosphere" if mode == "remix" else None
        await self._generate_video(motion_prompt=motion_prompt)
        self.steps_completed += 1

        # Generate audio
        audio_result = await self._generate_audio()
        self.steps_completed += 1

        # Build result
        if audio_result.get("status") == "skipped":
            # Meta will be generated manually via /generate-meta endpoint
            return WorkflowResult(
                video_id=self.video.id,
                steps_completed=self.steps_completed,
                message=f"{'Resumed: ' if is_resume else ''}{mode.capitalize()} video completed. Audio skipped. Generate meta manually.",
                mode=mode,
                total_time_seconds=self._elapsed_time(),
                audio_skipped=True,
                next_action="generate_meta"
            )
        else:
            return WorkflowResult(
                video_id=self.video.id,
                steps_completed=self.steps_completed,
                message=f"{'Resumed: ' if is_resume else ''}{mode.capitalize()} video generated. Select audio variant.",
                mode=mode,
                total_time_seconds=self._elapsed_time(),
                audio_variants=audio_result.get("content", {}).get("audio_variants", []),
                next_action="select_audio_variant"
            )

    def _fill_template(self) -> str:
        """Fill story template with content variables."""
        filled_prompt = self.project.story_template
        content_variables = self.video.content_variables or {}

        for key, value in content_variables.items():
            if isinstance(value, dict):
                value_str = ", ".join(f"{k}: {v}" for k, v in value.items())
            else:
                value_str = str(value)
            filled_prompt = filled_prompt.replace(f"{{{key}}}", value_str)

        return filled_prompt

    def _create_step(self, step_type: StepType) -> WorkflowStep:
        """Create a new workflow step."""
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

    def _complete_step(self, step: WorkflowStep, content: Dict[str, Any]):
        """Mark step as completed with content."""
        step.content = content
        step.status = WorkflowStatus.APPROVED
        step.completed_at = datetime.utcnow()
        step.generation_time_seconds = (datetime.utcnow() - step.started_at).total_seconds()
        self.db.commit()

    def _elapsed_time(self) -> float:
        """Get elapsed time since workflow start."""
        return (datetime.utcnow() - self.start_time).total_seconds()
