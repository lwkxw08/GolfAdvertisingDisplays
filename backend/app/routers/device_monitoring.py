"""
Device Monitoring Router
Handles device health tracking, alerts, and remote commands
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from ..database import (
    get_db, Device, DeviceHealthMetric, DeviceAlert, AlertNotification,
    DeviceRemoteCommand, AlertType, AlertSeverity, NotificationStatus,
    CommandStatus, User, UserRole, CampaignDisplayLog
)
from ..auth import require_tenant_access, require_admin
from .. import schemas
from ..services.device_monitoring_service import DeviceMonitoringService

router = APIRouter(prefix="/api", tags=["device-monitoring"])


@router.get("/devices/{device_id}/health/latest", response_model=schemas.DeviceHealthMetricResponse)
async def get_device_latest_health(
    device_id: int,
    current_user: User = Depends(require_tenant_access),
    db: Session = Depends(get_db)
):
    """Get the latest health metrics for a device"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN] and device.course_id != current_user.course_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    latest_health = db.query(DeviceHealthMetric).filter(
        DeviceHealthMetric.device_id == device_id
    ).order_by(DeviceHealthMetric.timestamp.desc()).first()
    
    if not latest_health:
        raise HTTPException(status_code=404, detail="No health metrics found for this device")
    
    return latest_health

@router.get("/devices/{device_id}/health/history", response_model=List[schemas.DeviceHealthMetricResponse])
async def get_device_health_history(
    device_id: int,
    hours: int = Query(default=24, ge=1, le=168),
    current_user: User = Depends(require_tenant_access),
    db: Session = Depends(get_db)
):
    """Get health metrics history for a device"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN] and device.course_id != current_user.course_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    health_metrics = db.query(DeviceHealthMetric).filter(
        DeviceHealthMetric.device_id == device_id,
        DeviceHealthMetric.timestamp >= since
    ).order_by(DeviceHealthMetric.timestamp.desc()).all()
    
    return health_metrics

@router.post("/devices/{device_id}/health", response_model=schemas.DeviceHealthMetricResponse)
async def record_device_health(
    device_id: int,
    health_data: schemas.DeviceStatusUpdate,
    db: Session = Depends(get_db)
):
    """Record health metrics for a device (called by device client)"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device.is_online = health_data.is_online
    device.last_sync = datetime.now(timezone.utc)
    
    health_metric = DeviceHealthMetric(
        device_id=device_id,
        battery_level=health_data.battery_level,
        battery_voltage=health_data.battery_voltage,
        is_charging=health_data.is_charging or False,
        connectivity_type=health_data.connectivity_type,
        signal_strength=health_data.signal_strength,
        wifi_ssid=health_data.wifi_ssid,
        temperature=health_data.temperature,
        cpu_usage=health_data.cpu_usage,
        memory_usage=health_data.memory_usage,
        storage_usage=health_data.storage_usage,
        display_errors=health_data.display_errors or 0,
        last_error=health_data.last_error,
        uptime_seconds=health_data.uptime_seconds
    )
    
    db.add(health_metric)
    db.commit()
    db.refresh(health_metric)
    
    await DeviceMonitoringService.check_device_health_alerts(device, health_metric, db)
    
    return health_metric

@router.get("/devices/health/summary", response_model=List[schemas.DeviceHealthSummary])
async def get_all_devices_health_summary(
    current_user: User = Depends(require_tenant_access),
    db: Session = Depends(get_db)
):
    """Get health summary for all devices (filtered by user access)"""
    if current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        devices = db.query(Device).all()
    else:
        devices = db.query(Device).filter(Device.course_id == current_user.course_id).all()
    
    summaries = []
    for device in devices:
        summary = DeviceMonitoringService.get_device_health_summary(device, db)
        summaries.append(summary)
    
    return summaries

@router.get("/devices/monitoring/dashboard", response_model=schemas.DeviceMonitoringDashboard)
async def get_monitoring_dashboard(
    current_user: User = Depends(require_tenant_access),
    db: Session = Depends(get_db)
):
    """Get comprehensive monitoring dashboard data"""
    health_summaries = await get_all_devices_health_summary(current_user, db)
    
    total_devices = len(health_summaries)
    online_devices = sum(1 for s in health_summaries if s.is_online)
    offline_devices = total_devices - online_devices
    
    if current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        devices_with_alerts = db.query(func.count(func.distinct(DeviceAlert.device_id))).filter(
            DeviceAlert.is_resolved == False
        ).scalar()
        
        critical_alerts = db.query(func.count(DeviceAlert.id)).filter(
            DeviceAlert.is_resolved == False,
            DeviceAlert.severity == AlertSeverity.CRITICAL
        ).scalar()
    else:
        device_ids = [s.device_id for s in health_summaries]
        devices_with_alerts = db.query(func.count(func.distinct(DeviceAlert.device_id))).filter(
            DeviceAlert.device_id.in_(device_ids),
            DeviceAlert.is_resolved == False
        ).scalar() if device_ids else 0
        
        critical_alerts = db.query(func.count(DeviceAlert.id)).filter(
            DeviceAlert.device_id.in_(device_ids),
            DeviceAlert.is_resolved == False,
            DeviceAlert.severity == AlertSeverity.CRITICAL
        ).scalar() if device_ids else 0
    
    battery_levels = [s.battery_level for s in health_summaries if s.battery_level is not None]
    avg_battery = sum(battery_levels) / len(battery_levels) if battery_levels else None
    
    signal_strengths = [s.signal_strength for s in health_summaries if s.signal_strength is not None]
    avg_signal = sum(signal_strengths) / len(signal_strengths) if signal_strengths else None
    
    devices_low_battery = sum(1 for s in health_summaries if s.battery_level and s.battery_level < 20)
    devices_high_temp = sum(1 for s in health_summaries if s.temperature and s.temperature > 70)
    
    return schemas.DeviceMonitoringDashboard(
        total_devices=total_devices,
        online_devices=online_devices,
        offline_devices=offline_devices,
        devices_with_alerts=devices_with_alerts,
        critical_alerts=critical_alerts,
        avg_battery_level=avg_battery,
        avg_signal_strength=avg_signal,
        devices_low_battery=devices_low_battery,
        devices_high_temp=devices_high_temp,
        device_health_summary=health_summaries
    )


@router.get("/alerts", response_model=List[schemas.DeviceAlertResponse])
async def list_alerts(
    device_id: Optional[int] = None,
    is_resolved: Optional[bool] = None,
    severity: Optional[AlertSeverity] = None,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(require_tenant_access),
    db: Session = Depends(get_db)
):
    """List device alerts with optional filters"""
    query = db.query(DeviceAlert)
    
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        device_ids = db.query(Device.id).filter(Device.course_id == current_user.course_id).all()
        device_ids = [d[0] for d in device_ids]
        query = query.filter(DeviceAlert.device_id.in_(device_ids))
    
    if device_id:
        query = query.filter(DeviceAlert.device_id == device_id)
    if is_resolved is not None:
        query = query.filter(DeviceAlert.is_resolved == is_resolved)
    if severity:
        query = query.filter(DeviceAlert.severity == severity)
    
    alerts = query.order_by(DeviceAlert.created_at.desc()).limit(limit).all()
    return alerts

@router.post("/alerts/{alert_id}/resolve", response_model=schemas.DeviceAlertResponse)
async def resolve_alert(
    alert_id: int,
    resolution: schemas.DeviceAlertResolve,
    current_user: User = Depends(require_tenant_access),
    db: Session = Depends(get_db)
):
    """Resolve a device alert"""
    alert = db.query(DeviceAlert).filter(DeviceAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    device = db.query(Device).filter(Device.id == alert.device_id).first()
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN] and device.course_id != current_user.course_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    alert.is_resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolved_by = current_user.id
    
    if resolution.resolution_note:
        if not alert.alert_metadata:
            alert.alert_metadata = {}
        alert.alert_metadata["resolution_note"] = resolution.resolution_note
    
    db.commit()
    db.refresh(alert)
    
    return alert

@router.get("/alerts/statistics", response_model=schemas.AlertStatistics)
async def get_alert_statistics(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(require_tenant_access),
    db: Session = Depends(get_db)
):
    """Get alert statistics"""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    query = db.query(DeviceAlert).filter(DeviceAlert.created_at >= since)
    
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        device_ids = db.query(Device.id).filter(Device.course_id == current_user.course_id).all()
        device_ids = [d[0] for d in device_ids]
        query = query.filter(DeviceAlert.device_id.in_(device_ids))
    
    all_alerts = query.all()
    
    total_alerts = len(all_alerts)
    unresolved_alerts = sum(1 for a in all_alerts if not a.is_resolved)
    critical_alerts = sum(1 for a in all_alerts if a.severity == AlertSeverity.CRITICAL and not a.is_resolved)
    
    alerts_by_type = {}
    for alert in all_alerts:
        alert_type = alert.alert_type.value
        alerts_by_type[alert_type] = alerts_by_type.get(alert_type, 0) + 1
    
    alerts_by_severity = {}
    for alert in all_alerts:
        severity = alert.severity.value
        alerts_by_severity[severity] = alerts_by_severity.get(severity, 0) + 1
    
    recent_alerts = query.filter(DeviceAlert.is_resolved == False).order_by(
        DeviceAlert.created_at.desc()
    ).limit(10).all()
    
    return schemas.AlertStatistics(
        total_alerts=total_alerts,
        unresolved_alerts=unresolved_alerts,
        critical_alerts=critical_alerts,
        alerts_by_type=alerts_by_type,
        alerts_by_severity=alerts_by_severity,
        recent_alerts=recent_alerts
    )


@router.post("/devices/{device_id}/commands", response_model=schemas.DeviceRemoteCommandResponse)
async def issue_remote_command(
    device_id: int,
    command: schemas.DeviceRemoteCommandCreate,
    current_user: User = Depends(require_tenant_access),
    db: Session = Depends(get_db)
):
    """Issue a remote command to a device"""
    from ..services.command_service import CommandService
    
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN] and device.course_id != current_user.course_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    valid_commands = ["reboot", "refresh_display", "update_firmware", "get_logs", "clear_cache", "test_display", "get_diagnostics"]
    if command.command_type not in valid_commands:
        raise HTTPException(status_code=400, detail=f"Invalid command type. Valid commands: {', '.join(valid_commands)}")
    
    rate_limit_error = CommandService.check_rate_limit(db, device_id, command.command_type)
    if rate_limit_error:
        raise HTTPException(status_code=429, detail=rate_limit_error)
    
    CommandService.deduplicate_pending_commands(db, device_id, command.command_type)
    
    remote_command = DeviceRemoteCommand(
        device_id=device_id,
        command_type=command.command_type,
        command_data=command.command_data,
        status=CommandStatus.PENDING,
        issued_by=current_user.id
    )
    
    db.add(remote_command)
    db.commit()
    db.refresh(remote_command)
    
    from ..websocket_manager import websocket_manager
    message = {
        "type": "remote_command",
        "command_type": command.command_type,
        "command_id": remote_command.id,
        "action": "refresh_playlist" if command.command_type == "refresh_display" else command.command_type
    }
    await websocket_manager.send_to_device(device.device_id, message)
    
    return remote_command

@router.get("/devices/{device_id}/commands", response_model=List[schemas.DeviceRemoteCommandResponse])
async def list_device_commands(
    device_id: int,
    status: Optional[CommandStatus] = None,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_tenant_access),
    db: Session = Depends(get_db)
):
    """List remote commands for a device"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN] and device.course_id != current_user.course_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = db.query(DeviceRemoteCommand).filter(DeviceRemoteCommand.device_id == device_id)
    
    if status:
        query = query.filter(DeviceRemoteCommand.status == status)
    
    commands = query.order_by(DeviceRemoteCommand.issued_at.desc()).limit(limit).all()
    return commands

@router.get("/devices/{device_id}/commands/pending", response_model=List[schemas.DeviceRemoteCommandResponse])
async def get_pending_commands(
    device_id: int,
    db: Session = Depends(get_db)
):
    """Get pending commands for a device by numeric ID (called by device client)"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    commands = db.query(DeviceRemoteCommand).filter(
        DeviceRemoteCommand.device_id == device_id,
        DeviceRemoteCommand.status == CommandStatus.PENDING
    ).order_by(DeviceRemoteCommand.issued_at.asc()).all()
    
    for cmd in commands:
        cmd.status = CommandStatus.EXECUTING
    
    db.commit()
    
    return commands

@router.get("/device/{external_device_id}/commands/pending", response_model=List[schemas.DeviceRemoteCommandResponse])
async def get_pending_commands_by_external_id(
    external_device_id: str,
    db: Session = Depends(get_db)
):
    """Get pending commands for a device by external device_id (called by device client)"""
    import logging
    logger = logging.getLogger(__name__)
    
    device = db.query(Device).filter(Device.device_id == external_device_id).first()
    if not device:
        logger.warning(f"Device not found with external_device_id: {external_device_id}")
        raise HTTPException(status_code=404, detail="Device not found")
    
    commands = db.query(DeviceRemoteCommand).filter(
        DeviceRemoteCommand.device_id == device.id,
        DeviceRemoteCommand.status == CommandStatus.PENDING
    ).order_by(DeviceRemoteCommand.issued_at.asc()).all()
    
    if commands:
        logger.info(f"Device {external_device_id} polling: found {len(commands)} pending command(s), updating to EXECUTING")
        for cmd in commands:
            logger.info(f"  Command {cmd.id}: {cmd.command_type} (issued at {cmd.issued_at})")
            cmd.status = CommandStatus.EXECUTING
            cmd.picked_up_at = datetime.now(timezone.utc)
        
        db.commit()
    else:
        logger.debug(f"Device {external_device_id} polling: no pending commands")
    
    return commands

@router.put("/devices/commands/{command_id}/result", response_model=schemas.DeviceRemoteCommandResponse)
async def update_command_result(
    command_id: int,
    result: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update command execution result (called by device client)"""
    command = db.query(DeviceRemoteCommand).filter(DeviceRemoteCommand.id == command_id).first()
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    
    command.status = CommandStatus.COMPLETED if result.get("success") else CommandStatus.FAILED
    command.executed_at = datetime.now(timezone.utc)
    command.result = result
    command.error_message = result.get("error")
    
    db.commit()
    db.refresh(command)
    
    return command

@router.put("/device/commands/{command_id}/result", response_model=schemas.DeviceRemoteCommandResponse)
async def update_command_result_by_device(
    command_id: int,
    result: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update command execution result by device (called by device client using external ID)"""
    import logging
    logger = logging.getLogger(__name__)
    
    command = db.query(DeviceRemoteCommand).filter(DeviceRemoteCommand.id == command_id).first()
    if not command:
        logger.error(f"Command {command_id} not found when trying to update result")
        raise HTTPException(status_code=404, detail="Command not found")
    
    old_status = command.status
    new_status = CommandStatus.COMPLETED if result.get("success") else CommandStatus.FAILED
    
    logger.info(f"Updating command {command_id} status: {old_status} → {new_status}, success={result.get('success')}")
    
    command.status = new_status
    command.executed_at = datetime.now(timezone.utc)
    command.result = result
    command.error_message = result.get("error")
    
    db.commit()
    db.refresh(command)
    
    logger.info(f"Command {command_id} result updated successfully")
    
    return command


@router.post("/device/{device_id}/proof_of_play/batch", response_model=schemas.ProofOfPlayBatchResponse)
async def ingest_proof_of_play_batch(
    device_id: str,
    batch: schemas.ProofOfPlayBatch,
    db: Session = Depends(get_db)
):
    """Ingest batch of proof-of-play events from device"""
    import logging
    logger = logging.getLogger(__name__)
    
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        logger.error(f"Device {device_id} not found for proof-of-play ingestion")
        raise HTTPException(status_code=404, detail="Device not found")
    
    accepted = []
    duplicates = []
    errors = []
    
    logger.info(f"Ingesting {len(batch.events)} proof-of-play events from device {device_id}")
    
    for event in batch.events:
        try:
            existing = db.query(CampaignDisplayLog).filter(
                CampaignDisplayLog.event_id == event.event_id
            ).first()
            
            if existing:
                duplicates.append(event.event_id)
                logger.debug(f"Duplicate event {event.event_id} skipped")
                continue
            
            duration = None
            if event.ended_at and event.displayed_at:
                duration = int((event.ended_at - event.displayed_at).total_seconds())
            elif event.duration_seconds:
                duration = event.duration_seconds
            
            log = CampaignDisplayLog(
                event_id=event.event_id,
                device_id=device.id,
                campaign_id=event.campaign_id,
                content_type=event.content_type,
                displayed_at=event.displayed_at,
                ended_at=event.ended_at,
                duration_seconds=duration,
                image_hash=event.image_hash,
                hash_algo=event.hash_algo or 'sha256',
                creative_url=event.creative_url,
                render_result=event.render_result,
                connectivity_type=event.connectivity_type,
                power_mode=event.power_mode,
                firmware_version=event.firmware_version
            )
            db.add(log)
            accepted.append(event.event_id)
            
        except Exception as e:
            logger.error(f"Error ingesting event {event.event_id}: {e}")
            errors.append({"event_id": event.event_id, "error": str(e)})
    
    try:
        db.commit()
        logger.info(f"Proof-of-play batch ingestion complete: {len(accepted)} accepted, {len(duplicates)} duplicates, {len(errors)} errors")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to commit proof-of-play batch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to commit batch: {str(e)}")
    
    return {
        "accepted": len(accepted),
        "duplicates": len(duplicates),
        "errors": len(errors),
        "details": {
            "accepted_ids": accepted,
            "duplicate_ids": duplicates,
            "errors": errors
        }
    }
