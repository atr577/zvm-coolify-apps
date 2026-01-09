"""
Tests for PiAPI client.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.piapi_client import PiAPIClient, PiAPIError, RateLimitError
from tests.fixtures.mock_responses import (
    MOCK_PIAPI_CHAT_RESPONSE,
    MOCK_PIAPI_TASK_CREATED,
    MOCK_PIAPI_TASK_COMPLETED,
    MOCK_PIAPI_TASK_PROCESSING,
    MOCK_TASK_ID,
    MOCK_VIDEO_URL
)


class TestPiAPIClient:
    """Tests for PiAPI client."""

    @pytest.fixture
    def client(self):
        """Create PiAPI client instance."""
        return PiAPIClient()

    def test_client_initialization(self, client: PiAPIClient):
        """Should initialize with correct settings."""
        assert client.llm_base_url is not None
        assert client.task_base_url is not None
        assert client.timeout is not None

    def test_get_llm_headers(self, client: PiAPIClient):
        """Should return correct LLM headers."""
        headers = client._get_llm_headers()

        assert "Authorization" in headers
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"].startswith("Bearer ")

    def test_get_task_headers(self, client: PiAPIClient):
        """Should return correct task headers."""
        headers = client._get_task_headers()

        assert "x-api-key" in headers
        assert headers["Content-Type"] == "application/json"

    def test_cache_key_generation(self, client: PiAPIClient):
        """Should generate consistent cache keys."""
        key1 = client._get_cache_key("POST", "/api/test", {"data": "test"})
        key2 = client._get_cache_key("POST", "/api/test", {"data": "test"})
        key3 = client._get_cache_key("POST", "/api/test", {"data": "different"})

        assert key1 == key2
        assert key1 != key3
        assert len(key1) == 16


class TestChatCompletion:
    """Tests for chat completion method."""

    @pytest.fixture
    def client(self):
        return PiAPIClient()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_chat_completion_success(
        self,
        mock_post: MagicMock,
        client: PiAPIClient
    ):
        """Should return chat completion response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_PIAPI_CHAT_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_post.return_value = mock_response

        result = await client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}]
        )

        assert "choices" in result
        assert len(result["choices"]) > 0

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_chat_completion_rate_limit(
        self,
        mock_post: MagicMock,
        client: PiAPIClient
    ):
        """Should handle rate limiting."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "1"}
        mock_response.text = "Rate limit exceeded"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "rate limit",
            request=MagicMock(),
            response=mock_response
        )

        mock_post.return_value = mock_response

        with pytest.raises(RateLimitError):
            await client.chat_completion(
                messages=[{"role": "user", "content": "Hello"}]
            )


class TestGenerateJson:
    """Tests for JSON generation method."""

    @pytest.fixture
    def client(self):
        return PiAPIClient()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_generate_json_success(
        self,
        mock_post: MagicMock,
        client: PiAPIClient
    ):
        """Should parse JSON from response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"key": "value", "number": 42}'
                }
            }]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = await client.generate_json(
            prompt="Generate JSON",
            system_prompt="You are a JSON generator"
        )

        assert result["key"] == "value"
        assert result["number"] == 42


class TestVideoGeneration:
    """Tests for video generation methods."""

    @pytest.fixture
    def client(self):
        return PiAPIClient()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    @patch("httpx.AsyncClient.get")
    async def test_create_video_task(
        self,
        mock_get: MagicMock,
        mock_post: MagicMock,
        client: PiAPIClient
    ):
        """Should create video task and return task_id."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_PIAPI_TASK_CREATED
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        task_id = await client.create_video_task(
            prompt="A cat on the beach",
            duration=5,
            aspect_ratio="9:16"
        )

        assert task_id == MOCK_TASK_ID

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_get_task_status(
        self,
        mock_get: MagicMock,
        client: PiAPIClient
    ):
        """Should get task status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_PIAPI_TASK_COMPLETED
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = await client.get_task_status(MOCK_TASK_ID)

        assert result["data"]["status"] == "completed"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_wait_for_video_completed(
        self,
        mock_get: MagicMock,
        client: PiAPIClient
    ):
        """Should return video URL when completed."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_PIAPI_TASK_COMPLETED
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        video_url = await client.wait_for_video(MOCK_TASK_ID)

        assert video_url == MOCK_VIDEO_URL

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_wait_for_video_timeout(
        self,
        mock_get: MagicMock,
        client: PiAPIClient
    ):
        """Should raise timeout if video not ready."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_PIAPI_TASK_PROCESSING
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with pytest.raises(TimeoutError):
            await client.wait_for_video(
                MOCK_TASK_ID,
                max_wait_time=1,
                poll_interval=0.5
            )


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def client(self):
        return PiAPIClient()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_http_error_retry(
        self,
        mock_post: MagicMock,
        client: PiAPIClient
    ):
        """Should retry on HTTP errors."""
        # First call fails, second succeeds
        fail_response = MagicMock()
        fail_response.status_code = 500
        fail_response.text = "Server error"
        fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error",
            request=MagicMock(),
            response=fail_response
        )

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = MOCK_PIAPI_CHAT_RESPONSE
        success_response.raise_for_status = MagicMock()

        mock_post.side_effect = [fail_response, success_response]

        # Should succeed on retry
        result = await client.chat_completion(
            messages=[{"role": "user", "content": "test"}]
        )

        assert "choices" in result
        assert mock_post.call_count == 2

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_video_generation_failed(
        self,
        mock_get: MagicMock,
        client: PiAPIClient
    ):
        """Should raise error when video generation fails."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "task_id": MOCK_TASK_ID,
                "status": "failed",
                "error": {"message": "Generation failed"}
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with pytest.raises(PiAPIError) as exc_info:
            await client.wait_for_video(MOCK_TASK_ID)

        assert "failed" in str(exc_info.value).lower()
