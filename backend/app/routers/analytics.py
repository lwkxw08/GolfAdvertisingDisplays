from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, datetime, timedelta
from ..database import get_db, RevenueConfiguration, SavedReport, ReportExport, CampaignDisplayLog, Device, SponsorCampaign
from ..auth import get_current_user, require_admin
from ..schemas import (
    CampaignPerformanceReport, DeviceUptimeReport, RevenueReport,
    RegionalRevenueReport, RevenueConfigurationCreate, RevenueConfigurationUpdate,
    RevenueConfigurationResponse, SavedReportCreate, SavedReportUpdate,
    SavedReportResponse, ReportExportRequest, ReportExportResponse,
    AnalyticsDashboard, UserResponse
)
from ..services.analytics_service import analytics_service
import tempfile
import os
import csv
import io

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/campaign-performance", response_model=List[CampaignPerformanceReport])
async def get_campaign_performance(
    campaign_id: Optional[int] = Query(None),
    device_id: Optional[int] = Query(None),
    course_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get campaign performance analytics"""
    try:
        if current_user.role.value != "admin" and current_user.course_id:
            course_id = current_user.course_id
        
        reports = await analytics_service.get_campaign_performance_report(
            db=db,
            campaign_id=campaign_id,
            device_id=device_id,
            course_id=course_id,
            start_date=start_date,
            end_date=end_date
        )
        return reports
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating campaign performance report: {str(e)}")


@router.get("/device-uptime", response_model=List[DeviceUptimeReport])
async def get_device_uptime(
    device_id: Optional[int] = Query(None),
    course_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get device uptime analytics"""
    try:
        if current_user.role.value != "admin" and current_user.course_id:
            course_id = current_user.course_id
        
        reports = await analytics_service.get_device_uptime_report(
            db=db,
            device_id=device_id,
            course_id=course_id,
            start_date=start_date,
            end_date=end_date
        )
        return reports
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating device uptime report: {str(e)}")


@router.get("/revenue", response_model=List[RevenueReport])
async def get_revenue_analytics(
    course_id: Optional[int] = Query(None),
    region_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get revenue analytics"""
    try:
        if current_user.role.value != "admin" and current_user.course_id:
            course_id = current_user.course_id
        
        reports = await analytics_service.get_revenue_report(
            db=db,
            course_id=course_id,
            region_id=region_id,
            start_date=start_date,
            end_date=end_date
        )
        return reports
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating revenue report: {str(e)}")


@router.get("/revenue/regional", response_model=List[RegionalRevenueReport])
async def get_regional_revenue(
    region_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: UserResponse = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get regional revenue analytics (admin only)"""
    try:
        reports = await analytics_service.get_regional_revenue_report(
            db=db,
            region_id=region_id,
            start_date=start_date,
            end_date=end_date
        )
        return reports
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating regional revenue report: {str(e)}")


@router.post("/revenue/calculate/{course_id}")
async def calculate_revenue(
    course_id: int,
    period_start: date = Query(...),
    period_end: date = Query(...),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calculate and store revenue analytics for a course"""
    try:
        if current_user.role.value != "admin" and current_user.course_id != course_id:
            raise HTTPException(status_code=403, detail="Not authorized to calculate revenue for this course")
        
        analytics = await analytics_service.calculate_revenue_analytics(
            db=db,
            course_id=course_id,
            period_start=period_start,
            period_end=period_end
        )
        return {"message": "Revenue analytics calculated successfully", "analytics_id": analytics.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating revenue analytics: {str(e)}")


@router.get("/revenue-config/{course_id}", response_model=List[RevenueConfigurationResponse])
async def get_revenue_configurations(
    course_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get revenue configurations for a course"""
    try:
        if current_user.role.value != "admin" and current_user.course_id != course_id:
            raise HTTPException(status_code=403, detail="Not authorized to view revenue configurations for this course")
        
        configs = db.query(RevenueConfiguration).filter(
            RevenueConfiguration.course_id == course_id
        ).order_by(RevenueConfiguration.effective_from.desc()).all()
        
        return configs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching revenue configurations: {str(e)}")


@router.post("/revenue-config", response_model=RevenueConfigurationResponse)
async def create_revenue_configuration(
    config: RevenueConfigurationCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new revenue configuration"""
    try:
        if current_user.role.value != "admin" and current_user.course_id != config.course_id:
            raise HTTPException(status_code=403, detail="Not authorized to create revenue configuration for this course")
        
        new_config = RevenueConfiguration(**config.dict())
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        
        return new_config
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating revenue configuration: {str(e)}")


@router.put("/revenue-config/{config_id}", response_model=RevenueConfigurationResponse)
async def update_revenue_configuration(
    config_id: int,
    config_update: RevenueConfigurationUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a revenue configuration"""
    try:
        existing_config = db.query(RevenueConfiguration).filter(
            RevenueConfiguration.id == config_id
        ).first()
        
        if not existing_config:
            raise HTTPException(status_code=404, detail="Revenue configuration not found")
        
        if current_user.role.value != "admin" and current_user.course_id != existing_config.course_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this revenue configuration")
        
        for field, value in config_update.dict(exclude_unset=True).items():
            setattr(existing_config, field, value)
        
        db.commit()
        db.refresh(existing_config)
        
        return existing_config
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating revenue configuration: {str(e)}")


@router.delete("/revenue-config/{config_id}")
async def delete_revenue_configuration(
    config_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a revenue configuration"""
    try:
        config = db.query(RevenueConfiguration).filter(
            RevenueConfiguration.id == config_id
        ).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="Revenue configuration not found")
        
        if current_user.role.value != "admin" and current_user.course_id != config.course_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this revenue configuration")
        
        db.delete(config)
        db.commit()
        
        return {"message": "Revenue configuration deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting revenue configuration: {str(e)}")


@router.get("/saved-reports", response_model=List[SavedReportResponse])
async def get_saved_reports(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all saved reports for the current user"""
    try:
        reports = db.query(SavedReport).filter(
            SavedReport.user_id == current_user.id,
            SavedReport.is_active == True
        ).order_by(SavedReport.created_at.desc()).all()
        
        return reports
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching saved reports: {str(e)}")


@router.post("/saved-reports", response_model=SavedReportResponse)
async def create_saved_report(
    report: SavedReportCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new saved report"""
    try:
        new_report = SavedReport(
            user_id=current_user.id,
            **report.dict()
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        
        return new_report
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating saved report: {str(e)}")


@router.put("/saved-reports/{report_id}", response_model=SavedReportResponse)
async def update_saved_report(
    report_id: int,
    report_update: SavedReportUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a saved report"""
    try:
        existing_report = db.query(SavedReport).filter(
            SavedReport.id == report_id,
            SavedReport.user_id == current_user.id
        ).first()
        
        if not existing_report:
            raise HTTPException(status_code=404, detail="Saved report not found")
        
        for field, value in report_update.dict(exclude_unset=True).items():
            setattr(existing_report, field, value)
        
        db.commit()
        db.refresh(existing_report)
        
        return existing_report
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating saved report: {str(e)}")


@router.delete("/saved-reports/{report_id}")
async def delete_saved_report(
    report_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a saved report"""
    try:
        report = db.query(SavedReport).filter(
            SavedReport.id == report_id,
            SavedReport.user_id == current_user.id
        ).first()
        
        if not report:
            raise HTTPException(status_code=404, detail="Saved report not found")
        
        db.delete(report)
        db.commit()
        
        return {"message": "Saved report deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting saved report: {str(e)}")


@router.post("/export/csv")
async def export_report_csv(
    export_request: ReportExportRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export report to CSV"""
    try:
        if export_request.report_type == "campaign_performance":
            course_id = None
            if current_user.role.value != "admin" and current_user.course_id:
                course_id = current_user.course_id
            
            data = await analytics_service.get_campaign_performance_report(
                db=db,
                course_id=course_id,
                start_date=export_request.date_range_start,
                end_date=export_request.date_range_end
            )
            columns = [
                'campaign_id', 'campaign_name', 'device_id', 'device_name',
                'total_impressions', 'total_rotations', 'total_display_time_hours',
                'avg_impressions_per_day', 'date_range_start', 'date_range_end'
            ]
        
        elif export_request.report_type == "device_uptime":
            course_id = None
            if current_user.role.value != "admin" and current_user.course_id:
                course_id = current_user.course_id
            
            data = await analytics_service.get_device_uptime_report(
                db=db,
                course_id=course_id,
                start_date=export_request.date_range_start,
                end_date=export_request.date_range_end
            )
            columns = [
                'device_id', 'device_name', 'course_id', 'course_name',
                'total_uptime_minutes', 'total_downtime_minutes', 'uptime_percentage',
                'total_syncs', 'total_errors', 'avg_syncs_per_day',
                'date_range_start', 'date_range_end'
            ]
        
        elif export_request.report_type == "revenue_analytics":
            course_id = None
            if current_user.role.value != "admin" and current_user.course_id:
                course_id = current_user.course_id
            
            data = await analytics_service.get_revenue_report(
                db=db,
                course_id=course_id,
                start_date=export_request.date_range_start,
                end_date=export_request.date_range_end
            )
            columns = [
                'course_id', 'course_name', 'period_start', 'period_end',
                'total_device_costs', 'total_sponsorship_revenue', 'gross_revenue',
                'course_revenue_share', 'platform_revenue_share', 'net_revenue',
                'active_devices_count', 'active_campaigns_count', 'total_impressions',
                'revenue_per_device', 'revenue_per_impression'
            ]
        else:
            raise HTTPException(status_code=400, detail="Invalid report type")
        
        csv_output = await analytics_service.export_to_csv(
            data=data,
            columns=columns,
            filename=f"{export_request.report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        export_log = ReportExport(
            user_id=current_user.id,
            report_type=export_request.report_type,
            export_format="csv",
            filters=export_request.dict()
        )
        db.add(export_log)
        db.commit()
        
        return Response(
            content=csv_output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={export_request.report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting report: {str(e)}")


@router.post("/export/pdf")
async def export_report_pdf(
    export_request: ReportExportRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export report to PDF (placeholder - requires reportlab installation)"""
    raise HTTPException(
        status_code=501,
        detail="PDF export not yet implemented. Please use CSV export instead."
    )


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_analytics_dashboard(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics dashboard summary"""
    try:
        course_id = None
        region_id = None
        
        if current_user.role.value != "admin" and current_user.course_id:
            course_id = current_user.course_id
        
        dashboard = await analytics_service.get_analytics_dashboard(
            db=db,
            course_id=course_id,
            region_id=region_id
        )
        
        return dashboard
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating analytics dashboard: {str(e)}")


@router.get("/proof-of-play/export")
async def export_proof_of_play(
    campaign_id: Optional[int] = Query(None),
    device_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    include_qr_analytics: bool = Query(False),
    format: str = Query("csv", regex="^(csv|json)$"),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export proof-of-play logs with optional QR analytics for sponsor reporting"""
    try:
        from ..database import QRCode, QRCodeScan
        
        query = db.query(
            CampaignDisplayLog,
            Device.name.label('device_name'),
            Device.device_id.label('device_external_id'),
            SponsorCampaign.sponsor_name
        ).join(
            Device, CampaignDisplayLog.device_id == Device.id
        ).outerjoin(
            SponsorCampaign, CampaignDisplayLog.campaign_id == SponsorCampaign.id
        )
        
        if current_user.role.value != "admin" and current_user.course_id:
            query = query.filter(Device.course_id == current_user.course_id)
        
        if campaign_id:
            query = query.filter(CampaignDisplayLog.campaign_id == campaign_id)
        if device_id:
            query = query.filter(CampaignDisplayLog.device_id == device_id)
        if start_date:
            query = query.filter(func.date(CampaignDisplayLog.displayed_at) >= start_date)
        if end_date:
            query = query.filter(func.date(CampaignDisplayLog.displayed_at) <= end_date)
        
        logs = query.order_by(CampaignDisplayLog.displayed_at.desc()).limit(10000).all()
        
        qr_data = {}
        if include_qr_analytics:
            qr_query = db.query(
                QRCode.campaign_id,
                func.count(QRCodeScan.id).label('scan_count')
            ).join(
                QRCodeScan, QRCode.id == QRCodeScan.qr_code_id
            ).filter(
                QRCode.campaign_id.isnot(None)
            )
            
            if current_user.role.value != "admin" and current_user.course_id:
                qr_query = qr_query.filter(QRCode.course_id == current_user.course_id)
            
            if campaign_id:
                qr_query = qr_query.filter(QRCode.campaign_id == campaign_id)
            if start_date:
                qr_query = qr_query.filter(func.date(QRCodeScan.scan_timestamp) >= start_date)
            if end_date:
                qr_query = qr_query.filter(func.date(QRCodeScan.scan_timestamp) <= end_date)
            
            qr_results = qr_query.group_by(QRCode.campaign_id).all()
            qr_data = {r.campaign_id: r.scan_count for r in qr_results}
        
        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            
            headers = [
                'Event ID', 'Campaign ID', 'Campaign Name', 'Device Internal ID', 
                'Device Name', 'Device External ID', 'Content Type', 'Displayed At', 
                'Ended At', 'Duration (seconds)', 'Image Hash', 'Hash Algorithm', 
                'Creative URL', 'Render Success', 'Connectivity', 'Power Mode', 
                'Firmware Version'
            ]
            if include_qr_analytics:
                headers.append('QR Scans')
            
            writer.writerow(headers)
            
            for log, device_name, device_external_id, sponsor_name in logs:
                row = [
                    log.event_id,
                    log.campaign_id or '',
                    sponsor_name or '',
                    log.device_id,
                    device_name or '',
                    device_external_id or '',
                    log.content_type,
                    log.displayed_at.isoformat() if log.displayed_at else '',
                    log.ended_at.isoformat() if log.ended_at else '',
                    log.duration_seconds or '',
                    log.image_hash,
                    log.hash_algo,
                    log.creative_url or '',
                    'Yes' if log.render_result else 'No',
                    log.connectivity_type or '',
                    log.power_mode or '',
                    log.firmware_version or ''
                ]
                if include_qr_analytics:
                    row.append(qr_data.get(log.campaign_id, 0) if log.campaign_id else 0)
                
                writer.writerow(row)
            
            filename = f"proof_of_play_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            import json
            data = []
            for log, device_name, device_external_id, sponsor_name in logs:
                item = {
                    'event_id': log.event_id,
                    'campaign_id': log.campaign_id,
                    'campaign_name': sponsor_name,
                    'device_internal_id': log.device_id,
                    'device_name': device_name,
                    'device_external_id': device_external_id,
                    'content_type': log.content_type,
                    'displayed_at': log.displayed_at.isoformat() if log.displayed_at else None,
                    'ended_at': log.ended_at.isoformat() if log.ended_at else None,
                    'duration_seconds': log.duration_seconds,
                    'image_hash': log.image_hash,
                    'hash_algo': log.hash_algo,
                    'creative_url': log.creative_url,
                    'render_result': log.render_result,
                    'connectivity_type': log.connectivity_type,
                    'power_mode': log.power_mode,
                    'firmware_version': log.firmware_version
                }
                if include_qr_analytics:
                    item['qr_scans'] = qr_data.get(log.campaign_id, 0) if log.campaign_id else 0
                
                data.append(item)
            
            filename = f"proof_of_play_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            return StreamingResponse(
                iter([json.dumps(data, indent=2)]),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting proof-of-play data: {str(e)}")
