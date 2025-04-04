import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Table, Integer, Boolean
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import relationship

from zoneinfo import ZoneInfo

from SqlModels.Models import BaseModel


class ProjectStatus(BaseModel):
    __tablename__ = "config_model_project_status"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

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
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=datetime.now(timezone.utc),
        nullable=True,
    )


class AttachmentType(BaseModel):
    __tablename__ = "config_model_attachment_type"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    attachment_name = Column(String(255), nullable=False)
    source_type = Column(Enum("default", "user_created", name="source_type_enum"), nullable=False)
    config_module_id = Column(
        CHAR(36),
        ForeignKey("config_module.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    config_module = relationship("ConfigModule", back_populates="attachment_type")
    created_by = Column(JSON, nullable=True)
    updated_by = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=datetime.now(timezone.utc),
        nullable=True,
    )


class Designations(BaseModel):
    __tablename__ = "config_model_designations"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

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

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    role_name = Column(String(255), nullable=False)
    description = Column(String(355), nullable=False)
    source_type = Column(Enum("default", "user_created", name="source_type_enum"), nullable=False)

    # connecting to Parent Config Module

    config_module_id = Column(
        CHAR(36),
        ForeignKey("config_module.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    config_module = relationship("ConfigModule", back_populates="roles_and_permissions")

    # now we will include permission Module Here

    associated_permissions = relationship(
        "RoleAssociatedPermissionModule", back_populates="role_module"
    )

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

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    module_label = Column(String(255), nullable=False)
    module_title = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)

    role_module_id = Column(
        CHAR(36),
        ForeignKey("config_role_module.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    parent_module_id = Column(CHAR(36), ForeignKey("config_role_associated_permissions.id"))

    role_module = relationship("ConfigRoleModule", back_populates="associated_permissions")

    parent_module = relationship(
        "RoleAssociatedPermissionModule", remote_side=[id], back_populates="sub_modules"
    )
    sub_modules = relationship("RoleAssociatedPermissionModule", back_populates="parent_module")

    permissions = relationship("PermissionModule", back_populates="associated_permissions_module")


class PermissionModule(BaseModel):
    __tablename__ = "permission_modules"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

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
