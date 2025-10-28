from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging

from .database import SessionLocal
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
        scheduler.start()
        logger.info("Background scheduler started - checking device status every 5 minutes")

def shutdown_scheduler():
    """Shutdown the background scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
