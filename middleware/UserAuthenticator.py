from sre_constants import SUCCESS
from fastapi import Depends, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from constants.constant import SUCCESS
from database.Database import db_dependencies
from models.sql import Models
from utils.helper.helper import model_to_filtered_dict
from utils.responseMessages import ERROR_MESSAGE

from .verifyToken import verify_token


def UserAuthenticatorMiddleware(
    request: Request,
    db: db_dependencies,
    token: str = Depends(verify_token),
) -> dict:

    maintenance_mode = db.query(Models.MaintenanceMode).first()

    if maintenance_mode and maintenance_mode.is_active:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Unauthorized: Missing or invalid auth token",
                "success": False,
                "data": jsonable_encoder(model_to_filtered_dict(maintenance_mode)),
            },
        )

    user_id = token["user_id"]

    session_id = token["session_id"]

    user = db.query(Models.User).filter(Models.User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": ERROR_MESSAGE.USER_NOT_FOUND,
                "success": SUCCESS.FALSE,
            },
        )
    if not user.account_status:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": ERROR_MESSAGE.SIGN_IN_ACCOUNT_INACTIVE, "success": SUCCESS.FALSE},
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

    return user
