"""
YouTube OAuth service for external account linking.
Handles token exchange, channel fetch, state JWT management.
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode, quote

import httpx
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.youtube_account import YouTubeAccount, YouTubeAccountStatus

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
STATE_JWT_TTL_MINUTES = 5

YOUTUBE_SCOPES = " ".join([
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/userinfo.email",
])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"


def create_state_jwt() -> str:
    """Create a short-lived JWT for CSRF protection."""
    payload = {
        "nonce": str(uuid.uuid4()),
        "exp": datetime.utcnow() + timedelta(minutes=STATE_JWT_TTL_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_state_jwt(state: str) -> bool:
    """Verify state JWT. Returns True if valid."""
    try:
        jwt.decode(state, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return True
    except JWTError:
        return False


def build_oauth_url(redirect_uri: str, state: str) -> str:
    """Build Google OAuth authorization URL."""
    params = {
        "client_id": settings.YOUTUBE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": YOUTUBE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str, redirect_uri: str) -> dict:
    """Exchange authorization code for tokens. Raises on failure."""
    async with httpx.AsyncClient() as client:
        response = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.YOUTUBE_CLIENT_ID,
            "client_secret": settings.YOUTUBE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        response.raise_for_status()
        return response.json()


async def get_userinfo(access_token: str) -> dict:
    """Get Google account userinfo (sub, email)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        return response.json()


async def get_youtube_channel(access_token: str) -> Optional[dict]:
    """Get first YouTube channel for the authenticated user. Returns None if no channel."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            YOUTUBE_CHANNELS_URL,
            params={"part": "snippet", "mine": "true"},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        return items[0] if items else None


def save_youtube_account(
    db: Session,
    google_account_id: str,
    google_email: str,
    channel_id: str,
    channel_title: str,
    channel_thumbnail_url: Optional[str],
    access_token: str,
    refresh_token: str,
    token_expiry: Optional[datetime],
    scopes: str,
    workspace_id: int,
) -> YouTubeAccount:
    """
    Save or update YouTubeAccount.
    - Same google_account_id → UPDATE (re-link)
    - Different google_account_id + same channel_id → raise ValueError (conflict)
    """
    existing_by_google = db.query(YouTubeAccount).filter(
        YouTubeAccount.google_account_id == google_account_id
    ).first()

    existing_by_channel = db.query(YouTubeAccount).filter(
        YouTubeAccount.channel_id == channel_id
    ).first()

    # Conflict: different account linked to same channel
    if existing_by_channel and (
        not existing_by_google or existing_by_channel.id != existing_by_google.id
    ):
        raise ValueError("already_linked")

    if existing_by_google:
        # Re-link: update tokens and channel data
        existing_by_google.google_email = google_email
        existing_by_google.channel_id = channel_id
        existing_by_google.channel_title = channel_title
        existing_by_google.channel_thumbnail_url = channel_thumbnail_url
        existing_by_google.access_token = access_token
        existing_by_google.refresh_token = refresh_token
        existing_by_google.token_expiry = token_expiry
        existing_by_google.scopes = scopes
        existing_by_google.token_status = YouTubeAccountStatus.ACTIVE.value
        existing_by_google.last_token_refresh = datetime.utcnow()
        db.commit()
        db.refresh(existing_by_google)
        return existing_by_google

    # New account
    account = YouTubeAccount(
        google_account_id=google_account_id,
        google_email=google_email,
        channel_id=channel_id,
        channel_title=channel_title,
        channel_thumbnail_url=channel_thumbnail_url,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expiry=token_expiry,
        scopes=scopes,
        token_status=YouTubeAccountStatus.ACTIVE.value,
        workspace_id=workspace_id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account
