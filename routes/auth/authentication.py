from fastapi import APIRouter, Depends, HTTPException, status
from SqlModels import Models
from Database.Database import db_dependencies
from Helper.jwtHelper import create_jwt_token , hash_passwords,verify_password
from Helper.helper import generate_full_name
from PydenticModels.UserModels import LoginUserInfo  ,SignUpUserInfo
from Middelware.verifyToken import oauth2_scheme , verify_token


routes = APIRouter(
    prefix="/app/v1/auth",
    tags=["auth"]
)


# This is the api that is used to signUp user
@routes.post(path="/signUp", status_code=status.HTTP_201_CREATED)
async def sign_up(
    db:db_dependencies , user_info: SignUpUserInfo = Depends(SignUpUserInfo.as_form)):
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

        user = {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "full_name": new_user.full_name,
            "default_organization_id": new_user.default_organization_id,
            "organizations": new_user.Organizations,
            "profile_picture": new_user.profile_picture,
            }
        
        return {"message":"The User Is Registered Successfully", "token":token , "success":True , "user_info":user}
    
    except HTTPException:
        raise
    
    except Exception as e:
        # Log the error here if you have logging set up
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while creating the user"
            )




# This is The Api that is used to log in the use
@routes.post(path="/login" , status_code=status.HTTP_201_CREATED)
async def login(
    db:db_dependencies, user_info: LoginUserInfo = Depends(LoginUserInfo.as_form)):
    try:
       
        find_user = db.query(Models.User).filter(Models.User.email == user_info.email).first()
       
        if not find_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        compare_password = verify_password(user_info.password , find_user.password)
        
        if not compare_password:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incorrect password")
        
        user = {
            "id":find_user.id,
            "username":find_user.username,
            "email":find_user.email,
            "first_name":find_user.first_name,
            "last_name":find_user.last_name,
            "full_name":find_user.full_name,
            "default_organization_id":find_user.default_organization_id,
            "organizations":find_user.Organizations,
            "profile_picture":find_user.profile_picture,
            }
        
        token_data = {
            "sub":find_user.id
            }
        token = create_jwt_token(data=token_data)
        
        return {"message": "Login successful" , "token":token , "success":True , "user_info":user}
    
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    



# this is the api to verify the users token
@routes.get(path="/verify-user" , status_code=status.HTTP_200_OK)
async def verify_user(db:db_dependencies , token:str = Depends(oauth2_scheme)):
    token_payload = verify_token(token)
    if not token_payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    find_user = db.query(Models.User).filter(Models.User.id == token_payload).first()
    if not find_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"message":"The User Is Verified Successfully", "success":True}



# this is the api to get the user info
