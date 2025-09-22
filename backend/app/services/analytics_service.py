from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from ..database import Device, DeviceAnalytics, Course, Subscription, Notice, SponsorCampaign
from typing import Dict, List

class AnalyticsService:
    def __init__(self):
        pass
    
    def get_system_summary(self, db: Session) -> Dict:
        """Get system-wide analytics summary"""
        total_devices = db.query(Device).count()
        online_devices = db.query(Device).filter(Device.is_online == True).count()
        
        analytics_data = db.query(
            func.sum(DeviceAnalytics.impressions_count).label('total_impressions'),
            func.sum(DeviceAnalytics.uptime_hours).label('total_uptime')
        ).first()
        
        total_impressions = analytics_data.total_impressions or 0
        total_uptime_hours = analytics_data.total_uptime or 0
        
        avg_uptime_percentage = 0
        if total_devices > 0:
            expected_hours = total_devices * 24 * 30
            avg_uptime_percentage = min((total_uptime_hours / expected_hours) * 100, 100)
        
        return {
            'total_devices': total_devices,
            'online_devices': online_devices,
            'total_impressions': int(total_impressions),
            'total_uptime_hours': float(total_uptime_hours),
            'avg_uptime_percentage': float(avg_uptime_percentage)
        }
    
    def get_course_analytics(self, db: Session) -> List[Dict]:
        """Get analytics for all courses"""
        results = db.query(
            Course.id,
            Course.name,
            func.count(Device.id).label('device_count'),
            func.sum(func.case([(Device.is_online == True, 1)], else_=0)).label('online_devices'),
            func.coalesce(func.sum(DeviceAnalytics.impressions_count), 0).label('total_impressions'),
            func.coalesce(func.sum(DeviceAnalytics.uptime_hours), 0).label('total_uptime_hours')
        ).outerjoin(Device, Course.id == Device.course_id)\
         .outerjoin(DeviceAnalytics, Device.id == DeviceAnalytics.device_id)\
         .group_by(Course.id, Course.name).all()
        
        course_analytics = []
        for result in results:
            course_analytics.append({
                'course_id': result.id,
                'course_name': result.name,
                'device_count': result.device_count or 0,
                'online_devices': result.online_devices or 0,
                'total_impressions': int(result.total_impressions),
                'total_uptime_hours': float(result.total_uptime_hours),
                'revenue': 0.0
            })
        
        return course_analytics
    
    def record_device_sync(self, db: Session, device_id: int, impressions: int, notices: int, campaigns: int):
        """Record device sync analytics"""
        analytics = DeviceAnalytics(
            device_id=device_id,
            sync_timestamp=datetime.utcnow(),
            uptime_hours=1.0,
            impressions_count=impressions,
            notices_displayed=notices,
            campaigns_displayed=campaigns
        )
        db.add(analytics)
        db.commit()

analytics_service = AnalyticsService()
