import jwt , os , hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

JWT_SECRET = os.getenv('JWT_SECRET_KEY')
ALGORITHM = os.getenv('JWT_ALGORITHM')

print(JWT_SECRET)


# Function To Convert Plain Text Password To Hash Passwords
def hash_passwords(password:str) -> str:
    salt = os.urandom(16)
    hashed_password = hashlib.pbkdf2_hmac('sha256' , password.encode('utf-8') , salt, 100000 )
    print(hashed_password)
    return salt.hex() + hashed_password.hex()

# Function To Verify The Hashed Password And Return True/False Accordingly
def verify_password(plain_password:str,hashed_password:str) -> bool:
    salt = bytes.fromhex(hashed_password[:32])
    stored_hash = bytes.fromhex(hashed_password[32:])
    password_hash = hashlib.pbkdf2_hmac('sha256' , plain_password.encode('utf-8') , salt, 100000 )
    return stored_hash == password_hash

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
    
    