#!/usr/bin/env python3
"""
Uptime Tracker for E-ink Device Client
Tracks device online/offline status per minute and sends 5-minute windows to backend
"""

import os
import json
import time
import logging
import threading
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class UptimeTracker:
    """
    Background thread that tracks device uptime/downtime per minute.
    Aggregates into 5-minute windows and sends to backend with idempotent retry.
    """
    
    def __init__(self, config: Dict[str, Any], api_base_url: str, device_id: str):
        self.config = config
        self.api_base_url = api_base_url
        self.device_id = device_id
        self.running = False
        self.thread = None
        
        self.state_file = Path('/var/lib/gad/uptime_state.json')
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.current_window_start = None
        self.current_window_minutes = []
        self.pending_windows = []
        
        self.last_successful_api_call = None
        self.last_sync_count = 0
        self.last_error_count = 0
        
        self._load_state()
    
    def _load_state(self):
        """Load persisted state from disk"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    
                self.last_successful_api_call = datetime.fromisoformat(state.get('last_successful_api_call', datetime.now(timezone.utc).isoformat()))
                self.pending_windows = state.get('pending_windows', [])
                
                last_heartbeat = datetime.fromisoformat(state.get('last_heartbeat', datetime.now(timezone.utc).isoformat()))
                now = datetime.now(timezone.utc)
                gap_minutes = int((now - last_heartbeat).total_seconds() / 60)
                
                if gap_minutes > 0:
                    logger.info(f"Detected {gap_minutes} minute gap since last heartbeat - attributing to downtime")
                    self._create_gap_windows(last_heartbeat, now, gap_minutes)
                
                logger.info(f"Loaded uptime state: {len(self.pending_windows)} pending windows")
        except Exception as e:
            logger.error(f"Failed to load uptime state: {e}")
            self.last_successful_api_call = datetime.now(timezone.utc)
    
    def _save_state(self):
        """Persist state to disk"""
        try:
            state = {
                'last_heartbeat': datetime.now(timezone.utc).isoformat(),
                'last_successful_api_call': self.last_successful_api_call.isoformat() if self.last_successful_api_call else None,
                'pending_windows': self.pending_windows
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save uptime state: {e}")
    
    def _create_gap_windows(self, start_time: datetime, end_time: datetime, gap_minutes: int):
        """Create windows for a gap period (all downtime)"""
        current = start_time
        while current < end_time:
            window_end = min(current + timedelta(minutes=5), end_time)
            minutes_in_window = int((window_end - current).total_seconds() / 60)
            
            if minutes_in_window > 0:
                self.pending_windows.append({
                    'window_start': current.isoformat(),
                    'window_end': window_end.isoformat(),
                    'uptime_minutes': 0,
                    'downtime_minutes': minutes_in_window,
                    'total_syncs': 0,
                    'error_count': 0
                })
            
            current = window_end
    
    def start(self):
        """Start the uptime tracking thread"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()
        logger.info("Uptime tracker started")
    
    def stop(self):
        """Stop the uptime tracking thread and flush pending data"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        self._finalize_current_window()
        self._flush_pending_windows()
        self._save_state()
        logger.info("Uptime tracker stopped")
    
    def record_successful_api_call(self):
        """Record that an API call succeeded (device is online)"""
        self.last_successful_api_call = datetime.now(timezone.utc)
        self.last_sync_count += 1
    
    def record_api_error(self):
        """Record that an API call failed"""
        self.last_error_count += 1
    
    def _is_device_online(self) -> bool:
        """Determine if device is currently online"""
        if not self.last_successful_api_call:
            return False
        
        grace_period = timedelta(minutes=2)
        return (datetime.now(timezone.utc) - self.last_successful_api_call) < grace_period
    
    def _tracking_loop(self):
        """Main tracking loop - runs every minute"""
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                seconds_until_next_minute = 60 - now.second
                time.sleep(seconds_until_next_minute)
                
                self._record_minute()
                
                if now.minute % 5 == 0:
                    self._save_state()
                
            except Exception as e:
                logger.error(f"Error in uptime tracking loop: {e}")
                time.sleep(60)
    
    def _record_minute(self):
        """Record uptime/downtime for the current minute"""
        now = datetime.now(timezone.utc)
        
        if self.current_window_start is None or now >= self.current_window_start + timedelta(minutes=5):
            self._finalize_current_window()
            minute = (now.minute // 5) * 5
            self.current_window_start = now.replace(minute=minute, second=0, microsecond=0)
            self.current_window_minutes = []
        
        is_online = self._is_device_online()
        syncs_this_minute = self.last_sync_count
        errors_this_minute = self.last_error_count
        
        self.current_window_minutes.append({
            'timestamp': now.isoformat(),
            'is_online': is_online,
            'syncs': syncs_this_minute,
            'errors': errors_this_minute
        })
        
        self.last_sync_count = 0
        self.last_error_count = 0
        
        logger.debug(f"Recorded minute: online={is_online}, syncs={syncs_this_minute}, errors={errors_this_minute}")
    
    def _finalize_current_window(self):
        """Finalize the current 5-minute window and add to pending"""
        if not self.current_window_start or not self.current_window_minutes:
            return
        
        uptime_minutes = sum(1 for m in self.current_window_minutes if m['is_online'])
        downtime_minutes = len(self.current_window_minutes) - uptime_minutes
        total_syncs = sum(m['syncs'] for m in self.current_window_minutes)
        total_errors = sum(m['errors'] for m in self.current_window_minutes)
        
        window_end = self.current_window_start + timedelta(minutes=len(self.current_window_minutes))
        
        window = {
            'window_start': self.current_window_start.isoformat(),
            'window_end': window_end.isoformat(),
            'uptime_minutes': uptime_minutes,
            'downtime_minutes': downtime_minutes,
            'total_syncs': total_syncs,
            'error_count': total_errors
        }
        
        self.pending_windows.append(window)
        logger.info(f"Finalized window: {uptime_minutes}m up, {downtime_minutes}m down, {total_syncs} syncs, {total_errors} errors")
        
        if len(self.pending_windows) >= 3:
            self._flush_pending_windows()
    
    def _flush_pending_windows(self):
        """Send pending windows to backend"""
        if not self.pending_windows:
            return
        
        try:
            url = f"{self.api_base_url}/api/device-uptime/ingest"
            payload = {'windows': self.pending_windows}
            params = {'device_external_id': self.device_id}
            
            response = requests.post(url, json=payload, params=params, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                accepted = result.get('accepted', 0)
                duplicates = result.get('duplicates', 0)
                errors = result.get('errors', 0)
                
                logger.info(f"Flushed {len(self.pending_windows)} windows: {accepted} accepted, {duplicates} duplicates, {errors} errors")
                
                self.pending_windows = []
                self._save_state()
            else:
                logger.error(f"Failed to flush uptime windows: HTTP {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error flushing uptime windows: {e}")
