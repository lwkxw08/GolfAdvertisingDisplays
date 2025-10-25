from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta, date, timezone
from ..database import (
    Device, DeviceAnalytics, Course, Subscription, Notice, SponsorCampaign, PlanType,
    CampaignAnalytics, DeviceUptimeLog, RevenueConfiguration, RevenueAnalytics,
    SavedReport, ReportExport, Region
)
from ..schemas import (
    CampaignPerformanceReport, DeviceUptimeReport, RevenueReport,
    RegionalRevenueReport, AnalyticsDashboard
)
from typing import Dict, List, Optional, Any
import csv
import io

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
    
    async def record_campaign_impression(
        self,
        db: Session,
        campaign_id: int,
        device_id: int,
        display_duration_seconds: int = 0
    ):
        """Record a campaign impression for analytics"""
        today = date.today()
        
        analytics = db.query(CampaignAnalytics).filter(
            CampaignAnalytics.campaign_id == campaign_id,
            CampaignAnalytics.device_id == device_id,
            CampaignAnalytics.date == today
        ).first()
        
        if analytics:
            analytics.impressions += 1
            analytics.rotation_count += 1
            analytics.display_duration_seconds += display_duration_seconds
        else:
            analytics = CampaignAnalytics(
                campaign_id=campaign_id,
                device_id=device_id,
                date=today,
                impressions=1,
                rotation_count=1,
                display_duration_seconds=display_duration_seconds
            )
            db.add(analytics)
        
        db.commit()
        return analytics
    
    async def record_device_uptime(
        self,
        db: Session,
        device_id: int,
        uptime_minutes: int = 0,
        downtime_minutes: int = 0,
        sync_count: int = 1,
        error_count: int = 0
    ):
        """Record device uptime for analytics"""
        today = date.today()
        
        uptime_log = db.query(DeviceUptimeLog).filter(
            DeviceUptimeLog.device_id == device_id,
            DeviceUptimeLog.date == today
        ).first()
        
        if uptime_log:
            uptime_log.uptime_minutes += uptime_minutes
            uptime_log.downtime_minutes += downtime_minutes
            uptime_log.total_syncs += sync_count
            uptime_log.error_count += error_count
        else:
            uptime_log = DeviceUptimeLog(
                device_id=device_id,
                date=today,
                uptime_minutes=uptime_minutes,
                downtime_minutes=downtime_minutes,
                total_syncs=sync_count,
                error_count=error_count
            )
            db.add(uptime_log)
        
        db.commit()
        return uptime_log
    
    async def get_campaign_performance_report(
        self,
        db: Session,
        campaign_id: Optional[int] = None,
        device_id: Optional[int] = None,
        course_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[CampaignPerformanceReport]:
        """Generate campaign performance report"""
        
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        query = db.query(
            CampaignAnalytics.campaign_id,
            SponsorCampaign.sponsor_name.label('campaign_name'),
            CampaignAnalytics.device_id,
            Device.name.label('device_name'),
            func.sum(CampaignAnalytics.impressions).label('total_impressions'),
            func.sum(CampaignAnalytics.rotation_count).label('total_rotations'),
            func.sum(CampaignAnalytics.display_duration_seconds).label('total_display_seconds'),
        ).join(
            SponsorCampaign, CampaignAnalytics.campaign_id == SponsorCampaign.id
        ).join(
            Device, CampaignAnalytics.device_id == Device.id
        ).filter(
            CampaignAnalytics.date >= start_date,
            CampaignAnalytics.date <= end_date
        )
        
        if campaign_id:
            query = query.filter(CampaignAnalytics.campaign_id == campaign_id)
        if device_id:
            query = query.filter(CampaignAnalytics.device_id == device_id)
        if course_id:
            query = query.filter(Device.course_id == course_id)
        
        query = query.group_by(
            CampaignAnalytics.campaign_id,
            SponsorCampaign.sponsor_name,
            CampaignAnalytics.device_id,
            Device.name
        )
        
        results = query.all()
        
        reports = []
        days_in_range = (end_date - start_date).days + 1
        
        for row in results:
            total_display_hours = row.total_display_seconds / 3600 if row.total_display_seconds else 0
            avg_impressions_per_day = row.total_impressions / days_in_range if days_in_range > 0 else 0
            
            reports.append(CampaignPerformanceReport(
                campaign_id=row.campaign_id,
                campaign_name=row.campaign_name,
                device_id=row.device_id,
                device_name=row.device_name,
                total_impressions=row.total_impressions or 0,
                total_rotations=row.total_rotations or 0,
                total_display_time_hours=round(total_display_hours, 2),
                avg_impressions_per_day=round(avg_impressions_per_day, 2),
                date_range_start=start_date,
                date_range_end=end_date
            ))
        
        return reports
    
    async def get_device_uptime_report(
        self,
        db: Session,
        device_id: Optional[int] = None,
        course_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[DeviceUptimeReport]:
        """Generate device uptime report"""
        
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        query = db.query(
            DeviceUptimeLog.device_id,
            Device.name.label('device_name'),
            Device.course_id,
            Course.name.label('course_name'),
            func.sum(DeviceUptimeLog.uptime_minutes).label('total_uptime_minutes'),
            func.sum(DeviceUptimeLog.downtime_minutes).label('total_downtime_minutes'),
            func.sum(DeviceUptimeLog.total_syncs).label('total_syncs'),
            func.sum(DeviceUptimeLog.error_count).label('total_errors'),
        ).join(
            Device, DeviceUptimeLog.device_id == Device.id
        ).join(
            Course, Device.course_id == Course.id
        ).filter(
            DeviceUptimeLog.date >= start_date,
            DeviceUptimeLog.date <= end_date
        )
        
        if device_id:
            query = query.filter(DeviceUptimeLog.device_id == device_id)
        if course_id:
            query = query.filter(Device.course_id == course_id)
        
        query = query.group_by(
            DeviceUptimeLog.device_id,
            Device.name,
            Device.course_id,
            Course.name
        )
        
        results = query.all()
        
        reports = []
        days_in_range = (end_date - start_date).days + 1
        
        for row in results:
            total_minutes = row.total_uptime_minutes + row.total_downtime_minutes
            uptime_percentage = (row.total_uptime_minutes / total_minutes * 100) if total_minutes > 0 else 0
            avg_syncs_per_day = row.total_syncs / days_in_range if days_in_range > 0 else 0
            
            reports.append(DeviceUptimeReport(
                device_id=row.device_id,
                device_name=row.device_name,
                course_id=row.course_id,
                course_name=row.course_name,
                total_uptime_minutes=row.total_uptime_minutes or 0,
                total_downtime_minutes=row.total_downtime_minutes or 0,
                uptime_percentage=round(uptime_percentage, 2),
                total_syncs=row.total_syncs or 0,
                total_errors=row.total_errors or 0,
                avg_syncs_per_day=round(avg_syncs_per_day, 2),
                date_range_start=start_date,
                date_range_end=end_date
            ))
        
        return reports
    
    async def calculate_revenue_analytics(
        self,
        db: Session,
        course_id: int,
        period_start: date,
        period_end: date
    ) -> RevenueAnalytics:
        """Calculate and store revenue analytics for a course"""
        
        config = db.query(RevenueConfiguration).filter(
            RevenueConfiguration.course_id == course_id,
            RevenueConfiguration.effective_from <= period_end,
            or_(
                RevenueConfiguration.effective_to.is_(None),
                RevenueConfiguration.effective_to >= period_start
            )
        ).order_by(RevenueConfiguration.effective_from.desc()).first()
        
        if not config:
            config = RevenueConfiguration(
                course_id=course_id,
                device_cost_per_month=0.0,
                sponsorship_revenue_per_month=0.0,
                course_revenue_split_percentage=50.0,
                platform_revenue_split_percentage=50.0,
                effective_from=period_start
            )
            db.add(config)
            db.commit()
        
        course = db.query(Course).filter(Course.id == course_id).first()
        region_id = course.region_id if course else None
        
        active_devices = db.query(func.count(Device.id)).filter(
            Device.course_id == course_id,
            Device.created_at <= period_end
        ).scalar() or 0
        
        active_campaigns = db.query(func.count(SponsorCampaign.id)).filter(
            SponsorCampaign.device_id.in_(
                db.query(Device.id).filter(Device.course_id == course_id)
            ),
            SponsorCampaign.start_date <= period_end,
            SponsorCampaign.end_date >= period_start
        ).scalar() or 0
        
        total_impressions = db.query(func.sum(CampaignAnalytics.impressions)).join(
            Device, CampaignAnalytics.device_id == Device.id
        ).filter(
            Device.course_id == course_id,
            CampaignAnalytics.date >= period_start,
            CampaignAnalytics.date <= period_end
        ).scalar() or 0
        
        months_in_period = ((period_end.year - period_start.year) * 12 + 
                           (period_end.month - period_start.month) + 1)
        
        total_device_costs = config.device_cost_per_month * active_devices * months_in_period
        total_sponsorship_revenue = config.sponsorship_revenue_per_month * active_devices * months_in_period
        
        course_revenue_share = total_sponsorship_revenue * (config.course_revenue_split_percentage / 100)
        platform_revenue_share = total_sponsorship_revenue * (config.platform_revenue_split_percentage / 100)
        net_revenue = platform_revenue_share - total_device_costs
        
        existing = db.query(RevenueAnalytics).filter(
            RevenueAnalytics.course_id == course_id,
            RevenueAnalytics.period_start == period_start,
            RevenueAnalytics.period_end == period_end
        ).first()
        
        if existing:
            existing.region_id = region_id
            existing.total_device_costs = total_device_costs
            existing.total_sponsorship_revenue = total_sponsorship_revenue
            existing.course_revenue_share = course_revenue_share
            existing.platform_revenue_share = platform_revenue_share
            existing.net_revenue = net_revenue
            existing.active_devices_count = active_devices
            existing.active_campaigns_count = active_campaigns
            existing.total_impressions = total_impressions
            analytics = existing
        else:
            analytics = RevenueAnalytics(
                course_id=course_id,
                region_id=region_id,
                period_start=period_start,
                period_end=period_end,
                total_device_costs=total_device_costs,
                total_sponsorship_revenue=total_sponsorship_revenue,
                course_revenue_share=course_revenue_share,
                platform_revenue_share=platform_revenue_share,
                net_revenue=net_revenue,
                active_devices_count=active_devices,
                active_campaigns_count=active_campaigns,
                total_impressions=total_impressions
            )
            db.add(analytics)
        
        db.commit()
        db.refresh(analytics)
        return analytics
    
    async def get_revenue_report(
        self,
        db: Session,
        course_id: Optional[int] = None,
        region_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[RevenueReport]:
        """Generate revenue report"""
        
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = date(end_date.year, end_date.month, 1)
        
        query = db.query(
            RevenueAnalytics.course_id,
            Course.name.label('course_name'),
            RevenueAnalytics.region_id,
            Region.name.label('region_name'),
            RevenueAnalytics.period_start,
            RevenueAnalytics.period_end,
            RevenueAnalytics.total_device_costs,
            RevenueAnalytics.total_sponsorship_revenue,
            RevenueAnalytics.course_revenue_share,
            RevenueAnalytics.platform_revenue_share,
            RevenueAnalytics.net_revenue,
            RevenueAnalytics.active_devices_count,
            RevenueAnalytics.active_campaigns_count,
            RevenueAnalytics.total_impressions
        ).join(
            Course, RevenueAnalytics.course_id == Course.id
        ).outerjoin(
            Region, RevenueAnalytics.region_id == Region.id
        ).filter(
            RevenueAnalytics.period_start >= start_date,
            RevenueAnalytics.period_end <= end_date
        )
        
        if course_id:
            query = query.filter(RevenueAnalytics.course_id == course_id)
        if region_id:
            query = query.filter(RevenueAnalytics.region_id == region_id)
        
        results = query.all()
        
        reports = []
        for row in results:
            gross_revenue = row.total_sponsorship_revenue
            revenue_per_device = gross_revenue / row.active_devices_count if row.active_devices_count > 0 else 0
            revenue_per_impression = gross_revenue / row.total_impressions if row.total_impressions > 0 else 0
            
            reports.append(RevenueReport(
                course_id=row.course_id,
                course_name=row.course_name,
                region_id=row.region_id,
                region_name=row.region_name,
                period_start=row.period_start,
                period_end=row.period_end,
                total_device_costs=row.total_device_costs,
                total_sponsorship_revenue=row.total_sponsorship_revenue,
                gross_revenue=gross_revenue,
                course_revenue_share=row.course_revenue_share,
                platform_revenue_share=row.platform_revenue_share,
                net_revenue=row.net_revenue,
                active_devices_count=row.active_devices_count,
                active_campaigns_count=row.active_campaigns_count,
                total_impressions=row.total_impressions,
                revenue_per_device=round(revenue_per_device, 2),
                revenue_per_impression=round(revenue_per_impression, 4)
            ))
        
        return reports
    
    async def get_regional_revenue_report(
        self,
        db: Session,
        region_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[RegionalRevenueReport]:
        """Generate regional revenue report"""
        
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = date(end_date.year, end_date.month, 1)
        
        query = db.query(
            RevenueAnalytics.region_id,
            Region.name.label('region_name'),
            func.count(func.distinct(RevenueAnalytics.course_id)).label('total_courses'),
            func.sum(RevenueAnalytics.active_devices_count).label('total_devices'),
            func.sum(RevenueAnalytics.total_device_costs).label('total_device_costs'),
            func.sum(RevenueAnalytics.total_sponsorship_revenue).label('total_sponsorship_revenue'),
            func.sum(RevenueAnalytics.course_revenue_share).label('total_course_revenue_share'),
            func.sum(RevenueAnalytics.platform_revenue_share).label('total_platform_revenue_share'),
            func.sum(RevenueAnalytics.net_revenue).label('total_net_revenue'),
            func.sum(RevenueAnalytics.total_impressions).label('total_impressions')
        ).join(
            Region, RevenueAnalytics.region_id == Region.id
        ).filter(
            RevenueAnalytics.period_start >= start_date,
            RevenueAnalytics.period_end <= end_date,
            RevenueAnalytics.region_id.isnot(None)
        )
        
        if region_id:
            query = query.filter(RevenueAnalytics.region_id == region_id)
        
        query = query.group_by(RevenueAnalytics.region_id, Region.name)
        
        results = query.all()
        
        reports = []
        for row in results:
            reports.append(RegionalRevenueReport(
                region_id=row.region_id,
                region_name=row.region_name,
                total_courses=row.total_courses or 0,
                total_devices=row.total_devices or 0,
                total_device_costs=row.total_device_costs or 0.0,
                total_sponsorship_revenue=row.total_sponsorship_revenue or 0.0,
                total_course_revenue_share=row.total_course_revenue_share or 0.0,
                total_platform_revenue_share=row.total_platform_revenue_share or 0.0,
                total_net_revenue=row.total_net_revenue or 0.0,
                total_impressions=row.total_impressions or 0,
                period_start=start_date,
                period_end=end_date
            ))
        
        return reports
    
    async def export_to_csv(
        self,
        data: List[Any],
        columns: List[str],
        filename: str
    ) -> io.StringIO:
        """Export data to CSV format"""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        
        for item in data:
            if hasattr(item, 'dict'):
                row_data = item.dict()
            else:
                row_data = item.__dict__
            
            filtered_row = {k: v for k, v in row_data.items() if k in columns}
            writer.writerow(filtered_row)
        
        output.seek(0)
        return output
    
    async def get_analytics_dashboard(
        self,
        db: Session,
        course_id: Optional[int] = None,
        region_id: Optional[int] = None
    ) -> AnalyticsDashboard:
        """Get analytics dashboard summary data"""
        
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        campaigns_query = db.query(SponsorCampaign)
        if course_id:
            campaigns_query = campaigns_query.join(Device).filter(Device.course_id == course_id)
        
        total_campaigns = campaigns_query.count()
        active_campaigns = campaigns_query.filter(
            SponsorCampaign.start_date <= end_date,
            SponsorCampaign.end_date >= start_date
        ).count()
        
        # Total impressions from campaign analytics
        impressions_query = db.query(func.sum(CampaignAnalytics.impressions)).filter(
            CampaignAnalytics.date >= start_date,
            CampaignAnalytics.date <= end_date
        )
        if course_id:
            impressions_query = impressions_query.join(Device).filter(Device.course_id == course_id)
        
        total_impressions = impressions_query.scalar() or 0
        
        devices_query = db.query(Device)
        if course_id:
            devices_query = devices_query.filter(Device.course_id == course_id)
        
        total_devices = devices_query.count()
        online_devices = devices_query.filter(Device.is_online == True).count()
        
        uptime_query = db.query(
            func.sum(DeviceUptimeLog.uptime_minutes).label('total_uptime'),
            func.sum(DeviceUptimeLog.downtime_minutes).label('total_downtime')
        ).filter(
            DeviceUptimeLog.date >= start_date,
            DeviceUptimeLog.date <= end_date
        )
        if course_id:
            uptime_query = uptime_query.join(Device).filter(Device.course_id == course_id)
        
        uptime_result = uptime_query.first()
        total_uptime = uptime_result.total_uptime or 0
        total_downtime = uptime_result.total_downtime or 0
        total_minutes = total_uptime + total_downtime
        total_uptime_percentage = (total_uptime / total_minutes * 100) if total_minutes > 0 else 0
        
        revenue_query = db.query(
            func.sum(RevenueAnalytics.total_sponsorship_revenue).label('total_revenue'),
            func.sum(RevenueAnalytics.platform_revenue_share).label('platform_revenue')
        ).filter(
            RevenueAnalytics.period_start >= start_date,
            RevenueAnalytics.period_end <= end_date
        )
        if course_id:
            revenue_query = revenue_query.filter(RevenueAnalytics.course_id == course_id)
        
        revenue_result = revenue_query.first()
        total_revenue = float(revenue_result.total_revenue or 0)
        platform_revenue = float(revenue_result.platform_revenue or 0)
        
        top_campaigns_query = db.query(
            CampaignAnalytics.campaign_id,
            SponsorCampaign.sponsor_name.label('campaign_name'),
            Device.name.label('device_name'),
            func.sum(CampaignAnalytics.impressions).label('total_impressions'),
            func.sum(CampaignAnalytics.rotation_count).label('total_rotations'),
            (func.sum(CampaignAnalytics.impressions) / 30.0).label('avg_impressions_per_day')
        ).join(
            SponsorCampaign, CampaignAnalytics.campaign_id == SponsorCampaign.id
        ).join(
            Device, CampaignAnalytics.device_id == Device.id
        ).filter(
            CampaignAnalytics.date >= start_date,
            CampaignAnalytics.date <= end_date
        )
        
        if course_id:
            top_campaigns_query = top_campaigns_query.filter(Device.course_id == course_id)
        
        top_campaigns_query = top_campaigns_query.group_by(
            CampaignAnalytics.campaign_id,
            SponsorCampaign.sponsor_name,
            Device.name
        ).order_by(func.sum(CampaignAnalytics.impressions).desc()).limit(10)
        
        top_campaigns_results = top_campaigns_query.all()
        
        top_performing_campaigns = [
            {
                "campaign_id": row.campaign_id,
                "campaign_name": row.campaign_name,
                "device_name": row.device_name,
                "total_impressions": row.total_impressions or 0,
                "total_rotations": row.total_rotations or 0,
                "avg_impressions_per_day": round(float(row.avg_impressions_per_day or 0), 2)
            }
            for row in top_campaigns_results
        ]
        
        return AnalyticsDashboard(
            total_campaigns=total_campaigns,
            active_campaigns=active_campaigns,
            total_impressions=int(total_impressions),
            total_devices=total_devices,
            online_devices=online_devices,
            total_uptime_percentage=round(total_uptime_percentage, 2),
            total_revenue=total_revenue,
            platform_revenue=platform_revenue,
            top_performing_campaigns=top_performing_campaigns
        )

analytics_service = AnalyticsService()
