from fastapi import APIRouter, Depends, HTTPException, status, Request , Form
from Database.Database import db_dependencies
from Middelware.verifyToken import verify_token , oauth2_scheme
from  Helper.jwtHelper import create_jwt_token
routes = APIRouter(
    prefix="/app/v1/auth",
    tags=["auth"]
)

class LoginForm:
    def __init__(self, username: str = Form(...), password: str = Form(...) , email:str = Form(...) , first_name:str = Form(...) , last_name:str = Form(...)):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.username = username
        self.password = password

@routes.post("/signUp" ,status_code=status.HTTP_201_CREATED)
async  def validate_user_info(dataBase:db_dependencies, user_info:LoginForm = Depends()):
    
    return {"message": "Login successful", "user_info": {"username": user_info.username, "password": user_info.password} }