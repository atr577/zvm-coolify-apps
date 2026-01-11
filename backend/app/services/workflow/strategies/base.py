"""Base strategy for workflow generation."""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseStrategy(ABC):
    """
    Base strategy for project types.

    Defines common interface for Discover and Remix strategies.
    SCENARIO step is abstract (different logic), other steps have default implementations.
    """

    async def generate(self, step: str, video, project) -> Dict[str, Any]:
        """
        Dispatch to step-specific method.

        Args:
            step: Step name (scenario, image, video, audio)
            video: Video model instance
            project: Project model instance

        Returns:
            Dict with generated content
        """
        method = getattr(self, f"generate_{step}", None)
        if method is None:
            raise ValueError(f"Unknown step: {step}")
        return await method(video, project)

    @abstractmethod
    async def generate_scenario(self, video, project) -> Dict[str, Any]:
        """
        Generate scenario data.

        Must be implemented by subclasses:
        - DiscoverStrategy: LLM generates creatively
        - RemixStrategy: LLM fills template placeholders
        """
        raise NotImplementedError

    async def generate_image(self, video, project) -> Dict[str, Any]:
        """Generate image from scenario."""
        from app.services.workflow.steps import image
        return await image.generate(video)

    async def generate_video(self, video, project) -> Dict[str, Any]:
        """Generate video from image."""
        from app.services.workflow.steps import video as video_step
        return await video_step.generate(video)

    async def generate_audio(self, video, project) -> Dict[str, Any]:
        """Add audio to video."""
        from app.services.workflow.steps import audio
        return await audio.generate(video)
