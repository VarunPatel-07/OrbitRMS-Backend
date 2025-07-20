import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from SqlModels.Models import BaseModel


class OrbitAdminSessions(BaseModel):
    __tablename__ = "orbit_admin_session"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
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
