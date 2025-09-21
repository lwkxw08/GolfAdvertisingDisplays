from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import os
import shutil
from pathlib import Path

from .database import engine, Base, get_db
from .auth import (
    get_password_hash, verify_password, create_access_token, 
    get_current_user, require_admin, require_tenant_access
)
from .schemas import (
    Token, LoginRequest, UserResponse, UserCreate, CourseResponse, CourseCreate,
    DeviceResponse, DeviceCreate, SponsorCampaignResponse, SponsorCampaignCreate,
    NoticeResponse, NoticeCreate, PlaylistItem, DevicePlaylist
)
from .database import User, Course, Device, SponsorCampaign, Notice, UserRole

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
    
    file_extension = creative.filename.split(".")[-1]
    filename = f"campaign_{campaign_data.device_id}_{datetime.now().timestamp()}.{file_extension}"
    file_path = UPLOAD_DIR / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(creative.file, buffer)
    
    db_campaign = SponsorCampaign(
        **campaign_data.dict(),
        creative_path=str(file_path)
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
                content=f"/uploads/{os.path.basename(campaign.creative_path)}",
                sponsor_name=campaign.sponsor_name
            ))
    
    return DevicePlaylist(
        device_id=device_id,
        last_updated=now,
        items=playlist_items
    )
