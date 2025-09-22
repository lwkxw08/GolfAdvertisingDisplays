"""
Backup and disaster recovery service for Golf CMS
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
import os
import json
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import subprocess
import tempfile
from pathlib import Path

from ..database import get_db, engine
from .email_service import email_service

class BackupService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.database_url = os.getenv("DATABASE_URL")
        
        self.s3_client = None
        if os.getenv("AWS_ACCESS_KEY_ID"):
            self.s3_client = boto3.client('s3')
            self.backup_bucket = os.getenv("BACKUP_S3_BUCKET", "golf-cms-backups")
    
    def create_database_backup(self, db: Session) -> Dict:
        """Create a full database backup"""
        try:
            backup_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"golf_cms_backup_{backup_timestamp}.sql"
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
                temp_path = temp_file.name
            
            dump_command = [
                "pg_dump",
                self.database_url,
                "--no-owner",
                "--no-privileges",
                "--clean",
                "--if-exists",
                "-f", temp_path
            ]
            
            result = subprocess.run(dump_command, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            backup_url = None
            if self.s3_client:
                backup_url = self._upload_backup_to_s3(temp_path, backup_filename)
            
            backup_record = {
                "timestamp": datetime.utcnow(),
                "filename": backup_filename,
                "size_bytes": os.path.getsize(temp_path),
                "backup_url": backup_url,
                "status": "completed"
            }
            
            os.unlink(temp_path)
            
            return backup_record
            
        except Exception as e:
            return {
                "timestamp": datetime.utcnow(),
                "status": "failed",
                "error": str(e)
            }
    
    def _upload_backup_to_s3(self, file_path: str, filename: str) -> str:
        """Upload backup file to S3"""
        try:
            s3_key = f"database_backups/{filename}"
            self.s3_client.upload_file(file_path, self.backup_bucket, s3_key)
            return f"s3://{self.backup_bucket}/{s3_key}"
        except Exception as e:
            raise Exception(f"S3 upload failed: {str(e)}")
    
    def create_data_export(self, db: Session, course_id: Optional[int] = None) -> Dict:
        """Create a data export for a specific course or all data"""
        try:
            from ..database import Course, Device, SponsorCampaign, Notice, User
            
            export_data = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "course_id": course_id,
                "data": {}
            }
            
            if course_id:
                courses = db.query(Course).filter(Course.id == course_id).all()
            else:
                courses = db.query(Course).all()
            
            export_data["data"]["courses"] = [
                {
                    "id": course.id,
                    "name": course.name,
                    "location": course.location,
                    "owner_email": course.owner_email,
                    "created_at": course.created_at.isoformat() if course.created_at else None
                }
                for course in courses
            ]
            
            if course_id:
                devices = db.query(Device).filter(Device.course_id == course_id).all()
            else:
                devices = db.query(Device).all()
            
            export_data["data"]["devices"] = [
                {
                    "id": device.id,
                    "device_id": device.device_id,
                    "name": device.name,
                    "location": device.location,
                    "course_id": device.course_id,
                    "is_online": device.is_online,
                    "last_sync": device.last_sync.isoformat() if device.last_sync else None
                }
                for device in devices
            ]
            
            device_ids = [d.id for d in devices] if course_id else None
            if device_ids:
                campaigns = db.query(SponsorCampaign).filter(SponsorCampaign.device_id.in_(device_ids)).all()
            else:
                campaigns = db.query(SponsorCampaign).all()
            
            export_data["data"]["campaigns"] = [
                {
                    "id": campaign.id,
                    "sponsor_name": campaign.sponsor_name,
                    "device_id": campaign.device_id,
                    "creative_path": campaign.creative_path,
                    "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
                    "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
                    "is_active": campaign.is_active
                }
                for campaign in campaigns
            ]
            
            return {
                "status": "success",
                "export_data": export_data,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
    
    def schedule_automated_backups(self, db: Session):
        """Schedule automated daily backups"""
        
        backup_result = self.create_database_backup(db)
        
        if backup_result.get("status") == "completed":
            self._notify_backup_completion(db, backup_result)
        else:
            self._notify_backup_failure(db, backup_result)
        
        return backup_result
    
    def _notify_backup_completion(self, db: Session, backup_info: Dict):
        """Send notification email for successful backup"""
        try:
            admin_emails = self._get_admin_emails(db)
            
            for email in admin_emails:
                email_service.send_email(
                    db=db,
                    template_name="backup_success",
                    recipient_email=email,
                    variables={
                        "backup_filename": backup_info.get("filename"),
                        "backup_size": f"{backup_info.get('size_bytes', 0) / 1024 / 1024:.2f} MB",
                        "backup_timestamp": backup_info.get("timestamp")
                    }
                )
        except Exception as e:
            print(f"Failed to send backup notification: {e}")
    
    def _notify_backup_failure(self, db: Session, backup_info: Dict):
        """Send alert email for failed backup"""
        try:
            admin_emails = self._get_admin_emails(db)
            
            for email in admin_emails:
                email_service.send_email(
                    db=db,
                    template_name="backup_failure",
                    recipient_email=email,
                    variables={
                        "error_message": backup_info.get("error"),
                        "timestamp": backup_info.get("timestamp")
                    }
                )
        except Exception as e:
            print(f"Failed to send backup failure alert: {e}")
    
    def _get_admin_emails(self, db: Session) -> List[str]:
        """Get list of admin email addresses"""
        from ..database import User, UserRole
        
        admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
        return [user.email for user in admin_users]

backup_service = BackupService()
