from pydantic import BaseModel


class WelcomeEmployeeMailModel(BaseModel):
    user_name: str
    organization_name: str
    create_password_link: str


class CreatePasswordPydanticBody(BaseModel):
    user_name: str
    organization_name: str
    create_password_link: str


class NewClientInquiryMailPydanticBody(BaseModel):
    user_name: str
    organization_name: str
    reset_password_link: str


class VerifyEmailPydanticBody(BaseModel):
    organization_name: str
    confirm_my_email: str
