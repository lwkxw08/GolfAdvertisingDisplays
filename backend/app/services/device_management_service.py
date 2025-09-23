from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..database import Device, Course, DeviceDiagnostic
import json
import requests

class DeviceManagementService:
    def __init__(self):
        pass
    
    def get_device_diagnostics(self, db: Session, device_id: int, 
                             hours: int = 24) -> List[DeviceDiagnostic]:
        """Get recent diagnostic data for a device"""
        since = datetime.utcnow() - timedelta(hours=hours)
        return db.query(DeviceDiagnostic).filter(
            DeviceDiagnostic.device_id == device_id,
            DeviceDiagnostic.timestamp >= since
        ).order_by(DeviceDiagnostic.timestamp.desc()).all()
    
    def record_diagnostic_data(self, db: Session, device_id: int, 
                             diagnostic_data: Dict[str, Any]) -> DeviceDiagnostic:
        """Record diagnostic data from device"""
        diagnostic = DeviceDiagnostic(
            device_id=device_id,
            battery_level=diagnostic_data.get('battery_level'),
            signal_strength=diagnostic_data.get('signal_strength'),
            temperature=diagnostic_data.get('temperature'),
            memory_usage=diagnostic_data.get('memory_usage'),
            storage_usage=diagnostic_data.get('storage_usage'),
            firmware_version=diagnostic_data.get('firmware_version'),
            last_error=diagnostic_data.get('last_error'),
            diagnostic_data=diagnostic_data
        )
        db.add(diagnostic)
        db.commit()
        db.refresh(diagnostic)
        return diagnostic
    
    def initiate_remote_update(self, db: Session, device_id: int, 
                             firmware_url: str, version: str) -> Dict[str, Any]:
        """Initiate remote firmware update for device"""
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {'success': False, 'error': 'Device not found'}
        
        if not device.remote_update_enabled:
            return {'success': False, 'error': 'Remote updates disabled for this device'}
        
        update_command = {
            'command': 'firmware_update',
            'firmware_url': firmware_url,
            'version': version,
            'device_id': device.device_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            device.firmware_version = version
            db.commit()
            
            return {
                'success': True,
                'message': f'Update initiated for device {device.name}',
                'update_id': f'update_{device_id}_{int(datetime.utcnow().timestamp())}'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_device_health_summary(self, db: Session, course_id: Optional[int] = None) -> Dict[str, Any]:
        """Get health summary for devices"""
        query = db.query(Device)
        if course_id:
            query = query.filter(Device.course_id == course_id)
        
        devices = query.all()
        
        health_data = []
        for device in devices:
            latest_diagnostic = db.query(DeviceDiagnostic).filter(
                DeviceDiagnostic.device_id == device.id
            ).order_by(DeviceDiagnostic.timestamp.desc()).first()
            
            health_status = 'unknown'
            if latest_diagnostic:
                battery_ok = (latest_diagnostic.battery_level or 0) > 20
                signal_ok = (latest_diagnostic.signal_strength or 0) > -80
                temp_ok = -10 <= (latest_diagnostic.temperature or 0) <= 60
                
                if battery_ok and signal_ok and temp_ok:
                    health_status = 'healthy'
                elif battery_ok and signal_ok:
                    health_status = 'warning'
                else:
                    health_status = 'critical'
            
            health_data.append({
                'device_id': device.id,
                'device_name': device.name,
                'device_identifier': device.device_id,
                'is_online': device.is_online,
                'last_sync': device.last_sync.isoformat() if device.last_sync else None,
                'health_status': health_status,
                'firmware_version': device.firmware_version,
                'diagnostic_data': {
                    'battery_level': latest_diagnostic.battery_level if latest_diagnostic else None,
                    'signal_strength': latest_diagnostic.signal_strength if latest_diagnostic else None,
                    'temperature': latest_diagnostic.temperature if latest_diagnostic else None,
                    'last_error': latest_diagnostic.last_error if latest_diagnostic else None
                }
            })
        
        total_devices = len(devices)
        online_devices = sum(1 for d in devices if d.is_online)
        healthy_devices = sum(1 for d in health_data if d['health_status'] == 'healthy')
        warning_devices = sum(1 for d in health_data if d['health_status'] == 'warning')
        critical_devices = sum(1 for d in health_data if d['health_status'] == 'critical')
        
        return {
            'summary': {
                'total_devices': total_devices,
                'online_devices': online_devices,
                'offline_devices': total_devices - online_devices,
                'healthy_devices': healthy_devices,
                'warning_devices': warning_devices,
                'critical_devices': critical_devices,
                'uptime_percentage': (online_devices / total_devices * 100) if total_devices > 0 else 0
            },
            'devices': health_data
        }
    
    def schedule_maintenance(self, db: Session, device_id: int, 
                           maintenance_type: str, scheduled_time: datetime) -> Dict[str, Any]:
        """Schedule maintenance for a device"""
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {'success': False, 'error': 'Device not found'}
        
        maintenance_record = {
            'device_id': device_id,
            'maintenance_type': maintenance_type,
            'scheduled_time': scheduled_time.isoformat(),
            'status': 'scheduled',
            'created_at': datetime.utcnow().isoformat()
        }
        
        return {
            'success': True,
            'maintenance_id': f'maint_{device_id}_{int(datetime.utcnow().timestamp())}',
            'message': f'Maintenance scheduled for {device.name}',
            'details': maintenance_record
        }

device_management_service = DeviceManagementService()
