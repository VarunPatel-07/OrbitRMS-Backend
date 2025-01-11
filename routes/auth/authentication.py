from fastapi import APIRouter, Depends, HTTPException, status, Request , Form
from pydantic import BaseModel
from SqlModels import Models
from Database.Database import db_dependencies
from Helper.jwtHelper import create_jwt_token , hash_passwords,verify_password
from Helper.helper import generate_full_name

routes = APIRouter(
    prefix="/app/v1/auth",
    tags=["auth"]
)

# Pydantic model for JSON payload
class UserInfo(BaseModel):
    username: str
    password: str
    email: str
    first_name: str
    last_name: str


@routes.post(path="/signUp", status_code=status.HTTP_201_CREATED)
async def sign_up(user_info: UserInfo, db:db_dependencies):
    try:
        existing_user = db.query(Models.User).filter((Models.User.username == user_info.username) | (Models.User.email == user_info.email)).first()
        
        # If We Not Found The User
        if existing_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User all ready exists")
        
        hashed_password = hash_passwords(user_info.password)
        
        new_user = Models.User(
            username=user_info.username,
            email=user_info.email,
            first_name=user_info.first_name,
            last_name=user_info.last_name,
            password=hashed_password,
            Organizations=[],
            full_name=generate_full_name(user_info.first_name, user_info.last_name),
            default_organization_id=""
            )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        token_data = {
            "sub": new_user.id,
            }
        
        token = create_jwt_token(data=token_data)
        
        return {"message":"The User Is Registered Successfully", "token":token}
    
    except HTTPException:
        raise
    
    except Exception as e:
        # Log the error here if you have logging set up
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while creating the user"
            )


@routes.post(path="/login" , status_code=status.HTTP_201_CREATED)
async def login(user_info:UserInfo , db:db_dependencies):
    try:
        find_user = db.query(Models.User).filter(Models.User.username == user_info.username).first()
       
        if not find_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        compare_password = verify_password(user_info.password , find_user.password)
        
        if not compare_password:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incorrect password")
        
        token_data = {
            "sub":find_user.id
            }
        token = create_jwt_token(data=token_data)
        
        return {"message": "Login successful" , "token":token}
    
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))