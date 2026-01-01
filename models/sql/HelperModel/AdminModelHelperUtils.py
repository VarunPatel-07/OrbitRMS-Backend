import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from models.sql.Models import BaseModel


class OrbitAdminSessions(BaseModel):
    __tablename__ = "orbit_admin_session"

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

    admin_signature = Column(String(255), nullable=True, default=None)

    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )

    admin_id = Column(
        CHAR(36),
        ForeignKey("orbit_admin.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    admin = relationship("Admin", back_populates="admin_sessions")


class AdminOrganizationUpdates(BaseModel):
    __tablename__ = "organization_updates_admin"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    images = Column(Text, nullable=True, default=None)
    description = Column(Text, nullable=True, default=None)

    isCommentDisabled = Column(Boolean, default=False, nullable=True)

    isLikeDisabled = Column(Boolean, default=False, nullable=True)

    user_id = Column(
        CHAR(36),
        ForeignKey("orbit_admin.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    publisher = relationship("Admin", back_populates="organization_updates", uselist=False)

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

    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )
