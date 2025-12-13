import json
from datetime import datetime
from typing import List
from zoneinfo import ZoneInfo

from fastapi import File, UploadFile
from sqlalchemy.orm import Session

from Config.EnvConfig import EnvConfig
from Database.Database import SessionLocal
from PydanticModels.SocialMediaModule.SocialMediaModule import (
    PostPublishRecords,
    SocialMediaPostBackgroundTaskData,
)
from routes.SocialMediaModule.Services.FacebookService import FacebookService
from routes.SocialMediaModule.Services.TwitterService import TwitterService
from SqlModels import Models

facebook_service = FacebookService(
    app_id=EnvConfig.META_APP_ID,
    app_secret=EnvConfig.META_APP_SECRET,
    redirect_uri=f"{EnvConfig.BACKEND_BASE_URL}/social/media/accounts/authenticate/facebook/callback",
)

twitter_service = TwitterService(
    consumer_key=EnvConfig.TWITTER_CONSUMER_KEY,
    consumer_secret=EnvConfig.TWITTER_CONSUMER_SECRETE,
    callback_uri=f"{EnvConfig.BACKEND_BASE_URL}/social/media/accounts/authenticate/twitter/callback",
)


def beautifyErrorMessage(error_records: list):
    error_message = []
    for data in error_records:
        error_message.append(
            f"posted_with_errors_for_{data.get('platform')}:-> {data.get('error')}"
        )
    return ",".join(error_message)


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

        social_media_accounts = (
            db.query(Models.SocialMediaAccount)
            .filter(Models.SocialMediaAccount.organization_id == organization_id)
            .all()
        )

        post_publish_records = []
        error_records = []

        for account in social_media_accounts:
            try:
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

                elif account.platform == "instagram" and "instagram" in platforms:
                    instagram_result = facebook_service.post_to_instagram(
                        account.extra_data.get("page_id"),
                        account.access_token,
                        caption=data.caption,
                        media_urls=data.uploaded_file_url,
                    )

                    post_publish_records.append(
                        {"platform": "instagram", "post_id": instagram_result.get("id")}
                    )

                elif account.platform == "twitter" and "twitter" in platforms:
                    access_token = account.access_token
                    refresh_token = account.refresh_token

                    twitter_result = twitter_service.post_tweet(
                        access_token=access_token,
                        refresh_token=refresh_token,
                        text=data.caption,
                    )

                    post_publish_records.append(
                        {
                            "platform": "twitter",
                            "post_id": twitter_result.get("data", {}).get("data", {}).get("id"),
                        }
                    )

                    # Update tokens if refreshed
                    if twitter_result.get("auth_data"):
                        account.access_token = twitter_result["auth_data"].get("access_token")
                        account.refresh_token = twitter_result["auth_data"].get("refresh_token")

                db.commit()

            except Exception as inner_error:
                # Log failure but continue with the next platform
                db.rollback()
                error_message = f"{account.platform} posting failed: {str(inner_error)}"
                print(error_message)
                error_records.append({"platform": account.platform, "error": str(inner_error)})

        # Update post_data with results (even if partial)
        post_data.post_publish_records = json.dumps(post_publish_records)
        post_data.error_records = json.dumps(error_records)
        post_data.status = "posted"
        if error_records:

            post_data.post_logs = beautifyErrorMessage(error_records)
        else:
            post_data.post_logs = "posted_successfully"
        post_data.posted_at = datetime.now(ZoneInfo("UTC"))

        db.commit()

    except Exception as e:
        print(f"Critical Error: {str(e)}")

    finally:
        db.close()


def HandelDeletingPostFromSocialMediaAccount(organization_id: str, post_data: str):
    try:

        db: Session = SessionLocal()

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
            if post.get("platform") == "twitter":
                twitter_accounts = [
                    acc for acc in social_media_accounts if acc.platform == "twitter"
                ]

                twitter_service.delete_tweet(
                    tweet_id=post.get("post_id"),
                    access_token=twitter_accounts[0].access_token,
                    refresh_token=twitter_accounts[0].refresh_token,
                )

    except Exception as e:
        print(str(e))
