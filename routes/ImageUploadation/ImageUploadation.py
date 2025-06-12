import os

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import joinedload

from Database.Database import db_dependencies
from Middleware.verifyToken import verify_token
from SqlModels import Models

load_dotenv(override=True)


# --- NOW We Are Configuring The Cloudinary ---

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)


imgRoute = APIRouter(prefix="/app/v1/uploadation", tags=["uploadation"])


@imgRoute.post("/single-upload", status_code=status.HTTP_200_OK)
async def ImageUploadation(
    db: db_dependencies, file: UploadFile = File(...), token: str = Depends(verify_token)
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
            .options(joinedload(Models.User.sessions))
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

        # We Will Also Check For The Relevant Session That This Particular Session Exists Or Not

        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
                headers={"WWW-Authenticate": "Bearer"},
            )

        #
        # *  Once The User Is Authenticated Then We Will Move Further
        #

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
