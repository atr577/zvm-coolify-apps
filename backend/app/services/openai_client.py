"""
OpenAI Client - Direct OpenAI SDK wrapper for LLM operations
Handles text generation, JSON generation, and vision analysis
"""

import asyncio
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Type
from openai import AsyncOpenAI, APIError, RateLimitError as OpenAIRateLimitError
from pydantic import BaseModel, ValidationError
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

        # In-flight request deduplication
        self._in_flight: Dict[str, asyncio.Future] = {}
        self._dedup_lock = asyncio.Lock()

        # Create cache directory if enabled
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"API response caching enabled: {self.cache_dir}")

    @property
    def client(self) -> AsyncOpenAI:
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            if not settings.OPENAI_API_KEY:
                raise OpenAIClientError("OPENAI_API_KEY not configured")
            self._client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY
            )
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

    def _get_request_key(self, messages: List[Dict[str, Any]], model: str, temperature: float) -> str:
        """Generate unique key for request deduplication"""
        data = json.dumps({"messages": messages, "model": model, "temp": temperature}, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    async def _make_request_with_retry(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Make chat completion request with retry logic and deduplication"""
        model = model or self.model

        # Deduplication: check if identical request is in flight
        request_key = self._get_request_key(messages, model, temperature)

        async with self._dedup_lock:
            if request_key in self._in_flight:
                logger.info(f"Dedup: waiting for in-flight request {request_key[:8]}")
                existing_future = self._in_flight[request_key]
                # Release lock while waiting

        # Check again after releasing lock
        if request_key in self._in_flight:
            try:
                return await self._in_flight[request_key]
            except Exception:
                pass  # If the original failed, we'll retry below

        # Create future for this request
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()

        async with self._dedup_lock:
            # Double-check after acquiring lock
            if request_key in self._in_flight:
                existing = self._in_flight[request_key]
                # Release lock and wait
                try:
                    return await existing
                except Exception:
                    pass
            self._in_flight[request_key] = future

        try:
            result = await self._do_request(messages, model, temperature, response_format, max_tokens, max_retries)
            future.set_result(result)
            return result
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            async with self._dedup_lock:
                self._in_flight.pop(request_key, None)

    async def _do_request(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float,
        response_format: Optional[Dict[str, str]],
        max_tokens: Optional[int],
        max_retries: int
    ) -> Dict[str, Any]:
        """Actually perform the request with retries"""
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

                import traceback
                caller = traceback.extract_stack()[-4]  # Get caller info
                logger.info(f"OpenAI request with model: {model} from {caller.filename.split('/')[-1]}:{caller.lineno} ({caller.name})")

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

    async def generate_validated_json(
        self,
        prompt: str,
        response_schema: Type[BaseModel],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_retries: int = 1
    ) -> BaseModel:
        """Generate JSON response with Pydantic v2 validation.

        Validation is ALWAYS applied — including custom prompts.

        Flow: generate_json() → model_validate() → return model
        On ValidationError: retry once with error context in prompt.

        Args:
            prompt: User prompt
            response_schema: Pydantic v2 model class to validate against
            system_prompt: Optional system prompt
            model: LLM model override
            temperature: Temperature for generation
            max_retries: Number of validation retries (default 1)

        Returns:
            Validated Pydantic model instance

        Raises:
            OpenAIClientError: If validation fails after all retries
        """
        current_prompt = prompt

        for attempt in range(max_retries + 1):
            try:
                raw_response = await self.generate_json(
                    prompt=current_prompt,
                    system_prompt=system_prompt,
                    model=model,
                    temperature=temperature
                )

                validated = response_schema.model_validate(raw_response)

                if attempt > 0:
                    logger.info(
                        f"LLM validation succeeded on retry: "
                        f"{response_schema.__name__} (attempt {attempt + 1})"
                    )
                else:
                    logger.info(
                        f"LLM response validated: {response_schema.__name__}"
                    )
                return validated

            except ValidationError as e:
                error_details = self._format_validation_error(e)

                if attempt < max_retries:
                    logger.warning(
                        f"LLM validation failed (attempt {attempt + 1}), "
                        f"retrying: {error_details}"
                    )
                    current_prompt = self._build_retry_prompt(
                        original_prompt=prompt,
                        validation_error=error_details,
                        expected_schema=response_schema
                    )
                else:
                    logger.error(
                        f"LLM validation failed after {max_retries + 1} attempts: "
                        f"{error_details}"
                    )
                    raise OpenAIClientError(
                        f"LLM response validation failed: {error_details}"
                    )

    def _format_validation_error(self, e: ValidationError) -> str:
        """Format Pydantic v2 validation error for logging and retry prompt."""
        errors = []
        for err in e.errors():
            field = ".".join(str(x) for x in err["loc"])
            msg = err["msg"]
            errors.append(f"{field}: {msg}")
        return "; ".join(errors)

    def _build_retry_prompt(
        self,
        original_prompt: str,
        validation_error: str,
        expected_schema: Type[BaseModel]
    ) -> str:
        """Build retry prompt with validation error context and expected schema."""
        schema_str = json.dumps(
            expected_schema.model_json_schema(), indent=2, ensure_ascii=False
        )

        return f"""{original_prompt}

IMPORTANT: Your previous response had validation errors:
{validation_error}

Expected JSON schema:
{schema_str}

Please fix the errors and return valid JSON matching this schema exactly."""

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
