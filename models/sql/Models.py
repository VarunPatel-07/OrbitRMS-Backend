import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Table, Text
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import expression

from database.Base import BaseModel

from .HelperModel.AdminModelHelperUtils import (
    AdminOrganizationUpdates,
    OrbitAdminSessions,
)
from .HelperModel.ConfigModelUtils import (
    ConfigRoleModule,
    Department,
    Designations,
    InquiryFormFields,
    InquiryFormSchema,
    OrganizationHolidaysSchema,
    PermissionModule,
    ProjectStatus,
    RoleAssociatedPermissionModule,
)
from .HelperModel.OrganizationModelUtils import (
    FeedComments,
    FeedLikes,
    LeaveBalance,
    LeavesSettings,
    OrganizationAboutInfo,
    OrganizationAddress,
    OrganizationContactInfo,
    OrganizationGeneralInfo,
    OrganizationSettings,
    OrganizationLocationsConfig,
)
from .HelperModel.SocialMediaModule import SocialMediaAccount, SocialMediaPosts
from .HelperModel.UserModelUtils import (
    Address,
    AttendanceLeavesModule,
    Children,
    EmergencyContact,
    EmployeeInfo,
    FamilyInfo,
    PersonalContactInfo,
    PersonalInfo,
    Sessions,
    SocialLinks,
    AttendancePunchInOutModule,
)

# This IS The Table That Will Connect The Multiple Leave Records

attendance_leave_notify_table = Table(
    "attendance_leave_notify",
    BaseModel.metadata,
    Column("leave_id", CHAR(36), ForeignKey("attendance_leave_module.id"), primary_key=True),
    Column("user_id", CHAR(36), ForeignKey("users.id"), primary_key=True),
)


class Admin(BaseModel):
    __tablename__ = "orbit_admin"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, default=None)
    password = Column(String(255), nullable=False)
    admin_sessions = relationship("OrbitAdminSessions", back_populates="admin")
    organization_updates = relationship("AdminOrganizationUpdates", back_populates="publisher")


class MaintenanceLog(BaseModel):
    __tablename__ = "maintenance_logs"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    started_by = Column(String(255), nullable=False)
    ended_by = Column(String(255), nullable=True)

    type = Column(Enum("manual", "scheduled", name="maintenance_type"), default="manual")
    status = Column(
        Enum("scheduled", "active", "completed", "cancelled", name="maintenance_status"),
        default="active",
    )

    cancellation_reason = Column(Text, nullable=True, default=None)

    reason = Column(Text, nullable=True, default=None)

    message = Column(Text, nullable=True, default=None)

    maintenance_mode_id = Column(CHAR(36), ForeignKey("maintenance_mode.id"))
    maintenance_mode = relationship("MaintenanceMode", back_populates="maintenance_mode_logs")

    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )


class MaintenanceMode(BaseModel):
    __tablename__ = "maintenance_mode"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    is_active = Column(Boolean, default=False)
    message = Column(Text, nullable=True, default=None)

    maintenance_mode_logs = relationship("MaintenanceLog", back_populates="maintenance_mode")

    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )
    updated_by = Column(String(255))


class User(BaseModel):
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    personal_info = relationship(
        "PersonalInfo", back_populates="user", uselist=False, cascade="all, delete"
    )

    employee_info = relationship(
        "EmployeeInfo",
        foreign_keys="[EmployeeInfo.user_id]",
        back_populates="user",
        uselist=False,
        cascade="all, delete",
    )
    reporting_employees = relationship(
        "EmployeeInfo",
        foreign_keys="[EmployeeInfo.reporting_to_id]",
        back_populates="reporting_manager",
    )
    notifying_users = relationship(
        "AttendanceLeavesModule",
        secondary="attendance_leave_notify",
        back_populates="notify_to_users",
    )

    personal_contact_info = relationship(
        "PersonalContactInfo", back_populates="user", uselist=False, cascade="all, delete"
    )

    leave_balance = relationship("LeaveBalance", back_populates="user")

    attendance = relationship(
        "AttendancePunchInOutModule", back_populates="user", cascade="all, delete", uselist=True
    )

    family_info = relationship("FamilyInfo", back_populates="user", cascade="all, delete")
    same_as_current_address = Column(Boolean, nullable=False, default=True)

    current_address_id = Column(CHAR(36), ForeignKey("address.id"), nullable=True)
    permanent_address_id = Column(CHAR(36), ForeignKey("address.id"), nullable=True)

    current_address = relationship(
        "Address", foreign_keys=[current_address_id], backref="users_current"
    )
    permanent_address = relationship(
        "Address", foreign_keys=[permanent_address_id], backref="users_permanent"
    )

    social_link = relationship("SocialLinks", back_populates="user", cascade="all, delete")
    password = Column(String(255), nullable=False)
    account_status = Column(Boolean, nullable=False, default=True)
    profile_created = Column(Boolean, nullable=False, default=False)
    reset_password_token = Column(String(255), nullable=True, default=None)
    password_created = Column(Boolean, nullable=False, default=False)
    organization_id = Column(
        CHAR(36),
        ForeignKey(
            "organization.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    organization = relationship("Organization", back_populates="employees")
    post = relationship("OrganizationUpdates", back_populates="publisher", cascade="all, delete")

    feed_likes = relationship("FeedLikes", back_populates="user", cascade="all, delete")
    feed_comments = relationship("FeedComments", back_populates="user", cascade="all, delete")

    sessions = relationship("Sessions", back_populates="user", cascade="all, delete")

    applied_leaves = relationship(
        "AttendanceLeavesModule",
        foreign_keys="[AttendanceLeavesModule.user_id]",
        back_populates="user",
    )

    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )


class Organization(BaseModel):
    __tablename__ = "organization"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    general_info = relationship(
        "OrganizationGeneralInfo",
        back_populates="organization",
        uselist=False,
        cascade="all, delete",
    )
    address = relationship(
        "OrganizationAddress", back_populates="organization", cascade="all, delete"
    )
    contact_info = relationship(
        "OrganizationContactInfo", back_populates="organization", cascade="all, delete"
    )
    about_info = relationship(
        "OrganizationAboutInfo", back_populates="organization", cascade="all, delete"
    )
    organization_settings = relationship(
        "OrganizationSettings", back_populates="organization", uselist=False, cascade="all, delete"
    )
    status = Column(Boolean, nullable=False, default=True)

    employees = relationship("User", back_populates="organization", cascade="all, delete")

    config_modules = relationship(
        "ConfigModule", back_populates="organization", cascade="all, delete"
    )

    client_inquires = relationship(
        "ClientInquires", back_populates="organization", cascade="all, delete", uselist=False
    )

    org_updates = relationship(
        "OrganizationUpdates", back_populates="organization", cascade="all, delete"
    )

    social_media_accounts = relationship(
        "SocialMediaAccount", back_populates="organization", uselist=True, cascade="all, delete"
    )
    social_media_posts = relationship(
        "SocialMediaPosts", back_populates="organization", uselist=True, cascade="all, delete"
    )

    leaves_settings = relationship(
        "LeavesSettings", back_populates="organization", uselist=True, cascade="all, delete"
    )
    locations_config = relationship(
        "OrganizationLocationsConfig",
        back_populates="organization",
        uselist=True,
        cascade="all, delete",
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
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_status = relationship(
        "ProjectStatus", back_populates="config_module", cascade="all, delete"
    )
    department = relationship("Department", back_populates="config_module", cascade="all, delete")
    designations = relationship(
        "Designations", back_populates="config_module", cascade="all, delete"
    )

    inquiry_form_schema = relationship(
        "InquiryFormSchema", back_populates="config_module", cascade="all, delete"
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

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    api_key = Column(String(255), nullable=False)
    api_secrete = Column(String(255), nullable=False)

    status = Column(Boolean, nullable=False, default=False)

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

    form_id = Column(CHAR(36), nullable=False, unique=False, default=None)

    form_name = Column(String(255), nullable=False, unique=False, default=None)

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    data = Column(JSON, nullable=True, default=None)

    client_inquire_id = Column(
        CHAR(36),
        ForeignKey("client_inquires.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    client_inquire = relationship("ClientInquires", back_populates="client_inquires_data")


class OrganizationUpdates(BaseModel):
    __tablename__ = "organization_updates"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    images = Column(Text, nullable=True, default=None)
    description = Column(Text, nullable=True, default=None)

    isCommentDisabled = Column(Boolean, default=False, nullable=True)

    isLikeDisabled = Column(Boolean, default=False, nullable=True)

    likes = relationship("FeedLikes", back_populates="organization_updates", cascade="all, delete")

    comments = relationship(
        "FeedComments", back_populates="organization_updates", cascade="all, delete"
    )

    # comments = relationship("FeedComments", back_populates="organization_updates", cascade="all, delete")
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    publisher = relationship("User", back_populates="post", uselist=False)

    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    source_type = Column(
        Enum(
            "system",
            "announcement_team",
            "user",
            name="source_type_enum",
        ),
        nullable=False,
        default="user",
    )

    announcement_type = Column(
        Enum(
            "general",
            "product_update",
            "birthday_wish",
            "work_anniversary_wish",
            name="announcement_type_enum",
        ),
        nullable=True,
    )

    organization = relationship("Organization", back_populates="org_updates")

    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )
