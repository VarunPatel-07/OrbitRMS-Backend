from typing import Any, List, Literal

from pydantic import BaseModel


class WelcomeEmployeeMailModel(BaseModel):
    user_name: str
    organization_name: str
    create_password_link: str


class NewOrganizationCreatedSuccessFully(BaseModel):
    user_name: str
    organization_name: str
    organization_dashboard_link: str


class CreatePasswordPydanticBody(BaseModel):
    user_name: str
    organization_name: str
    create_password_link: str


class NewClientInquiryMailPydanticBody(BaseModel):
    user_name: str
    organization_name: str
    reset_password_link: str


class ResetPasswordInstructionPydanticBody(BaseModel):
    user_name: str
    organization_name: str
    reset_password_link: str


class VerifyEmailPydanticBody(BaseModel):
    organization_name: str
    confirm_my_email: str


class DistanceCalculatorLatLong(BaseModel):
    latitude: float
    longitude: float


class CrudeFunctionReturnType(BaseModel):
    status_code: int
    message: str
    success: bool


class CommonCrudeFunctionReturnType(BaseModel):
    status_code: int
    message: str
    success: bool
    data: Any


class CreateCloudflareTurnStileWithManualModePydanticModel(BaseModel):
    turnstile_mode: Literal["non-interactive", "invisible", "managed"]
    allowed_domains: List[str]
    # turnstile_setup_mode: Literal["automated", "manual"]
    turnstile_secret_key: str
    turnstile_site_key: str


class VerifyTurnstileSetUpPydanticModal(BaseModel):
    turnstile_token: str
