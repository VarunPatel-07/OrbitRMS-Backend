import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import relationship

from models.sql.Models import BaseModel


class PersonalInfo(BaseModel):
    __tablename__ = "personal_info"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # todo: add the new field about
    normalized_full_name = Column(String(255), nullable=False, index=True)
    first_name = Column(String(255), nullable=False)
    middle_name = Column(String(255), nullable=True, default=None)
    last_name = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    profile_picture = Column(String(255), nullable=True, default=None)
    profile_picture_bg = Column(String(255), nullable=True, default=None)
    gender = Column(String(255), nullable=False)
    date_of_birth = Column(DateTime)
    blood_group = Column(String(255), nullable=False)
    about = Column(Text, nullable=True, default=None)
    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", back_populates="personal_info")


class EmployeeInfo(BaseModel):
    __tablename__ = "employee_info"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # todo: change the reporting to from storing the json to storing the reference to the reporting to manager id

    status = Column(String(255), nullable=False)
    employee_type = Column(String(255), nullable=True, default=None)
    organization_name = Column(String(255), nullable=False)
    employee_code = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    designation = Column(String(255), nullable=False)
    joining_date = Column(DateTime)
    employee_role_id = Column(
        CHAR(36), ForeignKey("config_role_module.id"), nullable=True, default=None
    )
    employee_role = relationship(
        "ConfigRoleModule",
        back_populates="associated_employees",
        foreign_keys=[employee_role_id],
    )
    employee_email = Column(String(255), nullable=False, default=None, index=True)
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", back_populates="employee_info", foreign_keys=[user_id])

    reporting_to_id = Column(CHAR(36), ForeignKey("users.id"), nullable=True, default=None)

    reporting_manager = relationship(
        "User", back_populates="reporting_employees", foreign_keys=[reporting_to_id]
    )


class EmergencyContact(BaseModel):
    __tablename__ = "emergency_contacts"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    emergency_contact_name = Column(String(255), nullable=False, default=None)
    emergency_contact_number = Column(String(255), nullable=False, default=None)
    emergency_contact_country_info = Column(JSON, nullable=True)

    contact_id = Column(CHAR(36), ForeignKey("personal_contact_info.id"), nullable=False)
    personal_contact_info = relationship("PersonalContactInfo", back_populates="emergency_contacts")


class PersonalContactInfo(BaseModel):
    __tablename__ = "personal_contact_info"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # todo Change the field name form alternative_contact to emergency_contact As a Json and It contain two field emergency_contact_number and emergency_contact_name

    personal_email = Column(String(255), nullable=False, default=None)
    mobile_number = Column(String(255), nullable=False, default=None)
    country_info = Column(JSON, nullable=True)
    emergency_contacts = relationship(
        "EmergencyContact", back_populates="personal_contact_info", cascade="all, delete-orphan"
    )

    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", back_populates="personal_contact_info")


class Children(BaseModel):
    __tablename__ = "children"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    child_name = Column(String(255), nullable=True, default=None)
    child_date_of_birth = Column(DateTime, nullable=True, default=None)

    family_info_id = Column(CHAR(36), ForeignKey("family_info.id"), nullable=False)
    family_info = relationship("FamilyInfo", back_populates="children")


class FamilyInfo(BaseModel):
    __tablename__ = "family_info"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # todo we will also add the children info like name and dob as a array of the children

    father_name = Column(String(255), nullable=False, default=None)
    mother_name = Column(String(255), nullable=False, default=None)
    marital_status = Column(CHAR(36), nullable=False, default=None)
    children = relationship("Children", back_populates="family_info", cascade="all, delete-orphan")

    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", back_populates="family_info")


class Address(BaseModel):
    __tablename__ = "address"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    address = Column(String(255), nullable=False, default=None)
    country = Column(String(255), nullable=False, default=None)
    state = Column(String(255), nullable=False, default=None)
    city = Column(String(255), nullable=False, default=None)
    zip_code = Column(String(255), nullable=False, default=None)
    country_code = Column(String(255), nullable=True, default=None)


class SocialLinks(BaseModel):
    __tablename__ = "social_link"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    icon = Column(Text, nullable=True, default=None)
    name = Column(String(255), nullable=True, default=None)
    link = Column(String(255), nullable=True, default=None)
    target_blank = Column(Boolean, nullable=True, default=True)
    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
    )
    user = relationship("User", back_populates="social_link")


class Sessions(BaseModel):
    __tablename__ = "session"

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
    user_location_info = Column(Text, nullable=True, default=None)

    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )

    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", back_populates="sessions")


class AttendanceLeavesModule(BaseModel):
    __tablename__ = "attendance_leave_module"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    leave_type_id = Column(
        CHAR(36), ForeignKey("organization_leaves_settings.id"), nullable=False, index=True
    )
    leave_type = relationship("LeavesSettings", back_populates="leaves", uselist=False)
    start_date = Column(String(255), nullable=False)
    start_half = Column(Enum("first_half", "second_half", name="half_day_enum"), nullable=False)

    is_planned = Column(Boolean, nullable=False, default=True)

    status = Column(
        Enum("pending", "approved", "rejected", "cancelled", name="leave_status_enum"),
        nullable=False,
        default="pending",
    )
    total_days = Column(Float, nullable=False, default=0)

    end_date = Column(String(255), nullable=False)
    end_half = Column(Enum("first_half", "second_half", name="half_day_enum"), nullable=False)

    description = Column(String(255), nullable=True, default=None)

    documents = Column(Text, nullable=True, default=None)

    notify_to_id = Column(CHAR(36), ForeignKey("users.id"), nullable=True, default=None)

    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", foreign_keys=[user_id], back_populates="applied_leaves")

    notify_to_users = relationship(
        "User", secondary="attendance_leave_notify", back_populates="notifying_users"
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


class AttendancePunchInOutModule(BaseModel):
    __tablename__ = "attendance_punch_in_out_module"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User", back_populates="attendance")

    punch_in_time = Column(String(255), nullable=False)
    punch_out_time = Column(String(255), nullable=False)

    status = Column(
        Enum(
            "active",
            "completed",
            "system_ended",
            name="attendance_punch_in_out_module_status_enum",
        ),
        default="active",
    )

    punch_in_coordinates = Column(Text, nullable=False)
    punch_out_coordinates = Column(Text, nullable=False)
    is_mislinious = Column(Boolean, nullable=False, default=False)

    total_working_hours = Column(Float, default=0)
    total_break_hours = Column(Float, default=0)
    gross_hours = Column(Float, default=0)

    attendance_breaks = relationship(
        "AttendanceBreakModel", back_populates="session", cascade="all, delete", uselist=True
    )

    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("UTC")), nullable=False)
    updated_at = Column(
        DateTime,
        default=None,
        onupdate=lambda: datetime.now(ZoneInfo("UTC")),
        nullable=True,
    )


class AttendanceBreakModel(BaseModel):
    __tablename__ = "attendance_break_model"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    session_id = Column(
        CHAR(36),
        ForeignKey("attendance_punch_in_out_module.id", ondelete="CASCADE"),
        nullable=False,
    )
    session = relationship("AttendancePunchInOutModule", back_populates="attendance_breaks")

    break_start_time = Column(String(255), nullable=False)
    break_end_time = Column(String(255), nullable=False)

    break_duration = Column(Float, default=0)

    punch_in_coordinates = Column(Text, nullable=False)
    punch_out_coordinates = Column(Text, nullable=False)
    is_mislinious = Column(Boolean, nullable=False, default=False)

    status = Column(
        Enum("active", "completed", "system_ended", name="break_status_enum"),
        default="active",
    )
