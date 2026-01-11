"""
Video step - generates video from image using motion prompts.

Uses kling_service.generate_video() with image_url and motion_prompt.
"""
from typing import Dict, Any
import logging

from app.services.kling_service import kling_service

logger = logging.getLogger(__name__)


async def generate(video) -> Dict[str, Any]:
    """
    Generate video from image.

    Args:
        video: Video model with image_url and scenario_data

    Returns:
        Dict with video_url and task_id
    """
    logger.info(f"Video step: generating for video {video.id}")

    # Get image URL
    image_url = video.image_url
    if not image_url:
        raise ValueError("image_url not found. Run image step first.")

    # Get motion prompt from scenario_data
    motion_prompt = None
    camera_control = None
    negative_prompt = None

    if video.scenario_data and isinstance(video.scenario_data, dict):
        motion_prompt = video.scenario_data.get("motion_prompt")
        camera_control = video.scenario_data.get("camera_movement")
        negative_prompt = video.scenario_data.get("negative_prompt")

    # Use image_prompt as fallback for motion
    if not motion_prompt:
        motion_prompt = video.image_prompt or "subtle natural movement"

    # Get duration from project
    duration = video.project.duration if video.project else 5

    # Generate video (returns tuple with task_id)
    video_url, task_id = await kling_service.generate_video(
        image_url=image_url,
        prompt=motion_prompt,
        duration=duration,
        camera_control=camera_control,
        negative_prompt=negative_prompt,
        return_task_id=True,
    )

    logger.info(f"Video step: generated {video_url[:50]}..., task_id={task_id}")

    return {
        "video_url": video_url,
        "task_id": task_id,
    }
