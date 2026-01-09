"""
Tests for workflow API endpoints.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.video import Video, WorkflowStatus, StepType
from app.models.workflow_step import WorkflowStep
from tests.fixtures.mock_responses import (
    MOCK_STORY,
    MOCK_DESCRIPTION,
    MOCK_PROMPT,
    MOCK_SCENARIO,
    MOCK_VALIDATION_PASS,
    MOCK_VALIDATION_FAIL,
    MOCK_IMAGE_URL,
    MOCK_VIDEO_URL,
    MOCK_TASK_ID,
    MOCK_AUDIO_VARIANTS
)


class TestGenerateStory:
    """Tests for POST /api/workflow/generate-story"""

    def test_generate_story_unauthorized(self, client: TestClient, test_video: Video):
        """Should return 401 without auth token."""
        response = client.post(
            "/api/workflow/generate-story",
            json={"video_id": test_video.id, "duration": 5}
        )
        assert response.status_code == 401

    def test_generate_story_video_not_found(
        self, client: TestClient, auth_headers: dict
    ):
        """Should return 404 for non-existent video."""
        response = client.post(
            "/api/workflow/generate-story",
            json={"video_id": 99999, "duration": 5},
            headers=auth_headers
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("app.services.openai_service.openai_service.generate_story")
    @patch("app.services.openai_service.openai_service.validate_content")
    def test_generate_story_success(
        self,
        mock_validate: MagicMock,
        mock_generate: MagicMock,
        client: TestClient,
        auth_headers: dict,
        test_video: Video,
        db: Session
    ):
        """Should generate story and return validation result."""
        mock_generate.return_value = MOCK_STORY
        mock_validate.return_value = MOCK_VALIDATION_PASS

        response = client.post(
            "/api/workflow/generate-story",
            json={
                "video_id": test_video.id,
                "theme": "cats",
                "target_audience": "pet lovers",
                "mood": "funny",
                "duration": 5,
                "platforms": ["instagram", "tiktok"]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "step_id" in data
        assert "content" in data
        assert "validation" in data
        assert data["content"]["concept"] == MOCK_STORY["concept"]
        assert data["validation"]["status"] == "pass"

        # Verify DB state
        db.refresh(test_video)
        assert test_video.story_data == MOCK_STORY
        assert test_video.current_step == StepType.STORY

    @patch("app.services.openai_service.openai_service.generate_story")
    @patch("app.services.openai_service.openai_service.validate_content")
    def test_generate_story_validation_fail(
        self,
        mock_validate: MagicMock,
        mock_generate: MagicMock,
        client: TestClient,
        auth_headers: dict,
        test_video: Video,
        db: Session
    ):
        """Should handle validation failure."""
        mock_generate.return_value = MOCK_STORY
        mock_validate.return_value = MOCK_VALIDATION_FAIL

        response = client.post(
            "/api/workflow/generate-story",
            json={"video_id": test_video.id, "duration": 5},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["validation"]["status"] == "fail"

        # Check step status
        step = db.query(WorkflowStep).filter(
            WorkflowStep.id == data["step_id"]
        ).first()
        assert step.validation_attempts == 1


class TestGenerateDescription:
    """Tests for POST /api/workflow/generate-description"""

    @patch("app.services.openai_service.openai_service.generate_description")
    @patch("app.services.openai_service.openai_service.validate_content")
    def test_generate_description_success(
        self,
        mock_validate: MagicMock,
        mock_generate: MagicMock,
        client: TestClient,
        auth_headers: dict,
        test_video_with_story: Video,
        db: Session
    ):
        """Should generate description from story data."""
        mock_generate.return_value = MOCK_DESCRIPTION
        mock_validate.return_value = MOCK_VALIDATION_PASS

        response = client.post(
            "/api/workflow/generate-description",
            json={
                "video_id": test_video_with_story.id,
                "story_data": MOCK_STORY
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"]["subject"]["type"] == "animal"
        assert data["validation"]["status"] == "pass"


class TestGeneratePrompt:
    """Tests for POST /api/workflow/generate-prompt"""

    @patch("app.services.openai_service.openai_service.generate_image_prompt")
    @patch("app.services.openai_service.openai_service.validate_content")
    def test_generate_prompt_success(
        self,
        mock_validate: MagicMock,
        mock_generate: MagicMock,
        client: TestClient,
        auth_headers: dict,
        test_video: Video
    ):
        """Should generate image prompt from description."""
        mock_generate.return_value = MOCK_PROMPT
        mock_validate.return_value = MOCK_VALIDATION_PASS

        response = client.post(
            "/api/workflow/generate-prompt",
            json={
                "video_id": test_video.id,
                "description_data": MOCK_DESCRIPTION
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "main_prompt" in data["content"]
        assert "negative_prompt" in data["content"]


class TestGenerateImage:
    """Tests for POST /api/workflow/generate-image"""

    @patch("app.services.kling_service.kling_service.generate_image")
    def test_generate_image_success(
        self,
        mock_generate: MagicMock,
        client: TestClient,
        auth_headers: dict,
        test_video: Video,
        db: Session
    ):
        """Should generate image and return URL."""
        mock_generate.return_value = MOCK_IMAGE_URL

        response = client.post(
            "/api/workflow/generate-image",
            json={
                "video_id": test_video.id,
                "prompt": "A cute cat on the beach",
                "aspect_ratio": "9:16"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"]["image_url"] == MOCK_IMAGE_URL
        assert data["status"] == "completed"

        # Verify DB
        db.refresh(test_video)
        assert test_video.image_url == MOCK_IMAGE_URL

    def test_generate_image_missing_prompt(
        self,
        client: TestClient,
        auth_headers: dict,
        test_video: Video
    ):
        """Should return error if no prompt provided."""
        response = client.post(
            "/api/workflow/generate-image",
            json={"video_id": test_video.id},
            headers=auth_headers
        )

        # Can be 422 (Pydantic) or 500 (endpoint logic if prompt is optional but used)
        assert response.status_code in (422, 500)


class TestGenerateVideo:
    """Tests for POST /api/workflow/generate-video"""

    @patch("app.services.kling_service.kling_service.generate_video")
    def test_generate_video_success(
        self,
        mock_generate: MagicMock,
        client: TestClient,
        auth_headers: dict,
        test_video: Video,
        db: Session
    ):
        """Should generate video and return URL with task_id."""
        mock_generate.return_value = (MOCK_VIDEO_URL, MOCK_TASK_ID)

        response = client.post(
            "/api/workflow/generate-video",
            json={
                "video_id": test_video.id,
                "image_url": MOCK_IMAGE_URL,
                "scenario_data": MOCK_SCENARIO,
                "duration": 5
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"]["video_url"] == MOCK_VIDEO_URL
        assert data["content"]["task_id"] == MOCK_TASK_ID

        # Verify DB
        db.refresh(test_video)
        assert test_video.video_url == MOCK_VIDEO_URL
        assert test_video.video_task_id == MOCK_TASK_ID


class TestGenerateAudio:
    """Tests for POST /api/workflow/generate-audio"""

    @patch("app.services.kling_service.kling_service.add_audio_to_video")
    def test_generate_audio_success(
        self,
        mock_generate: MagicMock,
        client: TestClient,
        auth_headers: dict,
        test_video: Video,
        db: Session
    ):
        """Should generate 4 audio variants."""
        # Set video_task_id first
        test_video.video_task_id = MOCK_TASK_ID
        db.commit()

        mock_generate.return_value = MOCK_AUDIO_VARIANTS

        response = client.post(
            "/api/workflow/generate-audio",
            json={"video_id": test_video.id},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["content"]["audio_variants"]) == 4

    def test_generate_audio_no_task_id(
        self,
        client: TestClient,
        auth_headers: dict,
        test_video: Video
    ):
        """Should return 400 if no video_task_id."""
        response = client.post(
            "/api/workflow/generate-audio",
            json={"video_id": test_video.id},
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "task_id" in response.json()["detail"].lower()


class TestSelectAudioVariant:
    """Tests for POST /api/workflow/select-audio-variant"""

    @patch("app.services.openai_service.openai_service.adapt_for_platforms")
    def test_select_audio_variant_success(
        self,
        mock_adapt: MagicMock,
        client: TestClient,
        auth_headers: dict,
        test_video: Video,
        db: Session
    ):
        """Should select audio variant and trigger adaptation."""
        from tests.fixtures.mock_responses import MOCK_ADAPTATION

        # Setup video with audio variants
        test_video.audio_variants = MOCK_AUDIO_VARIANTS
        test_video.story_data = MOCK_STORY
        test_video.scenario_data = MOCK_SCENARIO
        db.commit()

        mock_adapt.return_value = MOCK_ADAPTATION

        response = client.post(
            "/api/workflow/select-audio-variant",
            json={"video_id": test_video.id, "variant_index": 1},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["video_with_audio_url"] == MOCK_AUDIO_VARIANTS[1]
        assert "adaptation" in data

    def test_select_audio_invalid_index(
        self,
        client: TestClient,
        auth_headers: dict,
        test_video: Video,
        db: Session
    ):
        """Should return error for invalid variant index."""
        test_video.audio_variants = MOCK_AUDIO_VARIANTS
        db.commit()

        response = client.post(
            "/api/workflow/select-audio-variant",
            json={"video_id": test_video.id, "variant_index": 10},
            headers=auth_headers
        )

        # Can be 400 (business logic) or 422 (Pydantic validation)
        assert response.status_code in (400, 422)


class TestApproveStep:
    """Tests for POST /api/workflow/approve-step"""

    @patch("app.services.openai_service.openai_service.generate_description")
    @patch("app.services.openai_service.openai_service.validate_content")
    def test_approve_step_success(
        self,
        mock_validate: MagicMock,
        mock_generate: MagicMock,
        client: TestClient,
        auth_headers: dict,
        test_step_awaiting_approval: WorkflowStep,
        db: Session
    ):
        """Should approve step and transition to APPROVED."""
        # Mock auto-generation of next step (DESCRIPTION after STORY)
        mock_generate.return_value = MOCK_DESCRIPTION
        mock_validate.return_value = MOCK_VALIDATION_PASS

        response = client.post(
            "/api/workflow/approve-step",
            json={"step_id": test_step_awaiting_approval.id, "approved": True},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"

        # Verify DB
        db.refresh(test_step_awaiting_approval)
        assert test_step_awaiting_approval.status == WorkflowStatus.APPROVED
        assert test_step_awaiting_approval.user_approved is True

    def test_reject_step_with_regenerate(
        self,
        client: TestClient,
        auth_headers: dict,
        test_step_awaiting_approval: WorkflowStep,
        db: Session
    ):
        """Should reject step and set to PENDING for regeneration."""
        response = client.post(
            "/api/workflow/approve-step",
            json={
                "step_id": test_step_awaiting_approval.id,
                "approved": False,
                "feedback": "Need more drama",
                "regenerate": True
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"

        # Verify DB
        db.refresh(test_step_awaiting_approval)
        assert test_step_awaiting_approval.status == WorkflowStatus.PENDING
        assert test_step_awaiting_approval.user_feedback == "Need more drama"

    def test_reject_step_without_regenerate(
        self,
        client: TestClient,
        auth_headers: dict,
        test_step_awaiting_approval: WorkflowStep,
        db: Session
    ):
        """Should reject step and set to REJECTED."""
        response = client.post(
            "/api/workflow/approve-step",
            json={
                "step_id": test_step_awaiting_approval.id,
                "approved": False,
                "regenerate": False
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

    def test_approve_step_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Should return 404 for non-existent step."""
        response = client.post(
            "/api/workflow/approve-step",
            json={"step_id": 99999, "approved": True},
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_approve_already_approved(
        self,
        client: TestClient,
        auth_headers: dict,
        test_step_awaiting_approval: WorkflowStep,
        db: Session
    ):
        """Should handle double approval gracefully."""
        # First approval
        test_step_awaiting_approval.status = WorkflowStatus.APPROVED
        db.commit()

        response = client.post(
            "/api/workflow/approve-step",
            json={"step_id": test_step_awaiting_approval.id, "approved": True},
            headers=auth_headers
        )

        assert response.status_code == 200
        assert "already approved" in response.json()["message"].lower()


class TestAutoGenerateToVideo:
    """Tests for POST /api/workflow/auto-generate-to-video"""

    @patch("app.services.openai_service.openai_service.generate_story_from_template")
    @patch("app.services.openai_service.openai_service.generate_description")
    @patch("app.services.openai_service.openai_service.generate_image_prompt")
    @patch("app.services.openai_service.openai_service.generate_scenario")
    @patch("app.services.kling_service.kling_service.generate_image")
    @patch("app.services.kling_service.kling_service.generate_video")
    @patch("app.services.kling_service.kling_service.add_audio_to_video")
    def test_auto_generate_success(
        self,
        mock_audio: MagicMock,
        mock_video: MagicMock,
        mock_image: MagicMock,
        mock_scenario: MagicMock,
        mock_prompt: MagicMock,
        mock_description: MagicMock,
        mock_story: MagicMock,
        client: TestClient,
        auth_headers: dict,
        test_video: Video,
        db: Session
    ):
        """Should run full auto-generation pipeline."""
        mock_story.return_value = MOCK_STORY
        mock_description.return_value = MOCK_DESCRIPTION
        mock_prompt.return_value = MOCK_PROMPT
        mock_scenario.return_value = MOCK_SCENARIO
        mock_image.return_value = MOCK_IMAGE_URL
        mock_video.return_value = (MOCK_VIDEO_URL, MOCK_TASK_ID)
        mock_audio.return_value = MOCK_AUDIO_VARIANTS

        response = client.post(
            "/api/workflow/auto-generate-to-video",
            json={"video_id": test_video.id},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["steps_completed"] == 7
        assert len(data["audio_variants"]) == 4
        assert data["next_action"] == "select_audio_variant"

        # Verify all services were called
        mock_story.assert_called_once()
        mock_description.assert_called_once()
        mock_prompt.assert_called_once()
        mock_image.assert_called_once()
        mock_scenario.assert_called_once()
        mock_video.assert_called_once()
        mock_audio.assert_called_once()


class TestAccessControl:
    """Tests for video access control."""

    def test_cannot_access_other_workspace_video(
        self,
        client: TestClient,
        db: Session,
        test_user: "User"
    ):
        """Should deny access to video in different workspace."""
        from app.models.user import User, Workspace, WorkspaceMember
        from app.core.security import hash_password, create_access_token

        # Create another user with their own workspace
        other_user = User(
            email="other@example.com",
            hashed_password=hash_password("pass123"),
            is_active=True
        )
        db.add(other_user)
        db.commit()

        other_workspace = Workspace(name="Other Workspace", owner_id=other_user.id)
        db.add(other_workspace)
        db.commit()

        other_member = WorkspaceMember(
            user_id=other_user.id,
            workspace_id=other_workspace.id,
            role="owner"
        )
        db.add(other_member)
        db.commit()

        # Create project and video in other workspace
        other_project = Project(
            name="Other Project",
            workspace_id=other_workspace.id,
            story_template="test",
            platforms=["instagram"],
            duration=5
        )
        db.add(other_project)
        db.commit()

        other_video = Video(
            project_id=other_project.id,
            title="Other Video"
        )
        db.add(other_video)
        db.commit()

        # Try to access with test_user
        token = create_access_token(data={"user_id": test_user.id, "email": test_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/workflow/generate-story",
            json={"video_id": other_video.id, "duration": 5},
            headers=headers
        )

        assert response.status_code == 403


# Import at end to avoid circular imports
from app.models.project import Project
