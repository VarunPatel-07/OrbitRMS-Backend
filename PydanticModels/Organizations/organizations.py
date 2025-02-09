from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class CountryInfo(BaseModel):
    country_name: str
    country_flag: str
    country_number_code: str
    country_code: str


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


class OrganizationGeneralInfo(BaseModel):
    organization_name: str
    primary_email: str
    primary_number: str
    country_info: Optional[dict] = None
    portal_url: str
    website_url: Optional[str] = None
    is_meta_verified: bool
    meta_key: str
    meta_value: str
    terms_accepted: bool
    email_verified: bool
    organization_profile_picture: str = None

    class Config:
        orm_mode = True


class OrganizationAddress(BaseModel):
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    class Config:
        orm_mode = True


class OrganizationContactInfo(BaseModel):
    phone_number: Optional[str] = None
    company_email: Optional[str] = None

    class Config:
        orm_mode = True


class OrganizationAboutInfo(BaseModel):
    about: Optional[str] = None
    established_science: Optional[str] = None
    registration_number: Optional[str] = None

    class Config:
        orm_mode = True


class OrganizationSettings(BaseModel):
    email_domain_slug: Optional[str] = None
    employee_code_prefix: Optional[str] = None
    inter_code_prefix: Optional[str] = None
    default_timezone: Optional[str] = None

    class Config:
        orm_mode = True


class OnboardingOrganization(BaseModel):
    general_info: OrganizationGeneralInfo
    address: List[OrganizationAddress]
    contact_info: List[OrganizationContactInfo]
    about_info: OrganizationAboutInfo
    organization_settings: OrganizationSettings
    status: bool

    class Config:
        orm_mode = True
