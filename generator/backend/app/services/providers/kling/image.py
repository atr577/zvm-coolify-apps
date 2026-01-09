"""
KLING Image Service - generates images using Nano Banana Pro via PiAPI.
"""
import asyncio
import logging
from typing import Optional

from app.services.media.base import ImageServiceProtocol
from app.services.piapi_client import piapi_client, PiAPIError
from app.core.config import settings

logger = logging.getLogger(__name__)


class KlingImageService(ImageServiceProtocol):
    """Image generation using KLING/Nano Banana Pro via PiAPI."""

    def __init__(self):
        self.client = piapi_client
        self.mock_mode = settings.MOCK_MODE

    async def generate(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        negative_prompt: Optional[str] = None,
        style_suffix: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate image using Nano Banana Pro."""
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock image URL")
            from app.services.mock_data import MOCK_IMAGE_URL
            await asyncio.sleep(2)
            return MOCK_IMAGE_URL

        try:
            # Combine prompt with style suffix
            full_prompt = prompt
            if style_suffix:
                full_prompt = f"{prompt}. {style_suffix}"

            # Add negative prompt if provided
            if negative_prompt:
                full_prompt = f"{full_prompt} --no {negative_prompt}"

            logger.info(f"Generating image: {full_prompt[:80]}...")

            image_url = await self.client.generate_image(
                prompt=full_prompt,
                aspect_ratio=aspect_ratio,
                resolution=kwargs.get("resolution", "1K")
            )

            logger.info(f"Image generated: {image_url}")
            return image_url

        except PiAPIError as e:
            logger.error(f"Failed to generate image: {e}")
            raise
