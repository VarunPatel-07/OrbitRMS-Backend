
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.mysql import CHAR , JSON
import uuid
from sqlalchemy.orm import relationship
from Database.Database import BaseModel
from datetime import datetime , timezone
from SqlModels.HelperModel.UserModelUtils import PersonalInfo , EmployeeInfo , PersonalContactInfo , FamilyInfo , Address , EmergencyContact , Children



class User(BaseModel):
    __tablename__ = "users"
    
    id = Column(CHAR(36), primary_key=True, default=lambda :str(uuid.uuid4()) ,index=True)
    personal_info = relationship("PersonalInfo", back_populates="user")
    employee_info = relationship("EmployeeInfo", back_populates="user")
    personal_contact_info = relationship("PersonalContactInfo", back_populates="user")
    family_info = relationship("FamilyInfo", back_populates="user")
    address = relationship("Address", back_populates="user")
    emergency_contact = relationship("EmergencyContact", back_populates="user" , cascade="all, delete-orphan")
    social_link = Column(JSON)
    created_at = Column(DateTime , default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime , default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False)
    password = Column(String(255), nullable=False)
    
    