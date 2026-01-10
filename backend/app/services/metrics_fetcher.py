"""
Metrics Fetcher Service
Fetches video performance metrics from social platforms via their APIs
"""

import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core.config import settings

logger = logging.getLogger(__name__)


class InstagramMetricsFetcher:
    """Fetch metrics from Instagram Graph API"""

    def __init__(self):
        self.base_url = "https://graph.facebook.com/v18.0"

    async def fetch_media_insights(
        self,
        media_id: str,
        access_token: str
    ) -> Dict[str, int]:
        """
        Fetch insights for a specific media (Reel)

        Instagram metrics available:
        - plays (video views)
        - likes
        - comments
        - shares
        - saved
        - reach
        - impressions
        """
        metrics = "plays,likes,comments,shares,saved,reach"
        url = f"{self.base_url}/{media_id}/insights"
        params = {
            "metric": metrics,
            "access_token": access_token
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)

                if response.status_code != 200:
                    logger.error(f"Instagram API error: {response.text}")
                    return {}

                data = response.json()
                insights = {}

                for metric in data.get("data", []):
                    name = metric.get("name")
                    value = metric.get("values", [{}])[0].get("value", 0)
                    insights[name] = value

                return {
                    "views": insights.get("plays", 0),
                    "likes": insights.get("likes", 0),
                    "comments": insights.get("comments", 0),
                    "shares": insights.get("shares", 0),
                    "saves": insights.get("saved", 0),
                    "reach": insights.get("reach", 0)
                }

        except Exception as e:
            logger.error(f"Failed to fetch Instagram metrics: {e}")
            return {}


class TikTokMetricsFetcher:
    """Fetch metrics from TikTok API"""

    def __init__(self):
        self.base_url = "https://open.tiktokapis.com/v2"

    async def fetch_video_stats(
        self,
        video_id: str,
        access_token: str
    ) -> Dict[str, int]:
        """
        Fetch statistics for a specific video

        TikTok metrics available:
        - view_count
        - like_count
        - comment_count
        - share_count
        """
        url = f"{self.base_url}/video/query/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # TikTok requires fields specification
        params = {
            "fields": "id,like_count,comment_count,share_count,view_count"
        }

        body = {
            "filters": {
                "video_ids": [video_id]
            }
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, params=params, json=body)

                if response.status_code != 200:
                    logger.error(f"TikTok API error: {response.text}")
                    return {}

                data = response.json()
                videos = data.get("data", {}).get("videos", [])

                if not videos:
                    return {}

                video = videos[0]
                return {
                    "views": video.get("view_count", 0),
                    "likes": video.get("like_count", 0),
                    "comments": video.get("comment_count", 0),
                    "shares": video.get("share_count", 0)
                }

        except Exception as e:
            logger.error(f"Failed to fetch TikTok metrics: {e}")
            return {}


class YouTubeMetricsFetcher:
    """Fetch metrics from YouTube Data API"""

    def __init__(self):
        self.client_id = getattr(settings, "YOUTUBE_CLIENT_ID", None)
        self.client_secret = getattr(settings, "YOUTUBE_CLIENT_SECRET", None)

    async def fetch_video_stats(
        self,
        video_id: str,
        access_token: str,
        refresh_token: str = None
    ) -> Dict[str, int]:
        """
        Fetch statistics for a specific video

        YouTube metrics available:
        - viewCount
        - likeCount
        - commentCount
        - favoriteCount (не используется)

        Note: YouTube API doesn't provide share count directly
        """
        try:
            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret
            )

            youtube = build("youtube", "v3", credentials=credentials)

            request = youtube.videos().list(
                part="statistics",
                id=video_id
            )

            response = request.execute()
            items = response.get("items", [])

            if not items:
                return {}

            stats = items[0].get("statistics", {})

            return {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "shares": 0  # YouTube API doesn't expose shares
            }

        except Exception as e:
            logger.error(f"Failed to fetch YouTube metrics: {e}")
            return {}


class MetricsFetcher:
    """Unified metrics fetcher for all platforms"""

    def __init__(self):
        self.instagram = InstagramMetricsFetcher()
        self.tiktok = TikTokMetricsFetcher()
        self.youtube = YouTubeMetricsFetcher()

    async def fetch(
        self,
        platform: str,
        post_id: str,
        access_token: str,
        refresh_token: str = None
    ) -> Dict[str, int]:
        """
        Fetch metrics from specified platform

        Returns dict with: views, likes, comments, shares
        """
        if platform == "instagram":
            return await self.instagram.fetch_media_insights(post_id, access_token)

        elif platform == "tiktok":
            return await self.tiktok.fetch_video_stats(post_id, access_token)

        elif platform == "youtube":
            return await self.youtube.fetch_video_stats(post_id, access_token, refresh_token)

        else:
            logger.warning(f"Unknown platform: {platform}")
            return {}


# Singleton instance
metrics_fetcher = MetricsFetcher()
