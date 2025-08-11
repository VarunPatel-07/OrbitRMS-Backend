import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import relationship

from SqlModels.Models import BaseModel


class OrganizationGeneralInfo(BaseModel):
    __tablename__ = "organization_general_info"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    organization_name = Column(String(255), nullable=False, default=None)
    primary_email = Column(String(255), nullable=False, default=None)
    primary_number = Column(String(255), nullable=False, default=None)
    country_info = Column(JSON, nullable=True)
    portal_url = Column(String(255), nullable=False, default=None)
    portal_slug = Column(String(255), nullable=False, default=None)
    website_url = Column(String(255), nullable=True, default=None)
    is_meta_verified = Column(Boolean, nullable=False, default=False)
    meta_key = Column(String(255), nullable=False, default=None)
    meta_value = Column(String(255), nullable=False, default=None)
    terms_accepted = Column(Boolean, nullable=False, default=False)
    email_verified = Column(Boolean, nullable=False, default=False)
    organization_profile_picture = Column(String(255), nullable=True, default=None)
    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    organization = relationship("Organization", back_populates="general_info")


class OrganizationAddress(BaseModel):
    __tablename__ = "organization_address"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    address = Column(String(255), nullable=True, default=None)
    city = Column(String(255), nullable=True, default=None)
    state = Column(String(255), nullable=True, default=None)
    zip_code = Column(String(255), nullable=True, default=None)
    country = Column(String(255), nullable=True, default=None)
    country_code = Column(String(255), nullable=True, default=None)
    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    organization = relationship("Organization", back_populates="address")


class OrganizationContactInfo(BaseModel):
    __tablename__ = "organization_contact_info"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    phone_number = Column(String(255), nullable=True, default=None)
    company_email = Column(String(255), nullable=True, default=None)
    country_info = Column(JSON, nullable=True)

    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    organization = relationship("Organization", back_populates="contact_info")


class OrganizationAboutInfo(BaseModel):
    __tablename__ = "organization_about_info"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    about = Column(String(255), nullable=True, default=None)
    established_science = Column(DateTime, nullable=True)
    registration_number = Column(String(255), nullable=True, default=None)

    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    organization = relationship("Organization", back_populates="about_info")


class OrganizationSettings(BaseModel):
    __tablename__ = "organization_settings"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    email_domain_slug = Column(String(255), nullable=True, default=None)
    employee_code_prefix = Column(String(255), nullable=True, default=None)
    intern_code_prefix = Column(String(255), nullable=True, default=None)
    default_timezone = Column(String(255), nullable=True, default=None)
    default_dateformat = Column(String(255), nullable=True, default=None)

    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    organization = relationship("Organization", back_populates="organization_settings")


class FeedLikes(BaseModel):
    __tablename__ = "feed_likes"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", back_populates="feed_likes", uselist=False)

    organization_update_id = Column(
        CHAR(36),
        ForeignKey("organization_updates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_updates = relationship("OrganizationUpdates", back_populates="likes")


class FeedComments(BaseModel):

    __tablename__ = "feed_comments"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    is_replay = Column(Boolean, nullable=False, default=False)

    comment = Column(Text, nullable=True, default=None)

    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", back_populates="feed_comments", uselist=False)

    organization_update_id = Column(
        CHAR(36),
        ForeignKey("organization_updates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_updates = relationship("OrganizationUpdates", back_populates="comments")
