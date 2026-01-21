import json
from typing import List, Optional

import cloudinary
from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy import asc, desc
from sqlalchemy.orm import joinedload
from constants.constant import SUCCESS
from config.EnvConfig import EnvConfig
from database.Database import db_dependencies
from middleware.UserAuthenticator import UserAuthenticatorMiddleware
from middleware.verifyToken import verify_token
from models.sql import Models
from middleware.RateLimiting import limiter
from utils.helper.helper import filter_fields, model_to_filtered_dict
from utils.responseMessages import ERROR_MESSAGE, SUCCESS_MESSAGE

load_dotenv(override=True)

adminFeedControl = APIRouter(
    prefix="/app/v1/admin/organization-updates", tags=["organization-updates"]
)

API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING


cloudinary.config(
    cloud_name=EnvConfig.CLOUDINARY_CLOUD_NAME,
    api_key=EnvConfig.CLOUDINARY_API_KEY,
    api_secret=EnvConfig.CLOUDINARY_API_SECRET,
)


@adminFeedControl.post("/add-edit", status_code=status.HTTP_200_OK)
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
    token: str = Depends(verify_token),
):
    try:

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.UNAUTHORIZED, "success": SUCCESS.FALSE},
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.INVALID_SESSION, "success": SUCCESS.FALSE},
            )

        if type not in ["add", "edit"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={
                    "message": ERROR_MESSAGE.ONLY_ADD_OR_EDIT_ALLOWED,
                    "success": SUCCESS.FALSE,
                },
            )

        if type == "add":

            post_data = Models.AdminOrganizationUpdates(
                images=json.dumps(images),
                description=description,
                user_id=admin_id,
                isCommentDisabled=True,
                isLikeDisabled=True,
                source_type="announcement_team",
                announcement_type="product_update",
            )

            db.add(post_data)
            db.commit()

            return {
                "message": SUCCESS_MESSAGE.POST_UPLOADED_SUCCESSFULLY,
                "success": SUCCESS.TRUE,
                "data": model_to_filtered_dict(post_data),
            }

        else:
            if type == "edit" and not id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": ERROR_MESSAGE.ID_REQUIRED_FOR_EDIT,
                        "success": SUCCESS.FALSE,
                    },
                )

            existing_post = (
                db.query(Models.AdminOrganizationUpdates)
                .filter(Models.AdminOrganizationUpdates.id == id)
                .first()
            )

            if not existing_post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "message": ERROR_MESSAGE.POST_WITH_THIS_ID_NOT_FOUND,
                        "success": SUCCESS.FALSE,
                    },
                )

            if not existing_post.user_id == admin_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "message": ERROR_MESSAGE.NOT_AUTHORIZED,
                        "success": SUCCESS.FALSE,
                    },
                )

            existing_post.images = json.dumps(images)
            existing_post.description = description

            db.commit()
            db.refresh(existing_post)

            return {
                "message": SUCCESS_MESSAGE.POST_UPDATED_SUCCESSFULLY,
                "success": SUCCESS.TRUE,
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
                "message": ERROR_MESSAGE.ERROR_WHILE_POSTING_POST,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@adminFeedControl.get("/fetch-post", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def FetchTheOrganizationPost(
    request: Request,
    db: db_dependencies,
    order: Optional[str] = Query(None, description="This Is An Optional Field", alias="order"),
    field_name: Optional[str] = Query(
        None, description="This Is An Optional Field", alias="field_name"
    ),
    token: str = Depends(verify_token),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.UNAUTHORIZED, "success": SUCCESS.FALSE},
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.INVALID_SESSION, "success": SUCCESS.FALSE},
            )

        if not order:
            order = "asc"

        query_data = db.query(Models.AdminOrganizationUpdates)

        column_field = getattr(Models.AdminOrganizationUpdates, field_name, None)

        if not column_field:
            raise ValueError(f"{field_name} Not Found")

        if order == "asc":

            post_data = query_data.order_by(asc(column_field)).all()

        elif order == "desc":

            post_data = query_data.order_by(desc(column_field)).all()

        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": ERROR_MESSAGE.INVALID_INPUT,
                    "success": SUCCESS.FALSE,
                },
            )

        _data = []

        for data in post_data:
            post_info = model_to_filtered_dict(data)

            likes_info_array = []
            comment_array = []

            _data.append(
                {
                    "publisher": {
                        "full_name": "Team OrbitRMS",
                        "first_name": "Team",
                        "middle_name": "",
                        "last_name": "OrbitRMS",
                        "profile_picture": "https://res.cloudinary.com/ditphgtvl/image/upload/v1764827862/orbit-logo_dbry37.png",
                    },
                    "likes": likes_info_array,
                    "comments": comment_array,
                    **post_info,
                }
            )

        return {
            "message": SUCCESS_MESSAGE.POST_FETCHED_SUCCESSFULLY,
            "success": SUCCESS.TRUE,
            "data": _data,
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_FETCHING_POSTS,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )


@adminFeedControl.delete("/delete-post", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def HandelDeletePostFunction(
    request: Request,
    db: db_dependencies,
    id: str = Query(None, description="ID for delete operation"),
    token: str = Depends(verify_token),
):
    try:

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.UNAUTHORIZED, "success": SUCCESS.FALSE},
            )

        admin_id = token["admin_id"]
        session_id = token["session_id"]
        admin_signature = token["admin_signature"]

        admin = (
            db.query(Models.Admin)
            .options(joinedload(Models.Admin.admin_sessions))
            .filter(Models.Admin.id == admin_id)
            .first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.ADMIN_NOT_FOUND, "success": SUCCESS.FALSE},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": ERROR_MESSAGE.INVALID_SESSION, "success": SUCCESS.FALSE},
            )

        post = (
            db.query(Models.AdminOrganizationUpdates)
            .filter(Models.AdminOrganizationUpdates.id == id)
            .first()
        )

        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": ERROR_MESSAGE.POST_WITH_THIS_ID_NOT_FOUND,
                    "success": SUCCESS.FALSE,
                },
            )

        db.delete(post)
        db.commit()

        return {"success": SUCCESS.TRUE, "message": SUCCESS_MESSAGE.POST_DELETED_SUCCESSFULLY}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": ERROR_MESSAGE.ERROR_WHILE_DELETING_POST,
                "error": str(e),
                "success": SUCCESS.FALSE,
            },
        )
