"""
Tests for scheduled publisher — slot deduplication logic.

All external calls (social platforms) are mocked.
No fal.ai / LLM calls happen.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.project import Project
from app.models.user import User, Workspace, WorkspaceMember
from app.models.publishing_config import PublishingConfig
from app.models.approved_generation import ApprovedGeneration
from app.models.template_generation import TemplateGeneration
from app.core.security import hash_password
from app.services.scheduled_publisher import (
    check_should_publish_now,
    scheduled_publish_job,
)


# --- In-memory DB ---

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestSession()
    yield session
    session.close()


class _non_closing:
    """Wrapper that prevents scheduled_publish_job from closing the test session."""
    def __init__(self, session):
        self._session = session

    def __getattr__(self, name):
        if name == "close":
            return lambda: None  # no-op
        return getattr(self._session, name)


def _create_project_with_config(db, *, days, preferred_times, timezone="UTC"):
    """Helper: create user, workspace, project, publishing config, return project."""
    user = User(
        email="test@test.com",
        hashed_password=hash_password("pass"),
        is_active=True,
        role="user",
    )
    db.add(user)
    db.flush()

    ws = Workspace(name="ws", owner_id=user.id)
    db.add(ws)
    db.flush()

    member = WorkspaceMember(user_id=user.id, workspace_id=ws.id, role="owner")
    db.add(member)
    db.flush()

    project = Project(
        name="Test Template",
        workspace_id=ws.id,
        user_id=user.id,
        project_type="template",
        platforms=["tiktok"],
        timezone=timezone,
        story_template="test",
        duration=5,
        aspect_ratio="9:16",
        audio_mode="auto",
    )
    db.add(project)
    db.flush()

    config = PublishingConfig(
        project_id=project.id,
        enabled=True,
        days=days,
        preferred_times=preferred_times,
    )
    db.add(config)
    db.flush()

    db.commit()
    db.refresh(project)
    return project


def _create_approved_item(db, project, position, *, video_with_audio="data/media/videos/test.mp4"):
    """Helper: create template_generation + approved_generation."""
    gen = TemplateGeneration(
        project_id=project.id,
        llm_model="gpt-4o-mini",
        image_model="test",
        video_model="test",
        video_url="https://example.com/video.mp4",
        video_with_audio_path=video_with_audio,
        status="completed",
    )
    db.add(gen)
    db.flush()

    item = ApprovedGeneration(
        project_id=project.id,
        template_generation_id=gen.id,
        position=position,
        status="approved",
        publishing_metadata={"tiktok": {"title": "test", "description": "test"}},
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ============================================================
# check_should_publish_now tests
# ============================================================


class TestCheckShouldPublishNow:
    """Test slot matching logic."""

    def test_returns_utc_datetime_when_slot_matches(self):
        """Should return slot UTC datetime, not bool."""
        now = datetime.utcnow()
        day_abbr = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][now.weekday()]
        time_str = now.strftime("%H:%M")

        config = PublishingConfig(
            enabled=True,
            days=[day_abbr],
            preferred_times=[time_str],
        )

        result = check_should_publish_now(config, "UTC")
        assert result is not None
        assert isinstance(result, datetime)

    def test_returns_none_when_wrong_day(self):
        """Should return None when today is not in config.days."""
        now = datetime.utcnow()
        # Pick a day that is NOT today
        today_idx = now.weekday()
        wrong_idx = (today_idx + 1) % 7
        wrong_day = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][wrong_idx]
        time_str = now.strftime("%H:%M")

        config = PublishingConfig(
            enabled=True,
            days=[wrong_day],
            preferred_times=[time_str],
        )

        result = check_should_publish_now(config, "UTC")
        assert result is None

    def test_returns_none_when_wrong_time(self):
        """Should return None when current time is outside 5-min window."""
        now = datetime.utcnow()
        day_abbr = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][now.weekday()]
        # Time 2 hours from now — definitely outside window
        far_time = (now + timedelta(hours=2)).strftime("%H:%M")

        config = PublishingConfig(
            enabled=True,
            days=[day_abbr],
            preferred_times=[far_time],
        )

        result = check_should_publish_now(config, "UTC")
        assert result is None

    def test_returns_none_when_no_days(self):
        config = PublishingConfig(enabled=True, days=[], preferred_times=["18:00"])
        assert check_should_publish_now(config, "UTC") is None

    def test_slot_is_deterministic(self):
        """Same call twice returns same slot datetime (for dedup to work)."""
        now = datetime.utcnow()
        day_abbr = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][now.weekday()]
        time_str = now.strftime("%H:%M")

        config = PublishingConfig(
            enabled=True,
            days=[day_abbr],
            preferred_times=[time_str],
        )

        slot1 = check_should_publish_now(config, "UTC")
        slot2 = check_should_publish_now(config, "UTC")
        assert slot1 == slot2


# ============================================================
# scheduled_publish_job integration tests
# ============================================================


class TestScheduledPublishJob:
    """Integration tests — full job run with mocked externals."""

    @pytest.mark.asyncio
    @patch("app.services.scheduled_publisher.publish_to_platform", new_callable=AsyncMock)
    @patch("app.services.scheduled_publisher.get_project_social_account")
    @patch("app.services.scheduled_publisher.settings")
    @patch("app.services.scheduled_publisher.SessionLocal")
    async def test_publishes_one_item_per_slot(
        self, mock_session_local, mock_settings, mock_get_account, mock_publish, db
    ):
        """Two approved items, one slot → only first item published."""
        now = datetime.utcnow()
        day_abbr = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][now.weekday()]
        time_str = now.strftime("%H:%M")

        project = _create_project_with_config(
            db, days=[day_abbr], preferred_times=[time_str]
        )
        item1 = _create_approved_item(db, project, position=1)
        item2 = _create_approved_item(db, project, position=2)
        item1_id, item2_id = item1.id, item2.id

        # Mock externals — return a non-closing session wrapper
        mock_session_local.return_value = _non_closing(db)
        mock_settings.APP_BASE_URL = "https://test.example.com"

        mock_account = type("SA", (), {
            "access_token": "tok",
            "refresh_token": None,
            "platform_data": {},
        })()
        mock_get_account.return_value = mock_account
        mock_publish.return_value = {"id": "pub_123"}

        # First run — should publish item1
        await scheduled_publish_job()

        item1 = db.get(ApprovedGeneration, item1_id)
        item2 = db.get(ApprovedGeneration, item2_id)

        assert item1.scheduled_for is not None
        assert item1.status in ("published", "partially_published")
        assert item2.status == "approved"
        assert item2.scheduled_for is None

    @pytest.mark.asyncio
    @patch("app.services.scheduled_publisher.publish_to_platform", new_callable=AsyncMock)
    @patch("app.services.scheduled_publisher.get_project_social_account")
    @patch("app.services.scheduled_publisher.settings")
    @patch("app.services.scheduled_publisher.SessionLocal")
    async def test_second_run_skips_same_slot(
        self, mock_session_local, mock_settings, mock_get_account, mock_publish, db
    ):
        """Second job run for same slot should NOT publish item2."""
        now = datetime.utcnow()
        day_abbr = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][now.weekday()]
        time_str = now.strftime("%H:%M")

        project = _create_project_with_config(
            db, days=[day_abbr], preferred_times=[time_str]
        )
        item1 = _create_approved_item(db, project, position=1)
        item2 = _create_approved_item(db, project, position=2)
        item1_id, item2_id = item1.id, item2.id

        mock_session_local.return_value = _non_closing(db)
        mock_settings.APP_BASE_URL = "https://test.example.com"

        mock_account = type("SA", (), {
            "access_token": "tok",
            "refresh_token": None,
            "platform_data": {},
        })()
        mock_get_account.return_value = mock_account
        mock_publish.return_value = {"id": "pub_123"}

        # Run twice
        await scheduled_publish_job()
        await scheduled_publish_job()

        item1 = db.get(ApprovedGeneration, item1_id)
        item2 = db.get(ApprovedGeneration, item2_id)

        # item1 published, item2 still approved
        assert item1.status in ("published", "partially_published")
        assert item2.status == "approved"
        assert item2.scheduled_for is None

        # publish_to_platform called only once (for item1)
        assert mock_publish.call_count == 1

    @pytest.mark.asyncio
    @patch("app.services.scheduled_publisher.publish_to_platform", new_callable=AsyncMock)
    @patch("app.services.scheduled_publisher.get_project_social_account")
    @patch("app.services.scheduled_publisher.settings")
    @patch("app.services.scheduled_publisher.SessionLocal")
    async def test_different_slot_publishes_next_item(
        self, mock_session_local, mock_settings, mock_get_account, mock_publish, db
    ):
        """Different slot time → should publish item2."""
        now = datetime.utcnow()
        day_abbr = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][now.weekday()]
        time_str = now.strftime("%H:%M")

        project = _create_project_with_config(
            db, days=[day_abbr], preferred_times=[time_str]
        )
        item1 = _create_approved_item(db, project, position=1)
        item2 = _create_approved_item(db, project, position=2)
        item1_id, item2_id = item1.id, item2.id

        mock_session_local.return_value = _non_closing(db)
        mock_settings.APP_BASE_URL = "https://test.example.com"

        mock_account = type("SA", (), {
            "access_token": "tok",
            "refresh_token": None,
            "platform_data": {},
        })()
        mock_get_account.return_value = mock_account
        mock_publish.return_value = {"id": "pub_123"}

        # First run — publishes item1
        await scheduled_publish_job()

        # Simulate: item1 was published at a DIFFERENT slot (yesterday)
        item1 = db.get(ApprovedGeneration, item1_id)
        item1.scheduled_for = item1.scheduled_for - timedelta(days=1)
        db.commit()

        # Second run — should now publish item2 (slot is "free")
        await scheduled_publish_job()

        item2 = db.get(ApprovedGeneration, item2_id)
        assert item2.scheduled_for is not None
        assert item2.status in ("published", "partially_published")
        assert mock_publish.call_count == 2

    @pytest.mark.asyncio
    @patch("app.services.scheduled_publisher.SessionLocal")
    async def test_no_items_does_not_crash(self, mock_session_local, db):
        """Empty queue — job runs without error."""
        now = datetime.utcnow()
        day_abbr = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][now.weekday()]
        time_str = now.strftime("%H:%M")

        _create_project_with_config(
            db, days=[day_abbr], preferred_times=[time_str]
        )
        # No approved items

        mock_session_local.return_value = _non_closing(db)

        # Should not raise
        await scheduled_publish_job()
