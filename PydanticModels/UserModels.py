# Pydantic model for JSON payload
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, HttpUrl


class SocialLink(BaseModel):
    icon: HttpUrl
    name: str
    link: HttpUrl


class EmergencyContact(BaseModel):
    full_name: str
    contact_number: str


class Address(BaseModel):
    address: str
    country: str
    state: str
    city: str
    zip_code: str


class Children(BaseModel):
    name: str
    gender: str
    date_of_birth: str

    model_config = {
        "json_schema_extra": {"family_info": {"exclude": True}}  # ✅ Use this instead of 'fields'
    }


class FamilyInfo(BaseModel):
    father_name: str
    mother_name: str
    marital_status: str
    children: Optional[List[Children]] = None


class ContactInfo(BaseModel):
    personal_email: EmailStr
    mobile_number: str


class EmployeeInfo(BaseModel):
    status: str
    organization_name: str
    employee_code: str
    department: str
    designation: str
    reporting_to_id: str
    employee_role: str
    employee_email: EmailStr


class PersonalInfo(BaseModel):
    first_name: str
    middle_name: Optional[str]
    last_name: str
    full_name: str
    profile_picture: Optional[str]
    profile_picture_bg: Optional[str]
    gender: str
    date_of_birth: datetime
    blood_group: str


class User(BaseModel):
    personal_info: PersonalInfo
    employee_info: EmployeeInfo
    personal_contact_info: ContactInfo
    family_info: FamilyInfo
    address: Address
    emergency_contact: List[EmergencyContact]
    social_link: List[SocialLink]
