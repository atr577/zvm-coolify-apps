"""
Tests for T13: Social account binding to projects.

Covers:
1. GET /api/projects/{id} returns social_accounts in response
2. POST /api/projects/{id}/social-accounts — bind works
3. DELETE /api/projects/{id}/social-accounts/{acc_id} — unbind works
4. get_project_platforms() — fallback logic
5. Duplicate bind → 409
6. Unbind non-bound account → 404
7. GET /api/videos/{id} returns project.social_accounts
"""
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.user import User, SocialAccount
from app.models.project import Project
from app.models.video import Video
from app.api.projects import get_project_platforms


@pytest.fixture
def test_social_account(db: Session, test_user: User) -> SocialAccount:
    """Create an Instagram social account for the test user."""
    account = SocialAccount(
        user_id=test_user.id,
        platform="instagram",
        platform_user_id="ig_123456",
        username="test_instagram",
        display_name="Test IG",
        access_token="fake_token",
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def test_youtube_account(db: Session, test_user: User) -> SocialAccount:
    """Create a YouTube social account for the test user."""
    account = SocialAccount(
        user_id=test_user.id,
        platform="youtube",
        platform_user_id="yt_789",
        username="test_youtube",
        display_name="Test YT",
        access_token="fake_token_yt",
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def test_inactive_account(db: Session, test_user: User) -> SocialAccount:
    """Create an inactive TikTok social account."""
    account = SocialAccount(
        user_id=test_user.id,
        platform="tiktok",
        platform_user_id="tt_999",
        username="test_tiktok",
        access_token="fake_token_tt",
        is_active=False,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


class TestProjectResponseIncludesSocialAccounts:
    """GET /api/projects/{id} returns social_accounts field."""

    def test_project_response_has_empty_social_accounts(
        self, client: TestClient, auth_headers: dict, test_project: Project
    ):
        response = client.get(f"/api/projects/{test_project.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "social_accounts" in data
        assert data["social_accounts"] == []

    def test_project_response_includes_bound_accounts(
        self, client: TestClient, auth_headers: dict, test_project: Project,
        test_social_account: SocialAccount
    ):
        # Bind first
        client.post(
            f"/api/projects/{test_project.id}/social-accounts",
            json={"social_account_id": test_social_account.id},
            headers=auth_headers,
        )
        # Fetch project
        response = client.get(f"/api/projects/{test_project.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["social_accounts"]) == 1
        assert data["social_accounts"][0]["username"] == "test_instagram"
        assert data["social_accounts"][0]["platform"] == "instagram"


class TestVideoResponseIncludesSocialAccounts:
    """GET /api/videos/{id} returns project.social_accounts via ProjectBrief."""

    def test_video_response_has_project_social_accounts(
        self, client: TestClient, auth_headers: dict,
        test_project: Project, test_video: Video, test_social_account: SocialAccount
    ):
        # Bind account to project
        client.post(
            f"/api/projects/{test_project.id}/social-accounts",
            json={"social_account_id": test_social_account.id},
            headers=auth_headers,
        )
        # Fetch video — project.social_accounts must be populated
        response = client.get(f"/api/videos/{test_video.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["project"] is not None
        assert "social_accounts" in data["project"]
        assert len(data["project"]["social_accounts"]) == 1
        assert data["project"]["social_accounts"][0]["platform"] == "instagram"


class TestBindSocialAccount:
    """POST /api/projects/{id}/social-accounts"""

    def test_bind_success(
        self, client: TestClient, auth_headers: dict,
        test_project: Project, test_social_account: SocialAccount
    ):
        response = client.post(
            f"/api/projects/{test_project.id}/social-accounts",
            json={"social_account_id": test_social_account.id},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["social_accounts"]) == 1
        assert data["social_accounts"][0]["id"] == test_social_account.id

    def test_bind_duplicate_returns_409(
        self, client: TestClient, auth_headers: dict,
        test_project: Project, test_social_account: SocialAccount
    ):
        # First bind — success
        resp1 = client.post(
            f"/api/projects/{test_project.id}/social-accounts",
            json={"social_account_id": test_social_account.id},
            headers=auth_headers,
        )
        assert resp1.status_code == 200

        # Second bind — conflict
        resp2 = client.post(
            f"/api/projects/{test_project.id}/social-accounts",
            json={"social_account_id": test_social_account.id},
            headers=auth_headers,
        )
        assert resp2.status_code == 409

    def test_bind_nonexistent_account_returns_404(
        self, client: TestClient, auth_headers: dict, test_project: Project
    ):
        response = client.post(
            f"/api/projects/{test_project.id}/social-accounts",
            json={"social_account_id": 99999},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_bind_multiple_accounts(
        self, client: TestClient, auth_headers: dict,
        test_project: Project, test_social_account: SocialAccount,
        test_youtube_account: SocialAccount
    ):
        # Bind Instagram
        resp1 = client.post(
            f"/api/projects/{test_project.id}/social-accounts",
            json={"social_account_id": test_social_account.id},
            headers=auth_headers,
        )
        assert resp1.status_code == 200

        # Bind YouTube
        resp2 = client.post(
            f"/api/projects/{test_project.id}/social-accounts",
            json={"social_account_id": test_youtube_account.id},
            headers=auth_headers,
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert len(data["social_accounts"]) == 2

    def test_bind_requires_auth(
        self, client: TestClient, test_project: Project, test_social_account: SocialAccount
    ):
        response = client.post(
            f"/api/projects/{test_project.id}/social-accounts",
            json={"social_account_id": test_social_account.id},
        )
        assert response.status_code == 401


class TestUnbindSocialAccount:
    """DELETE /api/projects/{id}/social-accounts/{acc_id}"""

    def test_unbind_success(
        self, client: TestClient, auth_headers: dict,
        test_project: Project, test_social_account: SocialAccount
    ):
        # Bind first
        client.post(
            f"/api/projects/{test_project.id}/social-accounts",
            json={"social_account_id": test_social_account.id},
            headers=auth_headers,
        )

        # Unbind
        response = client.delete(
            f"/api/projects/{test_project.id}/social-accounts/{test_social_account.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify project has no bound accounts
        resp = client.get(f"/api/projects/{test_project.id}", headers=auth_headers)
        assert len(resp.json()["social_accounts"]) == 0

    def test_unbind_not_bound_returns_404(
        self, client: TestClient, auth_headers: dict,
        test_project: Project, test_social_account: SocialAccount
    ):
        response = client.delete(
            f"/api/projects/{test_project.id}/social-accounts/{test_social_account.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestGetProjectPlatforms:
    """Unit tests for get_project_platforms() helper."""

    def test_no_accounts_returns_project_platforms(
        self, db: Session, test_project: Project
    ):
        # test_project has platforms=["instagram", "tiktok"]
        result = get_project_platforms(test_project)
        assert set(result) == {"instagram", "tiktok"}

    def test_bound_active_accounts_override_platforms(
        self, db: Session, test_project: Project, test_social_account: SocialAccount
    ):
        # Bind Instagram account
        test_project.social_accounts.append(test_social_account)
        db.commit()
        db.refresh(test_project)

        result = get_project_platforms(test_project)
        assert result == ["instagram"]

    def test_inactive_accounts_fallback_to_platforms(
        self, db: Session, test_project: Project, test_inactive_account: SocialAccount
    ):
        # Bind inactive TikTok account
        test_project.social_accounts.append(test_inactive_account)
        db.commit()
        db.refresh(test_project)

        # Inactive account → fallback to project.platforms
        result = get_project_platforms(test_project)
        assert set(result) == {"instagram", "tiktok"}

    def test_mixed_active_inactive_returns_only_active(
        self, db: Session, test_project: Project,
        test_social_account: SocialAccount, test_inactive_account: SocialAccount
    ):
        test_project.social_accounts.append(test_social_account)  # active instagram
        test_project.social_accounts.append(test_inactive_account)  # inactive tiktok
        db.commit()
        db.refresh(test_project)

        result = get_project_platforms(test_project)
        assert result == ["instagram"]

    def test_empty_platforms_and_no_accounts(self, db: Session, test_project: Project):
        test_project.platforms = []
        db.commit()
        db.refresh(test_project)

        result = get_project_platforms(test_project)
        assert result == []
