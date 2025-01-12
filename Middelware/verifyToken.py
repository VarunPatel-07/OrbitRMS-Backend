from fastapi import Depends , HTTPException , status
from fastapi.security import OAuth2PasswordBearer
from Helper.jwtHelper import verify_jwt_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/app/v1/auth/login")

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = verify_jwt_token(token)

        return payload["sub"]
    
    except ValueError as error:
     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail=error , headers={"WWW-Authenticate":"Bearer"})
    