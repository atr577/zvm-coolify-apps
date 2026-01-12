"""
Video Provider Protocol.

All video providers must implement this protocol.
Signature matches existing video.py step pattern.
"""

from typing import Any, Dict, Protocol, Tuple, runtime_checkable


@runtime_checkable
class VideoProviderProtocol(Protocol):
    """
    Protocol for video generation providers.

    Implementations:
    - KlingVideoProvider: Video via KLING API

    Future:
    - RunwayProvider: Video via Runway API
    - PikaProvider: Video via Pika API
    """

    async def generate(self, video) -> Dict[str, Any]:
        """
        Generate video from image.

        Args:
            video: Video model instance with:
                - video.image_url: str (source image)
                - video.scenario_data: Dict with motion_prompt, camera_movement
                - video.project.duration: int (5 or 10 seconds)

        Returns:
            Dict with:
                - video_url: str (URL of generated video)
                - task_id: str (provider task ID for tracking)

        Raises:
            ValueError: If image_url is missing
            Exception: On API errors (will fail the step)
        """
        ...
