import jwt , os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from dotenv import load_dotenv
load_dotenv()

JWT_SECRET = os.getenv('JWT_SECRET_KEY')
ALGORITHM = os.getenv('JWT_ALGORITHM')


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Function To Convert Plain Text Password To Hash Passwords
def hash_passwords(password:str) -> str:
    return pwd_context.hash(password)

# Function To Verify The Hashed Password And Return True/False Accordingly
def verify_password(plain_password:str,hashed_password:str) -> bool:
    return pwd_context.verify(plain_password , hashed_password)

# Function To Generate The JWT Auth Token

def create_jwt_token(data:dict , expires_date:timedelta = None) -> str:
    encoded_data  = data.copy()
    if expires_date:
        expire_date = datetime.now() + expires_date
        encoded_data.update({"exp": expire_date})
    return  jwt.encode(encoded_data, JWT_SECRET, algorithm=ALGORITHM)


# Function To Encode The Incoming Jwt Token From The Request Header

def verify_jwt_token(jwt_token:str) -> dict:
    try:
        request_payload = jwt.decode(jwt_token, JWT_SECRET, algorithms=ALGORITHM)
        return request_payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
    
    