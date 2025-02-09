from pydantic import BaseModel


class CreatePassword(BaseModel):
    password: str


class SignIn(BaseModel):
    email: str
    password: str
