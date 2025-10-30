"""
Command Queue Service
Handles command lifecycle, timeouts, deduplication, and rate limiting
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from ..database import DeviceRemoteCommand, CommandStatus, Device

logger = logging.getLogger(__name__)


class CommandService:
    """Service for managing device remote commands"""
    
    COMMAND_TIMEOUT_MINUTES = 5
    COMMAND_EXECUTING_TIMEOUT_MINUTES = 10
    RATE_LIMIT_SECONDS = 30
    
    @staticmethod
    def cleanup_stuck_commands(db: Session) -> Dict[str, int]:
        """
        Mark stuck commands as failed
        Returns count of commands cleaned up
        """
        now = datetime.now(timezone.utc)
        
        pending_timeout = now - timedelta(minutes=CommandService.COMMAND_TIMEOUT_MINUTES)
        executing_timeout = now - timedelta(minutes=CommandService.COMMAND_EXECUTING_TIMEOUT_MINUTES)
        
        pending_stuck = db.query(DeviceRemoteCommand).filter(
            DeviceRemoteCommand.status == CommandStatus.PENDING,
            DeviceRemoteCommand.issued_at < pending_timeout
        ).all()
        
        executing_stuck = db.query(DeviceRemoteCommand).filter(
            DeviceRemoteCommand.status == CommandStatus.EXECUTING,
            DeviceRemoteCommand.issued_at < executing_timeout
        ).all()
        
        pending_count = 0
        for cmd in pending_stuck:
            cmd.status = CommandStatus.FAILED
            cmd.error_message = f"Command timed out after {CommandService.COMMAND_TIMEOUT_MINUTES} minutes (never delivered)"
            cmd.executed_at = now
            pending_count += 1
        
        executing_count = 0
        for cmd in executing_stuck:
            cmd.status = CommandStatus.FAILED
            cmd.error_message = f"Command execution timed out after {CommandService.COMMAND_EXECUTING_TIMEOUT_MINUTES} minutes"
            cmd.executed_at = now
            executing_count += 1
        
        if pending_count > 0 or executing_count > 0:
            db.commit()
            logger.info(f"Cleaned up {pending_count} pending and {executing_count} executing stuck commands")
        
        return {
            "pending_timeout": pending_count,
            "executing_timeout": executing_count,
            "total": pending_count + executing_count
        }
    
    @staticmethod
    def check_rate_limit(db: Session, device_id: int, command_type: str) -> Optional[str]:
        """
        Check if a command can be issued based on rate limiting
        Returns error message if rate limited, None if OK
        """
        now = datetime.now(timezone.utc)
        rate_limit_threshold = now - timedelta(seconds=CommandService.RATE_LIMIT_SECONDS)
        
        recent_command = db.query(DeviceRemoteCommand).filter(
            DeviceRemoteCommand.device_id == device_id,
            DeviceRemoteCommand.command_type == command_type,
            DeviceRemoteCommand.issued_at > rate_limit_threshold
        ).first()
        
        if recent_command:
            seconds_remaining = int((recent_command.issued_at + timedelta(seconds=CommandService.RATE_LIMIT_SECONDS) - now).total_seconds())
            return f"Rate limit exceeded. Please wait {seconds_remaining} seconds before issuing another {command_type} command."
        
        return None
    
    @staticmethod
    def deduplicate_pending_commands(db: Session, device_id: int, command_type: str) -> int:
        """
        Cancel duplicate pending commands of the same type for a device
        Returns count of cancelled commands
        """
        pending_commands = db.query(DeviceRemoteCommand).filter(
            DeviceRemoteCommand.device_id == device_id,
            DeviceRemoteCommand.command_type == command_type,
            DeviceRemoteCommand.status == CommandStatus.PENDING
        ).all()
        
        if len(pending_commands) <= 1:
            return 0
        
        cancelled_count = 0
        for cmd in pending_commands[:-1]:
            cmd.status = CommandStatus.CANCELLED
            cmd.error_message = "Cancelled due to newer command of same type"
            cmd.executed_at = datetime.now(timezone.utc)
            cancelled_count += 1
        
        if cancelled_count > 0:
            db.commit()
            logger.info(f"Cancelled {cancelled_count} duplicate {command_type} commands for device {device_id}")
        
        return cancelled_count
    
    @staticmethod
    def has_pending_command(db: Session, device_id: int) -> bool:
        """
        Check if device has any pending or executing command
        """
        pending = db.query(DeviceRemoteCommand).filter(
            DeviceRemoteCommand.device_id == device_id,
            or_(
                DeviceRemoteCommand.status == CommandStatus.PENDING,
                DeviceRemoteCommand.status == CommandStatus.EXECUTING
            )
        ).first()
        
        return pending is not None
    
    @staticmethod
    def get_command_statistics(db: Session, device_id: Optional[int] = None, hours: int = 24) -> Dict[str, Any]:
        """
        Get command execution statistics
        """
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=hours)
        
        query = db.query(DeviceRemoteCommand).filter(
            DeviceRemoteCommand.issued_at > since
        )
        
        if device_id:
            query = query.filter(DeviceRemoteCommand.device_id == device_id)
        
        commands = query.all()
        
        total = len(commands)
        completed = sum(1 for cmd in commands if cmd.status == CommandStatus.COMPLETED)
        failed = sum(1 for cmd in commands if cmd.status == CommandStatus.FAILED)
        pending = sum(1 for cmd in commands if cmd.status == CommandStatus.PENDING)
        executing = sum(1 for cmd in commands if cmd.status == CommandStatus.EXECUTING)
        cancelled = sum(1 for cmd in commands if cmd.status == CommandStatus.CANCELLED)
        
        avg_execution_time = None
        if completed > 0:
            execution_times = [
                (cmd.executed_at - cmd.issued_at).total_seconds()
                for cmd in commands
                if cmd.status == CommandStatus.COMPLETED and cmd.executed_at
            ]
            if execution_times:
                avg_execution_time = sum(execution_times) / len(execution_times)
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "executing": executing,
            "cancelled": cancelled,
            "success_rate": (completed / total * 100) if total > 0 else 0,
            "avg_execution_time_seconds": avg_execution_time
        }
