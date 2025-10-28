from fastapi import WebSocket
from typing import Dict, Set
import json
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections for real-time device notifications"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.device_subscriptions: Dict[int, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, device_id: str):
        """Accept and store a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[device_id] = websocket
        logger.info(f"Device {device_id} connected via WebSocket")
    
    def disconnect(self, device_id: str):
        """Remove a WebSocket connection"""
        if device_id in self.active_connections:
            del self.active_connections[device_id]
            logger.info(f"Device {device_id} disconnected from WebSocket")
        
        for course_devices in self.device_subscriptions.values():
            course_devices.discard(device_id)
    
    def subscribe_to_course(self, device_id: str, course_id: int):
        """Subscribe a device to course-level notifications"""
        if course_id not in self.device_subscriptions:
            self.device_subscriptions[course_id] = set()
        self.device_subscriptions[course_id].add(device_id)
        logger.info(f"Device {device_id} subscribed to course {course_id} notifications")
    
    async def send_to_device(self, device_id: str, message: dict):
        """Send a message to a specific device"""
        if device_id in self.active_connections:
            try:
                await self.active_connections[device_id].send_json(message)
                logger.debug(f"Sent message to device {device_id}: {message.get('type')}")
            except Exception as e:
                logger.error(f"Error sending message to device {device_id}: {e}")
                self.disconnect(device_id)
    
    async def broadcast_to_course(self, course_id: int, message: dict):
        """Broadcast a message to all devices in a course"""
        if course_id in self.device_subscriptions:
            device_ids = list(self.device_subscriptions[course_id])
            logger.info(f"Broadcasting to {len(device_ids)} devices in course {course_id}")
            for device_id in device_ids:
                await self.send_to_device(device_id, message)
    
    async def notify_campaign_start(self, course_id: int, campaign_id: int, campaign_name: str):
        """Notify devices that a campaign has started"""
        message = {
            "type": "campaign_start",
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "action": "refresh_playlist"
        }
        await self.broadcast_to_course(course_id, message)
    
    async def notify_campaign_end(self, course_id: int, campaign_id: int, campaign_name: str):
        """Notify devices that a campaign has ended"""
        message = {
            "type": "campaign_end",
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "action": "refresh_playlist"
        }
        await self.broadcast_to_course(course_id, message)
    
    async def notify_notice_start(self, device_id: str, notice_id: int, notice_title: str):
        """Notify a specific device that a notice has started"""
        message = {
            "type": "notice_start",
            "notice_id": notice_id,
            "notice_title": notice_title,
            "priority": "high",
            "action": "refresh_playlist"
        }
        await self.send_to_device(device_id, message)
    
    async def notify_notice_end(self, device_id: str, notice_id: int, notice_title: str):
        """Notify a specific device that a notice has ended"""
        message = {
            "type": "notice_end",
            "notice_id": notice_id,
            "notice_title": notice_title,
            "action": "refresh_playlist"
        }
        await self.send_to_device(device_id, message)

websocket_manager = WebSocketManager()
