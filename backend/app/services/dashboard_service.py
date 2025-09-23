from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from ..database import Device, Course, SponsorCampaign, Notice, DeviceAnalytics, User, CustomDashboard, DeviceDiagnostic
import json

class DashboardService:
    def __init__(self):
        pass
    
    def create_custom_dashboard(self, db: Session, user_id: int, name: str, 
                              layout: Dict, filters: Optional[Dict] = None) -> CustomDashboard:
        """Create a custom dashboard for user"""
        dashboard = CustomDashboard(
            user_id=user_id,
            name=name,
            layout=layout,
            filters=filters or {}
        )
        db.add(dashboard)
        db.commit()
        db.refresh(dashboard)
        return dashboard
    
    def get_user_dashboards(self, db: Session, user_id: int) -> List[CustomDashboard]:
        """Get all dashboards for a user"""
        return db.query(CustomDashboard).filter(
            or_(
                CustomDashboard.user_id == user_id,
                CustomDashboard.is_shared == True
            )
        ).all()
    
    def get_advanced_analytics(self, db: Session, user: User, 
                             date_range: Optional[tuple] = None) -> Dict[str, Any]:
        """Get advanced analytics data for dashboard"""
        if not date_range:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
        else:
            start_date, end_date = date_range
        
        device_filter = self._get_device_filter(db, user)
        
        device_metrics = db.query(
            Device.id,
            Device.name,
            func.avg(DeviceDiagnostic.battery_level).label('avg_battery'),
            func.avg(DeviceDiagnostic.signal_strength).label('avg_signal'),
            func.count(DeviceAnalytics.id).label('sync_count')
        ).join(DeviceDiagnostic, Device.id == DeviceDiagnostic.device_id, isouter=True)\
         .join(DeviceAnalytics, Device.id == DeviceAnalytics.device_id, isouter=True)\
         .filter(device_filter)\
         .filter(DeviceDiagnostic.timestamp.between(start_date, end_date))\
         .group_by(Device.id, Device.name).all()
        
        campaign_metrics = db.query(
            SponsorCampaign.sponsor_name,
            func.count(SponsorCampaign.id).label('campaign_count'),
            func.sum(DeviceAnalytics.impressions_count).label('total_impressions')
        ).join(Device, SponsorCampaign.device_id == Device.id)\
         .join(DeviceAnalytics, Device.id == DeviceAnalytics.device_id, isouter=True)\
         .filter(device_filter)\
         .filter(SponsorCampaign.start_date.between(start_date, end_date))\
         .group_by(SponsorCampaign.sponsor_name).all()
        
        notice_metrics = db.query(
            func.count(Notice.id).label('total_notices'),
            func.avg(Notice.duration_minutes).label('avg_duration')
        ).join(Device, Notice.device_id == Device.id)\
         .filter(device_filter)\
         .filter(Notice.start_time.between(start_date, end_date)).first()
        
        regional_data = []
        if user.role in ['super_admin', 'regional_admin']:
            regional_data = db.query(
                Course.name.label('course_name'),
                func.count(Device.id).label('device_count'),
                func.avg(DeviceAnalytics.uptime_hours).label('avg_uptime')
            ).join(Device, Course.id == Device.course_id)\
             .join(DeviceAnalytics, Device.id == DeviceAnalytics.device_id, isouter=True)\
             .group_by(Course.id, Course.name).all()
        
        return {
            'device_metrics': [
                {
                    'device_id': d.id,
                    'device_name': d.name,
                    'avg_battery': float(d.avg_battery or 0),
                    'avg_signal': float(d.avg_signal or 0),
                    'sync_count': d.sync_count or 0
                } for d in device_metrics
            ],
            'campaign_metrics': [
                {
                    'sponsor': c.sponsor_name,
                    'campaigns': c.campaign_count,
                    'impressions': c.total_impressions or 0
                } for c in campaign_metrics
            ],
            'notice_metrics': {
                'total_notices': notice_metrics.total_notices or 0,
                'avg_duration': float(notice_metrics.avg_duration or 0)
            },
            'regional_data': [
                {
                    'course': r.course_name,
                    'devices': r.device_count,
                    'uptime': float(r.avg_uptime or 0)
                } for r in regional_data
            ]
        }
    
    def _get_device_filter(self, db: Session, user: User):
        """Get device filter based on user role and permissions"""
        if user.role == 'super_admin':
            return True  # No filter, access all devices
        elif user.role == 'regional_admin' and user.region_id:
            return Device.course_id.in_(
                db.query(Course.id).filter(Course.region_id == user.region_id)
            )
        elif user.role in ['course_manager', 'client_tenant'] and user.course_id:
            return Device.course_id == user.course_id
        else:
            return False  # No access

dashboard_service = DashboardService()
