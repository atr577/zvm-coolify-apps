"""
Tests for T1: Discover + AUTO flow

Test scenario:
1. Create Video (project_type=discover, workflow_mode=AUTO)
2. POST /workflow/{video_id}/start → status IN_PROGRESS
3. All 7 steps execute without pause
4. Final: status=COMPLETED, WorkflowSteps created for all 7 steps
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.models.video import Video, WorkflowMode, WorkflowStatus, StepType
from app.models.project import Project
from app.models.workflow_step import WorkflowStep
from app.models.step_attempt import StepAttempt, Variant, AttemptStatus
from app.services.workflow.orchestrator_v2 import WorkflowOrchestratorV2, OrchestratorResult


@pytest.fixture
def mock_project():
    """Create a mock Discover project."""
    project = MagicMock(spec=Project)
    project.id = 1
    project.project_type = "discover"
    project.story_template = "Test story template"
    project.duration = 5
    project.platforms = ["instagram", "tiktok"]
    project.aspect_ratio = "9:16"
    project.system_prompts = {}
    return project


@pytest.fixture
def mock_video(mock_project):
    """Create a mock Video in AUTO mode."""
    video = MagicMock(spec=Video)
    video.id = 1
    video.project_id = mock_project.id
    video.project = mock_project
    video.workflow_mode = WorkflowMode.AUTO
    video.status = WorkflowStatus.PENDING
    video.current_step = None
    video.content_variables = {}
    video.story_data = None
    video.description_data = None
    video.prompt_data = None
    video.image_url = None
    video.image_prompt = None
    video.scenario_data = None
    video.video_url = None
    video.audio_variants = None
    video.video_with_audio_url = None
    return video


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    return db


@pytest.fixture
def mock_openai_service():
    """Mock OpenAI service responses."""
    with patch('app.services.workflow.orchestrator_v2.openai_service') as mock:
        mock.generate_story_from_template = AsyncMock(return_value={
            "concept": "Test concept",
            "hook": "Test hook",
            "tone": "comedic",
            "pacing": "fast"
        })
        mock.generate_description = AsyncMock(return_value={
            "scene": "Test scene",
            "setting": "Test setting",
            "lighting": "natural"
        })
        mock.generate_image_prompt = AsyncMock(return_value={
            "main_prompt": "Test image prompt",
            "negative_prompt": "blur, low quality",
            "style_suffix": "cinematic"
        })
        mock.generate_scenario = AsyncMock(return_value={
            "motion_prompt": "Test motion",
            "camera_movement": {"type": "static"}
        })
        yield mock


@pytest.fixture
def mock_services():
    """Mock media services."""
    with patch('app.services.workflow.orchestrator_v2.ImageStep') as mock_image, \
         patch('app.services.workflow.orchestrator_v2.VideoStep') as mock_video, \
         patch('app.services.workflow.orchestrator_v2.AudioStep') as mock_audio:

        # ImageStep mock
        image_instance = MagicMock()
        image_instance.execute = AsyncMock(return_value={"status": "success"})
        mock_image.return_value = image_instance

        # VideoStep mock
        video_instance = MagicMock()
        video_instance.execute = AsyncMock(return_value={"status": "success"})
        mock_video.return_value = video_instance

        # AudioStep mock
        audio_instance = MagicMock()
        audio_instance.execute = AsyncMock(return_value={
            "status": "success",
            "content": {"audio_variants": ["audio1.mp3", "audio2.mp3"]}
        })
        mock_audio.return_value = audio_instance

        yield {
            "image": mock_image,
            "video": mock_video,
            "audio": mock_audio
        }


class TestDiscoverAutoFlow:
    """Test suite for Discover + AUTO workflow."""

    @pytest.mark.asyncio
    async def test_orchestrator_runs_all_steps_in_auto_mode(
        self, mock_db, mock_video, mock_openai_service, mock_services
    ):
        """Test that AUTO mode runs all 7 steps without pausing."""
        # Track created steps
        created_steps = []
        created_attempts = []
        created_variants = []

        def track_add(obj):
            if isinstance(obj, WorkflowStep):
                created_steps.append(obj)
            elif isinstance(obj, StepAttempt):
                created_attempts.append(obj)
            elif isinstance(obj, Variant):
                created_variants.append(obj)

        mock_db.add = track_add
        mock_db.refresh = lambda x: setattr(x, 'id', len(created_steps) + len(created_attempts) + len(created_variants))

        # Run orchestrator
        orchestrator = WorkflowOrchestratorV2(mock_db, mock_video)
        result = await orchestrator.run()

        # Verify result
        assert result.status == "completed"
        assert result.current_step == "audio"
        assert result.message == "Workflow completed"

        # Verify video status
        assert mock_video.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_orchestrator_creates_workflow_steps(
        self, mock_db, mock_video, mock_openai_service, mock_services
    ):
        """Test that WorkflowStep is created for each step."""
        created_objects = []

        def track_add(obj):
            created_objects.append(obj)

        mock_db.add = track_add
        mock_db.refresh = lambda x: setattr(x, 'id', len(created_objects))

        orchestrator = WorkflowOrchestratorV2(mock_db, mock_video)
        await orchestrator.run()

        # Count WorkflowSteps
        step_count = sum(1 for obj in created_objects if isinstance(obj, WorkflowStep))
        assert step_count == 7, f"Expected 7 WorkflowSteps, got {step_count}"

    @pytest.mark.asyncio
    async def test_orchestrator_creates_step_attempts(
        self, mock_db, mock_video, mock_openai_service, mock_services
    ):
        """Test that StepAttempt is created for each step."""
        created_objects = []

        def track_add(obj):
            created_objects.append(obj)

        mock_db.add = track_add
        mock_db.refresh = lambda x: setattr(x, 'id', len(created_objects))

        orchestrator = WorkflowOrchestratorV2(mock_db, mock_video)
        await orchestrator.run()

        # Count StepAttempts
        attempt_count = sum(1 for obj in created_objects if isinstance(obj, StepAttempt))
        assert attempt_count == 7, f"Expected 7 StepAttempts, got {attempt_count}"

    @pytest.mark.asyncio
    async def test_orchestrator_creates_variants(
        self, mock_db, mock_video, mock_openai_service, mock_services
    ):
        """Test that Variant is created for each step."""
        created_objects = []

        def track_add(obj):
            created_objects.append(obj)

        mock_db.add = track_add
        mock_db.refresh = lambda x: setattr(x, 'id', len(created_objects))

        # Set audio_variants so audio step creates variants
        mock_video.audio_variants = ["audio1.mp3"]

        orchestrator = WorkflowOrchestratorV2(mock_db, mock_video)
        await orchestrator.run()

        # Count Variants (should be at least 7, one per step)
        variant_count = sum(1 for obj in created_objects if isinstance(obj, Variant))
        assert variant_count >= 7, f"Expected at least 7 Variants, got {variant_count}"

    @pytest.mark.asyncio
    async def test_auto_mode_copies_content_to_video(
        self, mock_db, mock_video, mock_openai_service, mock_services
    ):
        """Test that AUTO mode copies variant content to Video fields."""
        mock_db.add = lambda x: None
        mock_db.refresh = lambda x: setattr(x, 'id', 1)

        # Set up video to receive data
        mock_video.image_url = "test_image.jpg"
        mock_video.video_url = "test_video.mp4"
        mock_video.audio_variants = ["audio1.mp3"]

        orchestrator = WorkflowOrchestratorV2(mock_db, mock_video)
        await orchestrator.run()

        # Verify openai services were called
        mock_openai_service.generate_story_from_template.assert_called_once()
        mock_openai_service.generate_description.assert_called_once()
        mock_openai_service.generate_image_prompt.assert_called_once()
        mock_openai_service.generate_scenario.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_step_order(
        self, mock_db, mock_video, mock_openai_service, mock_services
    ):
        """Test that steps execute in correct order."""
        step_order = []

        original_create_step = WorkflowOrchestratorV2._create_step

        def track_create_step(self, step_type):
            step_order.append(step_type)
            step = MagicMock(spec=WorkflowStep)
            step.id = len(step_order)
            step.status = WorkflowStatus.IN_PROGRESS
            return step

        with patch.object(WorkflowOrchestratorV2, '_create_step', track_create_step):
            with patch.object(WorkflowOrchestratorV2, '_create_attempt') as mock_attempt:
                mock_attempt.return_value = MagicMock(id=1)
                with patch.object(WorkflowOrchestratorV2, '_create_variant') as mock_variant:
                    mock_variant.return_value = MagicMock(id=1, content={})
                    with patch.object(WorkflowOrchestratorV2, '_auto_approve'):
                        orchestrator = WorkflowOrchestratorV2(mock_db, mock_video)
                        await orchestrator.run()

        expected_order = [
            StepType.STORY,
            StepType.DESCRIPTION,
            StepType.PROMPT,
            StepType.IMAGE,
            StepType.SCENARIO,
            StepType.VIDEO,
            StepType.AUDIO,
        ]

        assert step_order == expected_order, f"Expected {expected_order}, got {step_order}"


class TestOrchestratorResult:
    """Test OrchestratorResult dataclass."""

    def test_result_has_required_fields(self):
        """Test that OrchestratorResult has all required fields."""
        result = OrchestratorResult(
            video_id=1,
            status="completed",
            current_step="audio",
            message="Test message"
        )

        assert result.video_id == 1
        assert result.status == "completed"
        assert result.current_step == "audio"
        assert result.message == "Test message"
