from fastapi import Request, Response
from sqlalchemy.orm import Session
from ..database import get_db, AuditLog
from ..auth import get_current_user
import json
from datetime import datetime

class AuditLoggingMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            if request.url.path in ["/healthz", "/docs", "/redoc"] or request.url.path.startswith("/static"):
                await self.app(scope, receive, send)
                return
            
            method = request.method
            path = request.url.path
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            
            user = None
            try:
                if "authorization" in request.headers:
                    pass
            except:
                pass
            
            response_body = b""
            status_code = 200
            
            async def send_wrapper(message):
                nonlocal response_body, status_code
                if message["type"] == "http.response.start":
                    status_code = message["status"]
                elif message["type"] == "http.response.body":
                    response_body += message.get("body", b"")
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
            
            if method in ["POST", "PUT", "DELETE", "PATCH"] and status_code < 400:
                try:
                    db = next(get_db())
                    
                    action = self._determine_action(method, path)
                    resource_type = self._determine_resource_type(path)
                    
                    if action and resource_type:
                        audit_log = AuditLog(
                            user_id=user.id if user else None,
                            action=action,
                            resource_type=resource_type,
                            resource_id=self._extract_resource_id(path),
                            details={
                                "method": method,
                                "path": path,
                                "status_code": status_code
                            },
                            ip_address=ip_address,
                            user_agent=user_agent
                        )
                        db.add(audit_log)
                        db.commit()
                except Exception as e:
                    print(f"Audit logging error: {e}")
                finally:
                    if 'db' in locals():
                        db.close()
        else:
            await self.app(scope, receive, send)
    
    def _determine_action(self, method: str, path: str) -> str:
        if method == "POST":
            return "create"
        elif method == "PUT" or method == "PATCH":
            return "update"
        elif method == "DELETE":
            return "delete"
        return "unknown"
    
    def _determine_resource_type(self, path: str) -> str:
        if "/courses" in path:
            return "course"
        elif "/devices" in path:
            return "device"
        elif "/campaigns" in path:
            return "campaign"
        elif "/notices" in path:
            return "notice"
        elif "/users" in path:
            return "user"
        return "unknown"
    
    def _extract_resource_id(self, path: str) -> str:
        parts = path.split("/")
        for i, part in enumerate(parts):
            if part.isdigit():
                return part
        return None
