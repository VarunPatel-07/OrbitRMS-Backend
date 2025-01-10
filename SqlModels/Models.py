from datetime import datetime , timezone
from symtable import Class

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.mysql import CHAR , JSON
import uuid

from sqlalchemy.orm import relationship

from Database.Database import BaseModel


class User(BaseModel):
    __tablename__ =   'users'

    id =  Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()) , index=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False , unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    Organizations = Column(JSON, nullable=False)
    default_organization_id = Column(CHAR(255), nullable=False)
    is_email_verified = Column(Boolean, nullable=False, default=False)
    two_Step_verification = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    organizations = relationship('Organization', back_populates='owner')
    members = relationship('Members', back_populates='users')

class Organization(BaseModel):
    __tablename__ = 'organizations'
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()) , index=True)
    organization_url = Column(String(255), nullable=False)
    organization_name = Column(String(255), nullable=False)
    organization_password = Column(String(255), nullable=False)
    organization_secret = Column(String(255), nullable=False)
    owner_id = Column(CHAR(36),ForeignKey('users.id'), nullable=False)
    owner  = relationship('User', back_populates='organizations')

    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    Members = relationship('Members', back_populates='organization')


class Members(BaseModel):
    __tablename__ = 'members'

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()) , index=True)

    user_id = Column(CHAR(36), ForeignKey('users.id'), nullable=False)
    user = relationship('User', back_populates='members')

    organization_id = Column(CHAR(36), ForeignKey('organizations.id'), nullable=False)
    organization = relationship('Organization', back_populates='members')

    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
