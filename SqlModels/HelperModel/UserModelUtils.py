import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import relationship

from SqlModels.Models import BaseModel


# main
class PersonalInfo(BaseModel):
    __tablename__ = "personal_info"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # todo: add the new field about

    first_name = Column(String(255), nullable=False)
    middle_name = Column(String(255), nullable=True, default=None)
    last_name = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    profile_picture = Column(String(255), nullable=True, default=None)
    profile_picture_bg = Column(String(255), nullable=True, default=None)
    gender = Column(String(255), nullable=False)
    date_of_birth = Column(DateTime)
    blood_group = Column(String(255), nullable=False)
    about = Column(Text, nullable=True, default=None)
    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", back_populates="personal_info")


class EmployeeInfo(BaseModel):
    __tablename__ = "employee_info"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # todo: change the reporting to from storing the json to storing the reference to the reporting to manager id

    status = Column(String(255), nullable=False)
    employee_type = Column(String(255), nullable=True, default=None)
    organization_name = Column(String(255), nullable=False)
    employee_code = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    designation = Column(String(255), nullable=False)
    joining_date = Column(DateTime)
    employee_role_id = Column(
        CHAR(36), ForeignKey("config_role_module.id"), nullable=True, default=None
    )
    employee_role = relationship(
        "ConfigRoleModule",
        back_populates="associated_employees",
        foreign_keys=[employee_role_id],
    )
    employee_email = Column(String(255), nullable=False, default=None)
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", back_populates="employee_info", foreign_keys=[user_id])

    reporting_to_id = Column(CHAR(36), ForeignKey("users.id"), nullable=True, default=None)

    reporting_manager = relationship(
        "User", back_populates="reporting_employees", foreign_keys=[reporting_to_id]
    )


class EmergencyContact(BaseModel):
    __tablename__ = "emergency_contacts"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    emergency_contact_name = Column(String(255), nullable=False, default=None)
    emergency_contact_number = Column(String(255), nullable=False, default=None)
    emergency_contact_country_info = Column(JSON, nullable=True)

    contact_id = Column(CHAR(36), ForeignKey("personal_contact_info.id"), nullable=False)
    personal_contact_info = relationship("PersonalContactInfo", back_populates="emergency_contacts")


class PersonalContactInfo(BaseModel):
    __tablename__ = "personal_contact_info"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # todo Change the field name form alternative_contact to emergency_contact As a Json and It contain two field emergency_contact_number and emergency_contact_name

    personal_email = Column(String(255), nullable=False, default=None)
    mobile_number = Column(String(255), nullable=False, default=None)
    country_info = Column(JSON, nullable=True)
    emergency_contacts = relationship(
        "EmergencyContact", back_populates="personal_contact_info", cascade="all, delete-orphan"
    )

    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", back_populates="personal_contact_info")


class Children(BaseModel):
    __tablename__ = "children"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    child_name = Column(String(255), nullable=True, default=None)
    child_date_of_birth = Column(DateTime, nullable=True, default=None)

    family_info_id = Column(CHAR(36), ForeignKey("family_info.id"), nullable=False)
    family_info = relationship("FamilyInfo", back_populates="children")


class FamilyInfo(BaseModel):
    __tablename__ = "family_info"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # todo we will also add the children info like name and dob as a array of the children

    father_name = Column(String(255), nullable=False, default=None)
    mother_name = Column(String(255), nullable=False, default=None)
    marital_status = Column(CHAR(36), nullable=False, default=None)
    children = relationship("Children", back_populates="family_info", cascade="all, delete-orphan")

    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", back_populates="family_info")


class Address(BaseModel):
    __tablename__ = "address"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    address = Column(String(255), nullable=False, default=None)
    country = Column(String(255), nullable=False, default=None)
    state = Column(String(255), nullable=False, default=None)
    city = Column(String(255), nullable=False, default=None)
    zip_code = Column(String(255), nullable=False, default=None)
    country_code = Column(String(255), nullable=True, default=None)


class SocialLinks(BaseModel):
    __tablename__ = "social_link"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    icon = Column(Text, nullable=True, default=None)
    name = Column(String(255), nullable=True, default=None)
    link = Column(String(255), nullable=True, default=None)
    target_blank = Column(Boolean, nullable=True, default=True)
    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
    )
    user = relationship("User", back_populates="social_link")


class Sessions(BaseModel):
    __tablename__ = "session"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ip_address = Column(String(255), nullable=True, default=None)
    browser = Column(String(255), nullable=True, default=None)
    browser_version = Column(String(255), nullable=True, default=None)
    os = Column(String(255), nullable=True, default=None)
    os_version = Column(String(255), nullable=True, default=None)
    device_type = Column(String(255), nullable=True, default=None)
    is_mobile = Column(Boolean, nullable=True, default=False)
    is_tablet = Column(Boolean, nullable=True, default=False)
    is_pc = Column(Boolean, nullable=True, default=False)
    is_bot = Column(Boolean, nullable=True, default=False)
    fingerprint = Column(String(500), nullable=True, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )

    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", back_populates="sessions")
