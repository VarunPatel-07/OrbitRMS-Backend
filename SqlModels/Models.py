import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.sql import expression

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, Enum
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import relationship

from Database.Base import BaseModel
from SqlModels.HelperModel.ConfigModelUtils import (
    ClientFormSchema,
    ConfigRoleModule,
    Department,
    Designations,
    PermissionModule,
    ProjectStatus,
    RoleAssociatedPermissionModule,
    OrganizationHolidaysSchema,
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

    personal_info = relationship("PersonalInfo", back_populates="user", uselist=False)

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
    post = relationship("OrganizationUpdates", back_populates="publisher")

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

    client_inquires = relationship(
        "ClientInquires", back_populates="organization", cascade="all, delete-orphan", uselist=False
    )

    org_updates = relationship(
        "OrganizationUpdates", back_populates="organization", cascade="all, delete-orphan"
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

    client_form_schema = relationship(
        "ClientFormSchema", back_populates="config_module", cascade="all, delete"
    )

    roles_and_permissions = relationship(
        "ConfigRoleModule", back_populates="config_module", cascade="all, delete"
    )
    organization_holidays = relationship(
        "OrganizationHolidaysSchema", back_populates="config_module", cascade="all, delete"
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


class ClientInquires(BaseModel):
    __tablename__ = "client_inquires"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    api_key = Column(String(255), nullable=False)
    api_secrete = Column(String(255), nullable=False)

    status = Column(Boolean, nullable=False, default=False)

    email_notification = Column(Boolean, nullable=True, default=True)

    authorized_recipient_emails = Column(Text, nullable=True, default=None)

    client_inquires_data = relationship(
        "ClientInquiresData", back_populates="client_inquire", cascade="all, delete-orphan"
    )

    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    organization = relationship("Organization", back_populates="client_inquires")


class ClientInquiresData(BaseModel):

    __tablename__ = "client_inquires_data"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    data = Column(JSON, nullable=True, default=None)

    client_inquire_id = Column(
        CHAR(36),
        ForeignKey("client_inquires.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    client_inquire = relationship("ClientInquires", back_populates="client_inquires_data")


class OrganizationUpdates(BaseModel):
    __tablename__ = "organization_updates"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    images = Column(Text, nullable=True, default=None)
    description = Column(Text, nullable=True, default=None)
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)

    isCommentDisabled = Column(Boolean, default=False, nullable=True)

    isLikeDisabled = Column(Boolean, default=False, nullable=True)

    publisher = relationship("User", back_populates="post", cascade="all", uselist=False)

    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    source_type = Column(
        Enum("default", "system", "user_created", name="source_type_enum"),
        nullable=False,
        default="system",
    )

    organization = relationship("Organization", back_populates="org_updates")

    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )
