from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import enum
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./golf_cms.db")

if SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CLIENT_TENANT = "client_tenant"

class CampaignInterval(str, enum.Enum):
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)  # Only for client tenants
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    course = relationship("Course", back_populates="users")

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    devices = relationship("Device", back_populates="course")
    users = relationship("User", back_populates="course")
    notices = relationship("Notice", back_populates="course")

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "Tee Box 1", "Hole 3 Tee"
    device_id = Column(String, unique=True, index=True, nullable=False)  # Unique device identifier
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    is_online = Column(Boolean, default=False)
    last_sync = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    course = relationship("Course", back_populates="devices")
    campaigns = relationship("SponsorCampaign", back_populates="device")
    notices = relationship("Notice", back_populates="device")

class SponsorCampaign(Base):
    __tablename__ = "sponsor_campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    sponsor_name = Column(String, nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    creative_path = Column(String, nullable=False)  # Path to uploaded image
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    rotation_interval = Column(Integer, nullable=False)  # Number of units
    rotation_unit = Column(Enum(CampaignInterval), nullable=False)  # hours/days/weeks/months
    priority = Column(Integer, default=1)  # For ordering campaigns
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    device = relationship("Device", back_populates="campaigns")

class Notice(Base):
    __tablename__ = "notices"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)  # Max 1 hour from start_time
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    device = relationship("Device", back_populates="notices")
    course = relationship("Course", back_populates="notices")
    creator = relationship("User")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
