from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import secrets

from ..database import get_db
from ..auth import get_current_user
from ..schemas import (
    UserResponse, QRCodeCreate, QRCodeUpdate, QRCodeResponse,
    QRCodePerformanceReport
)
from ..services.qr_code_service import qr_code_service

router = APIRouter(prefix="/api/qr-codes", tags=["qr-codes"])

@router.post("", response_model=QRCodeResponse)
async def create_qr_code(
    qr_code_data: QRCodeCreate,
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new QR code"""
    try:
        if current_user.role.value not in ["admin", "super_admin"] and current_user.course_id != qr_code_data.course_id:
            raise HTTPException(status_code=403, detail="Not authorized to create QR codes for this course")
        
        base_url = str(request.base_url).rstrip('/')
        
        qr_code = await qr_code_service.create_qr_code(
            db=db,
            qr_code_data=qr_code_data,
            user_id=current_user.id,
            base_url=base_url
        )
        
        return qr_code
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating QR code: {str(e)}")

@router.get("/{qr_code_id}", response_model=QRCodeResponse)
async def get_qr_code(
    qr_code_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get QR code by ID"""
    qr_code = await qr_code_service.get_qr_code(db, qr_code_id)
    
    if not qr_code:
        raise HTTPException(status_code=404, detail="QR code not found")
    
    if current_user.role.value not in ["admin", "super_admin"] and current_user.course_id != qr_code.course_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this QR code")
    
    return qr_code

@router.get("/campaign/{campaign_id}", response_model=List[QRCodeResponse])
async def get_qr_codes_by_campaign(
    campaign_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all QR codes for a campaign"""
    qr_codes = await qr_code_service.get_qr_codes_by_campaign(db, campaign_id)
    
    if current_user.role.value not in ["admin", "super_admin"]:
        qr_codes = [qr for qr in qr_codes if qr.course_id == current_user.course_id]
    
    return qr_codes

@router.get("/course/{course_id}", response_model=List[QRCodeResponse])
async def get_qr_codes_by_course(
    course_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all QR codes for a course"""
    if current_user.role.value not in ["admin", "super_admin"] and current_user.course_id != course_id:
        raise HTTPException(status_code=403, detail="Not authorized to view QR codes for this course")
    
    qr_codes = await qr_code_service.get_qr_codes_by_course(db, course_id)
    return qr_codes

@router.put("/{qr_code_id}", response_model=QRCodeResponse)
async def update_qr_code(
    qr_code_id: int,
    qr_code_data: QRCodeUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update QR code"""
    qr_code = await qr_code_service.get_qr_code(db, qr_code_id)
    
    if not qr_code:
        raise HTTPException(status_code=404, detail="QR code not found")
    
    if current_user.role.value not in ["admin", "super_admin"] and current_user.course_id != qr_code.course_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this QR code")
    
    updated_qr_code = await qr_code_service.update_qr_code(db, qr_code_id, qr_code_data)
    
    if not updated_qr_code:
        raise HTTPException(status_code=404, detail="QR code not found")
    
    return updated_qr_code

@router.delete("/{qr_code_id}")
async def delete_qr_code(
    qr_code_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete QR code"""
    qr_code = await qr_code_service.get_qr_code(db, qr_code_id)
    
    if not qr_code:
        raise HTTPException(status_code=404, detail="QR code not found")
    
    if current_user.role.value not in ["admin", "super_admin"] and current_user.course_id != qr_code.course_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this QR code")
    
    success = await qr_code_service.delete_qr_code(db, qr_code_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="QR code not found")
    
    return {"message": "QR code deleted successfully"}

@router.get("/performance/report", response_model=List[QRCodePerformanceReport])
async def get_qr_code_performance(
    qr_code_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    course_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get QR code performance report"""
    if current_user.role.value not in ["admin", "super_admin"]:
        course_id = current_user.course_id
    
    reports = await qr_code_service.get_qr_code_performance(
        db=db,
        qr_code_id=qr_code_id,
        campaign_id=campaign_id,
        course_id=course_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return reports

@router.get("/redirect/{qr_code_key}")
async def redirect_qr_code(
    qr_code_key: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Redirect QR code scan and track analytics"""
    qr_code = await qr_code_service.get_qr_code_by_key(db, qr_code_key)
    
    if not qr_code or not qr_code.is_active:
        raise HTTPException(status_code=404, detail="QR code not found or inactive")
    
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    referrer = request.headers.get("referer")
    
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = secrets.token_urlsafe(16)
    
    await qr_code_service.record_qr_scan(
        db=db,
        qr_code_key=qr_code_key,
        ip_address=ip_address,
        user_agent=user_agent,
        referrer=referrer,
        session_id=session_id
    )
    
    response = RedirectResponse(url=qr_code.destination_url, status_code=307)
    response.set_cookie(key="session_id", value=session_id, max_age=86400*30)
    
    return response
