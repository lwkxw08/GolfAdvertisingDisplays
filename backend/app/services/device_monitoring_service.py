"""
Device Monitoring Service
Handles device health tracking, alerts, and remote commands
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from ..database import (
    Device, DeviceHealthMetric, DeviceAlert, AlertNotification,
    DeviceRemoteCommand, AlertType, AlertSeverity, NotificationStatus,
    CommandStatus, UserRole
)
from .. import schemas

class DeviceMonitoringService:
    """Service for device monitoring and health tracking"""
    
    @staticmethod
    async def check_device_health_alerts(device: Device, health: DeviceHealthMetric, db: Session):
        """Check device health and create alerts if needed"""
        alerts_to_create = []
        
        if health.battery_level is not None and health.battery_level < 20 and not health.is_charging:
            existing_alert = db.query(DeviceAlert).filter(
                DeviceAlert.device_id == device.id,
                DeviceAlert.alert_type == AlertType.LOW_BATTERY,
                DeviceAlert.is_resolved == False
            ).first()
            
            if not existing_alert:
                alerts_to_create.append(DeviceAlert(
                    device_id=device.id,
                    alert_type=AlertType.LOW_BATTERY,
                    severity=AlertSeverity.WARNING if health.battery_level > 10 else AlertSeverity.CRITICAL,
                    title=f"Low Battery: {device.name}",
                    message=f"Device battery level is at {health.battery_level}%. Please charge the device.",
                    metadata={"battery_level": health.battery_level}
                ))
        
        if health.temperature is not None and health.temperature > 70:
            existing_alert = db.query(DeviceAlert).filter(
                DeviceAlert.device_id == device.id,
                DeviceAlert.alert_type == AlertType.HIGH_TEMPERATURE,
                DeviceAlert.is_resolved == False
            ).first()
            
            if not existing_alert:
                alerts_to_create.append(DeviceAlert(
                    device_id=device.id,
                    alert_type=AlertType.HIGH_TEMPERATURE,
                    severity=AlertSeverity.WARNING if health.temperature < 80 else AlertSeverity.ERROR,
                    title=f"High Temperature: {device.name}",
                    message=f"Device temperature is {health.temperature}°C. Check device ventilation.",
                    metadata={"temperature": health.temperature}
                ))
        
        if health.storage_usage is not None and health.storage_usage > 90:
            existing_alert = db.query(DeviceAlert).filter(
                DeviceAlert.device_id == device.id,
                DeviceAlert.alert_type == AlertType.STORAGE_FULL,
                DeviceAlert.is_resolved == False
            ).first()
            
            if not existing_alert:
                alerts_to_create.append(DeviceAlert(
                    device_id=device.id,
                    alert_type=AlertType.STORAGE_FULL,
                    severity=AlertSeverity.WARNING,
                    title=f"Storage Almost Full: {device.name}",
                    message=f"Device storage is {health.storage_usage}% full. Consider clearing cache.",
                    metadata={"storage_usage": health.storage_usage}
                ))
        
        if health.display_errors > 0:
            existing_alert = db.query(DeviceAlert).filter(
                DeviceAlert.device_id == device.id,
                DeviceAlert.alert_type == AlertType.DISPLAY_ERROR,
                DeviceAlert.is_resolved == False
            ).first()
            
            if not existing_alert:
                alerts_to_create.append(DeviceAlert(
                    device_id=device.id,
                    alert_type=AlertType.DISPLAY_ERROR,
                    severity=AlertSeverity.ERROR,
                    title=f"Display Errors: {device.name}",
                    message=f"Device has {health.display_errors} display errors. Last error: {health.last_error or 'Unknown'}",
                    metadata={"error_count": health.display_errors, "last_error": health.last_error}
                ))
        
        for alert in alerts_to_create:
            db.add(alert)
        
        if alerts_to_create:
            db.commit()
    
    @staticmethod
    def get_device_health_summary(device: Device, db: Session) -> schemas.DeviceHealthSummary:
        """Get health summary for a single device"""
        latest_health = db.query(DeviceHealthMetric).filter(
            DeviceHealthMetric.device_id == device.id
        ).order_by(DeviceHealthMetric.timestamp.desc()).first()
        
        since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        error_count = db.query(func.sum(DeviceHealthMetric.display_errors)).filter(
            DeviceHealthMetric.device_id == device.id,
            DeviceHealthMetric.timestamp >= since_24h
        ).scalar() or 0
        
        health_score = 100.0
        if latest_health:
            if latest_health.battery_level and latest_health.battery_level < 20:
                health_score -= 20
            if latest_health.temperature and latest_health.temperature > 70:
                health_score -= 15
            if latest_health.storage_usage and latest_health.storage_usage > 90:
                health_score -= 10
            if error_count > 0:
                health_score -= min(error_count * 5, 30)
            if not device.is_online:
                health_score -= 25
        else:
            health_score = 50.0  # No data available
        
        health_score = max(0, health_score)
        
        return schemas.DeviceHealthSummary(
            device_id=device.id,
            device_name=device.name,
            is_online=device.is_online,
            last_seen=device.last_sync,
            battery_level=latest_health.battery_level if latest_health else None,
            is_charging=latest_health.is_charging if latest_health else False,
            signal_strength=latest_health.signal_strength if latest_health else None,
            temperature=latest_health.temperature if latest_health else None,
            storage_usage=latest_health.storage_usage if latest_health else None,
            uptime_hours=latest_health.uptime_seconds / 3600 if latest_health and latest_health.uptime_seconds else None,
            error_count_24h=int(error_count),
            last_error=latest_health.last_error if latest_health else None,
            health_score=health_score
        )
    
    @staticmethod
    async def check_offline_devices(db: Session):
        """Background task to check for devices that have gone offline"""
        offline_threshold = datetime.now(timezone.utc) - timedelta(minutes=30)
        
        devices = db.query(Device).filter(
            Device.is_online == True,
            Device.last_sync < offline_threshold
        ).all()
        
        for device in devices:
            device.is_online = False
            
            existing_alert = db.query(DeviceAlert).filter(
                DeviceAlert.device_id == device.id,
                DeviceAlert.alert_type == AlertType.DEVICE_OFFLINE,
                DeviceAlert.is_resolved == False
            ).first()
            
            if not existing_alert:
                alert = DeviceAlert(
                    device_id=device.id,
                    alert_type=AlertType.DEVICE_OFFLINE,
                    severity=AlertSeverity.ERROR,
                    title=f"Device Offline: {device.name}",
                    message=f"Device has not synced since {device.last_sync.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    metadata={"last_sync": device.last_sync.isoformat()}
                )
                db.add(alert)
        
        db.commit()
