"""
Monitoring and health check endpoints for Golf CMS
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import psutil
import os
from typing import Dict, Any

from .database import get_db, engine
from .services.email_service import email_service
from .services.alerting_service import alerting_service

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "golf-cms-api"
    }

@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with dependency status"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "golf-cms-api",
        "checks": {}
    }
    
    overall_healthy = True
    
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": 0
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
    
    try:
        if email_service.sendgrid_api_key or (email_service.smtp_username and email_service.smtp_password):
            health_status["checks"]["email_service"] = {
                "status": "configured",
                "provider": email_service.email_provider
            }
        else:
            health_status["checks"]["email_service"] = {
                "status": "not_configured",
                "provider": email_service.email_provider
            }
    except Exception as e:
        health_status["checks"]["email_service"] = {
            "status": "error",
            "error": str(e)
        }
    
    try:
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_metrics = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent
        }
        
        health_status["checks"]["system"] = {
            "status": "healthy",
            **system_metrics
        }
        
        alerts = alerting_service.check_system_health(system_metrics)
        if alerts:
            health_status["checks"]["system"]["alerts"] = alerts
        
        device_alerts = alerting_service.check_device_health(db)
        health_status["checks"]["device_health"] = {
            "status": "healthy" if not device_alerts else "warning",
            "offline_devices": len(device_alerts),
            "alerts": device_alerts
        }
        
    except Exception as e:
        health_status["checks"]["system"] = {
            "status": "error",
            "error": str(e)
        }
    
    if not overall_healthy:
        health_status["status"] = "unhealthy"
    
    return health_status

@router.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """Get system metrics for monitoring"""
    from .database import User, Course, Device, SponsorCampaign, Notice
    
    try:
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "total_users": db.query(User).count(),
                "total_courses": db.query(Course).count(),
                "total_devices": db.query(Device).count(),
                "active_campaigns": db.query(SponsorCampaign).filter(SponsorCampaign.is_active == True).count(),
                "active_notices": db.query(Notice).filter(Notice.is_active == True).count()
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "uptime_seconds": psutil.boot_time()
            }
        }
        
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error collecting metrics: {str(e)}")

@router.get("/version")
async def get_version():
    """Get application version and build info"""
    return {
        "service": "golf-cms-api",
        "version": "1.0.0",
        "build_date": datetime.utcnow().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "python_version": os.sys.version,
        "features": [
            "multi_tenant_architecture",
            "supabase_storage",
            "email_notifications",
            "analytics_reporting",
            "stripe_billing_ready"
        ]
    }
