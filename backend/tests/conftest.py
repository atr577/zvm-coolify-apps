"""
Test configuration and fixtures for 4-step workflow.
"""
import pytest
from typing import Generator
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Patch scheduler to avoid event loop issues in tests
import app.core.scheduler as scheduler_module
scheduler_module.start_scheduler = lambda: None
scheduler_module.shutdown_scheduler = lambda: None

from app.main import app
from app.db.base import Base, get_db
from app.models.user import User, Workspace, WorkspaceMember
from app.models.project import Project
from app.models.video import Video, WorkflowMode, WorkflowStatus
from app.models.step_history import StepHistory
from app.core.security import hash_password, create_access_token


# Test database - in-memory SQLite
SQLALCHEMY_TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create fresh database for each test."""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Test client with overridden database dependency."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=hash_password("testpass123"),
        is_active=True,
        role="user"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin(db: Session) -> User:
    """Create a test admin user."""
    admin = User(
        email="admin@example.com",
        hashed_password=hash_password("adminpass123"),
        is_active=True,
        role="admin"
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Authorization headers for authenticated requests."""
    token = create_access_token(data={"user_id": test_user.id, "email": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(test_admin: User) -> dict:
    """Authorization headers for admin requests."""
    token = create_access_token(data={"user_id": test_admin.id, "email": test_admin.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_workspace(db: Session, test_user: User) -> Workspace:
    """Create a test workspace with the test user as owner."""
    workspace = Workspace(
        name="Test Workspace",
        owner_id=test_user.id
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    # Add user as member with owner role
    member = WorkspaceMember(
        user_id=test_user.id,
        workspace_id=workspace.id,
        role="owner"
    )
    db.add(member)
    db.commit()

    return workspace


@pytest.fixture
def test_project(db: Session, test_workspace: Workspace, test_user: User) -> Project:
    """Create a test project."""
    project = Project(
        name="Test Project",
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        story_template="A story about {animal} in {location}",
        platforms=["instagram", "tiktok"],
        duration=5,
        aspect_ratio="9:16",
        audio_mode="auto",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@pytest.fixture
def test_video(db: Session, test_project: Project) -> Video:
    """Create a test video (AUTO mode for complete workflow execution)."""
    video = Video(
        project_id=test_project.id,
        title="Test Video",
        workflow_mode=WorkflowMode.AUTO,
        content_variables={"animal": "cat", "location": "beach"},
        status=WorkflowStatus.PENDING,
        current_step="scenario"
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


@pytest.fixture
def test_video_with_scenario(db: Session, test_video: Video) -> Video:
    """Create a test video with completed scenario step."""
    scenario_content = {
        "image_prompt": "A cat on the beach, cinematic lighting",
        "motion_prompt": "Cat slowly walks on sand",
        "camera_movement": {"type": "pan_left", "speed": "slow"},
    }

    # Create scenario step history
    step = StepHistory(
        video_id=test_video.id,
        step_type="scenario",
        content=scenario_content,
        status="success",
        is_selected=True,
    )
    db.add(step)

    # Update video
    test_video.scenario_data = scenario_content
    test_video.image_prompt = scenario_content["image_prompt"]
    test_video.current_step = "image"
    test_video.status = WorkflowStatus.AWAITING_APPROVAL

    db.commit()
    db.refresh(test_video)
    return test_video


@pytest.fixture
def test_step_awaiting_approval(db: Session, test_video: Video) -> StepHistory:
    """Create a step history entry awaiting approval."""
    scenario_content = {
        "image_prompt": "A cat on the beach, cinematic lighting",
        "motion_prompt": "Cat slowly walks on sand",
    }

    # Set scenario_data on video
    test_video.scenario_data = scenario_content
    test_video.image_prompt = scenario_content["image_prompt"]
    db.commit()

    step = StepHistory(
        video_id=test_video.id,
        step_type="scenario",
        content=scenario_content,
        status="success",
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


@pytest.fixture
def test_remix_project(db: Session, test_workspace: Workspace, test_user: User) -> Project:
    """Create a test Remix project."""
    project = Project(
        name="Test Remix Project",
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        story_template="Remix template",
        platforms=["instagram", "tiktok"],
        duration=5,
        aspect_ratio="9:16",
        audio_mode="auto",
        project_type="remix",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@pytest.fixture
def test_remix_video(db: Session, test_remix_project: Project) -> Video:
    """Create a test video in Remix project with image_prompt set."""
    video = Video(
        project_id=test_remix_project.id,
        title="Test Remix Video",
        workflow_mode=WorkflowMode.AUTO,
        content_variables={},
        image_prompt="A beautiful sunset over the ocean, cinematic, 8k",
        status=WorkflowStatus.PENDING,
        current_step="image"
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video
