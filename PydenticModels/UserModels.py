# Pydantic model for JSON payload
from pydantic import BaseModel , EmailStr , HttpUrl
from datetime import datetime
from fastapi import Form
from typing import Optional , List


class LoginUserInfo(BaseModel):
    email: str
    password: str
    
    @classmethod
    def as_form(
            cls, email: str = Form(...), password: str = Form(...),
            ) -> "LoginUserInfo":
        return cls(
            email=email, password=password,
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
    date_of_birth: datetime


class FamilyInfo(BaseModel):
    father_name: str
    mother_name: str
    marital_status: str
    children: List[Children]


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
    profile_picture: Optional[HttpUrl]
    profile_picture_bg: Optional[HttpUrl]
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
  