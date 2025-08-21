from SqlModels import Models
from typing import List
from routes.SocialMediaModule.Services.FacebookService import FacebookService
from Config.EnvConfig import EnvConfig
from PydanticModels.SocialMediaModule.SocialMediaModule import (
    SocialMediaPostBackgroundTaskData,
    PostPublishRecords,
)
import json
from Database.Database import SessionLocal
from sqlalchemy.orm import Session
from datetime import datetime
from zoneinfo import ZoneInfo


def HandelPostingToSocialMediaAccount(
    organization_id: str,
    platforms: List[str],
    data: SocialMediaPostBackgroundTaskData,
    db_post_id: str,
):
    try:

        db: Session = SessionLocal()

        post_data = (
            db.query(Models.SocialMediaPosts)
            .filter(Models.SocialMediaPosts.id == db_post_id)
            .first()
        )

        if not post_data:
            return

        facebook_service = FacebookService(
            app_id=EnvConfig.META_APP_ID,
            app_secret=EnvConfig.META_APP_SECRET,
            redirect_uri=f"{EnvConfig.BACKEND_BASE_URL}/social/media/accounts/authenticate/facebook/callback",
        )

        social_media_accounts = (
            db.query(Models.SocialMediaAccount)
            .filter(Models.SocialMediaAccount.organization_id == organization_id)
            .all()
        )
        post_publish_records = []

        for account in social_media_accounts:
            if account.platform == "facebook" and "facebook" in platforms:

                facebook_result = facebook_service.post_to_page(
                    account.extra_data.get("page_id"),
                    account.access_token,
                    message=data.caption,
                    media_urls=data.uploaded_file_url,
                )

                post_publish_records.append(
                    {"platform": "facebook", "post_id": facebook_result.get("id")}
                )

            if account.platform == "instagram" and "instagram" in platforms:

                instagram_result = facebook_service.post_to_instagram(
                    account.extra_data.get("page_id"),
                    account.access_token,
                    caption=data.caption,
                    media_urls=data.uploaded_file_url,
                )
                print(instagram_result)
                post_publish_records.append(
                    {"platform": "instagram", "post_id": instagram_result.get("id")}
                )

        post_data.post_publish_records = json.dumps(post_publish_records)
        post_data.status = "posted"
        post_data.posted_at = datetime.now(ZoneInfo("UTC"))

        db.commit()
    except Exception as e:
        print(str(e))


def HandelDeletingPostFromSocialMediaAccount(organization_id: str, post_data: str):
    try:

        db: Session = SessionLocal()

        facebook_service = FacebookService(
            app_id=EnvConfig.META_APP_ID,
            app_secret=EnvConfig.META_APP_SECRET,
            redirect_uri=f"{EnvConfig.BACKEND_BASE_URL}/social/media/accounts/authenticate/facebook/callback",
        )

        post_publish_records = json.loads(post_data)

        social_media_accounts = (
            db.query(Models.SocialMediaAccount)
            .filter(Models.SocialMediaAccount.organization_id == organization_id)
            .all()
        )
        for post in post_publish_records:

            if post.get("platform") == "facebook":

                fb_accounts = [acc for acc in social_media_accounts if acc.platform == "facebook"]

                facebook_service.delete_from_page(
                    post.get("post_id"),
                    fb_accounts[0].access_token,
                )

    except Exception as e:
        print(str(e))
