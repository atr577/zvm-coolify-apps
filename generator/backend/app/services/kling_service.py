"""
KLING Service - now powered by AIMLAPI
Handles video generation through KLING AI models
"""

from app.services.piapi_client import piapi_client, PiAPIError
from app.core.config import settings
from typing import Dict, Any, Optional
import logging
import asyncio

logger = logging.getLogger(__name__)


class KlingService:
    """Service for KLING video generation via AIMLAPI"""

    def __init__(self):
        self.client = piapi_client
        self.model = settings.KLING_MODEL
        self.mock_mode = settings.MOCK_MODE

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        mode: str = "standard",
        negative_prompt: Optional[str] = None,
        style_suffix: Optional[str] = None
    ) -> str:
        """
        Генерация изображения с помощью Nano Banana Pro (Gemini)
        Используется как первый кадр для image-to-video

        Args:
            prompt: основной промпт
            aspect_ratio: соотношение сторон
            mode: режим генерации
            negative_prompt: что НЕ должно быть в изображении
            style_suffix: стилистические модификаторы (качество, стиль, освещение)
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock image URL")
            from app.services.mock_data import MOCK_IMAGE_URL
            await asyncio.sleep(2)
            return MOCK_IMAGE_URL

        try:
            # Комбинируем prompt и style_suffix
            full_prompt = prompt
            if style_suffix:
                full_prompt = f"{prompt}. {style_suffix}"

            # Добавляем negative prompt если есть (через разделитель)
            if negative_prompt:
                full_prompt = f"{full_prompt} --no {negative_prompt}"

            logger.info(f"Generating image with Nano Banana Pro: {full_prompt[:80]}...")

            # Используем Nano Banana Pro для генерации картинки
            image_url = await self.client.generate_image(
                prompt=full_prompt,
                aspect_ratio=aspect_ratio,
                resolution="1K"  # $0.105 за картинку
            )

            logger.info(f"Image generated successfully: {image_url}")
            return image_url

        except PiAPIError as e:
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
        return_task_id: bool = False
    ) -> str | tuple[str, str]:
        """
        Генерация видео из изображения (image-to-video)
        Returns video_url, or (video_url, task_id) if return_task_id=True
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock video URL")
            from app.services.mock_data import MOCK_VIDEO_URL
            await asyncio.sleep(3)  # Simulate longer processing time
            if return_task_id:
                return MOCK_VIDEO_URL, "mock_task_id_12345"
            return MOCK_VIDEO_URL

        try:
            logger.info(f"Generating video from image: {image_url[:50]}...")

            result = await self.client.generate_video_from_image(
                image_url=image_url,
                prompt=prompt,
                duration=duration,
                mode=mode,
                negative_prompt=negative_prompt,
                camera_control=camera_control,
                return_task_id=return_task_id
            )

            if return_task_id:
                video_url, task_id = result
                logger.info(f"Video generated successfully: {video_url}, task_id: {task_id}")
                return video_url, task_id
            else:
                logger.info(f"Video generated successfully: {result}")
                return result

        except PiAPIError as e:
            logger.error(f"Failed to generate video: {e}")
            raise

    async def add_audio_to_video(self, video_task_id: str) -> list[str]:
        """
        Add audio to existing video using Kling Sound API
        Returns list of 4 video URLs with different audio variants
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock audio variants")
            from app.services.mock_data import MOCK_VIDEO_URL
            await asyncio.sleep(2)
            return [MOCK_VIDEO_URL] * 4

        try:
            logger.info(f"Adding audio to video task: {video_task_id}")
            urls = await self.client.add_audio_to_video(video_task_id)
            logger.info(f"Audio added successfully: {len(urls)} variants")
            return urls

        except PiAPIError as e:
            logger.error(f"Failed to add audio: {e}")
            raise

    async def generate_video_with_motion(
        self,
        image_url: str,
        prompt: str,
        motion_brush: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Генерация видео с контролем движения (motion brush)

        Note: Может не поддерживаться всеми версиями KLING через AIMLAPI
        """
        try:
            logger.info(f"Generating video with motion control")

            # Motion brush может быть частью camera_control или отдельным параметром
            video_url = await self.client.generate_video_from_image(
                image_url=image_url,
                prompt=prompt,
                duration=kwargs.get("duration", 5),
                mode=kwargs.get("mode", "standard"),
                negative_prompt=kwargs.get("negative_prompt"),
                # motion_brush может передаваться через kwargs
            )

            logger.info(f"Video with motion generated successfully")
            return video_url

        except PiAPIError as e:
            logger.error(f"Failed to generate video with motion: {e}")
            raise

    async def text_to_video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        mode: str = "standard",
        **kwargs
    ) -> str:
        """
        Прямая генерация видео из текста (text-to-video)
        Без промежуточного изображения
        """
        try:
            logger.info(f"Generating video from text: {prompt[:50]}...")

            video_url = await self.client.generate_video_from_text(
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                mode=mode,
                negative_prompt=kwargs.get("negative_prompt"),
                camera_control=kwargs.get("camera_control")
            )

            logger.info(f"Text-to-video generated successfully")
            return video_url

        except PiAPIError as e:
            logger.error(f"Failed to generate text-to-video: {e}")
            raise


# Singleton instance
kling_service = KlingService()
