import json
import math
import os
from typing import List, Optional

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.encoders import jsonable_encoder
from sqlalchemy import asc, desc
from sqlalchemy.orm import joinedload

from config.EnvConfig import EnvConfig
from database.CacheDatabase import cache_database
from database.Database import db_dependencies
from middleware.UserAuthenticator import UserAuthenticatorMiddleware
from middleware.verifyToken import verify_token
from models.pydantic.Organizations.FeedControllerPydenticModal import FeedCommentData
from models.sql import Models
from RateLimiting import limiter
from utils.helper.helper import filter_fields, model_to_filtered_dict

load_dotenv(override=True)

feedControl = APIRouter(prefix="/app/v1/feed", tags=["Feed"])

API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING


cloudinary.config(
    cloud_name=EnvConfig.CLOUDINARY_CLOUD_NAME,
    api_key=EnvConfig.CLOUDINARY_API_KEY,
    api_secret=EnvConfig.CLOUDINARY_API_SECRET,
)


@feedControl.post("/add-edit", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def AddEditFeedPostController(
    request: Request,
    db: db_dependencies,
    type: str = Query(..., description="The Type Must Be Add or Edit"),
    description: str = File(...),
    isCommentDisabled: bool = File(...),
    isLikeDisabled: bool = File(...),
    videos: List[str] = Form(default=[]),
    images: List[str] = Form(default=[]),
    id: Optional[str] = Query(None, description="ID for edit operation"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        if type not in ["add", "edit"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={"message": "Only Add Or Edit Is Allowed", "success": False},
            )

        if type == "add":

            post_data = Models.OrganizationUpdates(
                images=json.dumps(images),
                description=description,
                user_id=user.id,
                isCommentDisabled=isCommentDisabled,
                isLikeDisabled=isLikeDisabled,
                organization_id=user.organization_id,
                source_type="user",
                announcement_type="general",
            )

            db.add(post_data)
            db.commit()

            return {
                "message": "Post Uploaded Successfully",
                "success": True,
                "data": model_to_filtered_dict(post_data),
            }

        else:
            if type == "edit" and not id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "ID is required for edit operation",
                        "success": False,
                    },
                )

            existing_post = (
                db.query(Models.OrganizationUpdates)
                .filter(Models.OrganizationUpdates.id == id)
                .first()
            )

            if not existing_post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "message": "Post With This Id Not Found",
                        "success": False,
                    },
                )

            if not existing_post.user_id == user.id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "message": "You Are Not Authorised",
                        "success": False,
                    },
                )

            existing_post.images = json.dumps(images)
            existing_post.description = description
            existing_post.isCommentDisabled = isCommentDisabled
            existing_post.isLikeDisabled = isLikeDisabled

            db.commit()
            db.refresh(existing_post)

            return {
                "message": "Post Updated Successfully",
                "success": True,
                "data": model_to_filtered_dict(existing_post),
            }

        #
        # *  Once The User Is Authenticated Then We Will Move Further
        #
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "error while Posting A Post",
                "error": str(e),
                "success": False,
            },
        )


@feedControl.get("/fetch-post", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def FetchTheOrganizationPost(
    request: Request,
    db: db_dependencies,
    order: Optional[str] = Query(None, description="This Is An Optional Field", alias="order"),
    field_name: Optional[str] = Query(
        None, description="This Is An Optional Field", alias="field_name"
    ),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        if not order:
            order = "asc"

        organization_updates = (
            db.query(Models.OrganizationUpdates)
            .options(
                joinedload(Models.OrganizationUpdates.publisher).joinedload(
                    Models.User.personal_info
                ),
                joinedload(Models.OrganizationUpdates.publisher).joinedload(
                    Models.User.employee_info
                ),
            )
            .filter(Models.OrganizationUpdates.organization_id == user.organization_id)
            .all()
        )

        admin_updates = db.query(Models.AdminOrganizationUpdates).all()

        query_data = organization_updates + admin_updates

        if order not in ["asc", "desc"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Invalid Input",
                    "success": False,
                },
            )

        reverse = True if order == "desc" else False

        post_data = sorted(query_data, key=lambda x: getattr(x, field_name, None), reverse=reverse)

        _data = []

        for data in post_data:

            post_info = model_to_filtered_dict(data)

            publisher = {}

            likes_info_array = []
            comment_array = []

            if data.source_type not in ["announcement_team"]:
                publisher_personal_info = (
                    filter_fields(
                        data.publisher.personal_info,
                        ["full_name", "first_name", "middle_name", "last_name", "profile_picture"],
                    )
                    if data.publisher
                    else {}
                )

                publisher_employee_info = (
                    filter_fields(
                        data.publisher.employee_info, ["department", "designation", "employee_code"]
                    )
                    if data.publisher
                    else {}
                )

                likes_info_array = [like.user_id for like in data.likes]
                comment_array = [comment.id for comment in data.comments]

                publisher = {
                    **publisher_personal_info,
                    "id": data.publisher.id,
                    **publisher_employee_info,
                }

            else:
                publisher = {
                    "full_name": "Team OrbitRMS",
                    "first_name": "Team",
                    "middle_name": "",
                    "last_name": "OrbitRMS",
                    "profile_picture": "https://res.cloudinary.com/ditphgtvl/image/upload/v1764827862/orbit-logo_dbry37.png",
                }

            _data.append(
                {
                    "publisher": publisher,
                    "likes": likes_info_array,
                    "comments": comment_array,
                    **post_info,
                }
            )

        return {
            "message": "Post Fetched Successfully",
            "success": True,
            "data": _data,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error while Fetching Posts",
                "error": str(e),
                "success": False,
            },
        )


@feedControl.delete("/delete-post", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def HandelDeletePostFunction(
    request: Request,
    db: db_dependencies,
    id: str = Query(None, description="ID for delete operation"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

        post = (
            db.query(Models.OrganizationUpdates).filter(Models.OrganizationUpdates.id == id).first()
        )

        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Post With This Id Not Found",
                    "success": False,
                },
            )

        db.delete(post)
        db.commit()

        return {"success": True, "message": "Post Deleted Successfully"}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error while Deleting a Post",
                "error": str(e),
                "success": False,
            },
        )


@feedControl.put("/like/toggle", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def HandelLikeUnlikePostFunction(
    request: Request,
    db: db_dependencies,
    post_id: str = Query(..., alias="post-id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        user_like_redis_key = f"user:{user.id}:liked_posts"
        post_like_count_key = f"post:{post_id}:likes"

        existing_like = await cache_database.sismember(user_like_redis_key, post_id)

        if existing_like:

            await cache_database.srem(user_like_redis_key, post_id)
            await cache_database.decr(post_like_count_key)

            event = {"post_id": post_id, "user_id": user.id, "action": "unlike"}
            await cache_database.rpush("likes_queue", json.dumps(event))

            return {
                "message": "Like removed",
                "success": True,
                "data": {"liked": False, "action": "unlike"},
            }

        await cache_database.sadd(user_like_redis_key, post_id)
        await cache_database.incr(post_like_count_key)

        event = {"post_id": post_id, "user_id": user.id, "action": "like"}

        await cache_database.rpush("likes_queue", json.dumps(event))

        return {
            "message": "Like registered",
            "success": True,
            "data": {"liked": True, "action": "like"},
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error while Deleting a Post",
                "error": str(e),
                "success": False,
            },
        )


@feedControl.put("/comment/toggle", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def HandelLikeUnlikePostFunction(
    request: Request,
    db: db_dependencies,
    data: FeedCommentData,
    post_id: str = Query(..., alias="post-id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:
        user_comment_redis_key = f"user:{user.id}:comment_on_post"
        post_comment_count_key = f"post:{post_id}:comment"

        await cache_database.sadd(user_comment_redis_key, post_id)
        await cache_database.incr(post_comment_count_key)

        event = {
            "post_id": post_id,
            "user_id": user.id,
            "comment": data.comment,
            "is_replay": False,
        }

        await cache_database.rpush("comment_queue", json.dumps(event))

        return {
            "message": "Comment registered",
            "success": True,
            "data": {
                "commented": True,
                "user_id": user.id,
            },
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error while Deleting a Post",
                "error": str(e),
                "success": False,
            },
        )


@feedControl.put("/comment/replay/toggle", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def HandelCommentReplayToggler(
    request: Request,
    db: db_dependencies,
    data: FeedCommentData,
    user: dict = Depends(UserAuthenticatorMiddleware),
    post_id: str = Query(..., alias="post-id"),
    comment_id: str = Query(..., alias="comment-id"),
):
    try:
        cache_data_key = f"feed_post_{post_id}_comments"
        cache_data = await cache_database.get(cache_data_key)
        if cache_data:
            await cache_database.delete(cache_data_key)

        post_data = (
            db.query(Models.OrganizationUpdates)
            .filter(Models.OrganizationUpdates.id == post_id)
            .first()
        )
        if not post_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Unable To Find The Post",
                    "success": False,
                },
            )

        parent_comment = (
            db.query(Models.FeedComments).filter(Models.FeedComments.id == comment_id).first()
        )

        if not parent_comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Unable To Find The Comment",
                    "success": False,
                },
            )

        comment_reply = Models.FeedComments(
            is_replay=True,
            comment=data.comment,
            parent_id=comment_id,
            user_id=user.id,
            organization_update_id=post_id,
        )

        db.add(comment_reply)
        db.commit()

        return {"message": "Comment Added Successfully", "success": True}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error while Deleting a Post",
                "error": str(e),
                "success": False,
            },
        )


def serialize_comment(comment):
    comment_personal_info = (
        filter_fields(
            comment.user.personal_info,
            ["full_name", "first_name", "middle_name", "last_name", "profile_picture"],
        )
        if comment.user
        else {}
    )
    comment_employee_info = (
        filter_fields(
            comment.user.employee_info,
            ["department", "designation", "employee_code"],
        )
        if comment.user
        else {}
    )
    return {
        "id": comment.id,
        "user_id": comment.user_id,
        "comment": comment.comment,
        **comment_personal_info,
        **comment_employee_info,
    }


def serialize_likes(likes):
    comment_personal_info = (
        filter_fields(
            likes.user.personal_info,
            ["full_name", "first_name", "middle_name", "last_name", "profile_picture"],
        )
        if likes.user
        else {}
    )
    comment_employee_info = (
        filter_fields(
            likes.user.employee_info,
            ["department", "designation", "employee_code"],
        )
        if likes.user
        else {}
    )
    return {
        "id": likes.id,
        "user_id": likes.user_id,
        "comment": likes.likes,
        **comment_personal_info,
        **comment_employee_info,
    }


def get_replies(comment_id, all_comments):
    replies = []

    for reply in all_comments:
        if reply.parent_id == comment_id:
            serialize = serialize_comment(reply)
            replies.append(serialize)
            replies.extend(get_replies(reply.id, all_comments))

    return replies


@feedControl.get("/fetch", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def FetchLikesAndComment(
    request: Request,
    db: db_dependencies,
    post_id: str = Query(..., alias="post-id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
    type: str = Query(..., alias="type"),
    page: int = Query(..., alias="page"),
    limit: int = Query(..., alias="limit"),
):
    try:
        if type not in ["likes", "comments"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={"message": "Only Like Or Comment Is Allowed", "success": False},
            )

        cache_data_key = f"feed_post_{post_id}_{type}"
        cached_data = await cache_database.get(cache_data_key)

        if cached_data:
            cached_Data = json.loads(cached_data)
            # cached_sorted_data = sorted(
            #     cached_Data,
            #     key=lambda x: datetime.fromisoformat(x["created_at"]),
            #     reverse=True if order.lower() == "desc" else False,
            # )
            return {
                "message": f"{type} Fetched Successfully. Cached!",
                "success": True,
                "data": cached_Data,
            }

        query_option = (
            joinedload(Models.OrganizationUpdates.likes).joinedload(Models.FeedLikes.user)
            if type == "likes"
            else joinedload(Models.OrganizationUpdates.comments).joinedload(
                Models.FeedComments.user
            )
        )

        query_data = (
            db.query(Models.OrganizationUpdates)
            .options(query_option)
            .filter(Models.OrganizationUpdates.id == post_id)
            .first()
        )

        if type == "likes":

            cache_data_key = f"feed_post_{post_id}_{type}"

            likes_info_array = []

            for like in query_data.likes:

                likes_info_array.append(serialize_likes(like))

                await cache_database.set(
                    cache_data_key,
                    json.dumps(
                        jsonable_encoder(
                            {
                                "likes": likes_info_array,
                                "total_likes": [like.id for like in query_data.likes],
                            }
                        )
                    ),
                    ex=3600,
                )
            return {
                "message": "Likes Fetched Successfully",
                "success": True,
                "data": {
                    "likes": likes_info_array,
                    "total_likes": [like.id for like in query_data.likes],
                },
            }
        else:
            all_comment = query_data.comments

            parent_comments = [comment for comment in all_comment if comment.parent_id is None]
            comment_replies = [comment for comment in all_comment if comment.parent_id is not None]

            comment_info_array = []

            page = page if page else 1
            limit = limit if limit else 1
            start = (page - 1) * limit
            end = start + limit

            for parent in parent_comments:
                parent_data = serialize_comment(parent)
                parent_replies_array = get_replies(parent.id, comment_replies)
                parent_data["replies"] = parent_replies_array[start:end]
                parent_data["metadata"] = (
                    {
                        "total_data": len(parent_replies_array),
                        "total_pages": math.ceil(len(parent_replies_array) / limit),
                        "current_page": page,
                        "record_per_page": limit,
                    },
                )[0]

                comment_info_array.append(parent_data)

            await cache_database.set(
                cache_data_key,
                json.dumps(
                    jsonable_encoder(
                        {
                            "comments": comment_info_array,
                            "total_comments": [comment.id for comment in all_comment],
                        }
                    )
                ),
                ex=3600,
            )

            return {
                "message": "Comments Fetched Successfully",
                "success": True,
                "data": {
                    "comments": comment_info_array,
                    "total_comments": [comment.id for comment in all_comment],
                },
            }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error while Deleting a Post",
                "error": str(e),
                "success": False,
            },
        )


@feedControl.get("/fetch-replies", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def FetchLikesAndComment(
    request: Request,
    db: db_dependencies,
    post_id: str = Query(..., alias="post-id"),
    comment_id: str = Query(..., alias="comment-id"),
    user: dict = Depends(UserAuthenticatorMiddleware),
    page: int = Query(..., alias="page"),
    limit: int = Query(..., alias="limit"),
):
    try:

        query_option = (
            joinedload(Models.OrganizationUpdates.likes).joinedload(Models.FeedLikes.user)
            if type == "likes"
            else joinedload(Models.OrganizationUpdates.comments).joinedload(
                Models.FeedComments.user
            )
        )

        query_data = (
            db.query(Models.OrganizationUpdates)
            .options(query_option)
            .filter(Models.OrganizationUpdates.id == post_id)
            .first()
        )

        all_comment = query_data.comments

        comment_replies = [comment for comment in all_comment if comment.parent_id is not None]

        page = page if page else 1
        limit = limit if limit else 1
        start = (page - 1) * limit
        end = start + limit

        parent_replies_array = get_replies(comment_id, comment_replies)

        return {
            "message": "Comments Fetched Successfully",
            "success": True,
            "data": parent_replies_array[start:end],
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error while Deleting a Post",
                "error": str(e),
                "success": False,
            },
        )
