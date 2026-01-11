"""
Image step - generates image from scenario prompts.

Uses kling_service.generate_image() with prompts from scenario_data.
"""
from typing import Dict, Any
import logging

from app.services.kling_service import kling_service

logger = logging.getLogger(__name__)


async def generate(video) -> Dict[str, Any]:
    """
    Generate image from scenario data.

    Args:
        video: Video model with image_prompt from scenario step

    Returns:
        Dict with image_url
    """
    logger.info(f"Image step: generating for video {video.id}")

    # Get prompt from video (set during scenario step)
    prompt = video.image_prompt
    if not prompt:
        raise ValueError("image_prompt not found. Run scenario step first.")

    # Get aspect ratio from project
    aspect_ratio = video.project.aspect_ratio if video.project else "9:16"

    # Get negative prompt from scenario_data if available
    negative_prompt = None
    if video.scenario_data and isinstance(video.scenario_data, dict):
        negative_prompt = video.scenario_data.get("negative_prompt")

    # Generate image
    image_url = await kling_service.generate_image(
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        negative_prompt=negative_prompt,
    )

    logger.info(f"Image step: generated {image_url[:50]}...")

    return {"image_url": image_url}
