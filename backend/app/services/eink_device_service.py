from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont
import io
import json
import requests
from ..database import Device, DeviceAnalytics, Course
from .analytics_service import analytics_service
import logging

logger = logging.getLogger(__name__)

class EInkDeviceService:
    """Service for managing E-ink specific device operations"""
    
    E6_WIDTH = 1200
    E6_HEIGHT = 1600
    E6_COLORS = {
        'BLACK': 0x000000,
        'WHITE': 0xffffff,
        'YELLOW': 0x00ffff,
        'RED': 0x0000ff,
        'BLUE': 0xff0000,
        'GREEN': 0x00ff00
    }
    
    def __init__(self):
        self.refresh_intervals = {
            'fast': 300,      # 5 minutes - for urgent notices
            'normal': 900,    # 15 minutes - standard refresh
            'slow': 3600,     # 1 hour - power saving mode
            'deep_sleep': 21600  # 6 hours - overnight/maintenance
        }
    
    def get_device_playlist_optimized(self, db: Session, device_id: str, 
                                    connectivity_type: str = 'wifi') -> Dict[str, Any]:
        """Get optimized playlist for E-ink device with connectivity awareness"""
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        device.last_sync = datetime.now(timezone.utc)
        device.is_online = True
        db.commit()
        
        self._record_connectivity_analytics(db, device, connectivity_type)
        
        playlist = self._get_optimized_content(db, device, connectivity_type)
        
        playlist['eink_config'] = self._get_eink_config(connectivity_type)
        playlist['power_management'] = self._get_power_config(device, connectivity_type)
        
        return playlist
    
    def _get_optimized_content(self, db: Session, device: Device, 
                             connectivity_type: str) -> Dict[str, Any]:
        """Get content optimized for connectivity type and E-ink display"""
        from datetime import date, time as dt_time
        now = datetime.now(timezone.utc)
        current_time = now.strftime("%H:%M")
        current_day = now.strftime("%A").lower()
        
        def to_aware_datetime(dt_or_date):
            """Convert date or datetime to timezone-aware datetime"""
            if isinstance(dt_or_date, datetime):
                return dt_or_date if dt_or_date.tzinfo else dt_or_date.replace(tzinfo=timezone.utc)
            elif isinstance(dt_or_date, date):
                return datetime.combine(dt_or_date, dt_time.min, tzinfo=timezone.utc)
            return None
        
        from ..database import Notice
        active_notices = db.query(Notice).filter(
            Notice.device_id == device.id,
            Notice.is_active == True
        ).order_by(Notice.created_at.desc()).all()
        
        active_notices = [
            n for n in active_notices
            if to_aware_datetime(n.start_time) <= now < to_aware_datetime(n.end_time)
        ]
        
        from ..database import SponsorCampaign
        all_campaigns_raw = db.query(SponsorCampaign).filter(
            SponsorCampaign.device_id == device.id,
            SponsorCampaign.is_active == True
        ).order_by(SponsorCampaign.priority.desc()).all()
        
        all_campaigns = []
        for campaign in all_campaigns_raw:
            start_dt = to_aware_datetime(campaign.start_date)
            end_dt = to_aware_datetime(campaign.end_date)
            if end_dt:
                end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            if start_dt <= now <= end_dt:
                all_campaigns.append(campaign)
        
        active_campaigns = []
        for campaign in all_campaigns:
            if self._is_campaign_active_now(campaign, current_time, current_day):
                active_campaigns.append(campaign)
        
        playlist_items = []
        
        for notice in active_notices:
            item = {
                'type': 'notice',
                'id': notice.id,
                'content': notice.content,
                'title': notice.title,
                'expires_at': notice.end_time.isoformat(),
                'priority': 100,  # Highest priority
                'eink_optimized': True
            }
            
            if notice.style_id:
                item['style'] = self._get_notice_style(db, notice.style_id)
            
            playlist_items.append(item)
        
        max_items = 3 if connectivity_type == 'lte' else 5  # Limit for LTE bandwidth
        
        if len(playlist_items) < max_items:
            for campaign in active_campaigns[:max_items - len(playlist_items)]:
                item = {
                    'type': 'campaign',
                    'id': campaign.id,
                    'content': campaign.creative_path,
                    'sponsor_name': campaign.sponsor_name,
                    'priority': campaign.priority,
                    'rotation_interval': campaign.rotation_interval,
                    'rotation_unit': campaign.rotation_unit.value,
                    'eink_optimized': True
                }
                
                item['eink_url'] = self._get_eink_optimized_url(campaign.creative_path)
                playlist_items.append(item)
        
        next_refresh_at = self._calculate_next_boundary(
            db, device, now, active_notices, all_campaigns
        )
        
        return {
            'device_id': device.device_id,
            'last_updated': now.isoformat(),
            'items': playlist_items,
            'connectivity_type': connectivity_type,
            'total_items': len(playlist_items),
            'next_refresh_at': next_refresh_at.isoformat() if next_refresh_at else None
        }
    
    def _calculate_next_boundary(self, db: Session, device: Device, now: datetime,
                                  active_notices: list, all_campaigns: list) -> Optional[datetime]:
        """Calculate the next content boundary time (notice expiry, campaign start/end, day change)"""
        from ..database import Notice, SponsorCampaign
        from datetime import date, time as dt_time
        
        def to_aware_datetime(dt_or_date):
            """Convert date or datetime to timezone-aware datetime"""
            if isinstance(dt_or_date, datetime):
                return dt_or_date if dt_or_date.tzinfo else dt_or_date.replace(tzinfo=timezone.utc)
            elif isinstance(dt_or_date, date):
                return datetime.combine(dt_or_date, dt_time.min, tzinfo=timezone.utc)
            return None
        
        boundaries = []
        
        for notice in active_notices:
            end_time_aware = to_aware_datetime(notice.end_time)
            if end_time_aware and end_time_aware > now:
                boundaries.append(end_time_aware)
        
        upcoming_notices = db.query(Notice).filter(
            Notice.device_id == device.id,
            Notice.is_active == True
        ).all()
        
        for notice in upcoming_notices:
            start_time_aware = to_aware_datetime(notice.start_time)
            if start_time_aware and start_time_aware > now and start_time_aware <= now + timedelta(days=7):
                boundaries.append(start_time_aware)
        
        current_time = now.strftime("%H:%M")
        current_day = now.strftime("%A").lower()
        
        for campaign in all_campaigns:
            start_dt = to_aware_datetime(campaign.start_date)
            end_dt = to_aware_datetime(campaign.end_date)
            
            if start_dt and start_dt > now:
                boundaries.append(start_dt)
            if end_dt and end_dt > now:
                boundaries.append(end_dt)
            
            if campaign.start_time and campaign.end_time:
                next_time_boundary = self._calculate_next_time_boundary(
                    now, campaign.start_time, campaign.end_time
                )
                if next_time_boundary:
                    boundaries.append(next_time_boundary)
            
            if campaign.days_of_week:
                try:
                    days_list = json.loads(campaign.days_of_week) if isinstance(campaign.days_of_week, str) else campaign.days_of_week
                    next_day_boundary = self._calculate_next_day_boundary(now, days_list, current_day)
                    if next_day_boundary:
                        boundaries.append(next_day_boundary)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        if boundaries:
            return min(boundaries)
        return None
    
    def _calculate_next_time_boundary(self, now: datetime, start_time: str, end_time: str) -> Optional[datetime]:
        """Calculate next time boundary for a campaign's time slot"""
        try:
            current_time = now.strftime("%H:%M")
            today = now.date()
            
            start_hour, start_min = map(int, start_time.split(':'))
            end_hour, end_min = map(int, end_time.split(':'))
            
            start_dt = datetime.combine(today, datetime.min.time().replace(hour=start_hour, minute=start_min))
            end_dt = datetime.combine(today, datetime.min.time().replace(hour=end_hour, minute=end_min))
            
            if start_time == end_time:
                return None
            
            if end_time < start_time:
                if current_time >= start_time:
                    return end_dt + timedelta(days=1)
                elif current_time < end_time:
                    return end_dt
                else:
                    return start_dt
            else:
                if current_time < start_time:
                    return start_dt
                elif current_time < end_time:
                    return end_dt
                else:
                    return start_dt + timedelta(days=1)
        except (ValueError, AttributeError):
            return None
    
    def _calculate_next_day_boundary(self, now: datetime, days_list: list, current_day: str) -> Optional[datetime]:
        """Calculate next day-of-week boundary for a campaign"""
        try:
            day_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            
            current_day_num = day_map.get(current_day.lower())
            if current_day_num is None:
                return None
            
            campaign_days = []
            for day in days_list:
                day_num = day_map.get(day.lower())
                if day_num is not None:
                    campaign_days.append(day_num)
            
            if not campaign_days:
                return None
            
            campaign_days.sort()
            
            is_active_today = current_day_num in campaign_days
            
            tomorrow = now.date() + timedelta(days=1)
            midnight = datetime.combine(tomorrow, datetime.min.time())
            
            return midnight
            
        except (ValueError, AttributeError, KeyError):
            return None
    
    def _is_campaign_active_now(self, campaign, current_time: str, current_day: str) -> bool:
        """Check if campaign is active based on time slots and days of week"""
        if not campaign.start_time and not campaign.end_time and not campaign.days_of_week:
            return True
        
        if campaign.days_of_week:
            try:
                days_list = json.loads(campaign.days_of_week) if isinstance(campaign.days_of_week, str) else campaign.days_of_week
                if current_day not in [day.lower() for day in days_list]:
                    return False
            except (json.JSONDecodeError, TypeError):
                pass
        
        if campaign.start_time and campaign.end_time:
            if campaign.start_time == campaign.end_time:
                return True
            
            if campaign.start_time < campaign.end_time:
                if campaign.start_time <= current_time <= campaign.end_time:
                    return True
                return False
            else:
                if current_time >= campaign.start_time or current_time <= campaign.end_time:
                    return True
                return False
        
        return True
    
    def _get_eink_config(self, connectivity_type: str) -> Dict[str, Any]:
        """Get E-ink specific configuration based on connectivity"""
        base_config = {
            'display_width': self.E6_WIDTH,
            'display_height': self.E6_HEIGHT,
            'color_mode': 'e6_spectra',
            'supported_colors': list(self.E6_COLORS.keys()),
            'refresh_time_seconds': 19,
            'partial_refresh_supported': False
        }
        
        if connectivity_type == 'lte':
            base_config.update({
                'refresh_interval': self.refresh_intervals['normal'],
                'image_compression': 'high',
                'batch_updates': True,
                'retry_attempts': 3,
                'timeout_seconds': 30
            })
        else:  # wifi
            base_config.update({
                'refresh_interval': self.refresh_intervals['fast'],
                'image_compression': 'medium',
                'batch_updates': False,
                'retry_attempts': 5,
                'timeout_seconds': 15
            })
        
        return base_config
    
    def _get_power_config(self, device: Device, connectivity_type: str) -> Dict[str, Any]:
        """Get power management configuration for solar-powered Pi Zero 2W"""
        current_hour = datetime.now(timezone.utc).hour
        
        if 22 <= current_hour or current_hour <= 6:  # Night time
            power_mode = 'deep_sleep'
        elif connectivity_type == 'lte':
            power_mode = 'slow'  # Conserve battery on LTE
        else:
            power_mode = 'normal'
        
        config = {
            'power_mode': power_mode,
            'refresh_interval': self.refresh_intervals[power_mode],
            'sleep_between_refreshes': True,
            'solar_charging_optimization': True,
            'battery_monitoring': True,
            'low_power_threshold': 20,  # Percentage
            'emergency_mode_threshold': 10
        }
        
        if connectivity_type == 'lte':
            config.update({
                'lte_power_saving': True,
                'connection_pooling': True,
                'data_compression': True,
                'scheduled_sync_windows': [8, 12, 16, 20]  # Hours
            })
        else:  # wifi
            config.update({
                'wifi_power_saving': True,
                'keep_alive_interval': 300,
                'connection_timeout': 30
            })
        
        return config
    
    def _get_notice_style(self, db: Session, style_id: int) -> Optional[Dict[str, Any]]:
        """Get notice style optimized for E-ink display"""
        from ..database import NoticeStyle
        style = db.query(NoticeStyle).filter(NoticeStyle.id == style_id).first()
        if not style:
            return None
        
        eink_style = {
            'font_family': style.font_family.value if style.font_family else 'ARIAL',
            'font_size': min(style.font_size or 24, 48),  # Limit for readability
            'font_weight': style.font_weight or 'normal',
            'text_color': self._convert_color_to_e6(style.text_color or '#000000'),
            'background_color': self._convert_color_to_e6(style.background_color or '#FFFFFF'),
            'text_align': style.text_align or 'center',
            'padding': style.padding or 10,
            'eink_optimized': True
        }
        
        return eink_style
    
    def _convert_color_to_e6(self, hex_color: str) -> str:
        """Convert hex color to nearest E6 Spectra color"""
        if not hex_color or hex_color == '#000000':
            return 'BLACK'
        elif hex_color == '#FFFFFF':
            return 'WHITE'
        elif 'ff0000' in hex_color.lower():
            return 'RED'
        elif '00ff00' in hex_color.lower():
            return 'GREEN'
        elif '0000ff' in hex_color.lower():
            return 'BLUE'
        elif 'ffff00' in hex_color.lower():
            return 'YELLOW'
        else:
            return 'BLACK'  # Default fallback
    
    def _get_eink_optimized_url(self, original_path: str) -> str:
        """Get E-ink optimized version of image URL"""
        if not original_path:
            return original_path
        
        if original_path.startswith('http'):
            return f"{original_path}?format=e6&width={self.E6_WIDTH}&height={self.E6_HEIGHT}"
        else:
            return original_path.replace('.jpg', '_e6.jpg').replace('.png', '_e6.png')
    
    def _record_connectivity_analytics(self, db: Session, device: Device, 
                                     connectivity_type: str):
        """Record connectivity analytics for monitoring"""
        try:
            analytics = DeviceAnalytics(
                device_id=device.id,
                sync_timestamp=datetime.now(timezone.utc),
                uptime_hours=1.0,  # Assume 1 hour uptime per sync
                impressions_count=1,
                notices_displayed=0,
                campaigns_displayed=0,
                connectivity_type=connectivity_type,
                power_level=85.0,  # Default - would come from device
                signal_strength=-65 if connectivity_type == 'lte' else -45
            )
            db.add(analytics)
            db.flush()
            
        except Exception as e:
            logger.warning(f"Failed to record connectivity analytics: {e}")
            db.rollback()
    
    def process_device_status_update(self, db: Session, device_id: str, 
                                   status_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process status update from E-ink device"""
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        device.last_sync = datetime.now(timezone.utc)
        device.is_online = True
        db.commit()
        
        battery_level = status_data.get('battery_level', 85)
        connectivity_type = status_data.get('connectivity_type', 'wifi')
        signal_strength = status_data.get('signal_strength', -50)
        display_status = status_data.get('display_status', 'ok')
        
        try:
            analytics = DeviceAnalytics(
                device_id=device.id,
                sync_timestamp=datetime.now(timezone.utc),
                uptime_hours=status_data.get('uptime_hours', 1.0),
                impressions_count=status_data.get('impressions_count', 1),
                notices_displayed=status_data.get('notices_displayed', 0),
                campaigns_displayed=status_data.get('campaigns_displayed', 1),
                connectivity_type=connectivity_type,
                power_level=battery_level,
                signal_strength=signal_strength,
                error_count=status_data.get('error_count', 0),
                last_refresh_duration=status_data.get('last_refresh_duration', 19.0)
            )
            db.add(analytics)
            db.commit()
            logger.debug(f"Device analytics recorded for {device_id}")
        except Exception as e:
            logger.warning(f"Failed to record analytics for {device_id}: {e}. Device will still show as online.")
            db.rollback()
        
        response = {
            'status': 'success',
            'next_sync_interval': self._calculate_next_sync_interval(
                battery_level, connectivity_type, display_status
            ),
            'power_mode': self._determine_power_mode(battery_level, connectivity_type),
            'config_updates': {}
        }
        
        if battery_level < 20:
            response['config_updates']['power_mode'] = 'emergency'
            response['next_sync_interval'] = self.refresh_intervals['deep_sleep']
        
        if display_status == 'error':
            response['config_updates']['diagnostic_mode'] = True
            response['next_sync_interval'] = self.refresh_intervals['fast']
        
        return response
    
    def _calculate_next_sync_interval(self, battery_level: float, 
                                    connectivity_type: str, display_status: str) -> int:
        """Calculate optimal next sync interval based on device status"""
        base_interval = self.refresh_intervals['normal']
        
        if battery_level < 20:
            base_interval = self.refresh_intervals['deep_sleep']
        elif battery_level < 50:
            base_interval = self.refresh_intervals['slow']
        
        if connectivity_type == 'lte' and battery_level < 70:
            base_interval = max(base_interval, self.refresh_intervals['slow'])
        
        if display_status == 'error':
            base_interval = self.refresh_intervals['fast']
        
        return base_interval
    
    def _determine_power_mode(self, battery_level: float, connectivity_type: str) -> str:
        """Determine optimal power mode for device"""
        if battery_level < 10:
            return 'emergency'
        elif battery_level < 20:
            return 'deep_sleep'
        elif battery_level < 50 and connectivity_type == 'lte':
            return 'slow'
        else:
            return 'normal'
    
    def get_device_diagnostics(self, db: Session, device_id: str) -> Dict[str, Any]:
        """Get comprehensive diagnostics for E-ink device"""
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        recent_analytics = db.query(DeviceAnalytics).filter(
            DeviceAnalytics.device_id == device.id
        ).order_by(DeviceAnalytics.sync_timestamp.desc()).limit(10).all()
        
        if recent_analytics:
            avg_battery = sum(a.power_level or 85 for a in recent_analytics) / len(recent_analytics)
            avg_signal = sum(a.signal_strength or -50 for a in recent_analytics) / len(recent_analytics)
            total_errors = sum(a.error_count or 0 for a in recent_analytics)
            avg_refresh_time = sum(a.last_refresh_duration or 19 for a in recent_analytics) / len(recent_analytics)
        else:
            avg_battery = avg_signal = total_errors = avg_refresh_time = 0
        
        health_score = self._calculate_health_score(avg_battery, avg_signal, total_errors, avg_refresh_time)
        
        return {
            'device_id': device.device_id,
            'device_name': device.name,
            'is_online': device.is_online,
            'last_sync': device.last_sync.isoformat() if device.last_sync else None,
            'health_score': health_score,
            'metrics': {
                'average_battery_level': round(avg_battery, 1),
                'average_signal_strength': round(avg_signal, 1),
                'total_errors_24h': total_errors,
                'average_refresh_time': round(avg_refresh_time, 1),
                'sync_count_24h': len(recent_analytics)
            },
            'recommendations': self._get_device_recommendations(avg_battery, avg_signal, total_errors),
            'eink_specific': {
                'display_type': 'Waveshare 13.3" E6 Spectra',
                'resolution': f"{self.E6_WIDTH}x{self.E6_HEIGHT}",
                'color_support': '6-color (E6)',
                'refresh_time': '19 seconds',
                'power_consumption': '<0.5W during refresh'
            }
        }
    
    def _calculate_health_score(self, battery: float, signal: float, 
                              errors: int, refresh_time: float) -> int:
        """Calculate device health score (0-100)"""
        score = 100
        
        if battery < 20:
            score -= 30
        elif battery < 50:
            score -= 15
        
        if signal < -80:  # Poor signal
            score -= 20
        elif signal < -60:  # Fair signal
            score -= 10
        
        score -= min(errors * 5, 25)  # Max 25 point deduction for errors
        
        if refresh_time > 25:
            score -= 10
        elif refresh_time > 30:
            score -= 20
        
        return max(0, score)
    
    def _get_device_recommendations(self, battery: float, signal: float, 
                                  errors: int) -> List[str]:
        """Get recommendations for device optimization"""
        recommendations = []
        
        if battery < 30:
            recommendations.append("Low battery - check solar panel positioning and cleaning")
        
        if signal < -70:
            recommendations.append("Poor signal strength - consider antenna repositioning")
        
        if errors > 5:
            recommendations.append("High error count - check device logs and connectivity")
        
        if not recommendations:
            recommendations.append("Device operating normally")
        
        return recommendations
    
    def update_offline_devices(self, db: Session, offline_threshold_minutes: int = 20) -> int:
        """
        Mark devices as offline if they haven't sent an update in the specified time.
        Returns the number of devices marked as offline.
        """
        threshold_time = datetime.now(timezone.utc) - timedelta(minutes=offline_threshold_minutes)
        
        stale_devices = db.query(Device).filter(
            Device.is_online == True,
            Device.last_sync < threshold_time
        ).all()
        
        count = 0
        for device in stale_devices:
            device.is_online = False
            count += 1
            logger.info(f"Marked device {device.device_id} as offline (last sync: {device.last_sync})")
        
        if count > 0:
            db.commit()
            logger.info(f"Marked {count} device(s) as offline")
        
        return count

eink_device_service = EInkDeviceService()
