from pydantic import BaseModel, validator, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from .database import UserRole, CampaignInterval, SubscriptionStatus, PlanType, DeviceOrientation, AlertType, AlertSeverity, NotificationStatus, CommandStatus

class UserBase(BaseModel):
    email: str
    role: UserRole
    course_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class LoginRequest(BaseModel):
    email: str
    password: str

class CourseBase(BaseModel):
    name: str
    location: str

class CourseCreate(CourseBase):
    pass

class CourseRegistrationRequest(BaseModel):
    course_name: str
    location: str
    owner_email: EmailStr
    owner_password: str
    phone: Optional[str] = None
    website: Optional[str] = None
    plan_type: PlanType = PlanType.BASIC

class CourseResponse(CourseBase):
    id: int
    owner_email: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    is_active: bool
    onboarding_completed: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class DeviceBase(BaseModel):
    name: str
    device_id: str
    course_id: int
    orientation: DeviceOrientation = DeviceOrientation.PORTRAIT

class DeviceCreate(DeviceBase):
    pass

class DeviceResponse(DeviceBase):
    id: int
    is_online: bool
    last_sync: Optional[datetime]
    orientation: DeviceOrientation
    created_at: datetime
    
    class Config:
        from_attributes = True

class SponsorCampaignBase(BaseModel):
    sponsor_name: str
    device_id: int
    start_date: datetime
    end_date: datetime
    start_time: Optional[str] = None  # Format: "HH:MM"
    end_time: Optional[str] = None    # Format: "HH:MM"
    days_of_week: Optional[List[str]] = None  # ["monday", "tuesday", ...]
    rotation_interval: int
    rotation_unit: CampaignInterval
    priority: int = 1

class SponsorCampaignCreate(SponsorCampaignBase):
    pass

class SponsorCampaignUpdate(BaseModel):
    sponsor_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    days_of_week: Optional[List[str]] = None
    rotation_interval: Optional[int] = None
    rotation_unit: Optional[CampaignInterval] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None

class SponsorCampaignResponse(SponsorCampaignBase):
    id: int
    creative_path: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    status: Optional[str] = None
    currently_active: Optional[bool] = None
    
    class Config:
        from_attributes = True

class BulkCampaignCreate(BaseModel):
    campaigns: List[Dict[str, Any]]  # List of campaign data with device_ids

class NoticeBase(BaseModel):
    title: str
    content: str
    device_id: int
    start_time: datetime

class NoticeCreate(NoticeBase):
    @validator('start_time')
    def validate_start_time(cls, v):
        from datetime import timezone
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v < datetime.now(timezone.utc).replace(hour=datetime.now(timezone.utc).hour - 1):
            raise ValueError('Start time cannot be more than 1 hour in the past')
        return v

class NoticeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    is_active: Optional[bool] = None

class NoticeResponse(NoticeBase):
    id: int
    course_id: int
    created_by: int
    end_time: datetime
    duration_minutes: Optional[int] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class PlaylistItem(BaseModel):
    type: str  # "campaign" or "notice"
    id: int
    content: str  # Path to image or notice content
    sponsor_name: Optional[str] = None
    title: Optional[str] = None
    expires_at: Optional[datetime] = None

class DevicePlaylist(BaseModel):
    device_id: str
    last_updated: datetime
    items: List[PlaylistItem]

class SubscriptionBase(BaseModel):
    plan_type: PlanType
    status: SubscriptionStatus

class SubscriptionCreate(SubscriptionBase):
    course_id: int

class SubscriptionResponse(SubscriptionBase):
    id: int
    course_id: int
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    trial_end: Optional[datetime]
    cancel_at_period_end: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DeviceAnalyticsResponse(BaseModel):
    id: int
    device_id: int
    sync_timestamp: datetime
    uptime_hours: float
    impressions_count: int
    notices_displayed: int
    campaigns_displayed: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class AnalyticsSummary(BaseModel):
    total_devices: int
    online_devices: int
    total_impressions: int
    total_uptime_hours: float
    avg_uptime_percentage: float

class CourseAnalytics(BaseModel):
    course_id: int
    course_name: str
    device_count: int
    online_devices: int
    total_impressions: int
    total_uptime_hours: float
    revenue: float

class EmailTemplateBase(BaseModel):
    name: str
    subject: str
    html_content: str
    text_content: Optional[str] = None
    variables: Optional[str] = None

class EmailTemplateCreate(EmailTemplateBase):
    pass

class EmailTemplateResponse(EmailTemplateBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class RevenueAnalytics(BaseModel):
    total_mrr: float
    total_arr: float
    total_subscribers: int
    plan_breakdown: Dict
    total_courses: int
    active_courses: int
    churn_rate: float
    growth_rate: float

class TenantUsageAnalytics(BaseModel):
    course_id: int
    course_name: str
    owner_email: str
    plan_type: str
    device_count: int
    online_devices: int
    total_impressions_30d: int
    total_uptime_hours_30d: float
    avg_uptime_percentage: float
    last_activity: Optional[datetime]
    onboarding_completed: bool
    created_at: datetime

class SystemPerformanceMetrics(BaseModel):
    device_sync_rate_24h: int
    device_uptime_percentage: float
    active_campaigns: int
    active_notices: int
    total_devices: int
    offline_devices: int
    system_health_score: float

class OnboardingProgress(BaseModel):
    course_created: bool
    devices_added: bool
    campaigns_created: bool
    onboarding_completed: bool
    steps_completed: int
    total_steps: int

class BackupResult(BaseModel):
    timestamp: datetime
    filename: Optional[str]
    size_bytes: Optional[int]
    backup_url: Optional[str]
    status: str
    error: Optional[str] = None

class NoticeTemplateBase(BaseModel):
    name: str
    title: str
    content: str
    style_id: Optional[int] = None
    default_duration_minutes: int = 60

class NoticeTemplateCreate(NoticeTemplateBase):
    recurrence_pattern: Optional[Dict[str, Any]] = None  # {"type": "daily"|"weekly", "days": [...], "time": "HH:MM"}

class NoticeTemplateUpdate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    style_id: Optional[int] = None
    default_duration_minutes: Optional[int] = None
    recurrence_pattern: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class NoticeTemplateResponse(NoticeTemplateBase):
    id: int
    course_id: int
    created_by: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class EnhancedNoticeCreate(BaseModel):
    title: str
    content: str
    device_id: int
    start_time: datetime
    duration_minutes: int = 60
    style_id: Optional[int] = None
    template_id: Optional[int] = None
    schedule: Optional[Dict[str, Any]] = None
    
    @validator('start_time')
    def validate_start_time(cls, v):
        from datetime import timezone
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v < datetime.now(timezone.utc).replace(hour=datetime.now(timezone.utc).hour - 1):
            raise ValueError('Start time cannot be more than 1 hour in the past')
        return v

# Device Monitoring & Health Schemas

class DeviceHealthMetricResponse(BaseModel):
    id: int
    device_id: int
    battery_level: Optional[float]
    battery_voltage: Optional[float]
    is_charging: bool
    connectivity_type: Optional[str]
    signal_strength: Optional[float]
    wifi_ssid: Optional[str]
    temperature: Optional[float]
    cpu_usage: Optional[float]
    memory_usage: Optional[float]
    storage_usage: Optional[float]
    display_errors: int
    last_error: Optional[str]
    uptime_seconds: Optional[int]
    timestamp: datetime
    
    class Config:
        from_attributes = True

class DeviceHealthSummary(BaseModel):
    device_id: int
    device_name: str
    is_online: bool
    last_seen: Optional[datetime]
    battery_level: Optional[float]
    is_charging: bool
    signal_strength: Optional[float]
    temperature: Optional[float]
    storage_usage: Optional[float]
    uptime_hours: Optional[float]
    error_count_24h: int
    last_error: Optional[str]
    health_score: float  # 0-100
    status_color: str  # 'green', 'yellow', 'red'
    status_reason: str  # Human-readable reason for status
    active_alerts: int = 0
    critical_alerts: int = 0

class DeviceAlertCreate(BaseModel):
    device_id: int
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    metadata: Optional[Dict[str, Any]] = None

class DeviceAlertResponse(BaseModel):
    id: int
    device_id: int
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    is_resolved: bool
    resolved_at: Optional[datetime]
    resolved_by: Optional[int]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True

class DeviceAlertResolve(BaseModel):
    resolution_note: Optional[str] = None

class AlertNotificationResponse(BaseModel):
    id: int
    alert_id: int
    notification_type: str
    recipient: str
    status: NotificationStatus
    sent_at: Optional[datetime]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class DeviceRemoteCommandCreate(BaseModel):
    command_type: str  # reboot, refresh_display, update_firmware, get_logs, clear_cache, test_display
    command_data: Optional[Dict[str, Any]] = None

class DeviceRemoteCommandResponse(BaseModel):
    id: int
    device_id: int
    command_type: str
    command_data: Optional[Dict[str, Any]]
    status: CommandStatus
    issued_by: int
    issued_at: datetime
    executed_at: Optional[datetime]
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True

class DeviceStatusUpdate(BaseModel):
    is_online: bool
    battery_level: Optional[float] = None
    battery_voltage: Optional[float] = None
    is_charging: Optional[bool] = None
    connectivity_type: Optional[str] = None
    signal_strength: Optional[float] = None
    wifi_ssid: Optional[str] = None
    temperature: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    storage_usage: Optional[float] = None
    display_errors: Optional[int] = None
    last_error: Optional[str] = None
    uptime_seconds: Optional[int] = None

class AlertStatistics(BaseModel):
    total_alerts: int
    unresolved_alerts: int
    critical_alerts: int
    alerts_by_type: Dict[str, int]
    alerts_by_severity: Dict[str, int]
    recent_alerts: List[DeviceAlertResponse]

class DeviceMonitoringDashboard(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    devices_with_alerts: int
    critical_alerts: int
    avg_battery_level: Optional[float]
    avg_signal_strength: Optional[float]
    devices_low_battery: int
    devices_high_temp: int
    device_health_summary: List[DeviceHealthSummary]


class CampaignAnalyticsResponse(BaseModel):
    id: int
    campaign_id: int
    device_id: int
    date: date
    impressions: int
    rotation_count: int
    display_duration_seconds: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CampaignPerformanceReport(BaseModel):
    campaign_id: int
    campaign_name: str
    device_id: int
    device_name: str
    total_impressions: int
    total_rotations: int
    total_display_time_hours: float
    avg_impressions_per_day: float
    date_range_start: date
    date_range_end: date

class DeviceUptimeLogResponse(BaseModel):
    id: int
    device_id: int
    date: date
    uptime_minutes: int
    downtime_minutes: int
    total_syncs: int
    error_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DeviceUptimeReport(BaseModel):
    device_id: int
    device_name: str
    course_id: int
    course_name: str
    total_uptime_minutes: int
    total_downtime_minutes: int
    uptime_percentage: float
    total_syncs: int
    total_errors: int
    avg_syncs_per_day: float
    date_range_start: date
    date_range_end: date

class RevenueConfigurationBase(BaseModel):
    course_id: int
    device_cost_per_month: float
    sponsorship_revenue_per_month: float
    course_revenue_split_percentage: float
    platform_revenue_split_percentage: float
    notes: Optional[str] = None
    effective_from: date
    effective_to: Optional[date] = None

class RevenueConfigurationCreate(RevenueConfigurationBase):
    pass

class RevenueConfigurationUpdate(BaseModel):
    device_cost_per_month: Optional[float] = None
    sponsorship_revenue_per_month: Optional[float] = None
    course_revenue_split_percentage: Optional[float] = None
    platform_revenue_split_percentage: Optional[float] = None
    notes: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None

class RevenueConfigurationResponse(RevenueConfigurationBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class RevenueAnalyticsResponse(BaseModel):
    id: int
    course_id: int
    region_id: Optional[int]
    period_start: date
    period_end: date
    total_device_costs: float
    total_sponsorship_revenue: float
    course_revenue_share: float
    platform_revenue_share: float
    net_revenue: float
    active_devices_count: int
    active_campaigns_count: int
    total_impressions: int
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class RevenueReport(BaseModel):
    course_id: int
    course_name: str
    region_id: Optional[int]
    region_name: Optional[str]
    period_start: date
    period_end: date
    total_device_costs: float
    total_sponsorship_revenue: float
    gross_revenue: float
    course_revenue_share: float
    platform_revenue_share: float
    net_revenue: float
    active_devices_count: int
    active_campaigns_count: int
    total_impressions: int
    revenue_per_device: float
    revenue_per_impression: float

class RegionalRevenueReport(BaseModel):
    region_id: int
    region_name: str
    total_courses: int
    total_devices: int
    total_device_costs: float
    total_sponsorship_revenue: float
    total_course_revenue_share: float
    total_platform_revenue_share: float
    total_net_revenue: float
    total_impressions: int
    period_start: date
    period_end: date

class SavedReportBase(BaseModel):
    report_name: str
    report_type: str  # campaign_performance, device_uptime, revenue_analytics
    filters: Optional[Dict[str, Any]] = None
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    course_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    schedule_frequency: Optional[str] = None  # daily, weekly, monthly

class SavedReportCreate(SavedReportBase):
    pass

class SavedReportUpdate(BaseModel):
    report_name: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    course_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    schedule_frequency: Optional[str] = None
    is_active: Optional[bool] = None

class SavedReportResponse(SavedReportBase):
    id: int
    user_id: int
    last_generated_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ReportExportRequest(BaseModel):
    report_type: str  # campaign_performance, device_uptime, revenue_analytics
    export_format: str  # csv, pdf
    filters: Optional[Dict[str, Any]] = None
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    course_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None

class ReportExportResponse(BaseModel):
    id: int
    user_id: int
    saved_report_id: Optional[int]
    report_type: str
    export_format: str
    file_path: Optional[str]
    file_size_bytes: Optional[int]
    download_url: Optional[str]
    filters: Optional[Dict[str, Any]]
    generated_at: datetime
    
    class Config:
        from_attributes = True

class AnalyticsDashboard(BaseModel):
    total_campaigns: int
    active_campaigns: int
    total_impressions: int
    total_devices: int
    online_devices: int
    total_uptime_percentage: float
    total_revenue: float
    platform_revenue: float
    course_revenue: float
    top_performing_campaigns: List[CampaignPerformanceReport]
    recent_reports: List[SavedReportResponse]

class QRCodeCreate(BaseModel):
    campaign_id: Optional[int] = None
    course_id: int
    destination_url: str
    title: Optional[str] = None
    description: Optional[str] = None

class QRCodeUpdate(BaseModel):
    destination_url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class QRCodeResponse(BaseModel):
    id: int
    campaign_id: Optional[int]
    course_id: int
    qr_code_key: str
    destination_url: str
    title: Optional[str]
    description: Optional[str]
    qr_code_image_url: Optional[str]
    is_active: bool
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class QRCodeScanCreate(BaseModel):
    qr_code_key: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    referrer: Optional[str] = None

class QRCodeScanResponse(BaseModel):
    id: int
    qr_code_id: int
    scan_timestamp: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    device_type: Optional[str]
    browser: Optional[str]
    operating_system: Optional[str]
    country: Optional[str]
    city: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    referrer: Optional[str]
    is_unique_visitor: bool
    session_id: Optional[str]
    
    class Config:
        from_attributes = True

class QRCodeAnalyticsResponse(BaseModel):
    id: int
    qr_code_id: int
    date: date
    total_scans: int
    unique_scans: int
    mobile_scans: int
    desktop_scans: int
    tablet_scans: int
    top_country: Optional[str]
    top_city: Optional[str]
    avg_scans_per_hour: float
    
    class Config:
        from_attributes = True

class QRCodePerformanceReport(BaseModel):
    qr_code_id: int
    qr_code_key: str
    qr_code_title: Optional[str]
    campaign_id: Optional[int]
    campaign_name: Optional[str]
    date: str
    total_scans: int
    unique_visitors: int
    mobile_scans: int
    desktop_scans: int
    tablet_scans: int
    mobile_percentage: float
    desktop_percentage: float
    tablet_percentage: float
    top_countries: List[Dict[str, Any]]
    top_cities: List[Dict[str, Any]]
    scans_by_date: List[Dict[str, Any]]
    date_range_start: date
    date_range_end: date

class ProofOfPlayEvent(BaseModel):
    """Single proof-of-play event from device"""
    event_id: str
    campaign_id: Optional[int] = None
    content_type: str  # 'campaign' or 'notice'
    displayed_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    image_hash: str
    hash_algo: Optional[str] = 'sha256'
    creative_url: Optional[str] = None
    render_result: bool
    connectivity_type: Optional[str] = None
    power_mode: Optional[str] = None
    firmware_version: Optional[str] = None

class ProofOfPlayBatch(BaseModel):
    """Batch of proof-of-play events from device"""
    events: List[ProofOfPlayEvent]

class ProofOfPlayBatchResponse(BaseModel):
    """Response from batch ingestion"""
    accepted: int
    duplicates: int
    errors: int
    details: Dict[str, Any]

class CampaignDisplayLogResponse(BaseModel):
    """Single proof-of-play log entry"""
    id: int
    event_id: str
    device_id: int
    campaign_id: Optional[int]
    content_type: str
    displayed_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    image_hash: str
    hash_algo: str
    creative_url: Optional[str]
    render_result: bool
    connectivity_type: Optional[str]
    power_mode: Optional[str]
    firmware_version: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProofOfPlayExportRequest(BaseModel):
    """Request parameters for proof-of-play export"""
    campaign_id: Optional[int] = None
    device_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    format: str = "csv"  # csv or json

class DeviceUptimeWindow(BaseModel):
    """5-minute window of device uptime data"""
    window_start: datetime
    window_end: datetime
    uptime_minutes: int
    downtime_minutes: int
    total_syncs: int = 0
    error_count: int = 0

class DeviceUptimeBatch(BaseModel):
    """Batch of uptime windows from device"""
    windows: List[DeviceUptimeWindow]

class DeviceUptimeBatchResponse(BaseModel):
    """Response from uptime batch ingestion"""
    accepted: int
    duplicates: int
    errors: int
    details: Dict[str, Any]

class DeviceHealthTrend(BaseModel):
    timestamp: datetime
    battery_level: Optional[float]
    temperature: Optional[float]
    signal_strength: Optional[float]
    storage_usage: Optional[float]
    health_score: float
    
    class Config:
        from_attributes = True

class DeviceTrendsResponse(BaseModel):
    device_id: int
    device_name: str
    period_days: int
    health_trends: List[DeviceHealthTrend]
    battery_degradation_rate: Optional[float]  # % per day
    avg_temperature: Optional[float]
    max_temperature: Optional[float]
    offline_incidents: int
    avg_uptime_hours: Optional[float]
    predictive_alerts: List[str]  # Predicted issues

class FleetTrendsResponse(BaseModel):
    period_days: int
    total_devices: int
    avg_health_score: float
    health_score_trend: List[Dict[str, Any]]  # [{date, avg_score}]
    battery_health_trend: List[Dict[str, Any]]
    offline_pattern: Dict[str, int]  # {day_of_week: count}
    devices_at_risk: List[Dict[str, Any]]  # Devices predicted to fail soon

class BulkCommandRequest(BaseModel):
    device_ids: List[int]
    command_type: str
    command_data: Optional[Dict[str, Any]] = None

class BulkCommandResponse(BaseModel):
    success: bool
    commands_issued: int
    command_ids: List[int]
    failed_devices: List[int] = []
