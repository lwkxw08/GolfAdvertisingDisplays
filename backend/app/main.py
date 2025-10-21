from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request, Query, Form, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

ACCESS_TOKEN_EXPIRE_MINUTES = 30
import os
import shutil
from pathlib import Path
import stripe

from .database import engine, Base, get_db
from .auth import (
    get_password_hash, verify_password, create_access_token, 
    get_current_user, require_admin, require_tenant_access,
    require_super_admin, require_course_manager
)
from .schemas import (
    Token, LoginRequest, UserResponse, UserCreate, CourseResponse, CourseCreate,
    DeviceResponse, DeviceCreate, SponsorCampaignResponse, SponsorCampaignCreate,
    NoticeResponse, NoticeCreate, PlaylistItem, DevicePlaylist,
    CourseRegistrationRequest, SubscriptionResponse, DeviceAnalyticsResponse,
    AnalyticsSummary, CourseAnalytics, EmailTemplateResponse, RevenueAnalytics,
    TenantUsageAnalytics, SystemPerformanceMetrics, OnboardingProgress, BackupResult,
    NoticeTemplateResponse, NoticeTemplateCreate, EnhancedNoticeCreate
)
from .database import (
    User, Course, Device, SponsorCampaign, Notice, UserRole, Subscription,
    DeviceAnalytics, EmailTemplate, SubscriptionStatus, PlanType, Region,
    AuditLog, CustomDashboard, DeviceDiagnostic, NoticeStyle, AdvancedSchedule,
    SSOProvider, FontStyle, CampaignScheduleType, NoticeTemplate
)
from .services.s3_service import storage_service
from .services.email_service import email_service
from .services.stripe_service import stripe_service
from .services.provisioning_service import provisioning_service
from .services.analytics_service import analytics_service
from .services.alerting_service import alerting_service
from .services.backup_service import backup_service
from .services.auth_service import auth_service
from .services.dashboard_service import dashboard_service
from .services.device_management_service import device_management_service
from .services.advanced_scheduling_service import advanced_scheduling_service
from .services.eink_device_service import eink_device_service
from .services.image_processing_service import image_processing_service
from .services.audit_service import audit_service
from .services.sso_service import sso_service
from .services.region_service import region_service
from .middleware.rate_limiting import RateLimitMiddleware
from .middleware.audit_logging import AuditLoggingMiddleware
from .monitoring import router as monitoring_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Golf CMS API",
    version="1.0.0",
    description="Multi-tenant CMS for managing e-ink golf tee box displays",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.include_router(monitoring_router, prefix="", tags=["monitoring"])

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.add_middleware(RateLimitMiddleware, redis_url=os.getenv("REDIS_URL"))

from .middleware.audit_logging import AuditLoggingMiddleware
app.add_middleware(AuditLoggingMiddleware)

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

@app.delete("/admin/courses/{course_id}")
async def delete_course(
    course_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    devices_count = db.query(Device).filter(Device.course_id == course_id).count()
    if devices_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete course with {devices_count} active devices")
    
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    db.delete(course)
    db.commit()
    return {"message": "Course deleted successfully"}

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

@app.delete("/admin/devices/{device_id}")
async def delete_device(
    device_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    db.query(SponsorCampaign).filter(SponsorCampaign.device_id == device_id).delete()
    db.query(Notice).filter(Notice.device_id == device_id).delete()
    db.query(DeviceAnalytics).filter(DeviceAnalytics.device_id == device_id).delete()
    
    db.delete(device)
    db.commit()
    return {"message": "Device deleted successfully"}

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

@app.get("/courses/{course_id}/notice-templates", response_model=List[NoticeTemplateResponse])
async def list_notice_templates(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_access)
):
    from .auth import check_course_access
    check_course_access(course_id, current_user)
    return db.query(NoticeTemplate).filter(
        NoticeTemplate.course_id == course_id,
        NoticeTemplate.is_active == True
    ).all()

@app.post("/courses/{course_id}/notice-templates", response_model=NoticeTemplateResponse)
async def create_notice_template(
    course_id: int,
    template_data: NoticeTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_access)
):
    from .auth import check_course_access
    check_course_access(course_id, current_user)
    
    db_template = NoticeTemplate(
        **template_data.dict(),
        course_id=course_id,
        created_by=current_user.id
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

@app.post("/courses/{course_id}/notices/enhanced", response_model=NoticeResponse)
async def create_enhanced_notice(
    course_id: int,
    notice_data: EnhancedNoticeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_access)
):
    try:
        print(f"DEBUG: Enhanced notice request data: {notice_data}")
        from .auth import check_course_access
        check_course_access(course_id, current_user)
        
        device = db.query(Device).filter(
            Device.id == notice_data.device_id,
            Device.course_id == course_id
        ).first()
        
        if not device:
            print(f"DEBUG: Device not found - device_id: {notice_data.device_id}, course_id: {course_id}")
            raise HTTPException(status_code=404, detail="Device not found in this course")
        
        max_duration = 1440 if current_user.role in [UserRole.COURSE_MANAGER, UserRole.REGIONAL_ADMIN, UserRole.SUPER_ADMIN] else 60
        if notice_data.duration_minutes > max_duration:
            print(f"DEBUG: Duration exceeded - requested: {notice_data.duration_minutes}, max: {max_duration}")
            raise HTTPException(status_code=400, detail=f"Duration cannot exceed {max_duration} minutes")
        
        enhanced_notice_data = {
            'title': notice_data.title,
            'content': notice_data.content,
            'device_id': notice_data.device_id,
            'course_id': course_id,
            'created_by': current_user.id,
            'start_time': notice_data.start_time,
            'duration_minutes': notice_data.duration_minutes,
            'style_id': notice_data.style_id
        }
        
        if notice_data.schedule:
            enhanced_notice_data['schedule'] = notice_data.schedule
        
        print(f"DEBUG: About to call advanced_scheduling_service with data: {enhanced_notice_data}")
        result = advanced_scheduling_service.create_advanced_notice(db, enhanced_notice_data)
        print(f"DEBUG: Successfully created enhanced notice: {result.id}")
        return result
    except Exception as e:
        print(f"DEBUG: Error in create_enhanced_notice: {str(e)}")
        print(f"DEBUG: Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        raise

@app.get("/api/device/{device_id}/playlist", response_model=DevicePlaylist)
async def get_device_playlist(
    device_id: str, 
    connectivity: str = Query("wifi", description="Connectivity type: wifi, lte, ethernet"),
    db: Session = Depends(get_db)
):
    """Get device playlist optimized for E-ink displays with connectivity awareness"""
    try:
        from .services.eink_device_service import eink_device_service
        playlist = eink_device_service.get_device_playlist_optimized(
            db=db, 
            device_id=device_id, 
            connectivity_type=connectivity
        )
        return playlist
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"ERROR in get_device_playlist: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/device/{device_id}/status")
async def update_device_status(
    device_id: str,
    status_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update device status with E-ink specific metrics"""
    try:
        from .services.eink_device_service import eink_device_service
        response = eink_device_service.process_device_status_update(
            db=db,
            device_id=device_id,
            status_data=status_data
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"ERROR in update_device_status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/device/{device_id}/diagnostics")
async def get_device_diagnostics(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive E-ink device diagnostics"""
    try:
        from .services.eink_device_service import eink_device_service
        diagnostics = eink_device_service.get_device_diagnostics(db=db, device_id=device_id)
        return diagnostics
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"ERROR in get_device_diagnostics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/images/process-for-eink")
async def process_image_for_eink(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Process uploaded image for E-ink display"""
    try:
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        processed_path = image_processing_service.process_image_for_e6(temp_path)
        
        image_info = image_processing_service.get_image_info(processed_path)
        
        os.remove(temp_path)
        
        return {
            'status': 'success',
            'processed_image_path': processed_path,
            'image_info': image_info,
            'message': 'Image processed for E-ink display'
        }
        
    except Exception as e:
        print(f"ERROR in process_image_for_eink: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notices/{notice_id}/generate-eink-image")
async def generate_notice_eink_image(
    notice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate E-ink optimized image for notice"""
    try:
        notice = db.query(Notice).filter(Notice.id == notice_id).first()
        if not notice:
            raise HTTPException(status_code=404, detail="Notice not found")
        
        from .auth import check_course_access
        check_course_access(notice.course_id, current_user)
        
        notice_data = {
            'id': notice.id,
            'title': notice.title,
            'content': notice.content
        }
        
        if notice.style_id:
            style = db.query(NoticeStyle).filter(NoticeStyle.id == notice.style_id).first()
            if style:
                notice_data['style'] = {
                    'font_size': style.font_size,
                    'text_color': style.font_family.value if style.font_family else 'BLACK',
                    'background_color': 'WHITE',
                    'text_align': style.text_align or 'center'
                }
        
        image_path = image_processing_service.create_notice_image(notice_data)
        
        return {
            'status': 'success',
            'image_path': image_path,
            'notice_id': notice_id,
            'message': 'E-ink notice image generated'
        }
        
    except Exception as e:
        print(f"ERROR in generate_notice_eink_image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/eink/connectivity-options")
async def get_connectivity_options():
    """Get available connectivity options for E-ink devices"""
    return {
        'connectivity_types': [
            {
                'type': 'wifi',
                'name': 'WiFi',
                'description': 'Standard WiFi connection',
                'power_consumption': 'Medium',
                'data_speed': 'High',
                'range': 'Limited to WiFi coverage',
                'recommended_for': 'Indoor installations with reliable WiFi'
            },
            {
                'type': 'lte',
                'name': 'LTE 4G',
                'description': 'Cellular LTE connection',
                'power_consumption': 'High',
                'data_speed': 'Medium-High',
                'range': 'Wide coverage area',
                'recommended_for': 'Outdoor installations without WiFi'
            },
            {
                'type': 'ethernet',
                'name': 'Ethernet',
                'description': 'Wired ethernet connection',
                'power_consumption': 'Low',
                'data_speed': 'Very High',
                'range': 'Limited to cable length',
                'recommended_for': 'Permanent installations with network access'
            }
        ],
        'power_modes': [
            {
                'mode': 'normal',
                'refresh_interval': '15 minutes',
                'description': 'Standard operation mode'
            },
            {
                'mode': 'slow',
                'refresh_interval': '1 hour',
                'description': 'Power saving mode for low battery'
            },
            {
                'mode': 'deep_sleep',
                'refresh_interval': '6 hours',
                'description': 'Deep sleep mode for overnight/maintenance'
            },
            {
                'mode': 'emergency',
                'refresh_interval': '24 hours',
                'description': 'Emergency mode for critical battery levels'
            }
        ],
        'hardware_specs': {
            'display': 'Waveshare 13.3" E-ink Spectra 6 (E6)',
            'resolution': '1600x1200 pixels',
            'colors': '6-color (Black, White, Red, Yellow, Blue, Green)',
            'refresh_time': '19 seconds',
            'controller': 'Raspberry Pi Zero 2W',
            'power_consumption': '<0.5W during refresh, <0.1W standby',
            'operating_temperature': '-10°C to 50°C',
            'storage_temperature': '-25°C to 70°C'
        }
    }

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

@app.post("/admin/backup/create")
async def create_backup(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a database backup"""
    result = backup_service.create_database_backup(db)
    return result

@app.get("/admin/backup/export")
async def export_data(
    course_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Export data for a specific course or all data"""
    result = backup_service.create_data_export(db, course_id)
    return result

@app.post("/admin/backup/schedule")
async def schedule_backup(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Schedule automated backup"""
    result = backup_service.schedule_automated_backups(db)
    return result

@app.get("/admin/analytics/revenue")
async def get_revenue_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get revenue analytics and subscription metrics"""
    return analytics_service.get_revenue_analytics(db)

@app.get("/admin/analytics/tenants")
async def get_tenant_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get usage analytics per tenant/course"""
    return analytics_service.get_tenant_usage_analytics(db)

@app.get("/admin/analytics/performance")
async def get_performance_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get system performance metrics"""
    return analytics_service.get_system_performance_metrics(db)

@app.post("/admin/alerts/test")
async def test_alert(
    alert_type: str = "device_offline",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Test alert system"""
    test_alert = {
        "type": alert_type,
        "severity": "warning",
        "message": "This is a test alert from Golf CMS",
        "device_name": "Test Device",
        "course_name": "Test Course"
    }
    
    if alert_type == "device_offline":
        alerting_service._send_alert(db, test_alert)
    else:
        alerting_service._send_system_alert(test_alert)
    
    return {"status": "Test alert sent"}

@app.get("/admin/alerts/check")
async def check_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Check for current alerts"""
    device_alerts = alerting_service.check_device_health(db)
    return {"device_alerts": device_alerts}

@app.get("/onboarding/progress/{course_id}")
async def get_onboarding_progress(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get onboarding progress for a course"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if current_user.role != UserRole.ADMIN and current_user.course_id != course_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    devices_count = db.query(Device).filter(Device.course_id == course_id).count()
    campaigns_count = db.query(SponsorCampaign).filter(
        SponsorCampaign.device_id.in_(
            db.query(Device.id).filter(Device.course_id == course_id)
        )
    ).count()
    
    progress = {
        "course_created": True,
        "devices_added": devices_count > 0,
        "campaigns_created": campaigns_count > 0,
        "onboarding_completed": course.onboarding_completed,
        "steps_completed": sum([
            True,  # course_created
            devices_count > 0,  # devices_added
            campaigns_count > 0,  # campaigns_created
            course.onboarding_completed  # onboarding_completed
        ]),
        "total_steps": 4
    }
    
    return progress

@app.post("/onboarding/complete/{course_id}")
async def complete_onboarding(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark onboarding as completed for a course"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if current_user.role != UserRole.ADMIN and current_user.course_id != course_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    course.onboarding_completed = True
    db.commit()
    
    return {"status": "Onboarding completed"}

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

@app.post("/auth/sso/{provider_name}")
async def sso_login(
    provider_name: str,
    sso_token: str,
    db: Session = Depends(get_db)
):
    """Authenticate user via SSO provider"""
    user = auth_service.authenticate_sso(db, provider_name, sso_token)
    if not user:
        raise HTTPException(status_code=401, detail="SSO authentication failed")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/admin/dashboards")
async def list_dashboards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's custom dashboards"""
    return dashboard_service.get_user_dashboards(db, current_user.id)

@app.post("/admin/dashboards")
async def create_dashboard(
    dashboard_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a custom dashboard"""
    dashboard = dashboard_service.create_custom_dashboard(
        db, current_user.id, dashboard_data['name'], 
        dashboard_data['layout'], dashboard_data.get('filters')
    )
    return dashboard

@app.get("/admin/analytics/advanced")
async def get_advanced_analytics(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get advanced analytics for custom dashboards"""

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    return dashboard_service.get_advanced_analytics(db, current_user, (start_date, end_date))

@app.get("/admin/devices/{device_id}/diagnostics")
async def get_device_diagnostics(
    device_id: int,
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get device diagnostic data"""
    return device_management_service.get_device_diagnostics(db, device_id, hours)

@app.post("/admin/devices/{device_id}/diagnostics")
async def record_device_diagnostics(
    device_id: int,
    diagnostic_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Record device diagnostic data"""
    return device_management_service.record_diagnostic_data(db, device_id, diagnostic_data)

@app.post("/admin/devices/{device_id}/update")
async def initiate_device_update(
    device_id: int,
    update_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Initiate remote device firmware update"""
    return device_management_service.initiate_remote_update(
        db, device_id, update_data['firmware_url'], update_data['version']
    )

@app.get("/admin/devices/health")
async def get_device_health_summary(
    course_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get device health summary"""
    return device_management_service.get_device_health_summary(db, course_id)

@app.post("/admin/schedules")
async def create_advanced_schedule(
    schedule_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create an advanced schedule"""
    from datetime import datetime
    schedule_data['start_date'] = datetime.fromisoformat(schedule_data['start_date'])
    schedule_data['end_date'] = datetime.fromisoformat(schedule_data['end_date'])
    return advanced_scheduling_service.create_advanced_schedule(db, schedule_data)

@app.post("/admin/campaigns/seasonal")
async def create_seasonal_campaign(
    campaign_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a seasonal campaign"""
    from datetime import datetime
    campaign_data['start_date'] = datetime.fromisoformat(campaign_data['start_date'])
    campaign_data['end_date'] = datetime.fromisoformat(campaign_data['end_date'])
    return advanced_scheduling_service.create_seasonal_campaign(db, campaign_data)

@app.post("/admin/campaigns/ab-test")
async def create_ab_test_campaign(
    test_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create A/B test campaigns"""
    from datetime import datetime
    test_data['start_date'] = datetime.fromisoformat(test_data['start_date'])
    test_data['end_date'] = datetime.fromisoformat(test_data['end_date'])
    return advanced_scheduling_service.create_ab_test_campaign(db, test_data)

@app.get("/admin/notice-styles")
async def list_notice_styles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get available notice styles"""
    return db.query(NoticeStyle).all()

@app.post("/admin/notice-styles")
async def create_notice_style(
    style_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_course_manager)
):
    """Create a custom notice style"""
    return advanced_scheduling_service.create_notice_style(db, style_data)

@app.post("/notices/advanced")
async def create_advanced_notice(
    notice_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_access)
):
    """Create a notice with advanced scheduling and styling"""
    from datetime import datetime
    notice_data['start_time'] = datetime.fromisoformat(notice_data['start_time'])
    notice_data['created_by'] = current_user.id
    
    if current_user.role != UserRole.SUPER_ADMIN:
        device = db.query(Device).filter(Device.id == notice_data['device_id']).first()
        if not device or (current_user.course_id and device.course_id != current_user.course_id):
            raise HTTPException(status_code=403, detail="Access denied to this device")
        notice_data['course_id'] = device.course_id
    
    return advanced_scheduling_service.create_advanced_notice(db, notice_data)

@app.get("/admin/audit-logs")
async def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    logs = audit_service.get_audit_logs(
        db, current_user, limit, offset, action, resource_type, 
        user_id, start_dt, end_dt
    )
    
    result = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        log_dict = {
            "id": log.id,
            "timestamp": log.timestamp,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "user_email": user.email if user else "Unknown"
        }
        result.append(log_dict)
    
    return result

@app.get("/admin/audit-logs/summary")
async def get_audit_summary(
    days: int = 30,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    return audit_service.get_audit_summary(db, current_user, days)

@app.post("/admin/audit-logs/export")
async def export_audit_logs(
    export_request: dict,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    start_date = datetime.fromisoformat(export_request['start_date'])
    end_date = datetime.fromisoformat(export_request['end_date'])
    format_type = export_request.get('format', 'json')
    
    return audit_service.export_audit_logs(db, current_user, start_date, end_date, format_type)

@app.get("/admin/regions")
async def list_regions(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    return region_service.get_regions(db, active_only=False)

@app.post("/admin/regions")
async def create_region(
    region_data: dict,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    return region_service.create_region(db, region_data)

@app.get("/admin/regions/{region_id}")
async def get_region(
    region_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    region = region_service.get_region(db, region_id)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    return region

@app.put("/admin/regions/{region_id}")
async def update_region(
    region_id: int,
    region_data: dict,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    region = region_service.update_region(db, region_id, region_data)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    return region

@app.delete("/admin/regions/{region_id}")
async def delete_region(
    region_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    success = region_service.delete_region(db, region_id)
    if not success:
        raise HTTPException(status_code=404, detail="Region not found")
    return {"message": "Region deleted successfully"}

@app.get("/admin/regions/{region_id}/statistics")
async def get_region_statistics(
    region_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    return region_service.get_region_statistics(db, region_id)

@app.get("/admin/sso-providers")
async def list_sso_providers(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    return sso_service.get_sso_providers(db, active_only=False)

@app.post("/admin/sso-providers")
async def create_sso_provider(
    provider_data: dict,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    provider = sso_service.create_sso_provider(db, provider_data)
    return provider

@app.post("/auth/sso/login")
async def sso_login(
    provider_id: int,
    code: str,
    state: str,
    redirect_uri: str,
    db: Session = Depends(get_db)
):
    provider = sso_service.get_sso_provider(db, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found")
    
    try:
        token_data = sso_service.exchange_code_for_token(provider, code, redirect_uri)
        
        user_info = sso_service.get_user_info(provider, token_data['access_token'])
        
        user = sso_service.create_or_update_user(db, provider, user_info)
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer", "user": user}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SSO login failed: {str(e)}")

@app.get("/auth/sso/providers")
async def get_sso_providers(db: Session = Depends(get_db)):
    providers = sso_service.get_sso_providers(db)
    return [
        {
            "id": p.id,
            "name": p.name,
            "provider_type": p.provider_type,
            "authorization_url": p.authorization_url
        }
        for p in providers
    ]

@app.get("/auth/sso/{provider_id}/authorize")
async def get_sso_authorization_url(
    provider_id: int,
    redirect_uri: str,
    state: str,
    db: Session = Depends(get_db)
):
    provider = sso_service.get_sso_provider(db, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found")
    
    auth_url = sso_service.get_authorization_url(provider, redirect_uri, state)
    return {"authorization_url": auth_url}
@app.delete("/admin/courses/{course_id}")
async def delete_course(
    course_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    devices = db.query(Device).filter(Device.course_id == course_id).count()
    if devices > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete course with {devices} active devices")
    
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    db.delete(course)
    db.commit()
    return {"message": "Course deleted successfully"}

@app.delete("/admin/devices/{device_id}")
async def delete_device(
    device_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    db.query(SponsorCampaign).filter(SponsorCampaign.device_id == device_id).delete()
    db.query(Notice).filter(Notice.device_id == device_id).delete()
    db.query(DeviceAnalytics).filter(DeviceAnalytics.device_id == device_id).delete()
    
    db.delete(device)
    db.commit()
    return {"message": "Device deleted successfully"}
