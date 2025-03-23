import os

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from Middleware.verifyToken import verify_token

load_dotenv(override=True)


# --- NOW We Are Configuring The Cloudinary ---

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)


imgRoute = APIRouter(prefix="/app/v1/uploadation", tags=["uploadation"])


@imgRoute.post("/single-upload", status_code=status.HTTP_200_OK)
async def ImageUploadation(file: UploadFile = File(...), token: str = Depends(verify_token)):
    try:

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized: Missing or invalid auth token",
                    "success": False,
                },
            )

        file_bytes = await file.read()

        result = cloudinary.uploader.upload(file_bytes, resource_type="image")

        return {"url": result["secure_url"], "success": True}
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
