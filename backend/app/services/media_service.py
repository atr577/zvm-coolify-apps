"""
Media Service - Unified media generation using fal.ai
Handles image, video, and music generation through fal.ai SDK
"""

from app.services.fal_client import fal_client_instance, FalClientError
from app.core.config import settings
from typing import Dict, Any, Optional
import logging
import asyncio

logger = logging.getLogger(__name__)


class MediaService:
    """Service for media generation via fal.ai"""

    def __init__(self):
        self.client = fal_client_instance
        self.mock_mode = settings.MOCK_MODE

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        mode: str = "standard",
        negative_prompt: Optional[str] = None,
        style_suffix: Optional[str] = None,
        seed: Optional[int] = None
    ) -> str:
        """
        Generate image using fal.ai (nano-banana-pro)
        Used as first frame for image-to-video

        Args:
            prompt: Main prompt
            aspect_ratio: Aspect ratio (9:16, 16:9, 1:1)
            mode: Generation mode (unused, kept for compatibility)
            negative_prompt: What NOT to include
            style_suffix: Style modifiers (quality, lighting)
            seed: Random seed for reproducibility

        Returns:
            Image URL
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock image URL")
            from app.services.mock_data import MOCK_IMAGE_URL
            await asyncio.sleep(2)
            return MOCK_IMAGE_URL

        try:
            # Combine prompt and style_suffix
            full_prompt = prompt
            if style_suffix:
                full_prompt = f"{prompt}. {style_suffix}"

            logger.info(f"Generating image with fal.ai: {full_prompt[:80]}...")

            image_url = await self.client.generate_image(
                prompt=full_prompt,
                aspect_ratio=aspect_ratio,
                negative_prompt=negative_prompt,
                seed=seed,
                resolution="1K"
            )

            logger.info(f"Image generated successfully: {image_url}")
            return image_url

        except FalClientError as e:
            logger.error(f"Failed to generate image: {e}")
            raise

    async def generate_video(
        self,
        image_url: str,
        prompt: str,
        duration: int = 5,
        mode: str = "standard",
        version: Optional[str] = None,
        camera_control: Optional[Dict[str, Any]] = None,
        negative_prompt: Optional[str] = None,
        generate_audio: bool = True,
        seed: Optional[int] = None,
        return_task_id: bool = False
    ) -> str:
        """
        Generate video from image using fal.ai (veo3.1)

        Args:
            image_url: Source image URL
            prompt: Motion/animation description
            duration: Duration in seconds (5, 8)
            mode: Generation mode (unused, kept for compatibility)
            version: Model version (unused, kept for compatibility)
            camera_control: Camera movement (unused for veo3.1)
            negative_prompt: What NOT to include
            generate_audio: Generate built-in audio with video
            seed: Random seed for reproducibility
            return_task_id: Return (url, task_id) tuple (deprecated)

        Returns:
            Video URL (or tuple if return_task_id=True)
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock video URL")
            from app.services.mock_data import MOCK_VIDEO_URL
            await asyncio.sleep(3)
            if return_task_id:
                return MOCK_VIDEO_URL, "mock_task_id_12345"
            return MOCK_VIDEO_URL

        try:
            logger.info(f"Generating video from image: {image_url[:50]}...")

            # Convert duration int to string format (veo3.1 expects "5s", "8s")
            duration_str = f"{duration}s"

            video_url = await self.client.generate_video(
                image_url=image_url,
                prompt=prompt,
                duration=duration_str,
                generate_audio=generate_audio,
                negative_prompt=negative_prompt,
                seed=seed
            )

            logger.info(f"Video generated successfully: {video_url}")

            if return_task_id:
                # Deprecated: return empty task_id for compatibility
                return video_url, ""
            return video_url

        except FalClientError as e:
            logger.error(f"Failed to generate video: {e}")
            raise

    async def generate_music(
        self,
        prompt: str,
        negative_prompt: str = "low quality",
        seed: Optional[int] = None
    ) -> str:
        """
        Generate music using fal.ai (Lyria2)

        Args:
            prompt: Music description
            negative_prompt: What to avoid
            seed: Random seed

        Returns:
            Audio URL (WAV)
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock audio URL")
            from app.services.mock_data import MOCK_VIDEO_URL
            await asyncio.sleep(2)
            return MOCK_VIDEO_URL.replace(".mp4", ".wav")

        try:
            logger.info(f"Generating music with Lyria2: {prompt[:50]}...")

            audio_url = await self.client.generate_music(
                prompt=prompt,
                negative_prompt=negative_prompt,
                seed=seed
            )

            logger.info(f"Music generated successfully: {audio_url}")
            return audio_url

        except FalClientError as e:
            logger.error(f"Failed to generate music: {e}")
            raise

    async def add_audio_to_video(self, video_task_id: str) -> list[str]:
        """
        DEPRECATED: Kling Sound API not available with veo3.1
        Use generate_music() + ffmpeg merge instead.

        Kept for backward compatibility, returns empty list.
        """
        logger.warning("add_audio_to_video is deprecated. Use generate_music() + ffmpeg merge.")
        return []


# Singleton instance
media_service = MediaService()

# Legacy alias for backward compatibility
kling_service = media_service
