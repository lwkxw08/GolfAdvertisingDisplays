from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum, Float, Index, JSON
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
    ADMIN = "admin"  # Legacy value for backward compatibility
    SUPER_ADMIN = "super_admin"
    REGIONAL_ADMIN = "regional_admin"
    COURSE_MANAGER = "course_manager"
    CLIENT_TENANT = "client_tenant"

class CampaignInterval(str, enum.Enum):
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"

class PlanType(str, enum.Enum):
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class DeviceOrientation(str, enum.Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    permissions = Column(Text, nullable=True)  # JSON string of specific permissions
    last_login = Column(DateTime(timezone=True), nullable=True)
    sso_provider = Column(String, nullable=True)  # For SSO integration
    sso_user_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    course = relationship("Course", back_populates="users")
    region = relationship("Region", back_populates="users", foreign_keys=[region_id])

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    owner_email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    onboarding_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    devices = relationship("Device", back_populates="course")
    users = relationship("User", back_populates="course")
    notices = relationship("Notice", back_populates="course")
    subscription = relationship("Subscription", back_populates="course", uselist=False)
    region = relationship("Region", back_populates="courses", foreign_keys=[region_id])

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    device_id = Column(String, unique=True, index=True, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    is_online = Column(Boolean, default=False)
    last_sync = Column(DateTime(timezone=True), nullable=True)
    firmware_version = Column(String, nullable=True)
    hardware_version = Column(String, nullable=True)
    remote_update_enabled = Column(Boolean, default=True)
    diagnostic_enabled = Column(Boolean, default=True)
    orientation = Column(Enum(DeviceOrientation), nullable=False, default=DeviceOrientation.PORTRAIT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    course = relationship("Course", back_populates="devices")
    campaigns = relationship("SponsorCampaign", back_populates="device")
    notices = relationship("Notice", back_populates="device")
    diagnostics = relationship("DeviceDiagnostic", back_populates="device", foreign_keys="DeviceDiagnostic.device_id")

class SponsorCampaign(Base):
    __tablename__ = "sponsor_campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    sponsor_name = Column(String, nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    creative_path = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    rotation_interval = Column(Integer, nullable=False)
    rotation_unit = Column(Enum(CampaignInterval), nullable=False)
    priority = Column(Integer, default=1)
    schedule_id = Column(Integer, ForeignKey("advanced_schedules.id"), nullable=True)
    ab_test_group = Column(String, nullable=True)  # A, B, or control
    performance_metrics = Column(Text, nullable=True)  # JSON string
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    device = relationship("Device", back_populates="campaigns")
    schedule = relationship("AdvancedSchedule")

class Notice(Base):
    __tablename__ = "notices"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False)  # Exact duration in minutes
    style_id = Column(Integer, ForeignKey("notice_styles.id"), nullable=True)
    schedule_id = Column(Integer, ForeignKey("advanced_schedules.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    device = relationship("Device", back_populates="notices")
    course = relationship("Course", back_populates="notices")
    creator = relationship("User")
    style = relationship("NoticeStyle", foreign_keys=[style_id])
    schedule = relationship("AdvancedSchedule", foreign_keys=[schedule_id])

class NoticeTemplate(Base):
    __tablename__ = "notice_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    style_id = Column(Integer, ForeignKey("notice_styles.id"), nullable=True)
    default_duration_minutes = Column(Integer, default=60)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    course = relationship("Course")
    creator = relationship("User")
    style = relationship("NoticeStyle", foreign_keys=[style_id])

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, unique=True)
    stripe_customer_id = Column(String, unique=True, nullable=True)
    stripe_subscription_id = Column(String, unique=True, nullable=True)
    plan_type = Column(Enum(PlanType), nullable=False, default=PlanType.BASIC)
    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.TRIALING)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    course = relationship("Course", back_populates="subscription")

class DeviceAnalytics(Base):
    __tablename__ = "device_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    sync_timestamp = Column(DateTime(timezone=True), nullable=False)
    uptime_hours = Column(Float, default=0.0)
    impressions_count = Column(Integer, default=0)
    notices_displayed = Column(Integer, default=0)
    campaigns_displayed = Column(Integer, default=0)
    connectivity_type = Column(String(20), default="wifi")
    power_level = Column(Float, default=85.0)
    signal_strength = Column(Float, default=-50.0)
    error_count = Column(Integer, default=0)
    last_refresh_duration = Column(Float, default=19.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    device = relationship("Device")
    
    __table_args__ = (
        Index('idx_device_analytics_device_timestamp', 'device_id', 'sync_timestamp'),
    )

class EmailTemplate(Base):
    __tablename__ = "email_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    subject = Column(String, nullable=False)
    html_content = Column(Text, nullable=False)
    text_content = Column(Text, nullable=True)
    variables = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class EmailLog(Base):
    __tablename__ = "email_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    recipient_email = Column(String, nullable=False)
    template_name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    status = Column(String, nullable=False)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_email_logs_recipient_sent', 'recipient_email', 'sent_at'),
    )

class Region(Base):
    __tablename__ = "regions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    courses = relationship("Course", back_populates="region", foreign_keys="Course.region_id")
    users = relationship("User", back_populates="region", foreign_keys="User.region_id")

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
    layout = Column(JSON, nullable=False)
    filters = Column(JSON, nullable=True)
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
    
    device = relationship("Device", foreign_keys=[device_id])

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
    conditions = Column(JSON, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    recurrence_pattern = Column(JSON, nullable=True)
    priority = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SSOProvider(Base):
    __tablename__ = "sso_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    provider_type = Column(String, nullable=False)
    configuration = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
