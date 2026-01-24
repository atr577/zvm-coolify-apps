"""
fal.ai Media Service Providers.

Implements protocols from app.services.media.base using fal.ai SDK.
"""

from typing import Optional, Tuple, Dict, Any, List
from app.services.media.base import (
    ImageServiceProtocol,
    VideoServiceProtocol,
    AudioServiceProtocol,
)
from app.services.media_service import media_service


class FalImageService(ImageServiceProtocol):
    """Image generation service using fal.ai (nano-banana-pro)."""

    async def generate(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        negative_prompt: Optional[str] = None,
        style_suffix: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate image using fal.ai nano-banana-pro."""
        return await media_service.generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            negative_prompt=negative_prompt,
            style_suffix=style_suffix,
            **kwargs
        )


class FalVideoService(VideoServiceProtocol):
    """Video generation service using fal.ai (veo3.1)."""

    async def generate(
        self,
        image_url: str,
        prompt: str,
        duration: int = 5,
        camera_control: Optional[Dict[str, Any]] = None,
        negative_prompt: Optional[str] = None,
        **kwargs
    ) -> Tuple[str, str]:
        """Generate video using fal.ai veo3.1."""
        video_url, task_id = await media_service.generate_video(
            image_url=image_url,
            prompt=prompt,
            duration=duration,
            negative_prompt=negative_prompt,
            return_task_id=True,
            **kwargs
        )
        return video_url, task_id


class FalAudioService(AudioServiceProtocol):
    """Audio generation service using fal.ai (Lyria2).

    Note: Veo 3.1 supports built-in audio, so this service
    generates standalone audio using Lyria2.
    """

    async def add_to_video(
        self,
        video_task_id: str,
        prompt: str = "Atmospheric music matching the video",
        **kwargs
    ) -> List[str]:
        """
        Generate audio using Lyria2.

        Note: This doesn't add audio to video directly.
        Use ffmpeg merge for combining video with audio.
        Returns list with single audio URL.
        """
        audio_url = await media_service.generate_music(
            prompt=prompt,
            **kwargs
        )
        return [audio_url]


__all__ = [
    "FalImageService",
    "FalVideoService",
    "FalAudioService",
]
