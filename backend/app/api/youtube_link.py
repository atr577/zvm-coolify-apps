"""
Public routes for YouTube account linking (no REGGY auth required).
GET /api/link-youtube/start    → redirect to Google OAuth
GET /api/link-youtube/callback → handle OAuth callback, save tokens
"""
import logging
from datetime import datetime, timedelta
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import get_db
from app.models.user import Workspace
from app.services.youtube_oauth import (
    build_oauth_url,
    create_state_jwt,
    exchange_code_for_tokens,
    get_userinfo,
    get_youtube_channel,
    save_youtube_account,
    verify_state_jwt,
)

logger = logging.getLogger(__name__)

router = APIRouter()

FRONTEND_LINK_PAGE = "/link-youtube-account"


def get_base_url(request: Request) -> str:
    """Get base URL respecting reverse proxy headers."""
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost"))
    return f"{proto}://{host}"


def frontend_error(base_url: str, reason: str) -> RedirectResponse:
    return RedirectResponse(url=f"{base_url}{FRONTEND_LINK_PAGE}?status=error&reason={reason}")


def frontend_success(base_url: str, email: str, channel: str) -> RedirectResponse:
    return RedirectResponse(
        url=f"{base_url}{FRONTEND_LINK_PAGE}?status=success&email={quote(email)}&channel={quote(channel)}"
    )


@router.get("/start")
async def start_youtube_link(request: Request):
    """Redirect to Google OAuth consent screen."""
    base_url = get_base_url(request)
    redirect_uri = f"{base_url}/api/link-youtube/callback"
    state = create_state_jwt()
    oauth_url = build_oauth_url(redirect_uri=redirect_uri, state=state)
    return RedirectResponse(url=oauth_url)


@router.get("/callback")
async def youtube_link_callback(
    request: Request,
    db: Session = Depends(get_db),
    code: str = None,
    state: str = None,
    error: str = None,
):
    """Handle Google OAuth callback. Save tokens and redirect to frontend."""
    base_url = get_base_url(request)

    # User denied access
    if error == "access_denied" or (error and not code):
        return frontend_error(base_url, "access_denied")

    # Missing code
    if not code:
        return frontend_error(base_url, "unknown")

    # Verify CSRF state
    if not state or not verify_state_jwt(state):
        return frontend_error(base_url, "invalid_state")

    redirect_uri = f"{base_url}/api/link-youtube/callback"

    try:
        # Exchange code for tokens
        tokens = await exchange_code_for_tokens(code=code, redirect_uri=redirect_uri)
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        return frontend_error(base_url, "unknown")

    # Must have refresh_token (requires access_type=offline + prompt=consent)
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        return frontend_error(base_url, "no_refresh_token")

    access_token = tokens.get("access_token", "")
    expires_in = tokens.get("expires_in")
    token_expiry = datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None
    scopes = tokens.get("scope", "")

    try:
        userinfo = await get_userinfo(access_token)
    except Exception as e:
        logger.error(f"Userinfo fetch failed: {e}")
        return frontend_error(base_url, "unknown")

    google_account_id = userinfo.get("id")
    google_email = userinfo.get("email", "")

    try:
        channel = await get_youtube_channel(access_token)
    except Exception as e:
        logger.error(f"Channel fetch failed: {e}")
        return frontend_error(base_url, "unknown")

    if not channel:
        return frontend_error(base_url, "no_channel")

    channel_id = channel["id"]
    snippet = channel.get("snippet", {})
    channel_title = snippet.get("title", "")
    thumbnails = snippet.get("thumbnails", {})
    channel_thumbnail_url = (
        thumbnails.get("default", {}).get("url") or
        thumbnails.get("medium", {}).get("url")
    )

    # Validate workspace exists
    workspace = db.query(Workspace).filter(
        Workspace.id == settings.YOUTUBE_DEFAULT_WORKSPACE_ID
    ).first()
    if not workspace:
        logger.error(f"YOUTUBE_DEFAULT_WORKSPACE_ID={settings.YOUTUBE_DEFAULT_WORKSPACE_ID} not found in DB")
        return frontend_error(base_url, "config_error")

    try:
        save_youtube_account(
            db=db,
            google_account_id=google_account_id,
            google_email=google_email,
            channel_id=channel_id,
            channel_title=channel_title,
            channel_thumbnail_url=channel_thumbnail_url,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry,
            scopes=scopes,
            workspace_id=settings.YOUTUBE_DEFAULT_WORKSPACE_ID,
        )
    except ValueError as e:
        if str(e) == "already_linked":
            return frontend_error(base_url, "already_linked")
        return frontend_error(base_url, "unknown")
    except IntegrityError:
        db.rollback()
        return frontend_error(base_url, "already_linked")
    except Exception as e:
        logger.error(f"Failed to save YouTubeAccount: {e}")
        return frontend_error(base_url, "unknown")

    return frontend_success(base_url, email=google_email, channel=channel_title)
