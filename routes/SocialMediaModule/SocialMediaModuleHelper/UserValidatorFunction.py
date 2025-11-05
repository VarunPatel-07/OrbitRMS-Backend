from fastapi import Depends, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError

from Database.Database import db_dependencies
from Helper.helper import model_to_filtered_dict
from Helper.jwtHelper import verify_jwt_token
from SqlModels import Models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/app/v1/auth/login")


from typing import Optional


def verify_token(
    direct_token: Optional[str] = None,
) -> dict:
    """
    Verify the JWT token from either:
    1. OAuth2 header (standard)
    2. Directly passed token (for cases like query params)
    """
    if not direct_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Unauthorized: Missing token", "success": False},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Remove "Bearer " prefix if present
    if direct_token.startswith("Bearer "):
        actual_token = direct_token[7:]
    else:
        actual_token = direct_token

    try:
        payload = verify_jwt_token(actual_token)
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Unauthorized: Token has expired", "success": False},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": f"Unauthorized: Invalid token - {str(e)}", "success": False},
            headers={"WWW-Authenticate": "Bearer"},
        )


def UserValidatorFunction(
    request: Request,
    db: db_dependencies,
    token: str,
) -> dict:

    _token = verify_token(direct_token=token)

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

    user_id = _token["user_id"]

    session_id = _token["session_id"]

    user = db.query(Models.User).filter(Models.User.id == user_id).first()

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

    return user
