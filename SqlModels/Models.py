import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import relationship

from Database.Base import BaseModel
from SqlModels.HelperModel.ConfigModelUtils import (
    ConfigRoleModule,
    Department,
    Designations,
    PermissionModule,
    ProjectStatus,
    RoleAssociatedPermissionModule,
)
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
    Sessions,
    SocialLinks,
)


class User(BaseModel):
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    personal_info = relationship("PersonalInfo", back_populates="user")

    employee_info = relationship(
        "EmployeeInfo",
        foreign_keys="[EmployeeInfo.user_id]",  # Define this in EmployeeInfo
        back_populates="user",
        uselist=False,  # If one-to-one
    )
    reporting_employees = relationship(  # Managers can have many reporting employees
        "EmployeeInfo",
        foreign_keys="[EmployeeInfo.reporting_to_id]",
        back_populates="reporting_manager",
    )

    personal_contact_info = relationship("PersonalContactInfo", back_populates="user")
    family_info = relationship("FamilyInfo", back_populates="user")
    same_as_current_address = Column(Boolean, nullable=False, default=True)

    current_address_id = Column(CHAR(36), ForeignKey("address.id"), nullable=True)
    permanent_address_id = Column(CHAR(36), ForeignKey("address.id"), nullable=True)

    current_address = relationship(
        "Address", foreign_keys=[current_address_id], backref="users_current"
    )
    permanent_address = relationship(
        "Address", foreign_keys=[permanent_address_id], backref="users_permanent"
    )

    social_link = relationship("SocialLinks", back_populates="user")
    password = Column(String(255), nullable=False)
    account_status = Column(Boolean, nullable=False, default=True)
    profile_created = Column(Boolean, nullable=False, default=False)
    reset_password_token = Column(String(255), nullable=True, default=None)
    password_created = Column(Boolean, nullable=False, default=False)
    organization_id = Column(CHAR(36), ForeignKey("organization.id"), nullable=False, index=True)
    organization = relationship("Organization", back_populates="employees")
    sessions = relationship("Sessions", back_populates="user")

    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
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

    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )
    organization_created = Column(Boolean, nullable=False, default=False)


class ConfigModule(BaseModel):
    __tablename__ = "config_module"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    project_status = relationship(
        "ProjectStatus", back_populates="config_module", cascade="all, delete"
    )
    department = relationship("Department", back_populates="config_module", cascade="all, delete")
    designations = relationship(
        "Designations", back_populates="config_module", cascade="all, delete"
    )

    roles_and_permissions = relationship(
        "ConfigRoleModule", back_populates="config_module", cascade="all, delete"
    )

    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    organization = relationship("Organization", back_populates="config_modules")

    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )
