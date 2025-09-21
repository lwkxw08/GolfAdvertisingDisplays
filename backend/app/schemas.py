from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from .database import UserRole, CampaignInterval

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

class CourseResponse(CourseBase):
    id: int
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
