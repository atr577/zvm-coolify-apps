"""
Tests for authentication API endpoints.
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, Invite, InviteType
from app.core.security import verify_password


class TestLogin:
    """Tests for POST /api/auth/login"""

    def test_login_success(
        self,
        client: TestClient,
        test_user: User
    ):
        """Should return access token for valid credentials."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(
        self,
        client: TestClient,
        test_user: User
    ):
        """Should return 401 for wrong password."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """Should return 401 for non-existent user."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "testpass123"
            }
        )

        assert response.status_code == 401


class TestRegister:
    """Tests for POST /api/auth/register"""

    def test_register_with_valid_invite(
        self,
        client: TestClient,
        db: Session,
        test_admin: User
    ):
        """Should register user with valid invite token."""
        # Create invite with required fields
        invite = Invite(
            token="valid-invite-token",
            type=InviteType.STANDALONE,
            email="newuser@example.com",
            created_by_id=test_admin.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(invite)
        db.commit()

        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "newpass123",
                "invite_token": "valid-invite-token"
            }
        )

        # 201 Created for successful registration
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"

        # Verify invite is marked as used
        db.refresh(invite)
        assert invite.is_used is True

    def test_register_without_invite(self, client: TestClient):
        """Should return error without invite token."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "newpass123"
            }
        )

        # Can be 400 (business logic) or 422 (Pydantic validation for required field)
        assert response.status_code in (400, 422)

    def test_register_invalid_invite(self, client: TestClient):
        """Should return 400 with invalid invite token."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "newpass123",
                "invite_token": "invalid-token"
            }
        )

        assert response.status_code == 400

    def test_register_duplicate_email(
        self,
        client: TestClient,
        db: Session,
        test_user: User,
        test_admin: User
    ):
        """Should return 400 for duplicate email."""
        invite = Invite(
            token="another-token",
            type=InviteType.STANDALONE,
            email="test@example.com",  # Same as test_user
            created_by_id=test_admin.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(invite)
        db.commit()

        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "newpass123",
                "invite_token": "another-token"
            }
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()


class TestGetCurrentUser:
    """Tests for GET /api/auth/me"""

    def test_get_me_authenticated(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User
    ):
        """Should return current user data."""
        response = client.get("/api/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert "hashed_password" not in data

    def test_get_me_unauthenticated(self, client: TestClient):
        """Should return 401 without token."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401


class TestInvites:
    """Tests for invite management endpoints."""

    def test_create_invite_admin(
        self,
        client: TestClient,
        admin_headers: dict
    ):
        """Admin should be able to create invites."""
        response = client.post(
            "/api/auth/invites",
            json={"email": "invited@example.com", "type": "standalone"},
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "invited@example.com"
        assert "token" in data

    def test_create_invite_non_admin(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Non-admin should not be able to create invites."""
        response = client.post(
            "/api/auth/invites",
            json={"email": "invited@example.com", "type": "standalone"},
            headers=auth_headers
        )

        assert response.status_code == 403

    def test_list_invites_admin(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        test_admin: User
    ):
        """Admin should see all invites."""
        # Create some invites with required fields
        for i in range(3):
            invite = Invite(
                token=f"token-{i}",
                type=InviteType.STANDALONE,
                email=f"user{i}@example.com",
                created_by_id=test_admin.id,
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            db.add(invite)
        db.commit()

        response = client.get("/api/auth/invites", headers=admin_headers)

        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_validate_invite(
        self,
        client: TestClient,
        db: Session,
        test_admin: User
    ):
        """Should validate invite token."""
        invite = Invite(
            token="check-this-token",
            type=InviteType.STANDALONE,
            email="check@example.com",
            created_by_id=test_admin.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(invite)
        db.commit()

        response = client.get("/api/auth/invite/check-this-token")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["email"] == "check@example.com"

    def test_validate_invalid_invite(self, client: TestClient):
        """Should return invalid for non-existent token."""
        response = client.get("/api/auth/invite/nonexistent-token")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
