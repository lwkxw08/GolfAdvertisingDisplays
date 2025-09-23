from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..database import Base

class Region(Base):
    __tablename__ = "regions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    courses = relationship("Course", back_populates="region")
    users = relationship("User", back_populates="region")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")

class CustomDashboard(Base):
    __tablename__ = "custom_dashboards"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    layout = Column(JSON, nullable=False)  # Dashboard widget configuration
    filters = Column(JSON, nullable=True)  # Default filters
    is_shared = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user = relationship("User")

class DeviceDiagnostic(Base):
    __tablename__ = "device_diagnostics"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    battery_level = Column(Float, nullable=True)
    signal_strength = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    storage_usage = Column(Float, nullable=True)
    firmware_version = Column(String, nullable=True)
    last_error = Column(Text, nullable=True)
    diagnostic_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    device = relationship("Device")

class FontStyle(str, enum.Enum):
    ARIAL = "arial"
    HELVETICA = "helvetica"
    TIMES = "times"
    COURIER = "courier"
    IMPACT = "impact"
    COMIC_SANS = "comic_sans"

class NoticeStyle(Base):
    __tablename__ = "notice_styles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    font_family = Column(Enum(FontStyle), nullable=False, default=FontStyle.ARIAL)
    font_size = Column(Integer, nullable=False, default=24)
    font_weight = Column(String, nullable=False, default="normal")
    text_color = Column(String, nullable=False, default="#000000")
    background_color = Column(String, nullable=False, default="#FFFFFF")
    border_style = Column(String, nullable=True)
    padding = Column(Integer, nullable=False, default=10)
    text_align = Column(String, nullable=False, default="center")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CampaignScheduleType(str, enum.Enum):
    STANDARD = "standard"
    SEASONAL = "seasonal"
    AB_TEST = "ab_test"
    CONDITIONAL = "conditional"

class AdvancedSchedule(Base):
    __tablename__ = "advanced_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    schedule_type = Column(Enum(CampaignScheduleType), nullable=False)
    conditions = Column(JSON, nullable=True)  # Weather, time, occupancy conditions
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    recurrence_pattern = Column(JSON, nullable=True)  # Complex recurrence rules
    priority = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SSOProvider(Base):
    __tablename__ = "sso_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    provider_type = Column(String, nullable=False)  # saml, oauth, oidc
    configuration = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
