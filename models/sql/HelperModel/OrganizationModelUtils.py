import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import backref, relationship

from models.sql.Models import BaseModel


class OrganizationGeneralInfo(BaseModel):
    __tablename__ = "organization_general_info"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    organization_name = Column(String(255), nullable=False, default=None)
    primary_email = Column(String(255), nullable=False, default=None, index=True)
    indexed_email_domain = Column(String(255), nullable=False, default=None, index=True)
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
    industry = Column(String(255), nullable=False, default=None)
    industry_slug = Column(String(255), nullable=False, default=None)
    employee_count = Column(String(255), nullable=False, default=None)
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

    about = Column(Text, nullable=True, default=None)
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

    total_gross_hours = Column(Integer, nullable=True, default=None)
    total_effective_hours = Column(Integer, nullable=True, default=None)

    half_day_gross_hours = Column(Integer, nullable=True, default=None)
    half_day_effective_hours = Column(Integer, nullable=True, default=None)

    error_corratin_metting = Column(Integer, nullable=True, default=None)

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

    parent_id = Column(CHAR(36), ForeignKey("feed_comments.id"), nullable=True, index=True)
    comment_replies = relationship(
        "FeedComments", backref=backref("parent", remote_side=[id]), cascade="all, delete-orphan"
    )

    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", back_populates="feed_comments", uselist=False)

    organization_update_id = Column(
        CHAR(36),
        ForeignKey("organization_updates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_updates = relationship("OrganizationUpdates", back_populates="comments")


class LeavesSettings(BaseModel):
    __tablename__ = "organization_leaves_settings"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    leave_name = Column(String(255), nullable=False, default=None, unique=True)
    leave_code = Column(String(255), nullable=False, default=None, unique=True)

    is_paid = Column(Boolean, nullable=False, default=False)
    max_number_of_leave = Column(Integer, nullable=False, default=0)

    refill_quarterly = Column(Boolean, nullable=False, default=False)
    refill_from = Column(
        Enum(
            "January",
            "April",
            "July",
            "October",
            name="refill_quarter_start_enum",
        ),
        nullable=True,
        default="January",
    )

    description = Column(Text, nullable=True, default=None)

    gender = Column(JSON, nullable=True, default=list)
    employee_status = Column(JSON, nullable=True, default=list)
    marital_status = Column(JSON, nullable=True, default=list)

    status = Column(Boolean, default=True, nullable=False)

    leaves = relationship("AttendanceLeavesModule", back_populates="leave_type")

    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization = relationship("Organization", back_populates="leaves_settings")

    leave_balance = relationship("LeaveBalance", back_populates="leave_type")

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


class LeaveBalance(BaseModel):
    __tablename__ = "leave_balance"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    leave_type_id = Column(CHAR(36), ForeignKey("organization_leaves_settings.id", ondelete="CASCADE"))
    leave_type = relationship("LeavesSettings", back_populates="leave_balance")

    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    user = relationship(
        "User",
        back_populates="leave_balance",
    )

    available_leaves = Column(Integer, nullable=False, default=0)
    last_refill_date = Column(Date, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )


class OrganizationLocationsConfig(BaseModel):
    __tablename__ = "organization_locations_config"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    location_name = Column(String(255), nullable=False, default=None)
    location_coordinates = Column(Text, nullable=False, default=None)

    allowed_radius_meters = Column(Integer, default=500, nullable=False)

    status = Column(Boolean, default=True, nullable=False)

    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    organization = relationship("Organization", back_populates="locations_config")

    created_by = Column(JSON, nullable=True)
    updated_by = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )
