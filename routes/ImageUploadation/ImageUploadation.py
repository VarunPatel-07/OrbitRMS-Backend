import cloudinary.uploader
from fastapi import APIRouter, HTTPException, status, File, UploadFile
from dotenv import load_dotenv
import cloudinary
import os

load_dotenv(override=True)


# --- NOW We Are Configuring The Cloudinary ---

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)


imgRoute = APIRouter(prefix="/app/v1/uploadation", tags=["uploadation"])


@imgRoute.post("/single-upload", status_code=status.HTTP_200_OK)
async def ImageUploadation(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()

        result = cloudinary.uploader.upload(file_bytes, resource_type="image")

        return {"url": result["secure_url"]}
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
