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

from app.models.video import Video, StepType, WorkflowStatus
from app.models.workflow_step import WorkflowStep
from app.models.project import Project
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

    async def run(self) -> WorkflowResult:
        """
        Run appropriate workflow based on project type.

        Handles:
        - Resume after image approval
        - Remix mode
        - Discover mode
        """
        is_remix = self.project.project_type == "remix"
        resume_from_image = (
            self.video.image_url and
            self.video.current_step in [StepType.SCENARIO, StepType.VIDEO]
        )

        if resume_from_image:
            return await self.resume_after_image_approval(is_remix)
        elif is_remix:
            return await self.run_remix_workflow()
        else:
            return await self.run_discover_workflow()

    async def run_discover_workflow(self) -> WorkflowResult:
        """
        Run full Discover workflow:
        Story → Description → Prompt → Image → Scenario → Video → Audio
        """
        # Step 1: Story
        await self._generate_story()
        self.steps_completed += 1

        # Step 2: Description
        await self._generate_description()
        self.steps_completed += 1

        # Step 3: Prompt
        await self._generate_prompt()
        self.steps_completed += 1

        # Step 4: Image
        image_result = await self._generate_image()
        self.steps_completed += 1

        # Check for image approval pause
        if self.project.require_image_approval:
            return WorkflowResult(
                video_id=self.video.id,
                steps_completed=self.steps_completed,
                message="Image generated. Approve to continue.",
                mode="discover",
                total_time_seconds=self._elapsed_time(),
                paused_for_approval=True,
                next_action="approve_image"
            )

        # Continue with remaining steps
        return await self._complete_video_generation(mode="discover")

    async def run_remix_workflow(self) -> WorkflowResult:
        """
        Run Remix workflow:
        Template → Image → Video → Audio
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

        # Check for image approval pause
        if self.project.require_image_approval:
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
