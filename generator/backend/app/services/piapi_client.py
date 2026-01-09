"""
Unified PiAPI client for LLM and KLING models
Handles all API communication with piapi.ai
"""

import httpx
import asyncio
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class PiAPIError(Exception):
    """Base exception for PiAPI errors"""
    pass


class RateLimitError(PiAPIError):
    """Rate limit exceeded"""
    pass


class PiAPIClient:
    """Unified client for PiAPI"""

    def __init__(self):
        self.api_key = settings.PIAPI_KEY
        self.llm_base_url = settings.PIAPI_LLM_URL
        self.task_base_url = settings.PIAPI_TASK_URL
        self.timeout = httpx.Timeout(300.0, connect=10.0)
        self.cache_enabled = settings.CACHE_API_RESPONSES
        self.cache_dir = Path(settings.API_CACHE_DIR)

        # Создаем директорию для кеша если включено кеширование
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"API response caching enabled: {self.cache_dir}")

    def _get_cache_key(self, method: str, url: str, data: Optional[Dict] = None) -> str:
        """Генерирует уникальный ключ кеша из параметров запроса"""
        cache_input = f"{method}:{url}:{json.dumps(data, sort_keys=True) if data else ''}"
        return hashlib.sha256(cache_input.encode()).hexdigest()[:16]

    def _save_to_cache(self, cache_key: str, category: str, request_data: Dict, response_data: Dict):
        """Сохраняет ответ API в кеш"""
        if not self.cache_enabled:
            return

        try:
            cache_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "category": category,
                "request": request_data,
                "response": response_data
            }

            # Создаем поддиректорию для категории
            category_dir = self.cache_dir / category
            category_dir.mkdir(exist_ok=True)

            cache_file = category_dir / f"{cache_key}.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_entry, f, ensure_ascii=False, indent=2)

            logger.debug(f"Cached API response: {category}/{cache_key}")
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")

    def _load_from_cache(self, cache_key: str, category: str) -> Optional[Dict]:
        """Загружает ответ из кеша (для mock режима)"""
        try:
            cache_file = self.cache_dir / category / f"{cache_key}.json"
            if cache_file.exists():
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_entry = json.load(f)
                return cache_entry.get("response")
        except Exception as e:
            logger.warning(f"Failed to load from cache: {e}")
        return None

    def _get_llm_headers(self) -> Dict[str, str]:
        """Headers for LLM API"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _get_task_headers(self) -> Dict[str, str]:
        """Headers for Task API (KLING)"""
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, headers=headers, params=params)
                    elif method.upper() == "POST":
                        response = await client.post(url, headers=headers, json=data)
                    else:
                        raise ValueError(f"Unsupported method: {method}")

                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limit hit, retrying after {retry_after}s")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_after)
                            continue
                        raise RateLimitError(f"Rate limit exceeded: {response.text}")

                    response.raise_for_status()
                    return response.json()

            except httpx.HTTPStatusError as e:
                error_detail = e.response.text if e.response else str(e)
                logger.error(f"HTTP error on attempt {attempt + 1}: {e}")
                logger.error(f"Response: {error_detail}")

                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise PiAPIError(f"Request failed: {error_detail}")

            except httpx.RequestError as e:
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise PiAPIError(f"Connection failed: {e}")

    # ============ LLM Methods ============

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Chat completion using LLM models"""
        model = model or settings.GPT_MODEL

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }

        if response_format:
            payload["response_format"] = response_format
        if max_tokens:
            payload["max_tokens"] = max_tokens

        logger.info(f"LLM request with model: {model}")

        url = f"{self.llm_base_url}/chat/completions"
        response = await self._make_request(
            "POST",
            url,
            headers=self._get_llm_headers(),
            data=payload
        )

        # Кешируем ответ
        cache_key = self._get_cache_key("POST", url, payload)
        self._save_to_cache(cache_key, "llm", payload, response)

        return response

    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Simple text generation"""
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
        """Generate JSON response"""
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

    async def analyze_image(
        self,
        image_url: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Analyze image using GPT-4o vision
        Returns JSON response based on prompt
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Vision message format with image_url
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": image_url}
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        })

        response = await self.chat_completion(
            messages=messages,
            model="gpt-4o",  # GPT-4o supports vision
            temperature=temperature,
            response_format={"type": "json_object"}
        )

        content = response["choices"][0]["message"]["content"]
        return json.loads(content)

    # ============ KLING Methods ============

    async def create_video_task(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        mode: str = "std",
        version: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        cfg_scale: float = 0.5,
        **kwargs
    ) -> str:
        """
        Create KLING video generation task
        Returns task_id for polling
        """
        version = version or settings.KLING_MODEL

        payload = {
            "model": "kling",
            "task_type": "video_generation",
            "input": {
                "prompt": prompt,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "mode": mode,
                "version": version,
                "cfg_scale": cfg_scale
            }
        }

        if negative_prompt:
            payload["input"]["negative_prompt"] = negative_prompt

        if image_url:
            payload["input"]["image_url"] = image_url

        # Camera control
        if "camera_control" in kwargs:
            payload["input"]["camera_control"] = kwargs["camera_control"]

        logger.info(f"Creating KLING video task: version={version}, duration={duration}s")

        response = await self._make_request(
            "POST",
            f"{self.task_base_url}/task",
            headers=self._get_task_headers(),
            data=payload
        )

        task_id = response.get("data", {}).get("task_id") or response.get("task_id")
        if not task_id:
            raise PiAPIError(f"No task_id in response: {response}")

        logger.info(f"Created task: {task_id}")
        return task_id

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of KLING task"""
        response = await self._make_request(
            "GET",
            f"{self.task_base_url}/task/{task_id}",
            headers=self._get_task_headers()
        )
        return response

    async def wait_for_video(
        self,
        task_id: str,
        max_wait_time: int = 900,
        poll_interval: int = 10
    ) -> str:
        """Poll video generation until complete, returns video URL"""
        elapsed = 0

        while elapsed < max_wait_time:
            result = await self.get_task_status(task_id)

            data = result.get("data", result)
            status = data.get("status", "").lower()

            logger.debug(f"Task {task_id} status: {status}")

            if status in ["completed", "succeeded", "success"]:
                # Extract video URL from output
                output = data.get("output", {})
                video_url = (
                    output.get("video_url") or
                    # Support video_urls array (like image_urls)
                    (output.get("video_urls", [None])[0] if output.get("video_urls") else None) or
                    data.get("video_url")
                )

                # Fallback: KLING format with works array
                if not video_url and output.get("works"):
                    works = output["works"]
                    if works and len(works) > 0:
                        video_url = works[0].get("video", {}).get("url")

                if not video_url:
                    raise PiAPIError(f"Video completed but no URL found: {result}")

                logger.info(f"Video ready: {video_url}")
                return video_url

            elif status in ["failed", "error"]:
                error_msg = data.get("error", {}).get("message", str(data))
                raise PiAPIError(f"Video generation failed: {error_msg}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Video generation timed out after {max_wait_time}s")

    async def generate_video_from_text(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        mode: str = "std",
        **kwargs
    ) -> str:
        """Generate video from text, returns video URL"""
        task_id = await self.create_video_task(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            mode=mode,
            **kwargs
        )
        video_url = await self.wait_for_video(task_id)

        # Кешируем результат
        request_data = {"prompt": prompt, "duration": duration, "aspect_ratio": aspect_ratio, "mode": mode, **kwargs}
        cache_key = self._get_cache_key("video_text", prompt, request_data)
        self._save_to_cache(cache_key, "video", request_data, {"video_url": video_url, "task_id": task_id})

        return video_url

    async def generate_video_from_image(
        self,
        image_url: str,
        prompt: str,
        duration: int = 5,
        mode: str = "std",
        return_task_id: bool = False,
        **kwargs
    ) -> str | tuple[str, str]:
        """Generate video from image, returns video URL (or tuple with task_id if return_task_id=True)"""
        task_id = await self.create_video_task(
            prompt=prompt,
            image_url=image_url,
            duration=duration,
            mode=mode,
            **kwargs
        )
        video_url = await self.wait_for_video(task_id)

        # Кешируем результат
        request_data = {"image_url": image_url, "prompt": prompt, "duration": duration, "mode": mode, **kwargs}
        cache_key = self._get_cache_key("video_image", image_url + prompt, request_data)
        self._save_to_cache(cache_key, "video", request_data, {"video_url": video_url, "task_id": task_id})

        if return_task_id:
            return video_url, task_id
        return video_url

    # ============ Kling Sound API ============

    async def create_sound_task(
        self,
        origin_task_id: Optional[str] = None,
        prompt: Optional[str] = None,
        duration: int = 10
    ) -> str:
        """
        Create Kling Sound generation task

        Two modes:
        - Add audio to video: provide origin_task_id
        - Text to audio: provide prompt and duration

        Returns task_id for polling
        """
        payload = {
            "model": "kling",
            "task_type": "sound",
            "input": {}
        }

        if origin_task_id:
            # Add audio to existing video
            payload["input"]["origin_task_id"] = origin_task_id
            logger.info(f"Creating sound task for video: {origin_task_id}")
        elif prompt:
            # Text to audio
            payload["input"]["prompt"] = prompt
            payload["input"]["duration"] = duration
            logger.info(f"Creating sound task from text: {prompt[:50]}...")
        else:
            raise ValueError("Either origin_task_id or prompt must be provided")

        response = await self._make_request(
            "POST",
            f"{self.task_base_url}/task",
            headers=self._get_task_headers(),
            data=payload
        )

        task_id = response.get("data", {}).get("task_id") or response.get("task_id")
        if not task_id:
            raise PiAPIError(f"No task_id in response: {response}")

        logger.info(f"Created sound task: {task_id}")
        return task_id

    async def wait_for_sound(
        self,
        task_id: str,
        max_wait_time: int = 300,
        poll_interval: int = 5
    ) -> List[str]:
        """Poll sound generation until complete, returns list of video/audio URLs (4 variants)"""
        elapsed = 0

        while elapsed < max_wait_time:
            result = await self.get_task_status(task_id)

            data = result.get("data", result)
            status = data.get("status", "").lower()

            logger.debug(f"Sound task {task_id} status: {status}")

            if status in ["completed", "succeeded", "success"]:
                output = data.get("output", {})

                # Sound API returns works array with 4 variants
                works = output.get("works", [])
                urls = []

                for work in works:
                    # For video with audio - API returns "resource" not "url"
                    video_data = work.get("video", {})
                    video_url = video_data.get("resource") or video_data.get("url")
                    if video_url:
                        urls.append(video_url)
                    # For audio only
                    audio_data = work.get("audio", {})
                    audio_url = audio_data.get("resource") or audio_data.get("url")
                    if audio_url and not video_url:
                        urls.append(audio_url)

                if not urls:
                    raise PiAPIError(f"Sound completed but no URLs found: {result}")

                logger.info(f"Sound ready: {len(urls)} variants")
                return urls

            elif status in ["failed", "error"]:
                error_msg = data.get("error", {}).get("message", str(data))
                raise PiAPIError(f"Sound generation failed: {error_msg}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Sound generation timed out after {max_wait_time}s")

    async def add_audio_to_video(self, video_task_id: str) -> List[str]:
        """
        Add audio to existing video using Kling Sound API
        Returns list of 4 video URLs with different audio variants
        """
        task_id = await self.create_sound_task(origin_task_id=video_task_id)
        return await self.wait_for_sound(task_id)


    # ============ Nano Banana Pro (Image Generation) ============

    async def create_image_task(
        self,
        prompt: str,
        image_urls: list = None,
        aspect_ratio: str = "9:16",
        resolution: str = "1K",
        output_format: str = "jpeg",
        safety_level: str = "low"
    ) -> str:
        """
        Create Nano Banana Pro image generation task
        Returns task_id for polling
        """
        payload = {
            "model": "gemini",
            "task_type": "nano-banana-pro",
            "input": {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
                "output_format": output_format,
                "safety_level": safety_level
            }
        }

        if image_urls:
            payload["input"]["image_urls"] = image_urls

        logger.info(f"Creating Nano Banana image task: {prompt[:50]}...")

        response = await self._make_request(
            "POST",
            f"{self.task_base_url}/task",
            headers=self._get_task_headers(),
            data=payload
        )

        task_id = response.get("data", {}).get("task_id") or response.get("task_id")
        if not task_id:
            raise PiAPIError(f"No task_id in response: {response}")

        logger.info(f"Created image task: {task_id}")
        return task_id

    async def wait_for_image(
        self,
        task_id: str,
        max_wait_time: int = 120,
        poll_interval: int = 3
    ) -> str:
        """Poll image generation until complete, returns image URL"""
        elapsed = 0

        while elapsed < max_wait_time:
            result = await self.get_task_status(task_id)

            data = result.get("data", result)
            status = data.get("status", "").lower()

            logger.debug(f"Image task {task_id} status: {status}")

            if status in ["completed", "succeeded", "success"]:
                output = data.get("output", {})
                image_url = (
                    output.get("image_url") or
                    output.get("url") or
                    # Nano Banana Pro returns image_urls array
                    (output.get("image_urls", [None])[0] if output.get("image_urls") else None) or
                    (output.get("images", [{}])[0].get("url") if output.get("images") else None)
                )

                if not image_url:
                    raise PiAPIError(f"Image completed but no URL found: {result}")

                logger.info(f"Image ready: {image_url}")
                return image_url

            elif status in ["failed", "error"]:
                error_msg = data.get("error", {}).get("message", str(data))
                raise PiAPIError(f"Image generation failed: {error_msg}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Image generation timed out after {max_wait_time}s")

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        resolution: str = "1K",
        image_urls: list = None
    ) -> str:
        """Generate image with Nano Banana Pro, returns image URL"""
        task_id = await self.create_image_task(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            image_urls=image_urls
        )
        image_url = await self.wait_for_image(task_id)

        # Кешируем результат
        request_data = {"prompt": prompt, "aspect_ratio": aspect_ratio, "resolution": resolution}
        cache_key = self._get_cache_key("image", prompt, request_data)
        self._save_to_cache(cache_key, "image", request_data, {"image_url": image_url, "task_id": task_id})

        return image_url


# Singleton instance
piapi_client = PiAPIClient()
