"""
Audio step - adds AI-generated audio to video.

Uses kling_service.add_audio_to_video() with video task_id.
"""
from typing import Dict, Any
import logging

from app.services.kling_service import kling_service

logger = logging.getLogger(__name__)


async def generate(video) -> Dict[str, Any]:
    """
    Add audio to video.

    Args:
        video: Video model with video_task_id

    Returns:
        Dict with audio_variants and video_with_audio_url
    """
    logger.info(f"Audio step: generating for video {video.id}")

    # Check if audio should be skipped
    if video.project and video.project.audio_mode == "none":
        logger.info(f"Audio step: skipped (audio_mode=none)")
        return {
            "audio_variants": [],
            "video_with_audio_url": video.video_url,
            "skipped": True,
        }

    # Get task_id from video generation
    task_id = video.video_task_id
    if not task_id:
        raise ValueError("video_task_id not found. Run video step first.")

    # Generate audio variants
    audio_variants = await kling_service.add_audio_to_video(task_id)

    logger.info(f"Audio step: generated {len(audio_variants)} variants")

    # First variant is the default
    video_with_audio_url = audio_variants[0] if audio_variants else video.video_url

    return {
        "audio_variants": audio_variants,
        "video_with_audio_url": video_with_audio_url,
    }
