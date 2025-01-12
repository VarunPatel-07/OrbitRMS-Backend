# Pydantic model for JSON payload
from pydantic import BaseModel
from fastapi import Form


class LoginUserInfo(BaseModel):
    username: str
    password: str
    
    @classmethod
    def as_form(
            cls, username: str = Form(...), password: str = Form(...),
            ) -> "LoginUserInfo":
        return cls(
            username=username, password=password,
            )


class SignUpUserInfo(BaseModel):
    username: str
    password: str
    email: str
    first_name: str
    last_name: str
    
    @classmethod
    def as_form(
            cls, username: str = Form(...), password: str = Form(...), email: str = Form(...),
            first_name: str = Form(...),
            last_name: str = Form(...)
            ) -> "SignUpUserInfo":
        return cls(
            username=username, password=password, email=email, first_name=first_name, last_name=last_name
            )
