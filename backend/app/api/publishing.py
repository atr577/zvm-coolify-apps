from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import logging
from app.db.base import get_db
from app.models.video import Video
from app.models.project import PublishResult
from app.models.user import User, SocialAccount, WorkspaceMember
from app.schemas.publishing import PublishRequest, PublishResponse
from app.services.social_service import social_publisher
from app.core.deps import get_current_user
from app.core.scheduler import schedule_metrics_for_video

logger = logging.getLogger(__name__)

router = APIRouter()


def get_user_workspace_ids(db: Session, user_id: int) -> List[int]:
    """Get all workspace IDs the user is a member of"""
    memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).all()
    return [m.workspace_id for m in memberships]


def verify_video_ownership(db: Session, video: Video, current_user: User):
    """Helper to verify user has access to the video via workspace"""
    workspace_ids = get_user_workspace_ids(db, current_user.id)
    if video.project.workspace_id not in workspace_ids:
        raise HTTPException(status_code=403, detail="Access denied")


def mark_video_published(video: Video):
    """Mark video as published (only on first publish)"""
    if not video.is_published:
        video.is_published = True
        video.published_at = datetime.utcnow()


@router.post("/instagram", response_model=PublishResponse)
async def publish_to_instagram(
    request: PublishRequest,
    social_account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Publish to Instagram Reels"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    # Get SocialAccount
    social_account = db.query(SocialAccount).filter(
        SocialAccount.id == social_account_id,
        SocialAccount.user_id == current_user.id,
        SocialAccount.platform == "instagram"
    ).first()
    if not social_account:
        raise HTTPException(status_code=404, detail="Instagram account not connected")

    if not social_account.is_active:
        raise HTTPException(status_code=400, detail="Instagram account is inactive")

    # Create publish record
    publish_record = PublishResult(
        video_id=video.id,
        platform="instagram",
        title=request.title,
        description=request.description,
        hashtags=request.hashtags.split() if request.hashtags else None,
        status="publishing"
    )
    db.add(publish_record)
    db.commit()
    db.refresh(publish_record)

    try:
        result = await social_publisher.publish(
            platform="instagram",
            video_url=request.video_url,
            title=request.title,
            description=request.description,
            access_token=social_account.access_token,
            business_account_id=social_account.platform_data.get("business_account_id") if social_account.platform_data else None
        )

        publish_record.status = "published"
        publish_record.post_id = result.get("post_id")
        publish_record.post_url = result.get("post_url")
        publish_record.published_at = datetime.utcnow()
        mark_video_published(video)
        db.commit()

        # Schedule metrics fetch jobs
        if publish_record.post_id:
            schedule_metrics_for_video(
                video_id=video.id,
                platform="instagram",
                post_id=publish_record.post_id,
                published_at=publish_record.published_at
            )
            logger.info(f"Scheduled metrics jobs for video {video.id} on Instagram")

        return PublishResponse(
            success=True,
            platform="instagram",
            post_id=result.get("post_id"),
            post_url=result.get("post_url"),
            status="published"
        )

    except Exception as e:
        publish_record.status = "failed"
        publish_record.error_message = str(e)
        db.commit()

        return PublishResponse(
            success=False,
            platform="instagram",
            error_message=str(e),
            status="failed"
        )


@router.post("/tiktok", response_model=PublishResponse)
async def publish_to_tiktok(
    request: PublishRequest,
    social_account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Publish to TikTok"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    social_account = db.query(SocialAccount).filter(
        SocialAccount.id == social_account_id,
        SocialAccount.user_id == current_user.id,
        SocialAccount.platform == "tiktok"
    ).first()
    if not social_account:
        raise HTTPException(status_code=404, detail="TikTok account not connected")

    if not social_account.is_active:
        raise HTTPException(status_code=400, detail="TikTok account is inactive")

    publish_record = PublishResult(
        video_id=video.id,
        platform="tiktok",
        title=request.title,
        description=request.description,
        hashtags=request.hashtags.split() if request.hashtags else None,
        status="publishing"
    )
    db.add(publish_record)
    db.commit()
    db.refresh(publish_record)

    try:
        result = await social_publisher.publish(
            platform="tiktok",
            video_url=request.video_url,
            title=request.title,
            description=request.description,
            access_token=social_account.access_token
        )

        publish_record.status = result.get("status", "processing")
        publish_record.post_id = result.get("post_id")
        publish_record.published_at = datetime.utcnow()
        if publish_record.status == "published":
            mark_video_published(video)
        db.commit()

        # Schedule metrics fetch jobs
        if publish_record.post_id:
            schedule_metrics_for_video(
                video_id=video.id,
                platform="tiktok",
                post_id=publish_record.post_id,
                published_at=publish_record.published_at
            )
            logger.info(f"Scheduled metrics jobs for video {video.id} on TikTok")

        return PublishResponse(
            success=True,
            platform="tiktok",
            post_id=result.get("post_id"),
            status=result.get("status", "processing")
        )

    except Exception as e:
        publish_record.status = "failed"
        publish_record.error_message = str(e)
        db.commit()

        return PublishResponse(
            success=False,
            platform="tiktok",
            error_message=str(e),
            status="failed"
        )


@router.post("/youtube", response_model=PublishResponse)
async def publish_to_youtube(
    request: PublishRequest,
    social_account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Publish to YouTube Shorts (or update if already published)"""
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    social_account = db.query(SocialAccount).filter(
        SocialAccount.id == social_account_id,
        SocialAccount.user_id == current_user.id,
        SocialAccount.platform == "youtube"
    ).first()
    if not social_account:
        raise HTTPException(status_code=404, detail="YouTube account not connected")

    if not social_account.is_active:
        raise HTTPException(status_code=400, detail="YouTube account is inactive")

    # Check if already published to YouTube
    existing_publish = db.query(PublishResult).filter(
        PublishResult.video_id == video.id,
        PublishResult.platform == "youtube",
        PublishResult.status == "published",
        PublishResult.post_id.isnot(None)
    ).first()

    # Prepare description with hashtags
    description = request.description or ""
    if request.hashtags:
        description = f"{description}\n\n{request.hashtags}"

    try:
        if existing_publish:
            # UPDATE existing video on YouTube
            result = await social_publisher.update(
                platform="youtube",
                post_id=existing_publish.post_id,
                title=request.title,
                description=description,
                access_token=social_account.access_token,
                refresh_token=social_account.refresh_token,
                tags=[],
                thumbnail_url=video.image_url
            )

            # Update existing record
            existing_publish.title = request.title
            existing_publish.description = request.description
            existing_publish.hashtags = request.hashtags.split() if request.hashtags else None
            existing_publish.updated_at = datetime.utcnow()
            db.commit()

            return PublishResponse(
                success=True,
                platform="youtube",
                post_id=existing_publish.post_id,
                post_url=existing_publish.post_url,
                status="updated"
            )

        else:
            # CREATE new video on YouTube
            publish_record = PublishResult(
                video_id=video.id,
                platform="youtube",
                title=request.title,
                description=request.description,
                hashtags=request.hashtags.split() if request.hashtags else None,
                status="publishing"
            )
            db.add(publish_record)
            db.commit()
            db.refresh(publish_record)

            result = await social_publisher.publish(
                platform="youtube",
                video_url=request.video_url,
                title=request.title,
                description=description,
                access_token=social_account.access_token,
                refresh_token=social_account.refresh_token,
                tags=[],
                privacy_status=request.privacy_status or "public",
                thumbnail_url=video.image_url
            )

            publish_record.status = "published"
            publish_record.post_id = result.get("post_id")
            publish_record.post_url = result.get("post_url")
            publish_record.published_at = datetime.utcnow()
            mark_video_published(video)
            db.commit()

            # Schedule metrics fetch jobs
            if publish_record.post_id:
                schedule_metrics_for_video(
                    video_id=video.id,
                    platform="youtube",
                    post_id=publish_record.post_id,
                    published_at=publish_record.published_at
                )
                logger.info(f"Scheduled metrics jobs for video {video.id} on YouTube")

            return PublishResponse(
                success=True,
                platform="youtube",
                post_id=result.get("post_id"),
                post_url=result.get("post_url"),
                status="published"
            )

    except Exception as e:
        if not existing_publish:
            # Only update status for new publish attempts
            publish_record = db.query(PublishResult).filter(
                PublishResult.video_id == video.id,
                PublishResult.platform == "youtube",
                PublishResult.status == "publishing"
            ).first()
            if publish_record:
                publish_record.status = "failed"
                publish_record.error_message = str(e)
                db.commit()

        return PublishResponse(
            success=False,
            platform="youtube",
            error_message=str(e),
            status="failed"
        )


@router.get("/status/{video_id}")
async def get_publish_status(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get publishing status for a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    verify_video_ownership(db, video, current_user)

    publish_results = db.query(PublishResult).filter(
        PublishResult.video_id == video_id
    ).all()

    return {
        "video_id": video_id,
        "results": [
            {
                "id": r.id,
                "platform": r.platform,
                "status": r.status,
                "post_id": r.post_id,
                "post_url": r.post_url,
                "error_message": r.error_message,
                "published_at": r.published_at
            }
            for r in publish_results
        ]
    }


@router.post("/retry/{publish_result_id}")
async def retry_publish(
    publish_result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry a failed publication"""
    publish_result = db.query(PublishResult).filter(
        PublishResult.id == publish_result_id
    ).first()

    if not publish_result:
        raise HTTPException(status_code=404, detail="Publish result not found")

    video = publish_result.video
    verify_video_ownership(db, video, current_user)

    if publish_result.status != "failed":
        raise HTTPException(status_code=400, detail="Can only retry failed publications")

    # Reset status
    publish_result.status = "pending"
    publish_result.error_message = None
    db.commit()

    return {"message": "Ready for retry", "publish_result_id": publish_result_id}
