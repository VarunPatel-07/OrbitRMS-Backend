from pydantic import BaseModel


class WelcomeEmployeeMailModel(BaseModel):
    user_name: str
    organization_name: str
    create_password_link: str
