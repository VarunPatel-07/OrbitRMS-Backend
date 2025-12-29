import os
from datetime import datetime

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import joinedload

from config.EnvConfig import EnvConfig
from database.Database import db_dependencies
from middleware.verifyToken import verify_token
from models.sql import Models
from middleware.RateLimiting import limiter
from utils.responseMessages.AuthErrorMessage import ADMIN_NOT_FOUND

load_dotenv(override=True)

API_RATE_LIMITING = EnvConfig.API_RATE_LIMITING
CLOUDINARY_API_SECRET = EnvConfig.CLOUDINARY_API_SECRET
CLOUDINARY_API_KEY = EnvConfig.CLOUDINARY_API_KEY
CLOUDINARY_CLOUD_NAME = EnvConfig.CLOUDINARY_CLOUD_NAME
# --- NOW We Are Configuring The Cloudinary ---

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
)


adminImgRoute = APIRouter(prefix="/app/v1/admin/upload", tags=["upload"])


@adminImgRoute.post("/single-upload", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def ImageUploadation(
    request: Request,
    db: db_dependencies,
    file: UploadFile = File(...),
    token: str = Depends(verify_token),
):
    try:

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized", "success": False},
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
                detail={"message": ADMIN_NOT_FOUND, "success": False},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid session", "success": False},
            )

        file_bytes = await file.read()

        result = cloudinary.uploader.upload(file_bytes, resource_type="image")

        return {
            "message": "Image Upload Successfully",
            "success": True,
            "data": {
                "url": result["secure_url"],
            },
        }
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error Accrued While Uploading Image",
                "success": False,
                "error": str(e),
            },
        )


@adminImgRoute.post("/cloud/signature", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def GetCloudUploadSignature(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized", "success": False},
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
                detail={"message": ADMIN_NOT_FOUND, "success": False},
            )

        if not any(
            session.id == session_id and session.admin_signature == admin_signature
            for session in admin.admin_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid session", "success": False},
            )

        time_stamp = round(datetime.now().timestamp())

        params = {"timestamp": time_stamp}

        signature = cloudinary.utils.api_sign_request(params, CLOUDINARY_API_SECRET)

        return {
            "message": "Signature Generated Successfully",
            "success": True,
            "data": {
                "time_stamp": time_stamp,
                "signature": signature,
                "api_key": CLOUDINARY_API_KEY,
                "cloud_name": CLOUDINARY_CLOUD_NAME,
            },
        }

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error Accrued While Uploading Image",
                "success": False,
                "error": str(e),
            },
        )
