"""
Tests for Video and WorkflowStep models.
"""
import pytest
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.video import Video, WorkflowStatus, StepType, WorkflowMode, VideoMetrics, MetricsPeriod
from app.models.workflow_step import WorkflowStep
from app.models.validation_result import ValidationResult, ValidationStatus
from app.models.project import Project


class TestVideoModel:
    """Tests for Video model."""

    def test_create_video(self, db: Session, test_project: Project):
        """Should create video with default values."""
        video = Video(
            project_id=test_project.id,
            title="Test Video"
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        assert video.id is not None
        assert video.status == WorkflowStatus.PENDING
        assert video.current_step == StepType.STORY
        assert video.workflow_mode == WorkflowMode.AUTO

    def test_video_project_relationship(self, db: Session, test_video: Video):
        """Should access project through relationship."""
        assert test_video.project is not None
        assert test_video.project.name == "Test Project"

    def test_video_cascade_delete(self, db: Session, test_video: Video):
        """Should cascade delete workflow steps."""
        # Create steps
        step = WorkflowStep(
            video_id=test_video.id,
            step_type=StepType.STORY,
            status=WorkflowStatus.PENDING
        )
        db.add(step)
        db.commit()
        step_id = step.id

        # Delete video
        db.delete(test_video)
        db.commit()

        # Verify step is deleted
        assert db.query(WorkflowStep).get(step_id) is None


class TestWorkflowStepModel:
    """Tests for WorkflowStep model."""

    def test_create_step(self, db: Session, test_video: Video):
        """Should create workflow step."""
        step = WorkflowStep(
            video_id=test_video.id,
            step_type=StepType.STORY,
            status=WorkflowStatus.PENDING
        )
        db.add(step)
        db.commit()
        db.refresh(step)

        assert step.id is not None
        assert step.validation_attempts == 0
        assert step.max_validation_attempts == 3

    def test_step_content_json(self, db: Session, test_video: Video):
        """Should store and retrieve JSON content."""
        content = {
            "concept": "Test concept",
            "hook": "Test hook",
            "nested": {"key": "value"}
        }

        step = WorkflowStep(
            video_id=test_video.id,
            step_type=StepType.STORY,
            status=WorkflowStatus.COMPLETED,
            content=content
        )
        db.add(step)
        db.commit()
        db.refresh(step)

        assert step.content == content
        assert step.content["nested"]["key"] == "value"

    def test_step_status_transitions(self, db: Session, test_video: Video):
        """Should allow status transitions."""
        step = WorkflowStep(
            video_id=test_video.id,
            step_type=StepType.STORY,
            status=WorkflowStatus.PENDING
        )
        db.add(step)
        db.commit()

        # Transition through states
        step.status = WorkflowStatus.IN_PROGRESS
        db.commit()
        assert step.status == WorkflowStatus.IN_PROGRESS

        step.status = WorkflowStatus.VALIDATING
        db.commit()
        assert step.status == WorkflowStatus.VALIDATING

        step.status = WorkflowStatus.AWAITING_APPROVAL
        db.commit()
        assert step.status == WorkflowStatus.AWAITING_APPROVAL

        step.status = WorkflowStatus.APPROVED
        db.commit()
        assert step.status == WorkflowStatus.APPROVED

    def test_step_validation_attempts(self, db: Session, test_video: Video):
        """Should track validation attempts."""
        step = WorkflowStep(
            video_id=test_video.id,
            step_type=StepType.STORY,
            status=WorkflowStatus.VALIDATING
        )
        db.add(step)
        db.commit()

        step.validation_attempts = 1
        db.commit()
        assert step.validation_attempts == 1

        step.validation_attempts = 2
        db.commit()
        assert step.validation_attempts == 2

        # Check max attempts
        assert step.validation_attempts < step.max_validation_attempts


class TestValidationResultModel:
    """Tests for ValidationResult model."""

    def test_create_validation_result(self, db: Session, test_video: Video):
        """Should create validation result."""
        step = WorkflowStep(
            video_id=test_video.id,
            step_type=StepType.STORY,
            status=WorkflowStatus.VALIDATING
        )
        db.add(step)
        db.commit()

        validation = ValidationResult(
            step_id=step.id,
            status=ValidationStatus.PASS,
            score=85,
            criteria_results={"relevance": 90, "clarity": 80},
            warnings=["Minor issue"],
            recommendations=["Consider adding more detail"]
        )
        db.add(validation)
        db.commit()
        db.refresh(validation)

        assert validation.id is not None
        assert validation.score == 85
        assert validation.status == ValidationStatus.PASS
        assert len(validation.warnings) == 1

    def test_validation_relationship(self, db: Session, test_video: Video):
        """Should access step through relationship."""
        step = WorkflowStep(
            video_id=test_video.id,
            step_type=StepType.STORY,
            status=WorkflowStatus.VALIDATING
        )
        db.add(step)
        db.commit()

        validation = ValidationResult(
            step_id=step.id,
            status=ValidationStatus.PASS,
            score=85
        )
        db.add(validation)
        db.commit()
        db.refresh(step)

        assert len(step.validations) == 1
        assert step.validations[0].score == 85


class TestVideoMetricsModel:
    """Tests for VideoMetrics model."""

    def test_create_metrics(self, db: Session, test_video: Video):
        """Should create video metrics."""
        metrics = VideoMetrics(
            video_id=test_video.id,
            platform="instagram",
            period=MetricsPeriod.HOURS_24,
            views=1000,
            likes=100,
            comments=20,
            shares=5
        )
        db.add(metrics)
        db.commit()
        db.refresh(metrics)

        assert metrics.id is not None
        assert metrics.views == 1000
        assert metrics.platform == "instagram"

    def test_metrics_engagement_rate(self, db: Session, test_video: Video):
        """Should calculate engagement rate."""
        metrics = VideoMetrics(
            video_id=test_video.id,
            platform="tiktok",
            period=MetricsPeriod.DAYS_7,
            views=10000,
            likes=500,
            comments=100,
            shares=50,
            engagement_rate=650  # (500+100+50)/10000 * 10000
        )
        db.add(metrics)
        db.commit()

        assert metrics.engagement_rate == 650


class TestStepTypes:
    """Tests for StepType enum."""

    def test_all_step_types_exist(self):
        """Should have all required step types."""
        expected_types = [
            "story", "description", "prompt", "image",
            "scenario", "video", "audio", "adaptation", "publishing"
        ]

        for step_type in expected_types:
            assert hasattr(StepType, step_type.upper())

    def test_step_type_values(self):
        """Step type values should be lowercase strings."""
        assert StepType.STORY.value == "story"
        assert StepType.DESCRIPTION.value == "description"
        assert StepType.VIDEO.value == "video"


class TestWorkflowStatus:
    """Tests for WorkflowStatus enum."""

    def test_all_statuses_exist(self):
        """Should have all required statuses."""
        expected_statuses = [
            "pending", "in_progress", "validating", "awaiting_approval",
            "approved", "rejected", "completed", "failed", "validation_failed"
        ]

        for status in expected_statuses:
            assert hasattr(WorkflowStatus, status.upper())
