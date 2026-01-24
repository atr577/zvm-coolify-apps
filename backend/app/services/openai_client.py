"""
OpenAI Client - Direct OpenAI SDK wrapper for LLM operations
Handles text generation, JSON generation, and vision analysis
"""

import asyncio
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI, APIError, RateLimitError as OpenAIRateLimitError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class OpenAIClientError(Exception):
    """Base exception for OpenAI client errors"""
    pass


class RateLimitError(OpenAIClientError):
    """Rate limit exceeded"""
    pass


class OpenAIClient:
    """Direct OpenAI SDK client for LLM operations"""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.LLM_MODEL or "gpt-4o-mini"
        self.cache_enabled = settings.CACHE_API_RESPONSES
        self.cache_dir = Path(settings.API_CACHE_DIR)

        # Initialize async client
        self._client: Optional[AsyncOpenAI] = None

        # Create cache directory if enabled
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"API response caching enabled: {self.cache_dir}")

    @property
    def client(self) -> AsyncOpenAI:
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            if not self.api_key:
                raise OpenAIClientError("OPENAI_API_KEY not configured")
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    # ============ Caching Methods ============

    def _get_cache_key(self, method: str, data: Optional[Dict] = None) -> str:
        """Generate unique cache key from request parameters"""
        cache_input = f"{method}:{json.dumps(data, sort_keys=True) if data else ''}"
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

    # ============ LLM Methods ============

    async def _make_request_with_retry(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Make chat completion request with retry logic"""
        model = model or self.model

        for attempt in range(max_retries):
            try:
                kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature
                }

                if response_format:
                    kwargs["response_format"] = response_format
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens

                logger.info(f"OpenAI request with model: {model}")

                response = await self.client.chat.completions.create(**kwargs)

                # Convert to dict for caching
                return {
                    "choices": [{
                        "message": {
                            "content": response.choices[0].message.content,
                            "role": response.choices[0].message.role
                        }
                    }],
                    "model": response.model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    } if response.usage else None
                }

            except OpenAIRateLimitError as e:
                retry_after = 60  # Default retry after
                logger.warning(f"Rate limit hit, retrying after {retry_after}s")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_after)
                    continue
                raise RateLimitError(f"Rate limit exceeded: {e}")

            except APIError as e:
                logger.error(f"API error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise OpenAIClientError(f"Request failed: {e}")

            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise OpenAIClientError(f"Request failed: {e}")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Chat completion using OpenAI models"""
        response = await self._make_request_with_retry(
            messages=messages,
            model=model,
            temperature=temperature,
            response_format=response_format,
            max_tokens=max_tokens
        )

        # Cache response
        cache_data = {
            "messages": messages,
            "model": model or self.model,
            "temperature": temperature
        }
        cache_key = self._get_cache_key("chat", cache_data)
        self._save_to_cache(cache_key, "llm", cache_data, response)

        return response

    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """Simple text generation"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

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


# Singleton instance
openai_client = OpenAIClient()
