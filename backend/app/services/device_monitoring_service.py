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
                    alert_metadata={"battery_level": health.battery_level}
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
                    alert_metadata={"temperature": health.temperature}
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
                    alert_metadata={"storage_usage": health.storage_usage}
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
                    alert_metadata={"error_count": health.display_errors, "last_error": health.last_error}
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
        
        active_alerts = db.query(func.count(DeviceAlert.id)).filter(
            DeviceAlert.device_id == device.id,
            DeviceAlert.is_resolved == False
        ).scalar() or 0
        
        critical_alerts = db.query(func.count(DeviceAlert.id)).filter(
            DeviceAlert.device_id == device.id,
            DeviceAlert.is_resolved == False,
            DeviceAlert.severity == AlertSeverity.CRITICAL
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
        
        status_color, status_reason = DeviceMonitoringService._compute_device_status(
            device, latest_health, critical_alerts, active_alerts
        )
        
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
            health_score=health_score,
            status_color=status_color,
            status_reason=status_reason,
            active_alerts=active_alerts,
            critical_alerts=critical_alerts
        )
    
    @staticmethod
    def _compute_device_status(device: Device, latest_health: Optional[DeviceHealthMetric], 
                               critical_alerts: int, active_alerts: int) -> tuple[str, str]:
        """
        Compute device status color and reason based on health metrics and alerts.
        
        Status Rules:
        - RED: offline >30m, battery <10%, critical alerts, or no health data >24h
        - YELLOW: online but battery 10-30%, signal 20-40%, last_seen 15-60m, or non-critical alerts
        - GREEN: online, last_seen ≤15m, battery ≥30%, signal ≥40%, no critical alerts
        """
        now = datetime.now(timezone.utc)
        
        if critical_alerts > 0:
            return 'red', f'{critical_alerts} critical alert(s)'
        
        if not device.is_online:
            if device.last_sync:
                minutes_offline = int((now - device.last_sync).total_seconds() / 60)
                if minutes_offline > 30:
                    return 'red', f'Offline for {minutes_offline}m'
            else:
                return 'red', 'Never connected'
        
        if not latest_health:
            return 'red', 'No health data available'
        
        if latest_health.timestamp:
            hours_since_health = (now - latest_health.timestamp).total_seconds() / 3600
            if hours_since_health > 24:
                return 'red', f'Health data stale ({int(hours_since_health)}h old)'
        
        if latest_health.battery_level is not None and latest_health.battery_level < 10:
            return 'red', f'Critical battery: {int(latest_health.battery_level)}%'
        
        yellow_reasons = []
        
        if device.last_sync:
            minutes_since_sync = int((now - device.last_sync).total_seconds() / 60)
            if 15 < minutes_since_sync <= 60:
                yellow_reasons.append(f'Last seen {minutes_since_sync}m ago')
        
        if latest_health.battery_level is not None and 10 <= latest_health.battery_level < 30:
            yellow_reasons.append(f'Low battery: {int(latest_health.battery_level)}%')
        
        if latest_health.signal_strength is not None and 20 <= latest_health.signal_strength < 40:
            yellow_reasons.append(f'Weak signal: {int(latest_health.signal_strength)}%')
        
        if active_alerts > critical_alerts:
            non_critical_alerts = active_alerts - critical_alerts
            yellow_reasons.append(f'{non_critical_alerts} warning(s)')
        
        if latest_health.temperature is not None and latest_health.temperature > 70:
            yellow_reasons.append(f'High temp: {int(latest_health.temperature)}°C')
        
        if latest_health.storage_usage is not None and latest_health.storage_usage > 90:
            yellow_reasons.append(f'Storage: {int(latest_health.storage_usage)}%')
        
        if yellow_reasons:
            return 'yellow', ', '.join(yellow_reasons[:2])  # Limit to 2 reasons for brevity
        
        return 'green', 'Healthy'
    
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
                    alert_metadata={"last_sync": device.last_sync.isoformat()}
                )
                db.add(alert)
        
        db.commit()
