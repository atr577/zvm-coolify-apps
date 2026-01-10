"""
Test configuration and fixtures.
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
from app.models.video import Video, WorkflowMode, WorkflowStatus, StepType
from app.models.workflow_step import WorkflowStep
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
    from app.services.prompt_builders import DEFAULT_SYSTEM_PROMPTS

    project = Project(
        name="Test Project",
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        story_template="A story about {animal} in {location}",
        platforms=["instagram", "tiktok"],
        duration=5,
        aspect_ratio="9:16",
        audio_mode="auto",
        system_prompts=DEFAULT_SYSTEM_PROMPTS
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
        workflow_mode=WorkflowMode.AUTO,  # AUTO for tests expecting complete workflow
        content_variables={"animal": "cat", "location": "beach"},
        status=WorkflowStatus.PENDING,
        current_step=StepType.STORY
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


@pytest.fixture
def test_video_with_story(db: Session, test_video: Video) -> Video:
    """Create a test video with completed story step."""
    from tests.fixtures.mock_responses import MOCK_STORY

    # Create story step
    step = WorkflowStep(
        video_id=test_video.id,
        step_type=StepType.STORY,
        status=WorkflowStatus.AWAITING_APPROVAL,
        content=MOCK_STORY
    )
    db.add(step)

    # Update video
    test_video.story_data = MOCK_STORY
    test_video.current_step = StepType.STORY
    test_video.status = WorkflowStatus.IN_PROGRESS

    db.commit()
    db.refresh(test_video)
    return test_video


@pytest.fixture
def test_step_awaiting_approval(db: Session, test_video: Video) -> WorkflowStep:
    """Create a workflow step awaiting approval."""
    from tests.fixtures.mock_responses import MOCK_STORY

    # Set story_data on video for auto-generation flow
    test_video.story_data = MOCK_STORY
    db.commit()

    step = WorkflowStep(
        video_id=test_video.id,
        step_type=StepType.STORY,
        status=WorkflowStatus.AWAITING_APPROVAL,
        content=MOCK_STORY
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


@pytest.fixture
def test_project_with_image_approval(db: Session, test_workspace: Workspace, test_user: User) -> Project:
    """Create a test project with require_image_approval=True."""
    from app.services.prompt_builders import DEFAULT_SYSTEM_PROMPTS

    project = Project(
        name="Test Project With Image Approval",
        workspace_id=test_workspace.id,
        user_id=test_user.id,
        story_template="A story about {animal} in {location}",
        platforms=["instagram", "tiktok"],
        duration=5,
        aspect_ratio="9:16",
        audio_mode="auto",
        require_image_approval=True,
        system_prompts=DEFAULT_SYSTEM_PROMPTS
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@pytest.fixture
def test_video_with_image_approval(db: Session, test_project_with_image_approval: Project) -> Video:
    """Create a test video in project with require_image_approval=True (AUTO mode)."""
    video = Video(
        project_id=test_project_with_image_approval.id,
        title="Test Video With Image Approval",
        workflow_mode=WorkflowMode.AUTO,  # AUTO mode - legacy test for require_image_approval
        content_variables={"animal": "cat", "location": "beach"},
        status=WorkflowStatus.PENDING,
        current_step=StepType.STORY
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


@pytest.fixture
def test_remix_project(db: Session, test_workspace: Workspace, test_user: User) -> Project:
    """Create a test Remix project."""
    from app.services.prompt_builders import DEFAULT_SYSTEM_PROMPTS

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
        system_prompts=DEFAULT_SYSTEM_PROMPTS
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@pytest.fixture
def test_remix_video(db: Session, test_remix_project: Project) -> Video:
    """Create a test video in Remix project with image_prompt set (AUTO mode for full workflow)."""
    video = Video(
        project_id=test_remix_project.id,
        title="Test Remix Video",
        workflow_mode=WorkflowMode.AUTO,  # AUTO to complete all steps without stopping
        content_variables={},
        image_prompt="A beautiful sunset over the ocean, cinematic, 8k",
        status=WorkflowStatus.PENDING,
        current_step=StepType.IMAGE
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video
