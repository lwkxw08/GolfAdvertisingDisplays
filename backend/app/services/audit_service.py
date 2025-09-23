from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from datetime import datetime, timedelta
from ..database import AuditLog, User
import json

class AuditService:
    def __init__(self):
        pass
    
    def get_audit_logs(self, db: Session, user: User, 
                      limit: int = 100, offset: int = 0,
                      action_filter: Optional[str] = None,
                      resource_filter: Optional[str] = None,
                      user_filter: Optional[int] = None,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> List[AuditLog]:
        """Get audit logs with filtering and pagination"""
        
        query = db.query(AuditLog).join(User, AuditLog.user_id == User.id)
        
        if user.role not in ['super_admin']:
            if user.role == 'regional_admin' and user.region_id:
                query = query.filter(AuditLog.user_id == user.id)
            else:
                query = query.filter(AuditLog.user_id == user.id)
        
        if action_filter:
            query = query.filter(AuditLog.action == action_filter)
        
        if resource_filter:
            query = query.filter(AuditLog.resource_type == resource_filter)
        
        if user_filter:
            query = query.filter(AuditLog.user_id == user_filter)
        
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        
        query = query.order_by(desc(AuditLog.timestamp))
        query = query.offset(offset).limit(limit)
        
        return query.all()
    
    def get_audit_summary(self, db: Session, user: User, days: int = 30) -> Dict[str, Any]:
        """Get audit log summary statistics"""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.query(AuditLog)
        
        if user.role not in ['super_admin']:
            if user.role == 'regional_admin' and user.region_id:
                query = query.filter(AuditLog.user_id == user.id)
            else:
                query = query.filter(AuditLog.user_id == user.id)
        
        query = query.filter(AuditLog.timestamp >= start_date)
        
        action_counts = db.query(
            AuditLog.action,
            func.count(AuditLog.id).label('count')
        ).filter(AuditLog.timestamp >= start_date).group_by(AuditLog.action).all()
        
        resource_counts = db.query(
            AuditLog.resource_type,
            func.count(AuditLog.id).label('count')
        ).filter(AuditLog.timestamp >= start_date).group_by(AuditLog.resource_type).all()
        
        daily_activity = db.query(
            func.date(AuditLog.timestamp).label('date'),
            func.count(AuditLog.id).label('count')
        ).filter(AuditLog.timestamp >= start_date)\
         .group_by(func.date(AuditLog.timestamp))\
         .order_by(func.date(AuditLog.timestamp)).all()
        
        top_users = db.query(
            User.email,
            func.count(AuditLog.id).label('count')
        ).join(AuditLog, User.id == AuditLog.user_id)\
         .filter(AuditLog.timestamp >= start_date)\
         .group_by(User.email)\
         .order_by(func.count(AuditLog.id).desc())\
         .limit(10).all()
        
        return {
            'total_logs': query.count(),
            'action_counts': {action: count for action, count in action_counts},
            'resource_counts': {resource: count for resource, count in resource_counts},
            'daily_activity': [
                {'date': str(date), 'count': count} 
                for date, count in daily_activity
            ],
            'top_users': [
                {'email': email, 'count': count} 
                for email, count in top_users
            ]
        }
    
    def export_audit_logs(self, db: Session, user: User, 
                         start_date: datetime, end_date: datetime,
                         format: str = 'json') -> Dict[str, Any]:
        """Export audit logs for compliance reporting"""
        
        logs = self.get_audit_logs(
            db, user, 
            limit=10000,  # Large limit for export
            start_date=start_date,
            end_date=end_date
        )
        
        export_data = []
        for log in logs:
            export_data.append({
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'user_id': log.user_id,
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'details': log.details,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent
            })
        
        return {
            'export_date': datetime.utcnow().isoformat(),
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'total_records': len(export_data),
            'logs': export_data
        }

audit_service = AuditService()
