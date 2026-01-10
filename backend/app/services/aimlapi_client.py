"""
Unified AIMLAPI client for GPT and KLING models
Handles all API communication with AIMLAPI.com
"""

import httpx
import asyncio
import json
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.core.models_config import VIDEO_MODEL_CONFIGS
import logging

logger = logging.getLogger(__name__)


class AIMLAPIError(Exception):
    """Base exception for AIMLAPI errors"""
    pass


class RateLimitError(AIMLAPIError):
    """Rate limit exceeded"""
    pass


class ModelNotFoundError(AIMLAPIError):
    """Model not found"""
    pass


class AIMLAPIClient:
    """Unified client for AIMLAPI"""

    def __init__(self):
        self.api_key = settings.AIMLAPI_KEY
        self.base_url = settings.AIMLAPI_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.timeout = httpx.Timeout(300.0, connect=10.0)  # 5 min total, 10 sec connect

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, headers=self.headers, params=params)
                    elif method.upper() == "POST":
                        response = await client.post(url, headers=self.headers, json=data)
                    else:
                        raise ValueError(f"Unsupported method: {method}")

                    # Handle different status codes
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limit hit, retrying after {retry_after}s")

                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            raise RateLimitError(f"Rate limit exceeded: {response.text}")

                    if response.status_code == 404:
                        raise ModelNotFoundError(f"Model not found: {response.text}")

                    response.raise_for_status()

                    return response.json()

            except httpx.HTTPStatusError as e:
                error_detail = ""
                try:
                    error_detail = e.response.text
                    logger.error(f"HTTP error on attempt {attempt + 1}: {e}")
                    logger.error(f"Response body: {error_detail}")
                except:
                    logger.error(f"HTTP error on attempt {attempt + 1}: {e}")

                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise AIMLAPIError(f"Request failed after {max_retries} attempts: {e}. Response: {error_detail}")

            except httpx.RequestError as e:
                logger.error(f"Request error on attempt {attempt + 1}: {e}")

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    raise AIMLAPIError(f"Connection failed after {max_retries} attempts: {e}")

    # ============ GPT Methods ============

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Chat completion using GPT models
        Compatible with OpenAI API format
        """
        model = model or settings.LLM_MODEL or settings.GPT_MODEL  # Legacy fallback

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }

        if response_format:
            payload["response_format"] = response_format

        if max_tokens:
            payload["max_tokens"] = max_tokens

        # Log the request for debugging
        logger.info(f"Sending chat completion request with model: {model}")
        logger.debug(f"Full payload: {json.dumps(payload, indent=2)}")

        # AIMLAPI uses OpenAI-compatible endpoint
        response = await self._make_request(
            "POST",
            "chat/completions",
            data=payload
        )

        return response

    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Simple text generation
        """
        messages = [{"role": "user", "content": prompt}]

        response = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return response["choices"][0]["message"]["content"]

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate JSON response
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"}
        )

        content = response["choices"][0]["message"]["content"]
        return json.loads(content)

    # ============ KLING Methods ============

    def _get_video_model_config(self) -> dict:
        """Get video model config from VIDEO_MODEL_CONFIGS."""
        model_name = settings.VIDEO_MODEL or settings.KLING_MODEL  # Legacy fallback

        # Handle legacy format: convert "2.5" to "kling-2.5"
        if model_name and not model_name.startswith("kling-"):
            model_name = f"kling-{model_name}"

        config = VIDEO_MODEL_CONFIGS.get(model_name)
        if not config:
            # Default fallback
            config = VIDEO_MODEL_CONFIGS.get("kling-2.5", {
                "provider": "kling",
                "version": "2.5",
                "max_duration": 10
            })
        return config

    async def create_video_task(
        self,
        task_type: str,
        prompt: Optional[str] = None,
        image_url: Optional[str] = None,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        mode: str = "standard",
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Create KLING video generation task
        Returns task_id for polling
        """
        # Get model version from config
        video_config = self._get_video_model_config()
        version = model or video_config.get("version", "2.5")

        # Build request based on AIMLAPI KLING format
        payload = {
            "model": f"kling/{version}/{task_type}",
            "prompt": prompt or "",
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "mode": mode
        }

        if image_url:
            payload["image_url"] = image_url

        # Add optional parameters
        if "negative_prompt" in kwargs:
            payload["negative_prompt"] = kwargs["negative_prompt"]

        if "cfg_scale" in kwargs:
            payload["cfg_scale"] = kwargs["cfg_scale"]

        if "camera_control" in kwargs:
            payload["camera_control"] = kwargs["camera_control"]

        response = await self._make_request(
            "POST",
            "video/generations",  # AIMLAPI endpoint for KLING
            data=payload
        )

        return response.get("id") or response.get("task_id")

    async def get_video_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get status of KLING video generation task
        """
        response = await self._make_request(
            "GET",
            f"video/generations/{task_id}"
        )

        return response

    async def wait_for_video(
        self,
        task_id: str,
        max_wait_time: int = 900,  # 15 minutes
        poll_interval: int = 10
    ) -> str:
        """
        Poll video generation status until complete
        Returns video URL
        """
        elapsed = 0

        while elapsed < max_wait_time:
            result = await self.get_video_task_status(task_id)

            status = result.get("status", "").lower()

            if status in ["completed", "succeeded", "success"]:
                # Extract video URL
                video_url = (
                    result.get("output", {}).get("video_url") or
                    result.get("video_url") or
                    result.get("url")
                )

                if not video_url:
                    raise AIMLAPIError(f"Video completed but no URL found: {result}")

                logger.info(f"Video generation completed: {video_url}")
                return video_url

            elif status in ["failed", "error"]:
                error_msg = result.get("error", {}).get("message", "Unknown error")
                raise AIMLAPIError(f"Video generation failed: {error_msg}")

            # Still processing
            logger.debug(f"Video status: {status}, waiting...")
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Video generation timed out after {max_wait_time}s")

    async def generate_video_from_text(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        mode: str = "standard",
        **kwargs
    ) -> str:
        """
        Generate video from text (text-to-video)
        Returns video URL
        """
        task_id = await self.create_video_task(
            task_type="text-to-video",
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            mode=mode,
            **kwargs
        )

        return await self.wait_for_video(task_id)

    async def generate_video_from_image(
        self,
        image_url: str,
        prompt: str,
        duration: int = 5,
        mode: str = "standard",
        **kwargs
    ) -> str:
        """
        Generate video from image (image-to-video)
        Returns video URL
        """
        task_id = await self.create_video_task(
            task_type="image-to-video",
            prompt=prompt,
            image_url=image_url,
            duration=duration,
            mode=mode,
            **kwargs
        )

        return await self.wait_for_video(task_id)


# Singleton instance
aimlapi_client = AIMLAPIClient()
