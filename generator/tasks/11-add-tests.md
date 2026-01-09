# Task 11: Добавление тестов

**Приоритет:** P0 (критический)
**Оценка:** 3 дня
**Зависимости:** Нет

## Проблема

Полное отсутствие тестов в проекте.

```bash
$ ls generator/backend/tests/
# пусто
```

## Цель

Создать базовый тестовый фреймворк и покрыть критический путь.

## Целевое покрытие

| Компонент | Цель |
|-----------|------|
| Workflow endpoints | 80% |
| AI services (mocked) | 70% |
| Models | 60% |
| Auth | 80% |

## Структура тестов

```
backend/tests/
├── conftest.py              # Fixtures, test DB
├── test_auth.py             # Auth endpoints
├── test_projects.py         # Projects CRUD
├── test_videos.py           # Videos CRUD
├── test_workflow.py         # Workflow endpoints
├── test_workflow_steps.py   # Individual step logic
├── test_services/
│   ├── test_openai_service.py
│   ├── test_kling_service.py
│   └── test_piapi_client.py
├── test_models/
│   ├── test_video.py
│   └── test_workflow_step.py
└── fixtures/
    ├── mock_responses.py    # Mock AI responses
    └── sample_data.py       # Test data
```

## Детальный план

### Phase 1: Инфраструктура (2-3 часа)

**Файл:** `backend/tests/conftest.py`

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.db.base import Base, get_db
from app.models.user import User
from app.core.security import create_access_token

# Test database
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    """Create fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    """Test client with overridden DB"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db):
    """Create test user"""
    from app.core.security import get_password_hash
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user):
    """Auth headers for authenticated requests"""
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_workspace(db, test_user):
    """Create test workspace"""
    from app.models.user import Workspace, WorkspaceMember
    workspace = Workspace(name="Test Workspace")
    db.add(workspace)
    db.commit()

    member = WorkspaceMember(
        user_id=test_user.id,
        workspace_id=workspace.id,
        role="owner"
    )
    db.add(member)
    db.commit()
    db.refresh(workspace)
    return workspace

@pytest.fixture
def test_project(db, test_workspace):
    """Create test project"""
    from app.models.project import Project
    project = Project(
        name="Test Project",
        workspace_id=test_workspace.id,
        story_template="Test story about {animal} in {location}",
        platforms=["instagram", "tiktok"],
        duration=5
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@pytest.fixture
def test_video(db, test_project):
    """Create test video"""
    from app.models.video import Video, WorkflowMode
    video = Video(
        project_id=test_project.id,
        title="Test Video",
        workflow_mode=WorkflowMode.MANUAL,
        content_variables={"animal": "cat", "location": "beach"}
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video
```

**Файл:** `backend/tests/fixtures/mock_responses.py`

```python
"""Mock responses for AI services"""

MOCK_STORY = {
    "concept": "A cute cat playing on a sunny beach",
    "hook": "Watch what happens when this cat sees the ocean",
    "hook_type": "visual",
    "climax": "The cat hilariously runs away from a small wave",
    "tone": "comedic",
    "pacing": "fast",
    "emotional_trigger": "laughter",
    "duration": 5
}

MOCK_DESCRIPTION = {
    "subject": {"type": "animal", "name": "Orange tabby cat"},
    "setting": {"location": "Tropical beach", "time": "Golden hour"},
    "action": "Playfully pawing at incoming waves",
    "composition": "Medium shot, cat centered",
    "lighting": "Warm sunset light",
    "mood": "Playful and cheerful"
}

MOCK_PROMPT = {
    "main_prompt": "Orange tabby cat on tropical beach at golden hour, playful expression",
    "negative_prompt": "blurry, dark, scary",
    "style_suffix": "photorealistic, 8k, detailed fur"
}

MOCK_VALIDATION_PASS = {
    "status": "pass",
    "score": 85,
    "criteria_results": {},
    "warnings": [],
    "errors": [],
    "recommendations": []
}
```

### Phase 2: Тесты Workflow (4-6 часов)

**Файл:** `backend/tests/test_workflow.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from app.models.video import WorkflowStatus, StepType

class TestGenerateStory:

    @patch("app.services.openai_service.openai_service.generate_story")
    async def test_generate_story_success(
        self, mock_generate, client, auth_headers, test_video
    ):
        from tests.fixtures.mock_responses import MOCK_STORY, MOCK_VALIDATION_PASS
        mock_generate.return_value = MOCK_STORY

        with patch("app.services.openai_service.openai_service.validate_content") as mock_validate:
            mock_validate.return_value = MOCK_VALIDATION_PASS

            response = client.post(
                "/api/workflow/generate-story",
                json={
                    "video_id": test_video.id,
                    "theme": "cats",
                    "duration": 5
                },
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert "step_id" in data
        assert data["content"]["concept"] == MOCK_STORY["concept"]
        assert data["validation"]["status"] == "pass"

    async def test_generate_story_video_not_found(self, client, auth_headers):
        response = client.post(
            "/api/workflow/generate-story",
            json={"video_id": 99999, "duration": 5},
            headers=auth_headers
        )
        assert response.status_code == 404

    async def test_generate_story_unauthorized(self, client, test_video):
        response = client.post(
            "/api/workflow/generate-story",
            json={"video_id": test_video.id, "duration": 5}
        )
        assert response.status_code == 401


class TestApproveStep:

    async def test_approve_step_success(self, client, auth_headers, db, test_video):
        from app.models.workflow_step import WorkflowStep

        # Create a step in AWAITING_APPROVAL status
        step = WorkflowStep(
            video_id=test_video.id,
            step_type=StepType.STORY,
            status=WorkflowStatus.AWAITING_APPROVAL,
            content={"concept": "test"}
        )
        db.add(step)
        db.commit()

        response = client.post(
            "/api/workflow/approve-step",
            json={"step_id": step.id, "approved": True},
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["status"] == "approved"

    async def test_reject_step_with_feedback(self, client, auth_headers, db, test_video):
        from app.models.workflow_step import WorkflowStep

        step = WorkflowStep(
            video_id=test_video.id,
            step_type=StepType.STORY,
            status=WorkflowStatus.AWAITING_APPROVAL,
            content={"concept": "test"}
        )
        db.add(step)
        db.commit()

        response = client.post(
            "/api/workflow/approve-step",
            json={
                "step_id": step.id,
                "approved": False,
                "feedback": "Need more drama",
                "regenerate": True
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["status"] == "pending"


class TestAutoGenerate:

    @patch("app.services.openai_service.openai_service")
    @patch("app.services.kling_service.kling_service")
    async def test_auto_generate_to_video(
        self, mock_kling, mock_openai, client, auth_headers, test_video
    ):
        from tests.fixtures.mock_responses import *

        # Mock all AI calls
        mock_openai.generate_story_from_template = AsyncMock(return_value=MOCK_STORY)
        mock_openai.generate_description = AsyncMock(return_value=MOCK_DESCRIPTION)
        mock_openai.generate_image_prompt = AsyncMock(return_value=MOCK_PROMPT)
        mock_openai.generate_scenario = AsyncMock(return_value={})
        mock_kling.generate_image = AsyncMock(return_value="https://example.com/image.jpg")
        mock_kling.generate_video = AsyncMock(return_value=("https://example.com/video.mp4", "task123"))
        mock_kling.add_audio_to_video = AsyncMock(return_value=["url1", "url2", "url3", "url4"])

        response = client.post(
            "/api/workflow/auto-generate-to-video",
            json={"video_id": test_video.id},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["steps_completed"] == 7
        assert len(data["audio_variants"]) == 4
```

### Phase 3: Тесты Services (3-4 часа)

**Файл:** `backend/tests/test_services/test_openai_service.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from app.services.openai_service import OpenAIService

class TestOpenAIService:

    @pytest.fixture
    def service(self):
        return OpenAIService()

    @patch("app.services.piapi_client.piapi_client.generate_json")
    async def test_generate_story(self, mock_generate, service):
        mock_generate.return_value = {
            "concept": "Test concept",
            "hook": "Test hook",
            "hook_type": "visual",
            "climax": "Test climax",
            "tone": "comedic",
            "pacing": "fast",
            "emotional_trigger": "laughter",
            "duration": 5
        }

        result = await service.generate_story(
            theme="cats",
            target_audience="young adults",
            mood="funny",
            duration=5
        )

        assert result["concept"] == "Test concept"
        assert result["hook_type"] in ["visual", "text", "audio"]
        mock_generate.assert_called_once()

    async def test_generate_story_mock_mode(self, service):
        service.mock_mode = True

        result = await service.generate_story(theme="test", duration=5)

        assert "concept" in result
        assert "hook" in result

    @patch("app.services.piapi_client.piapi_client.generate_json")
    async def test_validate_content_pass(self, mock_generate, service):
        mock_generate.return_value = {
            "status": "pass",
            "score": 90,
            "criteria_results": {},
            "warnings": [],
            "errors": [],
            "recommendations": []
        }

        result = await service.validate_content(
            content={"concept": "test"},
            step_type="story"
        )

        assert result["status"] == "pass"
        assert result["score"] >= 0
```

**Файл:** `backend/tests/test_services/test_piapi_client.py`

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.services.piapi_client import PiAPIClient, PiAPIError, RateLimitError

class TestPiAPIClient:

    @pytest.fixture
    def client(self):
        return PiAPIClient()

    @patch("httpx.AsyncClient.post")
    async def test_chat_completion_success(self, mock_post, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"test": "data"}'}}]
        }
        mock_post.return_value = mock_response

        result = await client.chat_completion(
            messages=[{"role": "user", "content": "test"}]
        )

        assert "choices" in result

    @patch("httpx.AsyncClient.post")
    async def test_rate_limit_retry(self, mock_post, client):
        # First call: rate limit
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "1"}
        rate_limit_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "rate limit", request=MagicMock(), response=rate_limit_response
        )

        # Second call: success
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "success"}

        mock_post.side_effect = [rate_limit_response, success_response]

        # Should retry and succeed
        # (Note: actual test would need async context)
```

### Phase 4: Тесты Models (2-3 часа)

**Файл:** `backend/tests/test_models/test_workflow_step.py`

```python
import pytest
from app.models.workflow_step import WorkflowStep, WorkflowStatus, StepType
from app.models.video import Video

class TestWorkflowStep:

    def test_create_step(self, db, test_video):
        step = WorkflowStep(
            video_id=test_video.id,
            step_type=StepType.STORY,
            status=WorkflowStatus.PENDING
        )
        db.add(step)
        db.commit()

        assert step.id is not None
        assert step.status == WorkflowStatus.PENDING

    def test_step_status_transitions(self, db, test_video):
        step = WorkflowStep(
            video_id=test_video.id,
            step_type=StepType.STORY,
            status=WorkflowStatus.PENDING
        )
        db.add(step)
        db.commit()

        # Valid transition
        step.status = WorkflowStatus.IN_PROGRESS
        db.commit()
        assert step.status == WorkflowStatus.IN_PROGRESS

        # Can transition to VALIDATING
        step.status = WorkflowStatus.VALIDATING
        db.commit()
        assert step.status == WorkflowStatus.VALIDATING

    def test_validation_attempts_increment(self, db, test_video):
        step = WorkflowStep(
            video_id=test_video.id,
            step_type=StepType.STORY,
            status=WorkflowStatus.VALIDATING
        )
        db.add(step)
        db.commit()

        assert step.validation_attempts == 0

        step.validation_attempts += 1
        db.commit()

        assert step.validation_attempts == 1
```

### Phase 5: CI/CD Integration (1-2 часа)

**Файл:** `backend/pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = -v --tb=short --strict-markers
markers =
    slow: marks tests as slow
    integration: marks tests requiring external services
```

**Файл:** `backend/requirements-dev.txt`

```
pytest==8.0.0
pytest-asyncio==0.23.0
pytest-cov==4.1.0
httpx==0.26.0
pytest-mock==3.12.0
```

## Команды запуска

```bash
# Запуск всех тестов
cd backend
pytest

# С покрытием
pytest --cov=app --cov-report=html

# Только workflow тесты
pytest tests/test_workflow.py -v

# Быстрые тесты (без slow)
pytest -m "not slow"
```

## Чеклист

- [ ] Создать `tests/conftest.py` с fixtures
- [ ] Создать `tests/fixtures/mock_responses.py`
- [ ] Написать тесты для workflow endpoints
- [ ] Написать тесты для approve_step
- [ ] Написать тесты для auto_generate
- [ ] Написать тесты для OpenAI service
- [ ] Написать тесты для PiAPI client
- [ ] Написать тесты для моделей
- [ ] Добавить `pytest.ini`
- [ ] Добавить `requirements-dev.txt`
- [ ] Достичь 70%+ покрытия критического пути

## Метрики успеха

| Метрика | До | После |
|---------|-----|-------|
| Тестов | 0 | 30+ |
| Покрытие workflow | 0% | 80% |
| Покрытие services | 0% | 70% |
| CI время | N/A | <2 мин |

---

**Статус:** Готова к выполнению
**Ответственный:** TBD
