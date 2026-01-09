"""
KLING Video Service - generates video from image via PiAPI.
"""
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple

from app.services.media.base import VideoServiceProtocol
from app.services.piapi_client import piapi_client, PiAPIError
from app.core.config import settings

logger = logging.getLogger(__name__)


class KlingVideoService(VideoServiceProtocol):
    """Video generation using KLING via PiAPI."""

    def __init__(self):
        self.client = piapi_client
        self.model = settings.KLING_MODEL
        self.mock_mode = settings.MOCK_MODE

    async def generate(
        self,
        image_url: str,
        prompt: str,
        duration: int = 5,
        camera_control: Optional[Dict[str, Any]] = None,
        negative_prompt: Optional[str] = None,
        **kwargs
    ) -> Tuple[str, str]:
        """Generate video from image (image-to-video)."""
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock video URL")
            from app.services.mock_data import MOCK_VIDEO_URL
            await asyncio.sleep(3)
            return MOCK_VIDEO_URL, "mock_task_id_12345"

        try:
            logger.info(f"Generating video from image: {image_url[:50]}...")

            video_url, task_id = await self.client.generate_video_from_image(
                image_url=image_url,
                prompt=prompt,
                duration=duration,
                mode=kwargs.get("mode", "standard"),
                negative_prompt=negative_prompt,
                camera_control=camera_control,
                return_task_id=True
            )

            logger.info(f"Video generated: {video_url}, task_id: {task_id}")
            return video_url, task_id

        except PiAPIError as e:
            logger.error(f"Failed to generate video: {e}")
            raise

    async def generate_from_text(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        **kwargs
    ) -> str:
        """Generate video directly from text (text-to-video)."""
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock video URL")
            from app.services.mock_data import MOCK_VIDEO_URL
            await asyncio.sleep(3)
            return MOCK_VIDEO_URL

        try:
            logger.info(f"Generating video from text: {prompt[:50]}...")

            video_url = await self.client.generate_video_from_text(
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                mode=kwargs.get("mode", "standard"),
                negative_prompt=kwargs.get("negative_prompt"),
                camera_control=kwargs.get("camera_control")
            )

            logger.info(f"Text-to-video generated: {video_url}")
            return video_url

        except PiAPIError as e:
            logger.error(f"Failed to generate text-to-video: {e}")
            raise
