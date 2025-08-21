from fastapi import (
    APIRouter,
    Request,
    status,
    HTTPException,
    Depends,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    Query,
)
from sqlalchemy.inspection import inspect
from sqlalchemy import asc, desc, and_
from typing import List, Optional

from Middleware.UserAuthenticator import UserAuthenticatorMiddleware
from BackgroundTasks.SocialMediaModule.SocialMediaModuleBackground import (
    HandelPostingToSocialMediaAccount,
    HandelDeletingPostFromSocialMediaAccount,
)
from PydanticModels.SocialMediaModule.SocialMediaModule import SocialMediaPostBackgroundTaskData
from Database.Database import db_dependencies
from RateLimiting import limiter
from Config.EnvConfig import EnvConfig
from Helper.helper import model_to_filtered_dict
from SqlModels import Models
import logging
import json
import cloudinary
import cloudinary.uploader
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
        organization = (
            db.query(Models.Organization)
            .filter(Models.Organization.id == user.organization_id)
            .first()
        )

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Unable To Find Organization", "success": False},
            )

        social_media_accounts = (
            db.query(Models.SocialMediaAccount)
            .filter(Models.SocialMediaAccount.organization_id == organization.id)
            .all()
        )

        return {
            "message": "Social Media Account Fetched SuccessFully",
            "success": True,
            "data": social_media_accounts if social_media_accounts else [],
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An error occurred during Fetch Social Accounts",
                "error": str(e),
            },
        )


@SocialAccount.post("/post/add", status_code=status.HTTP_200_OK)
@limiter.limit(EnvConfig.API_RATE_LIMITING)
async def Post_Content_To_Social_Media(
    request: Request,
    background_task: BackgroundTasks,
    db: db_dependencies,
    new_images: List[UploadFile] = File(...),
    caption: str = Form(...),
    existing_images: List[str] = Form(default=[]),
    platforms: List[str] = Form(default=[]),
    type: str = Form(...),
    scheduled_on: Optional[str] = Form(None),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        uploaded_file_url = []

        for image in new_images:

            file_bytes = await image.read()

            result = cloudinary.uploader.upload(file_bytes, resource_type="image")

            uploaded_file_url.append(result["secure_url"])

        post_data = Models.SocialMediaPosts(
            media_urls=json.dumps(uploaded_file_url),
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

        background_task_data = SocialMediaPostBackgroundTaskData(
            caption=caption, uploaded_file_url=uploaded_file_url
        )

        background_task.add_task(
            HandelPostingToSocialMediaAccount,
            user.organization_id,
            platforms,
            background_task_data,
            post_data.id,
        )

        return {
            "message": "Post Uploaded Successfully",
            "success": True,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An error occurred during Fetch Social Accounts",
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
                    "success": False,
                },
            )

        organization = (
            db.query(Models.Organization)
            .filter(Models.Organization.id == user.organization_id)
            .first()
        )

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "No Such Organization Found",
                    "success": False,
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
            "message": "Social Media Post Fetch Successfully",
            "success": True,
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
                "message": "An error occurred during Fetch Social Media Post",
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
        organization = (
            db.query(Models.Organization)
            .filter(Models.Organization.id == user.organization_id)
            .first()
        )

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "No Such Organization Found",
                    "success": False,
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
                    "message": "No Such Post Found",
                    "success": False,
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
            "message": "Post Deleted Successfully",
            "success": True,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An error occurred during Fetch Social Accounts",
                "error": str(e),
            },
        )
