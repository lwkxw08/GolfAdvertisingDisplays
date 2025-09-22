from pydantic import BaseModel, validator, EmailStr
from typing import Optional, List, Dict
from datetime import datetime
from .database import UserRole, CampaignInterval, SubscriptionStatus, PlanType

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

class DeviceCreate(DeviceBase):
    pass

class DeviceResponse(DeviceBase):
    id: int
    is_online: bool
    last_sync: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class SponsorCampaignBase(BaseModel):
    sponsor_name: str
    device_id: int
    start_date: datetime
    end_date: datetime
    rotation_interval: int
    rotation_unit: CampaignInterval
    priority: int = 1

class SponsorCampaignCreate(SponsorCampaignBase):
    pass

class SponsorCampaignResponse(SponsorCampaignBase):
    id: int
    creative_path: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class NoticeBase(BaseModel):
    title: str
    content: str
    device_id: int
    start_time: datetime

class NoticeCreate(NoticeBase):
    @validator('start_time')
    def validate_start_time(cls, v):
        if v < datetime.now():
            raise ValueError('Start time cannot be in the past')
        return v

class NoticeResponse(NoticeBase):
    id: int
    course_id: int
    created_by: int
    end_time: datetime
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
