import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import relationship

from Database.Database import BaseModel
from SqlModels.HelperModel.OrganizationModelUtils import (
    OrganizationAboutInfo,
    OrganizationAddress,
    OrganizationContactInfo,
    OrganizationGeneralInfo,
    OrganizationSettings,
)
from SqlModels.HelperModel.UserModelUtils import (
    Address,
    Children,
    EmergencyContact,
    EmployeeInfo,
    FamilyInfo,
    PersonalContactInfo,
    PersonalInfo,
    SocialLinks,
)
from SqlModels.HelperModel.ConfigModelUtils import ProjectStatus, AttachmentType, Designations


class User(BaseModel):
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    personal_info = relationship("PersonalInfo", back_populates="user")
    employee_info = relationship("EmployeeInfo", back_populates="user")
    personal_contact_info = relationship("PersonalContactInfo", back_populates="user")
    family_info = relationship("FamilyInfo", back_populates="user")
    address = relationship("Address", back_populates="user")
    emergency_contact = relationship(
        "EmergencyContact", back_populates="user", cascade="all, delete-orphan"
    )

    social_link = relationship("SocialLinks", back_populates="user")
    password = Column(String(255), nullable=False)
    account_status = Column(Boolean, nullable=False, default=True)
    profile_created = Column(Boolean, nullable=False, default=False)
    reset_password_token = Column(String(255), nullable=True, default=None)
    password_created = Column(Boolean, nullable=False, default=False)
    organization_id = Column(CHAR(36), ForeignKey("organization.id"), nullable=False, index=True)
    organization = relationship("Organization", back_populates="employees")
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )


class Organization(BaseModel):
    __tablename__ = "organization"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    general_info = relationship(
        "OrganizationGeneralInfo", back_populates="organization", uselist=False
    )
    address = relationship("OrganizationAddress", back_populates="organization")
    contact_info = relationship("OrganizationContactInfo", back_populates="organization")
    about_info = relationship("OrganizationAboutInfo", back_populates="organization")
    organization_settings = relationship("OrganizationSettings", back_populates="organization")
    status = Column(Boolean, nullable=False, default=True)

    employees = relationship("User", back_populates="organization", cascade="all, delete-orphan")

    config_modules = relationship(
        "ConfigModule", back_populates="organization", cascade="all, delete-orphan"
    )

    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )
    organization_created = Column(Boolean, nullable=False, default=False)


class ConfigModule(BaseModel):
    __tablename__ = "config_module"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    project_status = relationship(
        "ProjectStatus", back_populates="config_module", cascade="all, delete"
    )
    attachment_type = relationship(
        "AttachmentType", back_populates="config_module", cascade="all, delete"
    )
    designations = relationship(
        "Designations", back_populates="config_module", cascade="all, delete"
    )

    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    organization = relationship("Organization", back_populates="config_modules")

    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )
