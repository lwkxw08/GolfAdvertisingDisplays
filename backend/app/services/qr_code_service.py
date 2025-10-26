from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
import qrcode
import io
import base64
import secrets
import hashlib
import requests
from user_agents import parse

from ..database import (
    QRCode, QRCodeScan, QRCodeAnalytics, SponsorCampaign, Course
)
from ..schemas import (
    QRCodeCreate, QRCodeUpdate, QRCodeResponse,
    QRCodeScanCreate, QRCodeScanResponse,
    QRCodeAnalyticsResponse, QRCodePerformanceReport
)

class QRCodeService:
    def __init__(self):
        pass
    
    def generate_qr_code_key(self) -> str:
        """Generate a unique QR code key"""
        random_bytes = secrets.token_bytes(16)
        return hashlib.sha256(random_bytes).hexdigest()[:16]
    
    def generate_qr_code_image(self, qr_code_key: str, base_url: str) -> str:
        """Generate QR code image and return as base64 data URL"""
        redirect_url = f"{base_url}/qr/{qr_code_key}"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(redirect_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_base64}"
    
    async def create_qr_code(
        self,
        db: Session,
        qr_code_data: QRCodeCreate,
        user_id: int,
        base_url: str
    ) -> QRCode:
        """Create a new QR code"""
        qr_code_key = self.generate_qr_code_key()
        
        qr_code_image = self.generate_qr_code_image(qr_code_key, base_url)
        
        qr_code = QRCode(
            campaign_id=qr_code_data.campaign_id,
            course_id=qr_code_data.course_id,
            qr_code_key=qr_code_key,
            destination_url=qr_code_data.destination_url,
            title=qr_code_data.title,
            description=qr_code_data.description,
            qr_code_image_url=qr_code_image,
            created_by=user_id
        )
        
        db.add(qr_code)
        db.commit()
        db.refresh(qr_code)
        
        return qr_code
    
    async def get_qr_code(self, db: Session, qr_code_id: int) -> Optional[QRCode]:
        """Get QR code by ID"""
        return db.query(QRCode).filter(QRCode.id == qr_code_id).first()
    
    async def get_qr_code_by_key(self, db: Session, qr_code_key: str) -> Optional[QRCode]:
        """Get QR code by key"""
        return db.query(QRCode).filter(QRCode.qr_code_key == qr_code_key).first()
    
    async def get_qr_codes_by_campaign(
        self,
        db: Session,
        campaign_id: int
    ) -> List[QRCode]:
        """Get all QR codes for a campaign"""
        return db.query(QRCode).filter(QRCode.campaign_id == campaign_id).all()
    
    async def get_qr_codes_by_course(
        self,
        db: Session,
        course_id: int
    ) -> List[QRCode]:
        """Get all QR codes for a course"""
        return db.query(QRCode).filter(QRCode.course_id == course_id).all()
    
    async def update_qr_code(
        self,
        db: Session,
        qr_code_id: int,
        qr_code_data: QRCodeUpdate
    ) -> Optional[QRCode]:
        """Update QR code"""
        qr_code = await self.get_qr_code(db, qr_code_id)
        if not qr_code:
            return None
        
        if qr_code_data.destination_url is not None:
            qr_code.destination_url = qr_code_data.destination_url
        if qr_code_data.title is not None:
            qr_code.title = qr_code_data.title
        if qr_code_data.description is not None:
            qr_code.description = qr_code_data.description
        if qr_code_data.is_active is not None:
            qr_code.is_active = qr_code_data.is_active
        
        db.commit()
        db.refresh(qr_code)
        
        return qr_code
    
    async def delete_qr_code(self, db: Session, qr_code_id: int) -> bool:
        """Delete QR code"""
        qr_code = await self.get_qr_code(db, qr_code_id)
        if not qr_code:
            return False
        
        db.delete(qr_code)
        db.commit()
        
        return True
    
    def parse_user_agent(self, user_agent_string: str) -> Dict[str, str]:
        """Parse user agent string to extract device info"""
        user_agent = parse(user_agent_string)
        
        device_type = "desktop"
        if user_agent.is_mobile:
            device_type = "mobile"
        elif user_agent.is_tablet:
            device_type = "tablet"
        
        return {
            "device_type": device_type,
            "browser": f"{user_agent.browser.family} {user_agent.browser.version_string}",
            "operating_system": f"{user_agent.os.family} {user_agent.os.version_string}"
        }
    
    def get_geolocation(self, ip_address: Optional[str]) -> Dict[str, Optional[str]]:
        """Get geolocation data from IP address using ipapi.co"""
        if not ip_address or ip_address in ["127.0.0.1", "localhost", "::1"]:
            return {"country": None, "city": None}
        
        try:
            response = requests.get(
                f"https://ipapi.co/{ip_address}/json/",
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "country": data.get("country_name"),
                    "city": data.get("city")
                }
        except Exception as e:
            print(f"Geolocation lookup failed for {ip_address}: {e}")
        
        return {"country": None, "city": None}
    
    async def record_qr_scan(
        self,
        db: Session,
        qr_code_key: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Optional[QRCodeScan]:
        """Record a QR code scan"""
        qr_code = await self.get_qr_code_by_key(db, qr_code_key)
        if not qr_code or not qr_code.is_active:
            return None
        
        device_info = {}
        if user_agent:
            device_info = self.parse_user_agent(user_agent)
        
        geo_info = self.get_geolocation(ip_address)
        
        existing_scan = db.query(QRCodeScan).filter(
            QRCodeScan.qr_code_id == qr_code.id,
            QRCodeScan.session_id == session_id
        ).first() if session_id else None
        
        is_unique = existing_scan is None
        
        scan = QRCodeScan(
            qr_code_id=qr_code.id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_info.get("device_type"),
            browser=device_info.get("browser"),
            operating_system=device_info.get("operating_system"),
            country=geo_info.get("country"),
            city=geo_info.get("city"),
            referrer=referrer,
            is_unique_visitor=is_unique,
            session_id=session_id
        )
        
        db.add(scan)
        db.commit()
        db.refresh(scan)
        
        await self.update_qr_analytics(db, qr_code.id, device_info.get("device_type"))
        
        return scan
    
    async def update_qr_analytics(
        self,
        db: Session,
        qr_code_id: int,
        device_type: Optional[str] = None
    ):
        """Update QR code analytics for today"""
        today = date.today()
        
        analytics = db.query(QRCodeAnalytics).filter(
            QRCodeAnalytics.qr_code_id == qr_code_id,
            QRCodeAnalytics.date == today
        ).first()
        
        if analytics:
            analytics.total_scans += 1
            if device_type == "mobile":
                analytics.mobile_scans += 1
            elif device_type == "desktop":
                analytics.desktop_scans += 1
            elif device_type == "tablet":
                analytics.tablet_scans += 1
        else:
            mobile_scans = 1 if device_type == "mobile" else 0
            desktop_scans = 1 if device_type == "desktop" else 0
            tablet_scans = 1 if device_type == "tablet" else 0
            
            analytics = QRCodeAnalytics(
                qr_code_id=qr_code_id,
                date=today,
                total_scans=1,
                unique_scans=1,
                mobile_scans=mobile_scans,
                desktop_scans=desktop_scans,
                tablet_scans=tablet_scans
            )
            db.add(analytics)
        
        db.commit()
    
    async def get_qr_code_performance(
        self,
        db: Session,
        qr_code_id: Optional[int] = None,
        campaign_id: Optional[int] = None,
        course_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[QRCodePerformanceReport]:
        """Get QR code performance report"""
        
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        query = db.query(
            QRCodeAnalytics.qr_code_id,
            QRCode.qr_code_key,
            QRCode.title.label('qr_code_title'),
            QRCode.campaign_id,
            SponsorCampaign.sponsor_name.label('campaign_name'),
            func.sum(QRCodeAnalytics.total_scans).label('total_scans'),
            func.sum(QRCodeAnalytics.unique_scans).label('unique_scans'),
            func.sum(QRCodeAnalytics.mobile_scans).label('mobile_scans'),
            func.sum(QRCodeAnalytics.desktop_scans).label('desktop_scans'),
            func.sum(QRCodeAnalytics.tablet_scans).label('tablet_scans'),
        ).join(
            QRCode, QRCodeAnalytics.qr_code_id == QRCode.id
        ).outerjoin(
            SponsorCampaign, QRCode.campaign_id == SponsorCampaign.id
        ).filter(
            QRCodeAnalytics.date >= start_date,
            QRCodeAnalytics.date <= end_date
        )
        
        if qr_code_id:
            query = query.filter(QRCodeAnalytics.qr_code_id == qr_code_id)
        if campaign_id:
            query = query.filter(QRCode.campaign_id == campaign_id)
        if course_id:
            query = query.filter(QRCode.course_id == course_id)
        
        query = query.group_by(
            QRCodeAnalytics.qr_code_id,
            QRCode.qr_code_key,
            QRCode.title,
            QRCode.campaign_id,
            SponsorCampaign.sponsor_name
        )
        
        results = query.all()
        
        reports = []
        for row in results:
            total = row.total_scans or 0
            mobile_scans = row.mobile_scans or 0
            desktop_scans = row.desktop_scans or 0
            tablet_scans = row.tablet_scans or 0
            mobile_pct = (mobile_scans / total * 100) if total > 0 else 0
            desktop_pct = (desktop_scans / total * 100) if total > 0 else 0
            tablet_pct = (tablet_scans / total * 100) if total > 0 else 0
            
            top_countries = self._get_top_locations(
                db, row.qr_code_id, start_date, end_date, 'country'
            )
            top_cities = self._get_top_locations(
                db, row.qr_code_id, start_date, end_date, 'city'
            )
            scans_by_date = self._get_scans_by_date(
                db, row.qr_code_id, start_date, end_date
            )
            
            reports.append(QRCodePerformanceReport(
                qr_code_id=row.qr_code_id,
                qr_code_key=row.qr_code_key,
                qr_code_title=row.qr_code_title,
                campaign_id=row.campaign_id,
                campaign_name=row.campaign_name,
                date=str(end_date),
                total_scans=total,
                unique_visitors=row.unique_scans or 0,
                mobile_scans=mobile_scans,
                desktop_scans=desktop_scans,
                tablet_scans=tablet_scans,
                mobile_percentage=round(mobile_pct, 2),
                desktop_percentage=round(desktop_pct, 2),
                tablet_percentage=round(tablet_pct, 2),
                top_countries=top_countries,
                top_cities=top_cities,
                scans_by_date=scans_by_date,
                date_range_start=start_date,
                date_range_end=end_date
            ))
        
        return reports
    
    def _get_top_locations(
        self,
        db: Session,
        qr_code_id: int,
        start_date: date,
        end_date: date,
        location_type: str
    ) -> List[Dict[str, Any]]:
        """Get top locations (countries or cities) for QR code scans"""
        location_field = QRCodeScan.country if location_type == 'country' else QRCodeScan.city
        
        results = db.query(
            location_field.label('location'),
            func.count(QRCodeScan.id).label('count')
        ).filter(
            QRCodeScan.qr_code_id == qr_code_id,
            func.date(QRCodeScan.scan_timestamp) >= start_date,
            func.date(QRCodeScan.scan_timestamp) <= end_date,
            location_field.isnot(None)
        ).group_by(
            location_field
        ).order_by(
            func.count(QRCodeScan.id).desc()
        ).limit(5).all()
        
        return [{"location": r.location, "count": r.count} for r in results]
    
    def _get_scans_by_date(
        self,
        db: Session,
        qr_code_id: int,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get scan counts by date"""
        results = db.query(
            QRCodeAnalytics.date,
            QRCodeAnalytics.total_scans
        ).filter(
            QRCodeAnalytics.qr_code_id == qr_code_id,
            QRCodeAnalytics.date >= start_date,
            QRCodeAnalytics.date <= end_date
        ).order_by(QRCodeAnalytics.date).all()
        
        return [{"date": str(r.date), "scans": r.total_scans} for r in results]

qr_code_service = QRCodeService()
