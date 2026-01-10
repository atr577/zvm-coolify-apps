"""
KLING Audio Service - adds AI-generated audio to video via PiAPI.
"""
import asyncio
import logging
from typing import List

from app.services.media.base import AudioServiceProtocol
from app.services.piapi_client import piapi_client, PiAPIError
from app.core.config import settings

logger = logging.getLogger(__name__)


class KlingAudioService(AudioServiceProtocol):
    """Audio generation using KLING Sound via PiAPI."""

    def __init__(self):
        self.client = piapi_client
        self.mock_mode = settings.MOCK_MODE

    async def add_to_video(
        self,
        video_task_id: str,
        **kwargs
    ) -> List[str]:
        """Add AI-generated audio to video. Returns 4 variants."""
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock audio variants")
            from app.services.mock_data import MOCK_VIDEO_URL
            await asyncio.sleep(2)
            return [MOCK_VIDEO_URL] * 4

        try:
            logger.info(f"Adding audio to video task: {video_task_id}")

            urls = await self.client.add_audio_to_video(video_task_id)

            logger.info(f"Audio added: {len(urls)} variants")
            return urls

        except PiAPIError as e:
            logger.error(f"Failed to add audio: {e}")
            raise
