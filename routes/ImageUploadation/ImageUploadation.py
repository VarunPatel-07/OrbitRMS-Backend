import os

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from Database.Database import db_dependencies
from Middleware.UserAuthenticator import UserAuthenticatorMiddleware
from RateLimiting import limiter

load_dotenv(override=True)

API_RATE_LIMITING = os.getenv("API_RATE_LIMITING")


# --- NOW We Are Configuring The Cloudinary ---

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)


imgRoute = APIRouter(prefix="/app/v1/uploadation", tags=["uploadation"])


@imgRoute.post("/single-upload", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def ImageUploadation(
    request: Request,
    db: db_dependencies,
    file: UploadFile = File(...),
    user: dict = Depends(UserAuthenticatorMiddleware),
):
    try:

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
