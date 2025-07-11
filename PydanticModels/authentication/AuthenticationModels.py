from typing import Dict, List, Optional

from pydantic import BaseModel


class CreatePassword(BaseModel):
    password: str


class SignIn(BaseModel):
    email: str
    password: str


class CountryInfo(BaseModel):
    country_name: str
    country_flag: str
    country_number_code: str
    country_code: str


class RegisterOrganizationInfo(BaseModel):
    organization_name: str
    primary_email: str
    portal_url: str
    portal_slug: str
    website_url: Optional[str] = None
    primary_number: str
    country_info: CountryInfo
    is_meta_verified: bool = False
    meta_key: str
    meta_value: str
    terms_accepted: bool = False
    email_verified: bool = False
    organization_profile_picture: Optional[str] = None


class VerifyMetaTag(BaseModel):
    website_url: str
    meta_name: str
    meta_value: str


class PasswordResetPydanticModel(BaseModel):
    email: str
