import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import relationship

from SqlModels.Models import BaseModel


#  helper
class Children(BaseModel):
    __tablename__ = "children"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    name = Column(String(255), index=True)
    gender = Column(CHAR(36), index=True)
    date_of_birth = Column(DateTime)
    family_id = Column(CHAR(36), ForeignKey("family_info.id"), nullable=False)
    family_info = relationship(
        "FamilyInfo", backref="children"
    )  # Use backref for one-way relationship


class EmergencyContact(BaseModel):
    __tablename__ = "emergency_contact"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    full_name = Column(String(255), nullable=False)
    contact_number = Column(String(255), nullable=False)
    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", back_populates="emergency_contact")


# main
class PersonalInfo(BaseModel):
    __tablename__ = "personal_info"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    first_name = Column(String(255), nullable=False)
    middle_name = Column(String(255), nullable=True, default=None)
    last_name = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    profile_picture = Column(String(255), nullable=True, default=None)
    profile_picture_bg = Column(String(255), nullable=True, default=None)
    gender = Column(String(255), nullable=False)
    date_of_birth = Column(DateTime)
    blood_group = Column(String(255), nullable=False)
    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", back_populates="personal_info")


class EmployeeInfo(BaseModel):
    __tablename__ = "employee_info"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    status = Column(String(255), nullable=False)
    organization_name = Column(String(255), nullable=False)
    employee_code = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    designation = Column(String(255), nullable=False)
    reporting_to = Column(JSON, nullable=True, default=None)
    employee_role = Column(String(255), nullable=False)
    employee_email = Column(String(255), nullable=False, default=None)
    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", back_populates="employee_info")


class PersonalContactInfo(BaseModel):
    __tablename__ = "personal_contact_info"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    personal_email = Column(CHAR(36), nullable=False, default=None)
    mobile_number = Column(CHAR(36), nullable=False, default=None)
    alternative_contact = Column(CHAR(36), nullable=True, default=None)
    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", back_populates="personal_contact_info")


class FamilyInfo(BaseModel):
    __tablename__ = "family_info"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    father_name = Column(String(255), nullable=False, default=None)
    mother_name = Column(String(255), nullable=False, default=None)
    marital_status = Column(CHAR(36), nullable=False, default=None)
    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", back_populates="family_info")


class Address(BaseModel):
    __tablename__ = "address"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    address = Column(String(255), nullable=False, default=None)
    country = Column(String(255), nullable=False, default=None)
    state = Column(String(255), nullable=False, default=None)
    city = Column(String(255), nullable=False, default=None)
    zip_code = Column(String(255), nullable=False, default=None)
    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", back_populates="address")


class SocialLinks(BaseModel):
    __tablename__ = "social_link"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    icon = Column(String(255), nullable=True, default=None)
    name = Column(String(255), nullable=True, default=None)
    link = Column(String(255), nullable=True, default=None)
    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
    )
    user = relationship("User", back_populates="social_link")
