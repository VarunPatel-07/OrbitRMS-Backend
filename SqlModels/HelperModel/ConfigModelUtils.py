import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Enum
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import relationship

from SqlModels.Models import BaseModel



class ProjectStatus(BaseModel):
    __tablename__ = "config_model_project_status"
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    status_name = Column(String(255), nullable=False)
    source_type = Column(Enum("default", "user_created", name="source_type_enum"), nullable=False)
    config_module_id = Column(
        CHAR(36),
        ForeignKey("config_module.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    config_module = relationship("ConfigModule", back_populates="project_status")
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
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
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
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
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )
