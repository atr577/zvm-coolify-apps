"""
Tests for OpenAIClient.generate_validated_json() — validation + retry logic.
"""

import pytest
from unittest.mock import AsyncMock, patch
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any

from app.services.openai_client import OpenAIClient, OpenAIClientError


# ============ Test Schemas ============

class SimpleSchema(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    value: int


class NestedSchema(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: str
    items: List[Dict[str, Any]]


class StrictSchema(BaseModel):
    score: int = Field(ge=0, le=100)
    comment: str


# ============ Fixtures ============

@pytest.fixture
def client():
    """Create OpenAIClient with mocked internals."""
    with patch.object(OpenAIClient, '__init__', lambda self: None):
        c = OpenAIClient()
        c.model = "gpt-4o-mini"
        c.cache_enabled = False
        return c


# ============ Tests: Happy Path ============

@pytest.mark.asyncio
async def test_valid_data_passes_validation(client):
    """Valid LLM response → schema validates → returns Pydantic model."""
    client.generate_json = AsyncMock(return_value={"name": "test", "value": 42})

    result = await client.generate_validated_json(
        prompt="test prompt",
        response_schema=SimpleSchema
    )

    assert isinstance(result, SimpleSchema)
    assert result.name == "test"
    assert result.value == 42


@pytest.mark.asyncio
async def test_extra_fields_preserved(client):
    """LLM returns extra fields → extra='allow' keeps them."""
    client.generate_json = AsyncMock(
        return_value={"name": "test", "value": 42, "bonus": "extra_data"}
    )

    result = await client.generate_validated_json(
        prompt="test prompt",
        response_schema=SimpleSchema
    )

    assert result.name == "test"
    assert result.bonus == "extra_data"


# ============ Tests: Retry Logic ============

@pytest.mark.asyncio
async def test_retry_on_validation_error_then_success(client):
    """First call invalid → retry → second call valid → returns model."""
    client.generate_json = AsyncMock(side_effect=[
        {"name": "test"},              # Missing 'value' → ValidationError
        {"name": "test", "value": 42}  # Valid on retry
    ])

    result = await client.generate_validated_json(
        prompt="test prompt",
        response_schema=SimpleSchema,
        max_retries=1
    )

    assert isinstance(result, SimpleSchema)
    assert result.value == 42
    assert client.generate_json.call_count == 2


@pytest.mark.asyncio
async def test_retry_prompt_contains_error_and_schema(client):
    """On retry, the prompt includes error details and expected schema."""
    prompts_received = []

    async def capture_prompt(prompt, **kwargs):
        prompts_received.append(prompt)
        if len(prompts_received) == 1:
            return {"name": "test"}  # Invalid — missing 'value'
        return {"name": "test", "value": 42}  # Valid

    client.generate_json = capture_prompt

    await client.generate_validated_json(
        prompt="original prompt",
        response_schema=SimpleSchema,
        max_retries=1
    )

    assert len(prompts_received) == 2
    retry_prompt = prompts_received[1]
    assert "original prompt" in retry_prompt
    assert "validation errors" in retry_prompt.lower()
    assert "value" in retry_prompt  # Field name in error


# ============ Tests: Failure After Max Retries ============

@pytest.mark.asyncio
async def test_raises_after_max_retries_exhausted(client):
    """All attempts invalid → raises OpenAIClientError."""
    client.generate_json = AsyncMock(
        return_value={"name": "test"}  # Always missing 'value'
    )

    with pytest.raises(OpenAIClientError, match="validation failed"):
        await client.generate_validated_json(
            prompt="test prompt",
            response_schema=SimpleSchema,
            max_retries=1
        )

    assert client.generate_json.call_count == 2  # Original + 1 retry


@pytest.mark.asyncio
async def test_zero_retries_fails_immediately(client):
    """max_retries=0 → no retry, immediate failure."""
    client.generate_json = AsyncMock(
        return_value={"name": "test"}  # Missing 'value'
    )

    with pytest.raises(OpenAIClientError, match="validation failed"):
        await client.generate_validated_json(
            prompt="test prompt",
            response_schema=SimpleSchema,
            max_retries=0
        )

    assert client.generate_json.call_count == 1


# ============ Tests: Error Propagation ============

@pytest.mark.asyncio
async def test_api_error_propagates_directly(client):
    """OpenAIClientError from generate_json() is NOT retried — propagates."""
    client.generate_json = AsyncMock(
        side_effect=OpenAIClientError("API quota exceeded")
    )

    with pytest.raises(OpenAIClientError, match="API quota exceeded"):
        await client.generate_validated_json(
            prompt="test prompt",
            response_schema=SimpleSchema
        )

    # Only 1 call — no retry on API errors
    assert client.generate_json.call_count == 1


# ============ Tests: Error Formatting ============

def test_format_validation_error_readable(client):
    """_format_validation_error produces human-readable string."""
    from pydantic import ValidationError

    try:
        SimpleSchema.model_validate({"name": "test"})  # Missing 'value'
    except ValidationError as e:
        formatted = client._format_validation_error(e)

    assert "value" in formatted
    assert ":" in formatted  # "field: message" format


def test_format_nested_validation_error(client):
    """Nested field errors include full path."""
    from pydantic import ValidationError

    try:
        StrictSchema.model_validate({"score": 200, "comment": "ok"})  # score > 100
    except ValidationError as e:
        formatted = client._format_validation_error(e)

    assert "score" in formatted
