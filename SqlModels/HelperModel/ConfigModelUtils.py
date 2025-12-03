import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import relationship

from SqlModels.Models import BaseModel


class ProjectStatus(BaseModel):
    __tablename__ = "config_model_project_status"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    status_name = Column(String(255), nullable=False)
    source_type = Column(Enum("default", "user_created", name="source_type_enum"), nullable=False)
    status_color = Column(String(255), nullable=False)
    created_by = Column(JSON, nullable=True)
    updated_by = Column(JSON, nullable=True)
    config_module_id = Column(
        CHAR(36),
        ForeignKey("config_module.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    config_module = relationship("ConfigModule", back_populates="project_status")
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )


class Department(BaseModel):
    __tablename__ = "config_model_department"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    department_name = Column(String(255), nullable=False)
    source_type = Column(Enum("default", "user_created", name="source_type_enum"), nullable=False)
    config_module_id = Column(
        CHAR(36),
        ForeignKey("config_module.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    config_module = relationship("ConfigModule", back_populates="department")
    created_by = Column(JSON, nullable=True)
    updated_by = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )


class Designations(BaseModel):
    __tablename__ = "config_model_designations"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    designations_name = Column(String(255), nullable=False)
    source_type = Column(Enum("default", "user_created", name="source_type_enum"), nullable=False)
    config_module_id = Column(
        CHAR(36),
        ForeignKey("config_module.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    config_module = relationship("ConfigModule", back_populates="designations")
    created_by = Column(JSON, nullable=True)
    updated_by = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )


# Now We Will Create The ConfigRole Module Sql Utility


class ConfigRoleModule(BaseModel):
    __tablename__ = "config_role_module"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    role_name = Column(String(255), nullable=False)
    description = Column(String(355), nullable=False)
    source_type = Column(Enum("default", "user_created", name="source_type_enum"), nullable=False)
    is_editable = Column(Boolean, default=True)

    associated_employees = relationship(
        "EmployeeInfo",
        foreign_keys="[EmployeeInfo.employee_role_id]",  # Define this in EmployeeInfo
        back_populates="employee_role",
    )

    # connecting to Parent Config Module

    config_module_id = Column(
        CHAR(36),
        ForeignKey("config_module.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    config_module = relationship("ConfigModule", back_populates="roles_and_permissions")

    # now we will include permission Module Here

    associated_permissions = relationship(
        "RoleAssociatedPermissionModule", back_populates="role_module", cascade="all, delete"
    )
    status = Column(Boolean, default=True, nullable=False)

    # created At UpdatedAt Field
    created_by = Column(JSON, nullable=True)
    updated_by = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )


class RoleAssociatedPermissionModule(BaseModel):
    __tablename__ = "config_role_associated_permissions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    module_label = Column(String(255), nullable=False)
    module_title = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)

    role_module_id = Column(
        CHAR(36),
        ForeignKey("config_role_module.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    parent_module_id = Column(
        CHAR(36),
        ForeignKey("config_role_associated_permissions.id", ondelete="CASCADE", onupdate="CASCADE"),
    )

    role_module = relationship(
        "ConfigRoleModule", back_populates="associated_permissions", cascade="all, delete"
    )

    parent_module = relationship(
        "RoleAssociatedPermissionModule",
        remote_side=[id],
        back_populates="sub_modules",
        cascade="all, delete",
    )
    sub_modules = relationship(
        "RoleAssociatedPermissionModule", back_populates="parent_module", cascade="all, delete"
    )

    permissions = relationship("PermissionModule", back_populates="associated_permissions_module", cascade="all, delete")


class PermissionModule(BaseModel):
    __tablename__ = "permission_modules"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    label = Column(String(255), nullable=False)
    is_allowed = Column(Boolean, nullable=False, default=False)
    show_input = Column(Boolean, nullable=False, default=False)

    associated_permissions_module_id = Column(
        CHAR(36),
        ForeignKey("config_role_associated_permissions.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    associated_permissions_module = relationship(
        "RoleAssociatedPermissionModule", back_populates="permissions"
    )


class InquiryFormSchema(BaseModel):
    __tablename__ = "inquiry_form_schema"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    form_id = Column(CHAR(36), nullable=False, unique=True)
    form_name = Column(String(255), nullable=False, unique=True)

    status = Column(Boolean, nullable=False, default=True)
    description = Column(Text, nullable=True, default=None)

    source_type = Column(Enum("default", "user_created", name="source_type_enum"), nullable=False)

    config_module_id = Column(
        CHAR(36),
        ForeignKey("config_module.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    config_module = relationship("ConfigModule", back_populates="inquiry_form_schema")

    inquiry_form_fields = relationship(
        "InquiryFormFields", back_populates="inquiry_form_schema", cascade="all, delete"
    )

    email_notification = Column(Boolean, nullable=True, default=False)

    authorized_recipient_emails = Column(Text, nullable=True, default=None)

    created_by = Column(JSON, nullable=True)
    updated_by = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )


class InquiryFormFields(BaseModel):
    __tablename__ = "inquiry_form_fields"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    field_name = Column(String(255), nullable=False)
    is_required_field = Column(Boolean, nullable=False, default=True)
    type = Column(String(255), nullable=False)

    source_type = Column(Enum("default", "user_created", name="source_type_enum"), nullable=False)

    inquiry_form_schema_id = Column(
        CHAR(36),
        ForeignKey("inquiry_form_schema.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    inquiry_form_schema = relationship("InquiryFormSchema", back_populates="inquiry_form_fields")

    # created At UpdatedAt Field
    created_by = Column(JSON, nullable=True)
    updated_by = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )


class OrganizationHolidaysSchema(BaseModel):
    __tablename__ = "organization_holidays"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    holiday_name = Column(String(255), nullable=False)
    date = Column(DateTime, nullable=True, default=None)
    year = Column(Integer, nullable=True)

    source_type = Column(Enum("default", "user_created", name="source_type_enum"), nullable=False)
    config_module_id = Column(
        CHAR(36),
        ForeignKey("config_module.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    config_module = relationship("ConfigModule", back_populates="organization_holidays")

    # created At UpdatedAt Field
    created_by = Column(JSON, nullable=True)
    updated_by = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )
