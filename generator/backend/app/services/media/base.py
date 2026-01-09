"""
Base protocols for media generation services.

These protocols define provider-agnostic interfaces for:
- Image generation (text-to-image)
- Video generation (image-to-video)
- Audio generation (add audio to video)

Any provider (KLING, Runway, Pika, etc.) can implement these protocols.
"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any, List


class ImageServiceProtocol(ABC):
    """Protocol for image generation services."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        negative_prompt: Optional[str] = None,
        style_suffix: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate an image from text prompt.

        Args:
            prompt: Text description of the image
            aspect_ratio: Image aspect ratio (e.g., "9:16", "16:9", "1:1")
            negative_prompt: What should NOT appear in the image
            style_suffix: Style modifiers (quality, lighting, etc.)
            **kwargs: Provider-specific parameters

        Returns:
            URL of the generated image
        """
        pass


class VideoServiceProtocol(ABC):
    """Protocol for video generation services."""

    @abstractmethod
    async def generate(
        self,
        image_url: str,
        prompt: str,
        duration: int = 5,
        camera_control: Optional[Dict[str, Any]] = None,
        negative_prompt: Optional[str] = None,
        **kwargs
    ) -> Tuple[str, str]:
        """
        Generate video from an image (image-to-video).

        Args:
            image_url: URL of the source image
            prompt: Motion/scenario description
            duration: Video duration in seconds (typically 5 or 10)
            camera_control: Camera movement settings
            negative_prompt: What should NOT appear in the video
            **kwargs: Provider-specific parameters

        Returns:
            Tuple of (video_url, task_id)
            task_id is needed for audio generation
        """
        pass

    async def generate_from_text(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        **kwargs
    ) -> str:
        """
        Generate video directly from text (text-to-video).
        Optional - not all providers support this.

        Returns:
            URL of the generated video
        """
        raise NotImplementedError("Text-to-video not supported by this provider")


class AudioServiceProtocol(ABC):
    """Protocol for audio generation services."""

    @abstractmethod
    async def add_to_video(
        self,
        video_task_id: str,
        **kwargs
    ) -> List[str]:
        """
        Add AI-generated audio to a video.

        Args:
            video_task_id: Task ID from video generation
            **kwargs: Provider-specific parameters

        Returns:
            List of video URLs with different audio variants
        """
        pass
