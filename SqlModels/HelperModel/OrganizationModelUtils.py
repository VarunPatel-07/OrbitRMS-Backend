from SqlModels.Models import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import relationship
import uuid


class OrganizationGeneralInfo(BaseModel):
    __tablename__ = "organization_general_info"

    id = Column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    organization_name = Column(String(255), nullable=False, default=None)
    primary_email = Column(String(255), nullable=False, default=None)
    primary_number = Column(String(255), nullable=False, default=None)
    portal_url = Column(String(255), nullable=False, default=None)
    website_url = Column(String(255), nullable=True, default=None)
    is_meta_verified = Column(Boolean, nullable=False, default=None)
    meta_key = Column(String(255), nullable=False, default=None)
    meta_value = Column(String(255), nullable=False, default=None)
    terms_accepted = Column(Boolean, nullable=False, default=None)
    email_verified = Column(Boolean, nullable=False, default=None)
    organization_profile_picture = Column(String(255), nullable=True, default=None)
    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    organization = relationship("Organization", back_populates="organization_general_info")


class OrganizationAddress(BaseModel):
    __tablename__ = "organization_address"
    id = Column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    address = Column(String(255), nullable=True, default=None)
    city = Column(String(255), nullable=True, default=None)
    state = Column(String(255), nullable=True, default=None)
    zip_code = Column(String(255), nullable=True, default=None)
    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    organization = relationship("Organization", back_populates="organization_address")


class OrganizationContactInfo(BaseModel):
    __tablename__ = "organization_contact_info"
    id = Column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    phone_number = Column(String(255), nullable=True, default=None)
    company_email = Column(String(255), nullable=True, default=None)

    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    organization = relationship("Organization", back_populates="organization_contact_info")


class OrganizationAboutInfo(BaseModel):
    __tablename__ = "organization_about_info"
    id = Column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    about = Column(String(255), nullable=True, default=None)
    established_science = Column(String(255), nullable=True, default=None)
    registration_number = Column(String(255), nullable=True, default=None)

    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    organization = relationship("Organization", back_populates="organization_about_info")


class OrganizationSettings(BaseModel):
    __tablename__ = "organization_settings"

    id = Column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    email_domain_slug = Column(String(255), nullable=True, default=None)
    employee_code_prefix = Column(String(255), nullable=True, default=None)
    inter_code_prefix = Column(String(255), nullable=True, default=None)
    default_timezone = Column(String(255), nullable=True, default=None)

    organization_id = Column(
        CHAR(36),
        ForeignKey("organization.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    organization = relationship("Organization", back_populates="organization_settings")
