from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..database import SponsorCampaign, Notice, Device, AdvancedSchedule, CampaignScheduleType, NoticeStyle, FontStyle
import json
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY

class AdvancedSchedulingService:
    def __init__(self):
        pass
    
    def create_advanced_schedule(self, db: Session, schedule_data: Dict[str, Any]) -> AdvancedSchedule:
        """Create an advanced schedule with complex rules"""
        schedule = AdvancedSchedule(
            name=schedule_data['name'],
            schedule_type=CampaignScheduleType(schedule_data['schedule_type']),
            conditions=schedule_data.get('conditions'),
            start_date=schedule_data['start_date'],
            end_date=schedule_data['end_date'],
            recurrence_pattern=schedule_data.get('recurrence_pattern'),
            priority=schedule_data.get('priority', 1)
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule
    
    def create_seasonal_campaign(self, db: Session, campaign_data: Dict[str, Any]) -> SponsorCampaign:
        """Create a seasonal campaign with advanced scheduling"""
        schedule_data = {
            'name': f"Seasonal: {campaign_data['sponsor_name']}",
            'schedule_type': 'seasonal',
            'start_date': campaign_data['start_date'],
            'end_date': campaign_data['end_date'],
            'conditions': campaign_data.get('seasonal_conditions', {}),
            'recurrence_pattern': campaign_data.get('recurrence_pattern')
        }
        
        schedule = self.create_advanced_schedule(db, schedule_data)
        
        campaign = SponsorCampaign(
            sponsor_name=campaign_data['sponsor_name'],
            device_id=campaign_data['device_id'],
            creative_path=campaign_data['creative_path'],
            start_date=campaign_data['start_date'],
            end_date=campaign_data['end_date'],
            rotation_interval=campaign_data['rotation_interval'],
            rotation_unit=campaign_data['rotation_unit'],
            schedule_id=schedule.id,
            priority=campaign_data.get('priority', 1)
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return campaign
    
    def create_ab_test_campaign(self, db: Session, test_data: Dict[str, Any]) -> List[SponsorCampaign]:
        """Create A/B test campaigns"""
        campaigns = []
        
        for variant in ['A', 'B']:
            variant_data = test_data[f'variant_{variant}']
            
            schedule_data = {
                'name': f"A/B Test {variant}: {variant_data['sponsor_name']}",
                'schedule_type': 'ab_test',
                'start_date': test_data['start_date'],
                'end_date': test_data['end_date'],
                'conditions': {
                    'ab_test_id': test_data['test_id'],
                    'variant': variant,
                    'traffic_split': test_data.get('traffic_split', 50)
                }
            }
            
            schedule = self.create_advanced_schedule(db, schedule_data)
            
            campaign = SponsorCampaign(
                sponsor_name=variant_data['sponsor_name'],
                device_id=variant_data['device_id'],
                creative_path=variant_data['creative_path'],
                start_date=test_data['start_date'],
                end_date=test_data['end_date'],
                rotation_interval=variant_data['rotation_interval'],
                rotation_unit=variant_data['rotation_unit'],
                schedule_id=schedule.id,
                ab_test_group=variant,
                priority=test_data.get('priority', 1)
            )
            db.add(campaign)
            campaigns.append(campaign)
        
        db.commit()
        return campaigns
    
    def create_notice_style(self, db: Session, style_data: Dict[str, Any]) -> NoticeStyle:
        """Create a custom notice style"""
        style = NoticeStyle(
            name=style_data['name'],
            font_family=FontStyle(style_data.get('font_family', 'arial')),
            font_size=style_data.get('font_size', 24),
            font_weight=style_data.get('font_weight', 'normal'),
            text_color=style_data.get('text_color', '#000000'),
            background_color=style_data.get('background_color', '#FFFFFF'),
            border_style=style_data.get('border_style'),
            padding=style_data.get('padding', 10),
            text_align=style_data.get('text_align', 'center')
        )
        db.add(style)
        db.commit()
        db.refresh(style)
        return style
    
    def create_advanced_notice(self, db: Session, notice_data: Dict[str, Any]) -> Notice:
        """Create a notice with advanced scheduling and styling"""
        style_id = None
        if 'style' in notice_data:
            style = self.create_notice_style(db, notice_data['style'])
            style_id = style.id
        elif 'style_id' in notice_data:
            style_id = notice_data['style_id']
        
        schedule_id = None
        if 'schedule' in notice_data:
            schedule_data = notice_data['schedule']
            schedule_data['name'] = f"Notice: {notice_data['title']}"
            schedule = self.create_advanced_schedule(db, schedule_data)
            schedule_id = schedule.id
        
        start_time = notice_data['start_time']
        duration_minutes = notice_data['duration_minutes']
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        notice = Notice(
            title=notice_data['title'],
            content=notice_data['content'],
            device_id=notice_data['device_id'],
            course_id=notice_data['course_id'],
            created_by=notice_data['created_by'],
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            style_id=style_id,
            schedule_id=schedule_id
        )
        db.add(notice)
        db.commit()
        db.refresh(notice)
        return notice
    
    def get_active_schedules(self, db: Session, device_id: int, 
                           current_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get all active schedules for a device at current time"""
        if not current_time:
            current_time = datetime.utcnow()
        
        campaigns = db.query(SponsorCampaign).join(AdvancedSchedule).filter(
            SponsorCampaign.device_id == device_id,
            SponsorCampaign.is_active == True,
            AdvancedSchedule.is_active == True,
            AdvancedSchedule.start_date <= current_time,
            AdvancedSchedule.end_date >= current_time
        ).all()
        
        notices = db.query(Notice).join(AdvancedSchedule).filter(
            Notice.device_id == device_id,
            Notice.is_active == True,
            AdvancedSchedule.is_active == True,
            AdvancedSchedule.start_date <= current_time,
            AdvancedSchedule.end_date >= current_time
        ).all()
        
        active_items = []
        
        for campaign in campaigns:
            if self._should_display_now(campaign.schedule, current_time):
                active_items.append({
                    'type': 'campaign',
                    'id': campaign.id,
                    'content': campaign.creative_path,
                    'priority': campaign.schedule.priority,
                    'schedule_type': campaign.schedule.schedule_type,
                    'ab_test_group': campaign.ab_test_group
                })
        
        for notice in notices:
            if self._should_display_now(notice.schedule, current_time):
                active_items.append({
                    'type': 'notice',
                    'id': notice.id,
                    'content': notice.content,
                    'title': notice.title,
                    'priority': notice.schedule.priority,
                    'schedule_type': notice.schedule.schedule_type,
                    'style': self._get_notice_style(db, notice.style_id) if notice.style_id else None
                })
        
        active_items.sort(key=lambda x: x['priority'], reverse=True)
        
        return active_items
    
    def _should_display_now(self, schedule: AdvancedSchedule, current_time: datetime) -> bool:
        """Check if schedule should be active at current time"""
        if not schedule:
            return True
        
        if not (schedule.start_date <= current_time <= schedule.end_date):
            return False
        
        if schedule.recurrence_pattern:
            return self._check_recurrence(schedule, current_time)
        
        if schedule.conditions:
            return self._check_conditions(schedule.conditions, current_time)
        
        return True
    
    def _check_recurrence(self, schedule: AdvancedSchedule, current_time: datetime) -> bool:
        """Check if current time matches recurrence pattern"""
        pattern = schedule.recurrence_pattern
        
        if pattern.get('type') == 'daily':
            start_hour = pattern.get('start_hour', 0)
            end_hour = pattern.get('end_hour', 23)
            return start_hour <= current_time.hour <= end_hour
        
        elif pattern.get('type') == 'weekly':
            allowed_days = pattern.get('days', [0, 1, 2, 3, 4, 5, 6])  # 0=Monday
            return current_time.weekday() in allowed_days
        
        elif pattern.get('type') == 'monthly':
            allowed_dates = pattern.get('dates', list(range(1, 32)))
            return current_time.day in allowed_dates
        
        return True
    
    def _check_conditions(self, conditions: Dict[str, Any], current_time: datetime) -> bool:
        """Check if conditions are met for display"""
        return True
    
    def _get_notice_style(self, db: Session, style_id: int) -> Optional[Dict[str, Any]]:
        """Get notice style configuration"""
        style = db.query(NoticeStyle).filter(NoticeStyle.id == style_id).first()
        if not style:
            return None
        
        return {
            'font_family': style.font_family,
            'font_size': style.font_size,
            'font_weight': style.font_weight,
            'text_color': style.text_color,
            'background_color': style.background_color,
            'border_style': style.border_style,
            'padding': style.padding,
            'text_align': style.text_align
        }

advanced_scheduling_service = AdvancedSchedulingService()
