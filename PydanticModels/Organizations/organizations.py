from pydantic import BaseModel
from typing import Dict, Optional


class CountryInfo(BaseModel):
    country_name: str
    country_flag: str
    country_number_code: str


class RegisterOrganizationInfo(BaseModel):
    organization_name: str
    primary_email: str
    portal_url: str
    website_url: Optional[str] = None
    primary_number: str
    country_info: CountryInfo
    is_meta_verified: bool = False
    meta_key: str
    meta_value: str
    terms_accepted: bool = False
    email_verified: bool = False
    organization_profile_picture: Optional[str] = None
