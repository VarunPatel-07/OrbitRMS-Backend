from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ReportingTo(BaseModel):
    id: str
    name: str


class EmployeeRole(BaseModel):
    role_id: str
    role_name: str


class EmergencyContact(BaseModel):
    contact_id: str
    id: str
    emergency_contact_country_info: str
    emergency_contact_number: str
    emergency_contact_name: str


class Child(BaseModel):
    child_name: str
    child_date_of_birth: Optional[datetime] = None
    family_info_id: str
    id: str


class SocialLink(BaseModel):
    icon: str
    name: str
    link: str
    target_blank: bool
    id: str
    user_id: str


class PersonalInfo(BaseModel):
    first_name: str
    middle_name: str
    last_name: str
    full_name: str
    profile_picture: str
    gender: str
    date_of_birth: Optional[datetime] = None
    blood_group: str
    about: str


class EmployeeInfo(BaseModel):
    status: str
    organization_name: str
    employee_code: str
    department: str
    designation: str
    employee_email: str
    reporting_to: ReportingTo
    employee_role: EmployeeRole
    employee_type: str
    joining_date: Optional[datetime]


class PersonalContactInfo(BaseModel):
    personal_email: str
    mobile_number: str
    country_info: str
    emergency_contacts: List[EmergencyContact]


class FamilyInfo(BaseModel):
    father_name: str
    mother_name: str
    marital_status: str
    children: List[Child]


class Address(BaseModel):
    address: str
    country: str
    state: str
    city: str
    zip_code: str
    country_code: str


class AddEditUserProfileModel(BaseModel):
    personal_info: PersonalInfo
    employee_info: EmployeeInfo
    personal_contact_info: PersonalContactInfo
    family_info: FamilyInfo
    current_address: Address
    same_as_current_address: bool
    permanent_address: Address
    social_link: List[SocialLink]
