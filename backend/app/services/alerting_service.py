"""
Alerting and notification service for Golf CMS monitoring
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import os
import json

from .email_service import email_service
from ..database import Device, Course, User, UserRole

class AlertingService:
    def __init__(self):
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.alert_thresholds = {
            "device_offline_minutes": 30,
            "cpu_usage_percent": 80,
            "memory_usage_percent": 85,
            "disk_usage_percent": 90,
            "error_rate_percent": 5
        }
    
    def check_device_health(self, db: Session) -> List[Dict]:
        """Check all devices for health issues and send alerts"""
        alerts = []
        threshold_time = datetime.utcnow() - timedelta(minutes=self.alert_thresholds["device_offline_minutes"])
        
        offline_devices = db.query(Device).filter(
            Device.last_sync < threshold_time
        ).all()
        
        for device in offline_devices:
            course = db.query(Course).filter(Course.id == device.course_id).first()
            
            alert = {
                "type": "device_offline",
                "severity": "warning",
                "device_id": device.device_id,
                "device_name": device.name,
                "course_name": course.name if course else "Unknown",
                "last_sync": device.last_sync,
                "message": f"Device {device.name} has been offline for more than {self.alert_thresholds['device_offline_minutes']} minutes"
            }
            
            alerts.append(alert)
            self._send_alert(db, alert)
        
        return alerts
    
    def check_system_health(self, system_metrics: Dict) -> List[Dict]:
        """Check system metrics and generate alerts"""
        alerts = []
        
        if system_metrics.get("cpu_percent", 0) > self.alert_thresholds["cpu_usage_percent"]:
            alerts.append({
                "type": "high_cpu_usage",
                "severity": "warning",
                "value": system_metrics["cpu_percent"],
                "threshold": self.alert_thresholds["cpu_usage_percent"],
                "message": f"High CPU usage: {system_metrics['cpu_percent']}%"
            })
        
        if system_metrics.get("memory_percent", 0) > self.alert_thresholds["memory_usage_percent"]:
            alerts.append({
                "type": "high_memory_usage",
                "severity": "warning",
                "value": system_metrics["memory_percent"],
                "threshold": self.alert_thresholds["memory_usage_percent"],
                "message": f"High memory usage: {system_metrics['memory_percent']}%"
            })
        
        if system_metrics.get("disk_percent", 0) > self.alert_thresholds["disk_usage_percent"]:
            alerts.append({
                "type": "high_disk_usage",
                "severity": "critical",
                "value": system_metrics["disk_percent"],
                "threshold": self.alert_thresholds["disk_usage_percent"],
                "message": f"High disk usage: {system_metrics['disk_percent']}%"
            })
        
        for alert in alerts:
            self._send_system_alert(alert)
        
        return alerts
    
    def _send_alert(self, db: Session, alert: Dict):
        """Send alert through configured channels"""
        self._send_email_alert(db, alert)
        
        if self.slack_webhook_url:
            self._send_slack_alert(alert)
        
        if self.discord_webhook_url:
            self._send_discord_alert(alert)
    
    def _send_system_alert(self, alert: Dict):
        """Send system alert through configured channels"""
        if self.slack_webhook_url:
            self._send_slack_alert(alert)
        
        if self.discord_webhook_url:
            self._send_discord_alert(alert)
    
    def _send_email_alert(self, db: Session, alert: Dict):
        """Send alert via email"""
        try:
            admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
            admin_emails = [user.email for user in admin_users]
            
            if alert["type"] == "device_offline":
                device = db.query(Device).filter(Device.device_id == alert["device_id"]).first()
                if device and device.course:
                    admin_emails.append(device.course.owner_email)
            
            for email in set(admin_emails):  # Remove duplicates
                email_service.send_email(
                    db=db,
                    template_name="device_offline_alert",
                    recipient_email=email,
                    variables={
                        "device_name": alert.get("device_name"),
                        "course_name": alert.get("course_name"),
                        "last_sync": alert.get("last_sync"),
                        "message": alert.get("message")
                    }
                )
        except Exception as e:
            print(f"Failed to send email alert: {e}")
    
    def _send_slack_alert(self, alert: Dict):
        """Send alert to Slack"""
        try:
            color = "warning" if alert["severity"] == "warning" else "danger"
            
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"Golf CMS Alert: {alert['type'].replace('_', ' ').title()}",
                        "text": alert["message"],
                        "fields": [
                            {
                                "title": "Severity",
                                "value": alert["severity"].title(),
                                "short": True
                            },
                            {
                                "title": "Timestamp",
                                "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                                "short": True
                            }
                        ]
                    }
                ]
            }
            
            if alert["type"] == "device_offline":
                payload["attachments"][0]["fields"].extend([
                    {
                        "title": "Device",
                        "value": alert.get("device_name"),
                        "short": True
                    },
                    {
                        "title": "Course",
                        "value": alert.get("course_name"),
                        "short": True
                    }
                ])
            
            response = requests.post(self.slack_webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            print(f"Failed to send Slack alert: {e}")
    
    def _send_discord_alert(self, alert: Dict):
        """Send alert to Discord"""
        try:
            color = 0xFFA500 if alert["severity"] == "warning" else 0xFF0000  # Orange or Red
            
            payload = {
                "embeds": [
                    {
                        "title": f"Golf CMS Alert: {alert['type'].replace('_', ' ').title()}",
                        "description": alert["message"],
                        "color": color,
                        "timestamp": datetime.utcnow().isoformat(),
                        "fields": [
                            {
                                "name": "Severity",
                                "value": alert["severity"].title(),
                                "inline": True
                            }
                        ]
                    }
                ]
            }
            
            if alert["type"] == "device_offline":
                payload["embeds"][0]["fields"].extend([
                    {
                        "name": "Device",
                        "value": alert.get("device_name"),
                        "inline": True
                    },
                    {
                        "name": "Course",
                        "value": alert.get("course_name"),
                        "inline": True
                    }
                ])
            
            response = requests.post(self.discord_webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            print(f"Failed to send Discord alert: {e}")

alerting_service = AlertingService()
