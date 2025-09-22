from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from ..database import Device, DeviceAnalytics, Course, Subscription, Notice, SponsorCampaign, PlanType
from typing import Dict, List, Optional

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
            func.sum(func.case([(Device.is_online == True, 1)], 0)).label('online_devices'),
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
    
    def get_revenue_analytics(self, db: Session) -> Dict:
        """Get revenue analytics across all tenants"""
        try:
            plan_pricing = {
                PlanType.BASIC: 29.99,
                PlanType.PREMIUM: 99.99,
                PlanType.ENTERPRISE: 299.99
            }
            
            subscription_stats = db.query(
                Subscription.plan_type,
                func.count(Subscription.id).label('count')
            ).group_by(Subscription.plan_type).all()
            
            total_mrr = 0
            plan_breakdown = {}
            
            for plan_type, count in subscription_stats:
                monthly_revenue = plan_pricing.get(plan_type, 0) * count
                total_mrr += monthly_revenue
                plan_breakdown[plan_type.value] = {
                    "subscribers": count,
                    "monthly_revenue": monthly_revenue,
                    "price_per_month": plan_pricing.get(plan_type, 0)
                }
            
            total_courses = db.query(Course).count()
            active_courses = db.query(Course).filter(Course.is_active == True).count()
            
            return {
                "total_mrr": total_mrr,
                "total_arr": total_mrr * 12,
                "total_subscribers": sum(stats["subscribers"] for stats in plan_breakdown.values()),
                "plan_breakdown": plan_breakdown,
                "total_courses": total_courses,
                "active_courses": active_courses,
                "churn_rate": 0.0,  # Would calculate based on historical data
                "growth_rate": 0.0  # Would calculate based on historical data
            }
        except Exception as e:
            print(f"Error getting revenue analytics: {e}")
            return {
                "total_mrr": 0,
                "total_arr": 0,
                "total_subscribers": 0,
                "plan_breakdown": {},
                "total_courses": 0,
                "active_courses": 0,
                "churn_rate": 0.0,
                "growth_rate": 0.0
            }
    
    def get_tenant_usage_analytics(self, db: Session) -> List[Dict]:
        """Get usage analytics per tenant/course"""
        try:
            courses = db.query(Course).filter(Course.is_active == True).all()
            tenant_analytics = []
            
            for course in courses:
                devices = db.query(Device).filter(Device.course_id == course.id).all()
                online_devices = [d for d in devices if d.is_online]
                
                recent_analytics = db.query(DeviceAnalytics).join(Device).filter(
                    Device.course_id == course.id,
                    DeviceAnalytics.sync_timestamp >= datetime.utcnow() - timedelta(days=30)
                ).all()
                
                total_impressions = sum(a.impressions_count for a in recent_analytics)
                total_uptime = sum(a.uptime_hours for a in recent_analytics)
                
                subscription = db.query(Subscription).filter(
                    Subscription.course_id == course.id
                ).first()
                
                tenant_analytics.append({
                    "course_id": course.id,
                    "course_name": course.name,
                    "owner_email": course.owner_email,
                    "plan_type": subscription.plan_type.value if subscription else "none",
                    "device_count": len(devices),
                    "online_devices": len(online_devices),
                    "total_impressions_30d": total_impressions,
                    "total_uptime_hours_30d": total_uptime,
                    "avg_uptime_percentage": (total_uptime / (len(devices) * 24 * 30) * 100) if devices else 0,
                    "last_activity": max([d.last_sync for d in devices if d.last_sync], default=None),
                    "onboarding_completed": course.onboarding_completed,
                    "created_at": course.created_at
                })
            
            return tenant_analytics
        except Exception as e:
            print(f"Error getting tenant usage analytics: {e}")
            return []
    
    def get_system_performance_metrics(self, db: Session) -> Dict:
        """Get system-wide performance metrics"""
        try:
            recent_syncs = db.query(DeviceAnalytics).filter(
                DeviceAnalytics.sync_timestamp >= datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            total_devices = db.query(Device).count()
            offline_devices = db.query(Device).filter(Device.is_online == False).count()
            
            active_campaigns = db.query(SponsorCampaign).filter(
                SponsorCampaign.is_active == True
            ).count()
            
            active_notices = db.query(Notice).filter(
                Notice.is_active == True,
                Notice.end_time > datetime.utcnow()
            ).count()
            
            return {
                "device_sync_rate_24h": recent_syncs,
                "device_uptime_percentage": ((total_devices - offline_devices) / total_devices * 100) if total_devices > 0 else 0,
                "active_campaigns": active_campaigns,
                "active_notices": active_notices,
                "total_devices": total_devices,
                "offline_devices": offline_devices,
                "system_health_score": 95.0  # Would calculate based on various metrics
            }
        except Exception as e:
            print(f"Error getting system performance metrics: {e}")
            return {
                "device_sync_rate_24h": 0,
                "device_uptime_percentage": 0,
                "active_campaigns": 0,
                "active_notices": 0,
                "total_devices": 0,
                "offline_devices": 0,
                "system_health_score": 0.0
            }

analytics_service = AnalyticsService()
