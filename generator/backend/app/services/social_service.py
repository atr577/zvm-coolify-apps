import httpx
import tempfile
import os
from typing import Dict, Any, Optional, List
from app.core.config import settings
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


class InstagramService:
    """Instagram Graph API integration"""

    def __init__(self):
        self.base_url = "https://graph.facebook.com/v18.0"

    async def publish_reel(
        self,
        video_url: str,
        caption: str,
        access_token: str,
        business_account_id: str,
        share_to_feed: bool = True
    ) -> Dict[str, Any]:
        """
        Publish Reel to Instagram using OAuth token
        """
        if not access_token or not business_account_id:
            raise ValueError("Instagram requires access_token and business_account_id")

        # Step 1: Create media container
        container_url = f"{self.base_url}/{business_account_id}/media"
        container_params = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": share_to_feed,
            "access_token": access_token
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            container_response = await client.post(container_url, params=container_params)
            container_response.raise_for_status()
            container_data = container_response.json()

        creation_id = container_data.get("id")
        if not creation_id:
            raise Exception(f"Failed to create Instagram media container: {container_data}")

        # Step 2: Wait for video processing (Instagram needs time to process)
        import asyncio
        await asyncio.sleep(5)

        # Step 3: Publish container
        publish_url = f"{self.base_url}/{business_account_id}/media_publish"
        publish_params = {
            "creation_id": creation_id,
            "access_token": access_token
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            publish_response = await client.post(publish_url, params=publish_params)
            publish_response.raise_for_status()
            publish_data = publish_response.json()

        post_id = publish_data.get("id")

        return {
            "success": True,
            "post_id": post_id,
            "post_url": f"https://www.instagram.com/reel/{post_id}",
            "status": "published"
        }


class TikTokService:
    """TikTok Content Posting API integration"""

    def __init__(self):
        self.base_url = "https://open.tiktokapis.com/v2"

    async def publish_video(
        self,
        access_token: str,
        video_url: str,
        title: str,
        privacy_level: str = "PUBLIC_TO_EVERYONE",
        disable_duet: bool = False,
        disable_comment: bool = False,
        disable_stitch: bool = False
    ) -> Dict[str, Any]:
        """
        Publish video to TikTok
        """
        # Initialize video upload
        init_url = f"{self.base_url}/post/publish/video/init/"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        init_data = {
            "post_info": {
                "title": title[:150],  # TikTok title limit
                "privacy_level": privacy_level,
                "disable_duet": disable_duet,
                "disable_comment": disable_comment,
                "disable_stitch": disable_stitch
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url
            }
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            init_response = await client.post(init_url, headers=headers, json=init_data)

            if init_response.status_code != 200:
                error_data = init_response.json()
                raise Exception(f"TikTok API error: {error_data}")

            init_result = init_response.json()

        publish_id = init_result.get("data", {}).get("publish_id")

        if not publish_id:
            raise Exception(f"Failed to initialize TikTok video upload: {init_result}")

        return {
            "success": True,
            "post_id": publish_id,
            "status": "processing"  # TikTok processes video async
        }


class YouTubeService:
    """YouTube Data API v3 integration"""

    def __init__(self):
        self.client_id = settings.YOUTUBE_CLIENT_ID
        self.client_secret = settings.YOUTUBE_CLIENT_SECRET

    async def download_video(self, video_url: str) -> str:
        """Download video from URL to temp file"""
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(video_url)
            response.raise_for_status()

            # Create temp file
            fd, temp_path = tempfile.mkstemp(suffix=".mp4")
            try:
                with os.fdopen(fd, 'wb') as f:
                    f.write(response.content)
                return temp_path
            except:
                os.unlink(temp_path)
                raise

    async def publish_short(
        self,
        access_token: str,
        refresh_token: str,
        video_url: str,
        title: str,
        description: str,
        tags: List[str] = None,
        privacy_status: str = "private"
    ) -> Dict[str, Any]:
        """
        Publish Short to YouTube
        """
        # Ensure #Shorts in description
        if "#Shorts" not in description and "#shorts" not in description:
            description += " #Shorts"

        # Build credentials from tokens
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret
        )

        # Download video to temp file (YouTube API needs local file)
        video_file_path = await self.download_video(video_url)

        try:
            youtube = build("youtube", "v3", credentials=credentials)

            body = {
                "snippet": {
                    "title": title[:100],  # YouTube title limit
                    "description": description[:5000],
                    "tags": tags or [],
                    "categoryId": "22"  # People & Blogs
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False
                }
            }

            media = MediaFileUpload(
                video_file_path,
                mimetype="video/mp4",
                resumable=True
            )

            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()

            video_id = response.get("id")

            return {
                "success": True,
                "post_id": video_id,
                "post_url": f"https://youtube.com/shorts/{video_id}",
                "status": "published"
            }
        finally:
            # Cleanup temp file
            if os.path.exists(video_file_path):
                os.unlink(video_file_path)


class SocialMediaPublisher:
    """Unified publisher for all platforms"""

    def __init__(self):
        self.instagram = InstagramService()
        self.tiktok = TikTokService()
        self.youtube = YouTubeService()

    async def publish(
        self,
        platform: str,
        video_url: str,
        title: str,
        description: str,
        access_token: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Publish to selected platform
        """
        try:
            if platform == "instagram":
                business_account_id = kwargs.get("business_account_id")
                if not access_token or not business_account_id:
                    raise ValueError("Instagram requires access_token and business_account_id")

                result = await self.instagram.publish_reel(
                    video_url=video_url,
                    caption=description,
                    access_token=access_token,
                    business_account_id=business_account_id
                )

            elif platform == "tiktok":
                if not access_token:
                    raise ValueError("TikTok requires access_token")

                result = await self.tiktok.publish_video(
                    access_token=access_token,
                    video_url=video_url,
                    title=title
                )

            elif platform == "youtube":
                refresh_token = kwargs.get("refresh_token")
                if not access_token:
                    raise ValueError("YouTube requires access_token")

                result = await self.youtube.publish_short(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    video_url=video_url,
                    title=title,
                    description=description,
                    tags=kwargs.get("tags", []),
                    privacy_status=kwargs.get("privacy_status", "public")
                )

            else:
                raise ValueError(f"Unsupported platform: {platform}")

            return {
                "platform": platform,
                **result
            }

        except Exception as e:
            return {
                "success": False,
                "platform": platform,
                "error_message": str(e),
                "status": "failed"
            }


# Singleton instance
social_publisher = SocialMediaPublisher()
