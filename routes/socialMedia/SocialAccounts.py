import json
import logging
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import and_, asc, desc
from sqlalchemy.inspection import inspect

from config.EnvConfig import EnvConfig
from constants.constant import SUCCESS
from database.Database import db_dependencies
from jobs.backgroundTasks.socialMedia.SocialMediaModuleBackground import (
    HandelDeletingPostFromSocialMediaAccount,
    HandelPostingToSocialMediaAccount,
)
from middleware.RateLimiting import limiter
from middleware.UserAuthenticator import UserAuthenticatorMiddleware
from models.pydantic.SocialMediaModule.SocialMediaModule import (
    SocialMediaPostBackgroundTaskData,
)
from models.sql import Models
from utils.helper.helper import model_to_filtered_dict
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE

from .Services.FacebookService import FacebookService

# Set up logging
logger = logging.getLogger(__name__)

SocialAccount = APIRouter(prefix="/app/v1/social/media/accounts", tags=["accounts"])


@SocialAccount.get("/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(EnvConfig.API_RATE_LIMITING)
async def Fetch_All_The_Linked_Account(
    request: Request, db: db_dependencies, user: dict = Depends(UserAuthenticatorMiddleware)
):
    try:
        organization = db.query(Models.Organization).filter(Models.Organization.id == user.organization_id).first()

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": ERROR_MESSAGE.ORGANIZATION_NOT_FOUND, "success": SUCCESS.FAlSE},
            )

        social_media_accounts = (
            db.query(Models.SocialMediaAccount)
            .filter(Models.SocialMediaAccount.organization_id == organization.id)
            .all()
        )

        return {
            "message": SUCCESS_MESSAGE.SOCIAL_MEDIA_ACCOUNT_FETCHED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": social_media_accounts if social_media_accounts else [],
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_FETCHING_SOCIAL_ACCOUNTS,
                "error": str(e),
            },
        )


@SocialAccount.post("/post/add", status_code=status.HTTP_200_OK)
@limiter.limit(EnvConfig.API_RATE_LIMITING)
async def Post_Content_To_Social_Media(
    request: Request,
    background_task: BackgroundTasks,
    db: db_dependencies,
    videos: List[str] = Form(default=[]),
    images: List[str] = Form(default=[]),
    caption: str = Form(...),
    platforms: List[str] = Form(default=[]),
    type: str = Form(...),
    scheduled_on: Optional[str] = Form(None),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        post_data = Models.SocialMediaPosts(
            media_urls=json.dumps(images),
            caption=caption,
            type="default",
            status="queued",
            scheduled_on=None,
            post_publish_records=None,
            posted_at=None,
            organization_id=user.organization_id,
            selected_platforms=json.dumps(platforms),
            is_scheduled=False,
        )

        db.add(post_data)
        db.commit()

        background_task_data = SocialMediaPostBackgroundTaskData(caption=caption, uploaded_file_url=images)

        background_task.add_task(
            HandelPostingToSocialMediaAccount,
            user.organization_id,
            platforms,
            background_task_data,
            post_data.id,
        )

        return {
            "message": SUCCESS_MESSAGE.POST_UPDATED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_FETCHING_SOCIAL_ACCOUNTS,
                "error": str(e),
            },
        )


@SocialAccount.get("/post/fetch-all", status_code=status.HTTP_200_OK)
@limiter.limit(EnvConfig.API_RATE_LIMITING)
async def Fetch_All_Created_Scheduled_Posts(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    order: str = Query("asc", alias="order"),
    sort_by: str = Query("created_at", alias="sort_by"),
):
    try:

        valid_columns = [col.key for col in inspect(Models.SocialMediaPosts).columns]

        if sort_by not in valid_columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": f"Invalid sort_by field '{sort_by}'. Valid fields: {list(valid_columns)}",
                    "success": SUCCESS.FAlSE,
                },
            )

        organization = db.query(Models.Organization).filter(Models.Organization.id == user.organization_id).first()

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": ERROR_MESSAGE.ORGANIZATION_NOT_FOUND,
                    "success": SUCCESS.FAlSE,
                },
            )

        sort_func = asc if order.lower() == "asc" else desc

        social_media_posts = (
            db.query(Models.SocialMediaPosts)
            .filter(Models.SocialMediaPosts.organization_id == organization.id)
            .order_by(sort_func(getattr(Models.SocialMediaPosts, sort_by)))
            .all()
        )

        return {
            "message": SUCCESS_MESSAGE.SOCIAL_MEDIA_ACCOUNT_FETCHED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": [
                model_to_filtered_dict(
                    data,
                )
                for data in social_media_posts
            ],
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_FETCHING_SOCIAL_ACCOUNTS,
                "error": str(e),
            },
        )


@SocialAccount.delete("/post/delete", status_code=status.HTTP_200_OK)
@limiter.limit(EnvConfig.API_RATE_LIMITING)
async def Post_Content_To_Social_Media(
    request: Request,
    background_task: BackgroundTasks,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    id: str = Query(..., alias="id"),
):
    try:
        organization = db.query(Models.Organization).filter(Models.Organization.id == user.organization_id).first()

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": ERROR_MESSAGE.ORGANIZATION_NOT_FOUND,
                    "success": SUCCESS.FAlSE,
                },
            )

        post_data = (
            db.query(Models.SocialMediaPosts)
            .filter(
                and_(
                    Models.SocialMediaPosts.organization_id == organization.id,
                    Models.SocialMediaPosts.id == id,
                )
            )
            .first()
        )

        if not post_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": ERROR_MESSAGE.NO_POST_FOUND,
                    "success": SUCCESS.FAlSE,
                },
            )

        background_task.add_task(
            HandelDeletingPostFromSocialMediaAccount,
            user.organization_id,
            post_data.post_publish_records,
        )

        db.delete(post_data)
        db.commit()
        return {
            "message": ERROR_MESSAGE.POST_DELETED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_FETCHING_SOCIAL_ACCOUNTS,
                "error": str(e),
            },
        )


#  This are The Api That Will Be Used To Disconnect The the Social Media Account
@SocialAccount.put("/status/toggle", status_code=status.HTTP_200_OK)
@limiter.limit(EnvConfig.API_RATE_LIMITING)
async def handel_disconnecting_social_media_account(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    account_id: str = Query(..., alias="id"),
):
    organization = db.query(Models.Organization).filter(Models.Organization.id == user.organization_id).first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": ERROR_MESSAGE.ORGANIZATION_NOT_FOUND, "success": SUCCESS.FAlSE},
        )

    social_media_account = (
        db.query(Models.SocialMediaAccount)
        .filter(
            Models.SocialMediaAccount.organization_id == organization.id,
            Models.SocialMediaAccount.id == account_id,
        )
        .first()
    )

    if not social_media_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.UNABLE_TO_FIND_SOCIAL_MEDIA_ACCOUNT,
                "success": SUCCESS.FAlSE,
            },
        )

    message = ""

    if social_media_account.is_active:
        social_media_account.is_active = False
        message = SUCCESS_MESSAGE.ACCOUNT_DEACTIVATED_SUCCESSFULLY
    else:
        social_media_account.is_active = True
        message = SUCCESS_MESSAGE.ACCOUNT_ACTIVATED_SUCCESSFULLY

    db.commit()

    return {
        "message": message,
        "success": SUCCESS.TRUE,
    }


@SocialAccount.put("/disconnect", status_code=status.HTTP_200_OK)
@limiter.limit(EnvConfig.API_RATE_LIMITING)
async def handel_disconnecting_social_media_account(
    request: Request,
    db: db_dependencies,
    user: dict = Depends(UserAuthenticatorMiddleware),
    account_id: str = Query(..., alias="id"),
):
    organization = db.query(Models.Organization).filter(Models.Organization.id == user.organization_id).first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": ERROR_MESSAGE.ORGANIZATION_NOT_FOUND, "success": SUCCESS.FAlSE},
        )

    social_media_account = (
        db.query(Models.SocialMediaAccount)
        .filter(
            Models.SocialMediaAccount.organization_id == organization.id,
            Models.SocialMediaAccount.id == account_id,
        )
        .first()
    )

    if not social_media_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": ERROR_MESSAGE.UNABLE_TO_FIND_SOCIAL_MEDIA_ACCOUNT,
                "success": SUCCESS.FAlSE,
            },
        )

    db.delete(social_media_account)
    db.commit()

    return {
        "message": SUCCESS_MESSAGE.SOCIAL_MEDIA_ACCOUNT_DISCONNECTED_SUCCESSFULLY,
        "success": SUCCESS.TRUE,
    }
