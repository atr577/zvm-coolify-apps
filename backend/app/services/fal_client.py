"""
fal.ai Client - Direct SDK wrapper for image/video/music generation
Uses fal_client SDK for async submit + polling pattern
"""

import asyncio
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import fal_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class FalClientError(Exception):
    """Base exception for fal.ai client errors"""
    pass


class RateLimitError(FalClientError):
    """Rate limit exceeded"""
    pass


class ContentPolicyError(FalClientError):
    """Content rejected by safety filter — do not retry"""
    pass


class TimeoutError(FalClientError):
    """Operation timed out"""
    pass


class FalClient:
    """Direct fal.ai SDK client for media generation"""

    # Model IDs
    IMAGE_MODEL = "fal-ai/nano-banana-pro"
    VIDEO_MODEL = "fal-ai/veo3.1/image-to-video"
    MUSIC_MODEL = "fal-ai/lyria2"
    MMAUDIO_MODEL = "fal-ai/mmaudio-v2"

    def __init__(self):
        self.api_key = settings.FAL_KEY
        self.cache_enabled = settings.CACHE_API_RESPONSES
        self.cache_dir = Path(settings.API_CACHE_DIR)
        self.mock_mode = settings.MOCK_MODE

        # Semaphore for Lyria 2 (max 2 concurrent requests)
        self._lyria_semaphore = asyncio.Semaphore(2)

        # Set fal_client API key
        if self.api_key:
            import os
            os.environ["FAL_KEY"] = self.api_key

        # Create cache directory if enabled
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"API response caching enabled: {self.cache_dir}")

    # ============ Caching Methods ============

    def _get_cache_key(self, category: str, data: Dict, seed: Optional[int] = None) -> str:
        """Generate unique cache key from request parameters (includes seed)"""
        # Include seed in cache key for reproducibility
        cache_input = f"{category}:{json.dumps(data, sort_keys=True)}:{seed if seed else 'random'}"
        return hashlib.sha256(cache_input.encode()).hexdigest()[:16]

    def _save_to_cache(self, cache_key: str, category: str, request_data: Dict, response_data: Dict):
        """Save API response to cache"""
        if not self.cache_enabled:
            return

        try:
            cache_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "category": category,
                "request": request_data,
                "response": response_data
            }

            category_dir = self.cache_dir / category
            category_dir.mkdir(exist_ok=True)

            cache_file = category_dir / f"{cache_key}.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_entry, f, ensure_ascii=False, indent=2)

            logger.debug(f"Cached API response: {category}/{cache_key}")
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")

    def _load_from_cache(self, cache_key: str, category: str) -> Optional[Dict]:
        """Load response from cache (for mock mode)"""
        try:
            cache_file = self.cache_dir / category / f"{cache_key}.json"
            if cache_file.exists():
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_entry = json.load(f)
                return cache_entry.get("response")
        except Exception as e:
            logger.warning(f"Failed to load from cache: {e}")
        return None

    # ============ Core Methods ============

    async def _submit_task(
        self,
        model: str,
        input_data: Dict[str, Any],
        max_retries: int = 3
    ) -> str:
        """Submit task to fal.ai, returns request_id"""
        if not self.api_key:
            raise FalClientError("FAL_KEY not configured")

        for attempt in range(max_retries):
            try:
                logger.info(f"Submitting task to {model}")

                handler = await fal_client.submit_async(model, arguments=input_data)
                request_id = handler.request_id

                logger.info(f"Task submitted: {request_id}")
                return request_id

            except Exception as e:
                error_str = str(e).lower()

                # Content policy — don't retry, raise immediately
                if "content_policy" in error_str:
                    raise ContentPolicyError(f"Content rejected by safety filter: {e}")

                # Rate limit handling
                if "429" in error_str or "rate limit" in error_str:
                    retry_after = 60  # Default
                    logger.warning(f"Rate limit hit, retrying after {retry_after}s")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_after)
                        continue
                    raise RateLimitError(f"Rate limit exceeded: {e}")

                logger.error(f"Submit error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise FalClientError(f"Submit failed: {e}")

    async def _poll_status(
        self,
        model: str,
        request_id: str,
        max_wait_time: int = 600,
        poll_interval: int = 10,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Poll task status until complete, returns result"""
        elapsed = 0

        while elapsed < max_wait_time:
            for attempt in range(max_retries):
                try:
                    status = await fal_client.status_async(model, request_id, with_logs=False)

                    # fal_client returns Completed/InProgress/Queued class instances
                    # Check class name instead of .status attribute
                    status_class = type(status).__name__
                    logger.debug(f"Task {request_id} status: {status_class}")

                    if status_class == "Completed":
                        # Get the result
                        result = await fal_client.result_async(model, request_id)
                        return result

                    elif status_class in ["Failed", "Error"]:
                        error_msg = getattr(status, 'error', str(status))
                        if "content_policy" in str(error_msg).lower():
                            raise ContentPolicyError(f"Content rejected by safety filter: {error_msg}")
                        raise FalClientError(f"Task failed: {error_msg}")

                    # InProgress or Queued - still waiting, break retry loop
                    break

                except FalClientError:
                    raise
                except Exception as e:
                    error_str = str(e).lower()

                    # Content policy — don't retry, raise immediately
                    if "content_policy" in error_str:
                        raise ContentPolicyError(f"Content rejected by safety filter: {e}")

                    # Rate limit
                    if "429" in error_str or "rate limit" in error_str:
                        if attempt < max_retries - 1:
                            await asyncio.sleep(60)
                            continue
                        raise RateLimitError(f"Rate limit exceeded: {e}")

                    logger.error(f"Poll error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        raise FalClientError(f"Poll failed: {e}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Task {request_id} timed out after {max_wait_time}s")

    # ============ Image Generation ============

    def _convert_aspect_ratio_to_image_size(self, aspect_ratio: str) -> str:
        """Convert aspect_ratio (9:16, 16:9, 1:1) to flux image_size format."""
        mapping = {
            "9:16": "portrait_16_9",
            "16:9": "landscape_16_9",
            "1:1": "square",
            "4:3": "landscape_4_3",
            "3:4": "portrait_4_3",
        }
        return mapping.get(aspect_ratio, "portrait_16_9")

    async def submit_image(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None,
        resolution: str = "1K",
        output_format: str = "jpeg",
        model: Optional[str] = None
    ) -> str:
        """Submit image generation task, returns request_id"""
        use_model = model or settings.IMAGE_MODEL or self.IMAGE_MODEL
        is_flux = "flux" in use_model.lower()

        # Model-aware parameter building
        if is_flux:
            # Flux models use image_size instead of aspect_ratio
            image_size = self._convert_aspect_ratio_to_image_size(aspect_ratio)
            input_data = {
                "prompt": prompt,
                "image_size": image_size,
                "output_format": output_format,
                "num_images": 1
            }
            logger.info(f"Flux model: converted aspect_ratio '{aspect_ratio}' to image_size '{image_size}'")
        else:
            # Other models (nano-banana-pro, ideogram, imagen) use aspect_ratio
            input_data = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
                "output_format": output_format,
                "num_images": 1
            }

        if negative_prompt:
            input_data["negative_prompt"] = negative_prompt
        if seed is not None:
            input_data["seed"] = seed

        return await self._submit_task(use_model, input_data)

    async def poll_image(
        self,
        request_id: str,
        max_wait_time: int = 300,
        poll_interval: int = 3,
        model: Optional[str] = None
    ) -> str:
        """Poll image generation until complete, returns image URL"""
        use_model = model or settings.IMAGE_MODEL or self.IMAGE_MODEL
        result = await self._poll_status(
            use_model,
            request_id,
            max_wait_time=max_wait_time,
            poll_interval=poll_interval
        )

        # Extract image URL from result
        images = result.get("images", [])
        if not images:
            raise FalClientError(f"No images in result: {result}")

        return images[0].get("url") or images[0]

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None,
        resolution: str = "1K",
        model: Optional[str] = None
    ) -> str:
        """High-level: submit + poll, returns image URL"""
        # Mock mode
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock image URL")
            await asyncio.sleep(1)
            return "https://mock.fal.ai/image/mock-image.jpg"

        # Check cache
        request_data = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "model": model
        }
        cache_key = self._get_cache_key("image", request_data, seed)
        cached = self._load_from_cache(cache_key, "image")
        if cached:
            logger.info(f"Cache hit for image: {cache_key}")
            return cached.get("image_url")

        # Submit and poll
        request_id = await self.submit_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            negative_prompt=negative_prompt,
            seed=seed,
            resolution=resolution,
            model=model
        )
        image_url = await self.poll_image(request_id, model=model)

        # Cache result
        self._save_to_cache(cache_key, "image", request_data, {
            "image_url": image_url,
            "request_id": request_id
        })

        return image_url

    # ============ Video Generation ============

    async def submit_video(
        self,
        image_url: str,
        prompt: str,
        duration: str = "6s",
        aspect_ratio: str = "auto",
        resolution: str = "720p",
        generate_audio: bool = True,
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """Submit video generation task, returns request_id"""
        use_model = model or settings.VIDEO_MODEL or self.VIDEO_MODEL
        is_kling = "kling" in use_model.lower()

        is_wan = "wan" in use_model.lower()

        # Model-specific duration validation
        if is_kling and "/v3/" in use_model:
            # Kling v3: integer 3-15 seconds
            try:
                dur_int = int(duration)
                if dur_int < 3 or dur_int > 15:
                    duration = "5"
                    logger.info(f"Adjusted duration to {duration} (kling v3 range 3-15)")
            except ValueError:
                duration = "5"
                logger.info(f"Adjusted duration to {duration} (kling v3 requires integer)")
        elif is_kling:
            # Kling v2.1/v2.6: only 5 or 10 (no 's' suffix)
            if duration not in {"5", "10"}:
                duration = "5"
                logger.info(f"Adjusted duration to {duration} (kling v2.x constraint)")
        elif is_wan:
            # Wan v2.6: 5, 10, or 15 seconds (integer, no 's' suffix)
            dur_clean = duration.rstrip("s")
            if dur_clean not in {"5", "10", "15"}:
                duration = "5"
                logger.info(f"Adjusted duration to {duration} (wan constraint)")
            else:
                duration = dur_clean
        else:
            # Veo supports 4s, 6s, 8s
            valid_durations = {"4s", "6s", "8s"}
            if duration not in valid_durations:
                duration_map = {"5s": "6s", "7s": "8s", "10s": "8s", "5": "6s", "10": "8s"}
                duration = duration_map.get(duration, "6s")
                logger.info(f"Adjusted duration to {duration} (veo constraint)")

        input_data = {
            "prompt": prompt,
            "image_url": image_url,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "generate_audio": generate_audio
        }

        if negative_prompt:
            input_data["negative_prompt"] = negative_prompt
        if seed is not None:
            input_data["seed"] = seed

        return await self._submit_task(use_model, input_data)

    async def poll_video(
        self,
        request_id: str,
        max_wait_time: int = 600,
        poll_interval: int = 10,
        model: Optional[str] = None
    ) -> str:
        """Poll video generation until complete, returns video URL"""
        use_model = model or settings.VIDEO_MODEL or self.VIDEO_MODEL
        result = await self._poll_status(
            use_model,
            request_id,
            max_wait_time=max_wait_time,
            poll_interval=poll_interval
        )

        # Extract video URL from result
        video = result.get("video", {})
        video_url = video.get("url") if isinstance(video, dict) else video

        if not video_url:
            raise FalClientError(f"No video URL in result: {result}")

        return video_url

    async def generate_video(
        self,
        image_url: str,
        prompt: str,
        duration: str = "6s",
        aspect_ratio: str = "auto",
        resolution: str = "720p",
        generate_audio: bool = True,
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """High-level: submit + poll, returns video URL"""
        use_model = model or settings.VIDEO_MODEL or self.VIDEO_MODEL
        is_kling = "kling" in use_model.lower()
        is_wan = "wan" in use_model.lower()

        # Model-specific duration validation
        if is_kling and "/v3/" in use_model:
            # Kling v3: integer 3-15 seconds
            try:
                dur_int = int(duration)
                if dur_int < 3 or dur_int > 15:
                    duration = "5"
                    logger.info(f"Adjusted duration to {duration} (kling v3 range 3-15)")
            except ValueError:
                duration = "5"
                logger.info(f"Adjusted duration to {duration} (kling v3 requires integer)")
        elif is_kling:
            # Kling v2.1/v2.6: only 5 or 10 (no 's' suffix)
            if duration not in {"5", "10"}:
                duration = "5"
                logger.info(f"Adjusted duration to {duration} (kling v2.x constraint)")
        elif is_wan:
            # Wan v2.6: 5, 10, or 15 seconds (integer, no 's' suffix)
            dur_clean = duration.rstrip("s")
            if dur_clean not in {"5", "10", "15"}:
                duration = "5"
                logger.info(f"Adjusted duration to {duration} (wan constraint)")
            else:
                duration = dur_clean
        else:
            # Veo supports 4s, 6s, 8s
            valid_durations = {"4s", "6s", "8s"}
            if duration not in valid_durations:
                duration_map = {"5s": "6s", "7s": "8s", "10s": "8s", "5": "6s", "10": "8s"}
                duration = duration_map.get(duration, "6s")
                logger.info(f"Adjusted duration to {duration} (veo constraint)")

        # Mock mode
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock video URL")
            await asyncio.sleep(2)
            return "https://mock.fal.ai/video/mock-video.mp4"

        # Check cache
        request_data = {
            "image_url": image_url,
            "prompt": prompt,
            "duration": duration,
            "generate_audio": generate_audio,
            "model": model
        }
        cache_key = self._get_cache_key("video", request_data, seed)
        cached = self._load_from_cache(cache_key, "video")
        if cached:
            logger.info(f"Cache hit for video: {cache_key}")
            return cached.get("video_url")

        # Submit and poll
        request_id = await self.submit_video(
            image_url=image_url,
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            generate_audio=generate_audio,
            negative_prompt=negative_prompt,
            seed=seed,
            model=model
        )
        video_url = await self.poll_video(request_id, model=model)

        # Cache result
        self._save_to_cache(cache_key, "video", request_data, {
            "video_url": video_url,
            "request_id": request_id
        })

        return video_url

    # ============ Music Generation ============

    async def submit_music(
        self,
        prompt: str,
        negative_prompt: str = "low quality",
        seed: Optional[int] = None
    ) -> str:
        """Submit music generation task, returns request_id"""
        input_data = {
            "prompt": prompt,
            "negative_prompt": negative_prompt
        }

        if seed is not None:
            input_data["seed"] = seed

        model = settings.MUSIC_MODEL or self.MUSIC_MODEL
        return await self._submit_task(model, input_data)

    async def poll_music(
        self,
        request_id: str,
        max_wait_time: int = 300,
        poll_interval: int = 10
    ) -> str:
        """Poll music generation until complete, returns audio URL"""
        model = settings.MUSIC_MODEL or self.MUSIC_MODEL
        result = await self._poll_status(
            model,
            request_id,
            max_wait_time=max_wait_time,
            poll_interval=poll_interval
        )

        # Extract audio URL from result
        audio = result.get("audio", {})
        audio_url = audio.get("url") if isinstance(audio, dict) else audio

        if not audio_url:
            raise FalClientError(f"No audio URL in result: {result}")

        return audio_url

    async def generate_music(
        self,
        prompt: str,
        negative_prompt: str = "low quality",
        seed: Optional[int] = None
    ) -> str:
        """High-level: submit + poll with Lyria2 concurrency control"""
        # Mock mode
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock audio URL")
            await asyncio.sleep(1)
            return "https://mock.fal.ai/audio/mock-audio.wav"

        # Check cache
        request_data = {
            "prompt": prompt,
            "negative_prompt": negative_prompt
        }
        cache_key = self._get_cache_key("music", request_data, seed)
        cached = self._load_from_cache(cache_key, "music")
        if cached:
            logger.info(f"Cache hit for music: {cache_key}")
            return cached.get("audio_url")

        # Use semaphore for Lyria2 concurrency control (max 2 concurrent)
        async with self._lyria_semaphore:
            logger.info("Acquired Lyria2 semaphore slot")

            # Submit and poll
            request_id = await self.submit_music(
                prompt=prompt,
                negative_prompt=negative_prompt,
                seed=seed
            )
            audio_url = await self.poll_music(request_id)

            # Cache result
            self._save_to_cache(cache_key, "music", request_data, {
                "audio_url": audio_url,
                "request_id": request_id
            })

            return audio_url


    # ============ MMAudio V2 (Sound FX) ============

    async def submit_mmaudio(
        self,
        video_url: str,
        prompt: Optional[str] = None,
    ) -> str:
        """Submit MMAudio V2 task for video-to-audio generation, returns request_id.

        Args:
            video_url: URL of the video to generate audio for
            prompt: Optional text prompt for audio style. None = auto mode (model decides).
        """
        input_data = {"video_url": video_url}
        if prompt:
            input_data["prompt"] = prompt

        return await self._submit_task(self.MMAUDIO_MODEL, input_data, max_retries=2)

    async def poll_mmaudio(
        self,
        request_id: str,
        max_wait_time: int = 120,
        poll_interval: int = 5,
    ) -> str:
        """Poll MMAudio V2 generation until complete, returns audio URL."""
        result = await self._poll_status(
            self.MMAUDIO_MODEL,
            request_id,
            max_wait_time=max_wait_time,
            poll_interval=poll_interval,
        )

        # MMAudio V2 returns {audio: {url: "..."}}
        audio = result.get("audio", {})
        audio_url = audio.get("url") if isinstance(audio, dict) else audio

        if not audio_url:
            raise FalClientError(f"No audio URL in MMAudio result: {result}")

        return audio_url

    async def generate_mmaudio(
        self,
        video_url: str,
        prompt: Optional[str] = None,
    ) -> str:
        """High-level: submit + poll MMAudio V2, returns audio URL."""
        # Mock mode
        if self.mock_mode:
            logger.info("MOCK MODE: Returning mock MMAudio URL")
            await asyncio.sleep(1)
            return "https://mock.fal.ai/audio/mock-mmaudio.wav"

        # Check cache
        request_data = {"video_url": video_url, "prompt": prompt}
        cache_key = self._get_cache_key("mmaudio", request_data)
        cached = self._load_from_cache(cache_key, "mmaudio")
        if cached:
            logger.info(f"Cache hit for mmaudio: {cache_key}")
            return cached.get("audio_url")

        # Submit and poll
        request_id = await self.submit_mmaudio(video_url=video_url, prompt=prompt)
        audio_url = await self.poll_mmaudio(request_id)

        # Cache result
        self._save_to_cache(cache_key, "mmaudio", request_data, {
            "audio_url": audio_url,
            "request_id": request_id,
        })

        return audio_url


# Singleton instance
fal_client_instance = FalClient()
