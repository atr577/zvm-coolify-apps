from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.user import User, SocialAccount
from app.core.deps import get_current_user
from app.core.config import settings
import httpx
from typing import Optional

router = APIRouter()


# OAuth configuration
OAUTH_CONFIGS = {
    "instagram": {
        "authorize_url": "https://api.instagram.com/oauth/authorize",
        "token_url": "https://api.instagram.com/oauth/access_token",
        "scope": "user_profile,user_media",
        "client_id": getattr(settings, "INSTAGRAM_CLIENT_ID", None),
        "client_secret": getattr(settings, "INSTAGRAM_CLIENT_SECRET", None),
    },
    "tiktok": {
        "authorize_url": "https://www.tiktok.com/v2/auth/authorize/",
        "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
        "scope": "user.info.basic,video.list,video.upload",
        "client_id": getattr(settings, "TIKTOK_CLIENT_ID", None),
        "client_secret": getattr(settings, "TIKTOK_CLIENT_SECRET", None),
    },
    "youtube": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/userinfo.email",
        "client_id": getattr(settings, "YOUTUBE_CLIENT_ID", None),
        "client_secret": getattr(settings, "YOUTUBE_CLIENT_SECRET", None),
    }
}


@router.get("/connect/{platform}")
async def initiate_oauth(
    platform: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Инициировать OAuth flow для подключения социальной сети

    Платформы: instagram, tiktok, youtube
    """
    if platform not in OAUTH_CONFIGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}"
        )

    config = OAUTH_CONFIGS[platform]

    if not config["client_id"] or not config["client_secret"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OAuth not configured for {platform}. Please add {platform.upper()}_CLIENT_ID and {platform.upper()}_CLIENT_SECRET to environment variables."
        )

    # Формируем redirect_uri (callback URL)
    redirect_uri = str(request.base_url) + f"api/oauth/callback/{platform}"

    # Формируем state для CSRF protection (можно использовать JWT с user_id)
    state = f"{current_user.id}:{platform}"

    # Формируем authorization URL
    auth_params = {
        "client_id": config["client_id"],
        "redirect_uri": redirect_uri,
        "scope": config["scope"],
        "response_type": "code",
        "state": state,
    }

    # Для YouTube используем access_type=offline для refresh token
    if platform == "youtube":
        auth_params["access_type"] = "offline"
        auth_params["prompt"] = "consent"

    auth_url = config["authorize_url"] + "?" + "&".join(
        f"{k}={v}" for k, v in auth_params.items()
    )

    return {
        "authorization_url": auth_url,
        "platform": platform,
        "message": "Redirect user to authorization_url to complete OAuth flow"
    }


@router.get("/callback/{platform}")
async def oauth_callback(
    platform: str,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    OAuth callback endpoint - обрабатывает ответ от социальной сети

    После авторизации пользователя, социальная сеть редиректит сюда с authorization code
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error}"
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter"
        )

    # Парсим state для получения user_id
    try:
        user_id_str, platform_from_state = state.split(":")
        user_id = int(user_id_str)
        if platform != platform_from_state:
            raise ValueError("Platform mismatch")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )

    # Получаем пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    config = OAUTH_CONFIGS[platform]
    redirect_uri = str(request.base_url) + f"api/oauth/callback/{platform}"

    # Обмениваем authorization code на access token
    try:
        async with httpx.AsyncClient() as client:
            token_data = {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }

            response = await client.post(
                config["token_url"],
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to exchange code for token: {response.text}"
                )

            tokens = response.json()
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")

            # Получаем информацию о пользователе платформы
            user_info = await get_platform_user_info(platform, access_token)

            # YouTube may return multiple channels - handle as list
            user_info_list = user_info if isinstance(user_info, list) else [user_info]

            # Создаем или обновляем SocialAccount для каждого канала
            for info in user_info_list:
                existing_account = db.query(SocialAccount).filter(
                    SocialAccount.user_id == user_id,
                    SocialAccount.platform == platform,
                    SocialAccount.platform_user_id == info["id"]
                ).first()

                if existing_account:
                    existing_account.access_token = access_token
                    existing_account.refresh_token = refresh_token
                    existing_account.username = info.get("username")
                    existing_account.display_name = info.get("display_name")
                    existing_account.profile_picture = info.get("profile_picture")
                    existing_account.is_active = True
                else:
                    account = SocialAccount(
                        user_id=user_id,
                        platform=platform,
                        platform_user_id=info["id"],
                        access_token=access_token,
                        refresh_token=refresh_token,
                        username=info.get("username"),
                        display_name=info.get("display_name"),
                        profile_picture=info.get("profile_picture"),
                        is_active=True
                    )
                    db.add(account)

            db.commit()

            # Редирект на фронтенд с success
            frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
            return RedirectResponse(
                url=f"{frontend_url}/social-accounts?success=true&platform={platform}"
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
        )


async def get_platform_user_info(platform: str, access_token: str) -> dict:
    """
    Получить информацию о пользователе с платформы
    """
    async with httpx.AsyncClient() as client:
        if platform == "instagram":
            response = await client.get(
                "https://graph.instagram.com/me",
                params={"fields": "id,username", "access_token": access_token}
            )
            data = response.json()
            return {
                "id": data.get("id"),
                "username": data.get("username"),
                "display_name": data.get("username"),
                "profile_picture": None
            }

        elif platform == "tiktok":
            response = await client.get(
                "https://open.tiktokapis.com/v2/user/info/",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            data = response.json().get("data", {}).get("user", {})
            return {
                "id": data.get("open_id"),
                "username": data.get("display_name"),
                "display_name": data.get("display_name"),
                "profile_picture": data.get("avatar_url")
            }

        elif platform == "youtube":
            # Get Google account email
            email_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            email_data = email_response.json()
            google_email = email_data.get("email", "")

            # Get YouTube channels (with snippet for title and customUrl for handle)
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={"part": "snippet", "mine": "true"},
                headers={"Authorization": f"Bearer {access_token}"}
            )
            data = response.json()
            if data.get("items"):
                # Return ALL channels, not just the first one
                channels = []
                for channel in data["items"]:
                    channel_title = channel["snippet"].get("title", "")
                    # customUrl is the @handle (e.g. @georgym)
                    custom_url = channel["snippet"].get("customUrl", "")
                    handle = custom_url if custom_url else ""
                    # Format: "email - channel_name (handle)" or "email - channel_name" if no handle
                    if google_email and handle:
                        display = f"{google_email} - {channel_title} ({handle})"
                    elif google_email:
                        display = f"{google_email} - {channel_title}"
                    elif handle:
                        display = f"{channel_title} ({handle})"
                    else:
                        display = channel_title
                    channels.append({
                        "id": channel.get("id"),
                        "username": handle or channel_title,
                        "display_name": display,
                        "profile_picture": channel["snippet"].get("thumbnails", {}).get("default", {}).get("url")
                    })
                # Return list for youtube, single dict for others
                return channels if len(channels) > 1 else channels[0]

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get user info for {platform}"
        )


@router.post("/refresh/{platform}/{account_id}")
async def refresh_token(
    platform: str,
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Обновить access token используя refresh token
    """
    account = db.query(SocialAccount).filter(
        SocialAccount.id == account_id,
        SocialAccount.user_id == current_user.id,
        SocialAccount.platform == platform
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found"
        )

    if not account.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No refresh token available"
        )

    config = OAUTH_CONFIGS[platform]

    try:
        async with httpx.AsyncClient() as client:
            token_data = {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "refresh_token": account.refresh_token,
                "grant_type": "refresh_token"
            }

            response = await client.post(
                config["token_url"],
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to refresh token: {response.text}"
                )

            tokens = response.json()
            account.access_token = tokens.get("access_token")
            if tokens.get("refresh_token"):
                account.refresh_token = tokens.get("refresh_token")

            db.commit()
            db.refresh(account)

            return {
                "message": "Token refreshed successfully",
                "account_id": account.id,
                "platform": platform
            }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh token: {str(e)}"
        )
