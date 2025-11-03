from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum, Float, Index, JSON, Date, DECIMAL, UniqueConstraint
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
    start_time = Column(String, nullable=True)  # Format: "HH:MM" (e.g., "09:00")
    end_time = Column(String, nullable=True)    # Format: "HH:MM" (e.g., "17:00")
    days_of_week = Column(String, nullable=True)  # JSON array: ["monday", "tuesday", ...]
    rotation_interval = Column(Integer, nullable=False)
    rotation_unit = Column(Enum(CampaignInterval), nullable=False)
    priority = Column(Integer, default=1)
    schedule_id = Column(Integer, ForeignKey("advanced_schedules.id"), nullable=True)
    ab_test_group = Column(String, nullable=True)  # A, B, or control
    performance_metrics = Column(Text, nullable=True)  # JSON string
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
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
    recurrence_pattern = Column(JSON, nullable=True)  # {"type": "daily"|"weekly", "days": [...], "time": "HH:MM"}
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

class AlertType(str, enum.Enum):
    DEVICE_OFFLINE = "device_offline"
    LOW_BATTERY = "low_battery"
    HIGH_TEMPERATURE = "high_temperature"
    DISPLAY_ERROR = "display_error"
    CONNECTIVITY_ISSUE = "connectivity_issue"
    STORAGE_FULL = "storage_full"
    FIRMWARE_UPDATE_FAILED = "firmware_update_failed"

class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"

class CommandStatus(str, enum.Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class DeviceHealthMetric(Base):
    __tablename__ = "device_health_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    battery_level = Column(Float, nullable=True)
    battery_voltage = Column(Float, nullable=True)
    is_charging = Column(Boolean, default=False)
    connectivity_type = Column(String(20), nullable=True)
    signal_strength = Column(Float, nullable=True)
    wifi_ssid = Column(String(100), nullable=True)
    temperature = Column(Float, nullable=True)
    cpu_usage = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    storage_usage = Column(Float, nullable=True)
    display_errors = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    uptime_seconds = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    device = relationship("Device")
    
    __table_args__ = (
        Index('idx_device_health_device_timestamp', 'device_id', 'timestamp'),
    )

class DeviceAlert(Base):
    __tablename__ = "device_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    alert_type = Column(Enum(AlertType), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    alert_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    device = relationship("Device")
    resolver = relationship("User", foreign_keys=[resolved_by])
    notifications = relationship("AlertNotification", back_populates="alert")
    
    __table_args__ = (
        Index('idx_device_alerts_device', 'device_id'),
        Index('idx_device_alerts_type', 'alert_type'),
        Index('idx_device_alerts_resolved', 'is_resolved'),
    )

class AlertNotification(Base):
    __tablename__ = "alert_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("device_alerts.id"), nullable=False)
    notification_type = Column(String(20), nullable=False)  # email, sms
    recipient = Column(String(200), nullable=False)
    status = Column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.PENDING)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    alert = relationship("DeviceAlert", back_populates="notifications")
    
    __table_args__ = (
        Index('idx_alert_notifications_status', 'status'),
    )

class DeviceRemoteCommand(Base):
    __tablename__ = "device_remote_commands"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    command_type = Column(String(50), nullable=False)  # reboot, refresh_display, update_firmware, get_logs, etc.
    command_data = Column(JSON, nullable=True)
    status = Column(Enum(CommandStatus), nullable=False, default=CommandStatus.PENDING)
    issued_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    executed_at = Column(DateTime(timezone=True), nullable=True)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    device = relationship("Device")
    issuer = relationship("User", foreign_keys=[issued_by])
    
    __table_args__ = (
        Index('idx_device_commands_device', 'device_id'),
        Index('idx_device_commands_status', 'status'),
    )

class CampaignAnalytics(Base):
    __tablename__ = "campaign_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("sponsor_campaigns.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    date = Column(Date, nullable=False)
    impressions = Column(Integer, default=0)
    rotation_count = Column(Integer, default=0)
    display_duration_seconds = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    campaign = relationship("SponsorCampaign")
    device = relationship("Device")
    
    __table_args__ = (
        Index('idx_campaign_analytics_campaign', 'campaign_id'),
        Index('idx_campaign_analytics_device', 'device_id'),
        Index('idx_campaign_analytics_date', 'date'),
    )

class CampaignDisplayLog(Base):
    """Proof-of-Play logging: immutable record of every campaign display"""
    __tablename__ = "campaign_display_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID for idempotency
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("sponsor_campaigns.id"), nullable=True, index=True)
    content_type = Column(String(20), nullable=False)  # 'campaign' or 'notice'
    displayed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    image_hash = Column(String(64), nullable=False)  # SHA-256 hash of displayed image
    hash_algo = Column(String(10), default='sha256')
    creative_url = Column(Text, nullable=True)
    render_result = Column(Boolean, nullable=False)  # Did display succeed?
    connectivity_type = Column(String(20), nullable=True)  # wifi/lte/none
    power_mode = Column(String(20), nullable=True)  # fast/normal/slow/deep_sleep
    firmware_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    device = relationship("Device")
    campaign = relationship("SponsorCampaign")
    
    __table_args__ = (
        Index('idx_display_logs_campaign_date', 'campaign_id', 'displayed_at'),
    )

class DeviceUptimeWindow(Base):
    """5-minute windows of device uptime data for idempotent ingestion"""
    __tablename__ = "device_uptime_windows"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    uptime_minutes = Column(Integer, default=0)
    downtime_minutes = Column(Integer, default=0)
    total_syncs = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    device = relationship("Device")
    
    __table_args__ = (
        Index('idx_uptime_windows_device', 'device_id'),
        Index('idx_uptime_windows_start', 'window_start'),
        Index('idx_uptime_windows_device_start', 'device_id', 'window_start'),
        UniqueConstraint('device_id', 'window_start', name='unique_device_window'),
    )

class DeviceUptimeLog(Base):
    __tablename__ = "device_uptime_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    date = Column(Date, nullable=False)
    uptime_minutes = Column(Integer, default=0)
    downtime_minutes = Column(Integer, default=0)
    total_syncs = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    device = relationship("Device")
    
    __table_args__ = (
        Index('idx_device_uptime_device', 'device_id'),
        Index('idx_device_uptime_date', 'date'),
    )

class RevenueConfiguration(Base):
    __tablename__ = "revenue_configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    device_cost_per_month = Column(Float, default=0.0)
    sponsorship_revenue_per_month = Column(Float, default=0.0)
    course_revenue_split_percentage = Column(Float, default=50.0)
    platform_revenue_split_percentage = Column(Float, default=50.0)
    notes = Column(Text, nullable=True)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    course = relationship("Course")
    
    __table_args__ = (
        Index('idx_revenue_config_course', 'course_id'),
        Index('idx_revenue_config_dates', 'effective_from', 'effective_to'),
    )

class RevenueAnalytics(Base):
    __tablename__ = "revenue_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    total_device_costs = Column(Float, default=0.0)
    total_sponsorship_revenue = Column(Float, default=0.0)
    course_revenue_share = Column(Float, default=0.0)
    platform_revenue_share = Column(Float, default=0.0)
    net_revenue = Column(Float, default=0.0)
    active_devices_count = Column(Integer, default=0)
    active_campaigns_count = Column(Integer, default=0)
    total_impressions = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    course = relationship("Course")
    region = relationship("Region")
    
    __table_args__ = (
        Index('idx_revenue_analytics_course', 'course_id'),
        Index('idx_revenue_analytics_region', 'region_id'),
        Index('idx_revenue_analytics_period', 'period_start', 'period_end'),
    )

class SavedReport(Base):
    __tablename__ = "saved_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    report_name = Column(String(200), nullable=False)
    report_type = Column(String(50), nullable=False)
    filters = Column(JSON, nullable=True)
    date_range_start = Column(Date, nullable=True)
    date_range_end = Column(Date, nullable=True)
    course_ids = Column(JSON, nullable=True)
    region_ids = Column(JSON, nullable=True)
    schedule_frequency = Column(String(20), nullable=True)
    last_generated_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user = relationship("User")
    
    __table_args__ = (
        Index('idx_saved_reports_user', 'user_id'),
        Index('idx_saved_reports_type', 'report_type'),
    )

class ReportExport(Base):
    __tablename__ = "report_exports"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    saved_report_id = Column(Integer, ForeignKey("saved_reports.id"), nullable=True)
    report_type = Column(String(50), nullable=False)
    export_format = Column(String(10), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    filters = Column(JSON, nullable=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")
    saved_report = relationship("SavedReport")
    
    __table_args__ = (
        Index('idx_report_exports_user', 'user_id'),
        Index('idx_report_exports_generated', 'generated_at'),
    )

class QRCode(Base):
    __tablename__ = "qr_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("sponsor_campaigns.id"), nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    qr_code_key = Column(String(100), unique=True, nullable=False, index=True)
    destination_url = Column(Text, nullable=False)
    title = Column(String(200))
    description = Column(Text)
    qr_code_image_url = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    campaign = relationship("SponsorCampaign", backref="qr_codes")
    course = relationship("Course", backref="qr_codes")
    creator = relationship("User", foreign_keys=[created_by])
    scans = relationship("QRCodeScan", back_populates="qr_code", cascade="all, delete-orphan")
    analytics = relationship("QRCodeAnalytics", back_populates="qr_code", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_qr_codes_campaign', 'campaign_id'),
        Index('idx_qr_codes_course', 'course_id'),
    )

class QRCodeScan(Base):
    __tablename__ = "qr_code_scans"
    
    id = Column(Integer, primary_key=True, index=True)
    qr_code_id = Column(Integer, ForeignKey("qr_codes.id"), nullable=False)
    scan_timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    device_type = Column(String(50))
    browser = Column(String(100))
    operating_system = Column(String(100))
    country = Column(String(100))
    city = Column(String(100))
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    referrer = Column(Text)
    is_unique_visitor = Column(Boolean, default=True, index=True)
    session_id = Column(String(100), index=True)
    
    qr_code = relationship("QRCode", back_populates="scans")
    
    __table_args__ = (
        Index('idx_qr_scans_qr_code', 'qr_code_id'),
    )

class QRCodeAnalytics(Base):
    __tablename__ = "qr_code_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    qr_code_id = Column(Integer, ForeignKey("qr_codes.id"), nullable=False)
    date = Column(Date, nullable=False)
    total_scans = Column(Integer, default=0)
    unique_scans = Column(Integer, default=0)
    mobile_scans = Column(Integer, default=0)
    desktop_scans = Column(Integer, default=0)
    tablet_scans = Column(Integer, default=0)
    top_country = Column(String(100))
    top_city = Column(String(100))
    avg_scans_per_hour = Column(DECIMAL(10, 2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    qr_code = relationship("QRCode", back_populates="analytics")
    
    __table_args__ = (
        Index('idx_qr_analytics_qr_code', 'qr_code_id'),
        Index('idx_qr_analytics_date', 'date'),
    )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
