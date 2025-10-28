from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import logging
import asyncio

from .database import SessionLocal, SponsorCampaign, Notice, Device
from .services.eink_device_service import eink_device_service

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def check_device_status():
    """Background job to check and update device online/offline status"""
    db = SessionLocal()
    try:
        logger.info("Running scheduled device status check...")
        count = eink_device_service.update_offline_devices(db, offline_threshold_minutes=20)
        if count > 0:
            logger.info(f"Marked {count} device(s) as offline")
    except Exception as e:
        logger.error(f"Error in scheduled device status check: {e}")
    finally:
        db.close()

def check_campaign_notice_events():
    """Background job to check for campaigns/notices starting or ending"""
    db = SessionLocal()
    try:
        from .websocket_manager import websocket_manager
        now = datetime.utcnow()
        check_window = timedelta(minutes=1)
        
        starting_campaigns = db.query(SponsorCampaign).filter(
            SponsorCampaign.start_date <= now,
            SponsorCampaign.start_date >= now - check_window,
            SponsorCampaign.is_active == True
        ).all()
        
        for campaign in starting_campaigns:
            device = db.query(Device).filter(Device.id == campaign.device_id).first()
            if device:
                asyncio.run(websocket_manager.notify_campaign_start(
                    device.course_id, campaign.id, campaign.sponsor_name
                ))
                logger.info(f"Notified campaign start: {campaign.sponsor_name}")
        
        ending_campaigns = db.query(SponsorCampaign).filter(
            SponsorCampaign.end_date <= now,
            SponsorCampaign.end_date >= now - check_window,
            SponsorCampaign.is_active == True
        ).all()
        
        for campaign in ending_campaigns:
            device = db.query(Device).filter(Device.id == campaign.device_id).first()
            if device:
                asyncio.run(websocket_manager.notify_campaign_end(
                    device.course_id, campaign.id, campaign.sponsor_name
                ))
                logger.info(f"Notified campaign end: {campaign.sponsor_name}")
        
        starting_notices = db.query(Notice).filter(
            Notice.start_time <= now,
            Notice.start_time >= now - check_window,
            Notice.is_active == True
        ).all()
        
        for notice in starting_notices:
            device = db.query(Device).filter(Device.id == notice.device_id).first()
            if device:
                asyncio.run(websocket_manager.notify_notice_start(
                    device.device_id, notice.id, notice.title or "Notice"
                ))
                logger.info(f"Notified notice start: {notice.title}")
        
        ending_notices = db.query(Notice).filter(
            Notice.end_time <= now,
            Notice.end_time >= now - check_window,
            Notice.is_active == True
        ).all()
        
        for notice in ending_notices:
            device = db.query(Device).filter(Device.id == notice.device_id).first()
            if device:
                asyncio.run(websocket_manager.notify_notice_end(
                    device.device_id, notice.id, notice.title or "Notice"
                ))
                logger.info(f"Notified notice end: {notice.title}")
                
    except Exception as e:
        logger.error(f"Error in campaign/notice event check: {e}")
    finally:
        db.close()

def start_scheduler():
    """Start the background scheduler"""
    if not scheduler.running:
        scheduler.add_job(
            check_device_status,
            trigger=IntervalTrigger(minutes=5),
            id='check_device_status',
            name='Check device online/offline status',
            replace_existing=True
        )
        scheduler.add_job(
            check_campaign_notice_events,
            trigger=IntervalTrigger(minutes=1),
            id='check_campaign_notice_events',
            name='Check for campaign/notice start/end events',
            replace_existing=True
        )
        scheduler.start()
        logger.info("Background scheduler started - checking device status every 5 minutes and campaign/notice events every minute")

def shutdown_scheduler():
    """Shutdown the background scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
