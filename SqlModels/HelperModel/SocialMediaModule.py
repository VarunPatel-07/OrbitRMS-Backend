import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import relationship

from SqlModels.Models import BaseModel


class SocialMediaAccount(BaseModel):
    __tablename__ = "social_media_accounts"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    platform = Column(String(255))
    account_name = Column(String(255))
    access_token = Column(String(255))
    refresh_token = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    extra_data = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)

    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    organization = relationship("Organization", back_populates="social_media_accounts")


class SocialMediaPosts(BaseModel):
    __tablename__ = "social_media_posts"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    caption = Column(Text, nullable=False)
    media_urls = Column(Text, nullable=True)
    type = Column(
        Enum("default", "scheduled", name="post_type_enum"), nullable=False, default="default"
    )

    status = Column(
        Enum("queued", "scheduled", "posted", "cancelled", name="post_status_enum"), nullable=False
    )
    post_logs = Column(Text, nullable=True, default=None)

    selected_platforms = Column(Text, nullable=True)

    is_scheduled = Column(Boolean, default=False)
    scheduled_on = Column(DateTime, nullable=True)

    post_publish_records = Column(Text, nullable=True)
    posted_at = Column(DateTime, nullable=True)

    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    organization = relationship("Organization", back_populates="social_media_posts")

    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )
