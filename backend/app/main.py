from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from typing import List, Optional
import os
import shutil
from pathlib import Path
import stripe

from .database import engine, Base, get_db
from .auth import (
    get_password_hash, verify_password, create_access_token, 
    get_current_user, require_admin, require_tenant_access
)
from .schemas import (
    Token, LoginRequest, UserResponse, UserCreate, CourseResponse, CourseCreate,
    DeviceResponse, DeviceCreate, SponsorCampaignResponse, SponsorCampaignCreate,
    NoticeResponse, NoticeCreate, PlaylistItem, DevicePlaylist,
    CourseRegistrationRequest, SubscriptionResponse, DeviceAnalyticsResponse,
    AnalyticsSummary, CourseAnalytics, EmailTemplateResponse
)
from .database import (
    User, Course, Device, SponsorCampaign, Notice, UserRole, Subscription,
    DeviceAnalytics, EmailTemplate, SubscriptionStatus, PlanType
)
from .services.s3_service import storage_service
from .services.email_service import email_service
from .services.stripe_service import stripe_service
from .services.provisioning_service import provisioning_service
from .services.analytics_service import analytics_service

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Golf CMS API", version="1.0.0")

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/auth/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@app.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role,
        course_id=user_data.course_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.post("/auth/register-course")
async def register_course(registration_data: CourseRegistrationRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == registration_data.owner_email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    result = provisioning_service.create_course_with_owner(db, registration_data.dict())
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create course"
        )
    
    return {
        "message": "Course registered successfully",
        "course_id": result["course_id"],
        "user_id": result["user_id"]
    }

@app.post("/admin/courses", response_model=CourseResponse)
async def create_course(
    course_data: CourseCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    db_course = Course(**course_data.dict())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

@app.get("/admin/courses", response_model=List[CourseResponse])
async def list_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return db.query(Course).all()

@app.get("/admin/courses/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@app.post("/admin/devices", response_model=DeviceResponse)
async def create_device(
    device_data: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    if db.query(Device).filter(Device.device_id == device_data.device_id).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device ID already exists"
        )
    
    db_device = Device(**device_data.dict())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

@app.get("/admin/devices", response_model=List[DeviceResponse])
async def list_all_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return db.query(Device).all()

@app.get("/courses/{course_id}/devices", response_model=List[DeviceResponse])
async def list_course_devices(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_access)
):
    from .auth import check_course_access
    check_course_access(course_id, current_user)
    return db.query(Device).filter(Device.course_id == course_id).all()

@app.post("/admin/campaigns", response_model=SponsorCampaignResponse)
async def create_campaign(
    campaign_data: SponsorCampaignCreate,
    creative: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    device = db.query(Device).filter(Device.id == campaign_data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    active_campaigns = db.query(SponsorCampaign).filter(
        SponsorCampaign.device_id == campaign_data.device_id,
        SponsorCampaign.is_active == True
    ).count()
    
    if active_campaigns >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 campaigns per device allowed"
        )
    
    file_content = await creative.read()
    file_url = storage_service.upload_file(
        file_content=file_content,
        filename=creative.filename,
        content_type=creative.content_type
    )
    
    if not file_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload creative file"
        )
    
    db_campaign = SponsorCampaign(
        **campaign_data.dict(),
        creative_path=file_url
    )
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    
    return db_campaign

@app.get("/admin/campaigns", response_model=List[SponsorCampaignResponse])
async def list_campaigns(
    device_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    query = db.query(SponsorCampaign)
    if device_id:
        query = query.filter(SponsorCampaign.device_id == device_id)
    return query.all()

@app.post("/courses/{course_id}/notices", response_model=NoticeResponse)
async def create_notice(
    course_id: int,
    notice_data: NoticeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_access)
):
    from .auth import check_course_access
    check_course_access(course_id, current_user)
    
    device = db.query(Device).filter(
        Device.id == notice_data.device_id,
        Device.course_id == course_id
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found in this course")
    
    end_time = notice_data.start_time + timedelta(hours=1)
    
    db_notice = Notice(
        **notice_data.dict(),
        course_id=course_id,
        created_by=current_user.id,
        end_time=end_time
    )
    db.add(db_notice)
    db.commit()
    db.refresh(db_notice)
    
    return db_notice

@app.get("/courses/{course_id}/notices", response_model=List[NoticeResponse])
async def list_notices(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_access)
):
    from .auth import check_course_access
    check_course_access(course_id, current_user)
    return db.query(Notice).filter(Notice.course_id == course_id).all()

@app.get("/api/device/{device_id}/playlist", response_model=DevicePlaylist)
async def get_device_playlist(device_id: str, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device.last_sync = datetime.now()
    device.is_online = True
    db.commit()
    
    now = datetime.now()
    playlist_items = []
    
    active_notices = db.query(Notice).filter(
        Notice.device_id == device.id,
        Notice.start_time <= now,
        Notice.end_time > now,
        Notice.is_active == True
    ).all()
    
    for notice in active_notices:
        playlist_items.append(PlaylistItem(
            type="notice",
            id=notice.id,
            content=notice.content,
            title=notice.title,
            expires_at=notice.end_time
        ))
    
    if not playlist_items:
        active_campaigns = db.query(SponsorCampaign).filter(
            SponsorCampaign.device_id == device.id,
            SponsorCampaign.start_date <= now,
            SponsorCampaign.end_date > now,
            SponsorCampaign.is_active == True
        ).order_by(SponsorCampaign.priority).all()
        
        for campaign in active_campaigns:
            playlist_items.append(PlaylistItem(
                type="campaign",
                id=campaign.id,
                content=campaign.creative_path,
                sponsor_name=campaign.sponsor_name
            ))
    
    analytics_service.record_device_sync(
        db=db,
        device_id=device.id,
        impressions=len(playlist_items),
        notices=len([item for item in playlist_items if item.type == "notice"]),
        campaigns=len([item for item in playlist_items if item.type == "campaign"])
    )
    
    return DevicePlaylist(
        device_id=device_id,
        last_updated=now,
        items=playlist_items
    )

@app.get("/admin/subscriptions", response_model=List[SubscriptionResponse])
async def list_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return db.query(Subscription).all()

@app.get("/admin/analytics/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    summary = analytics_service.get_system_summary(db)
    return AnalyticsSummary(**summary)

@app.get("/admin/analytics/courses", response_model=List[CourseAnalytics])
async def get_course_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    analytics = analytics_service.get_course_analytics(db)
    return [CourseAnalytics(**course) for course in analytics]

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    event = stripe_service.handle_webhook(payload.decode(), sig_header)
    if not event:
        raise HTTPException(status_code=400, detail="Invalid webhook")
    
    if event['type'] == 'customer.subscription.updated':
        stripe_service.update_subscription_in_db(db, event['data']['object']['id'], event['data'])
    elif event['type'] == 'customer.subscription.deleted':
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == event['data']['object']['id']
        ).first()
        if subscription:
            subscription.status = SubscriptionStatus.CANCELED
            db.commit()
    
    return {"status": "success"}

@app.get("/admin/email-templates", response_model=List[EmailTemplateResponse])
async def list_email_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return db.query(EmailTemplate).all()

@app.post("/admin/setup-templates")
async def setup_default_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    provisioning_service.create_default_email_templates(db)
    return {"message": "Default email templates created"}
