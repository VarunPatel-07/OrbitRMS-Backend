import json
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
from sqlalchemy import asc, desc
from sqlalchemy.orm import joinedload

from Database.Database import db_dependencies
from Helper.helper import filter_fields, model_to_filtered_dict
from Middleware.verifyToken import verify_token
from RateLimiting import limiter
from SqlModels import Models

load_dotenv(override=True)

feedControl = APIRouter(prefix="/app/v1/feed", tags=["Feed"])

API_RATE_LIMITING = os.getenv("API_RATE_LIMITING")


cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)


@feedControl.post("/add-edit", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def AddEditFeedPostController(
    request: Request,
    db: db_dependencies,
    type: str = Query(..., description="The Type Must Be Add or Edit"),
    token: str = Depends(verify_token),
    description: str = File(...),
    isCommentDisabled: bool = File(...),
    isLikeDisabled: bool = File(...),
    new_images: List[UploadFile] = File(default=[]),
    existing_images: List[str] = Form(default=[]),
    id: Optional[str] = Query(None, description="ID for edit operation"),
):
    try:
        #
        # *  We Will Firstly Check For The User's Authentication
        #
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        session_id = token["session_id"]

        user = (
            db.query(Models.User)
            .options(joinedload(Models.User.sessions), joinedload(Models.User.organization))
            .filter(Models.User.id == user_id)
            .first()
        )

        if not user or not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Account is deactivated. Access denied."
                        if user.account_status
                        else "User Not Found"
                    ),
                    "success": False,
                },
            )

        if not user.organization.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        # We Will Also Check For The Relevant Session That This Particular Session Exists Or Not

        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
                headers={"WWW-Authenticate": "Bearer"},
            )

        if type not in ["add", "edit"]:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail={"message": "Only Add Or Edit Is Allowed", "success": False},
            )

        if type == "add":

            uploaded_file_url = []

            for img in new_images:
                file_bytes = await img.read()
                result = cloudinary.uploader.upload(file_bytes, resource_type="image")
                uploaded_file_url.append(result["secure_url"])

            post_data = Models.OrganizationUpdates(
                images=json.dumps(uploaded_file_url),
                description=description,
                user_id=user.id,
                isCommentDisabled=isCommentDisabled,
                isLikeDisabled=isLikeDisabled,
                organization_id=user.organization_id,
                source_type="user_created",
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

            if not existing_post.user_id == user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "message": "You Are Not Authorised",
                        "success": False,
                    },
                )

            uploaded_file_url = []

            for img in new_images:
                file_bytes = await img.read()
                result = cloudinary.uploader.upload(file_bytes, resource_type="image")
                uploaded_file_url.append(result["secure_url"])

            final_images = existing_images + uploaded_file_url

            existing_post.images = json.dumps(final_images)
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
    token: str = Depends(verify_token),
    order: Optional[str] = Query(None, description="This Is An Optional Field", alias="order"),
    field_name: Optional[str] = Query(
        None, description="This Is An Optional Field", alias="field_name"
    ),
):
    try:
        if not order:
            order = "asc"
        #
        # *  We Will Firstly Check For The User's Authentication
        #
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        session_id = token["session_id"]

        user = (
            db.query(Models.User)
            .options(joinedload(Models.User.sessions), joinedload(Models.User.organization))
            .filter(Models.User.id == user_id)
            .first()
        )

        if not user or not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Account is deactivated. Access denied."
                        if user.account_status
                        else "User Not Found"
                    ),
                    "success": False,
                },
            )

        if not user.organization.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        # We Will Also Check For The Relevant Session That This Particular Session Exists Or Not

        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
                headers={"WWW-Authenticate": "Bearer"},
            )

        query_data = (
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
        )

        column_field = getattr(Models.OrganizationUpdates, field_name, None)

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
                    "message": "Invalid Input",
                    "success": False,
                },
            )

        _data = []

        for data in post_data:
            post_info = model_to_filtered_dict(data)

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

            _data.append(
                {
                    "publisher": {
                        **publisher_personal_info,
                        "id": data.publisher.id,
                        **publisher_employee_info,
                    },
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
    token: str = Depends(verify_token),
    id: str = Query(None, description="ID for delete operation"),
):
    try:
        #
        # *  We Will Firstly Check For The User's Authentication
        #
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        user_id = token["user_id"]

        session_id = token["session_id"]

        user = (
            db.query(Models.User)
            .options(joinedload(Models.User.sessions), joinedload(Models.User.organization))
            .filter(Models.User.id == user_id)
            .first()
        )

        if not user or not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Account is deactivated. Access denied."
                        if user.account_status
                        else "User Not Found"
                    ),
                    "success": False,
                },
            )

        if not user.organization.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Organization is deactivated. Access denied.",
                    "success": False,
                },
            )

        # We Will Also Check For The Relevant Session That This Particular Session Exists Or Not

        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
                headers={"WWW-Authenticate": "Bearer"},
            )
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
