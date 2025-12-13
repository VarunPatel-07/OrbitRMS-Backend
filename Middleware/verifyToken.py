from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError

from Helper.jwtHelper import verify_jwt_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/app/v1/auth/login")


def verify_token(token: str = Depends(oauth2_scheme)):
    """Verify the JWT token and return its payload."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Unauthorized: Missing or invalid auth token", "success": False},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_jwt_token(token)

        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Unauthorized: Token has expired", "success": False},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Unauthorized: Invalid token", "success": False},
            headers={"WWW-Authenticate": "Bearer"},
        )
