"""
Rate limiting middleware for Golf CMS API
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import redis
import os
from typing import Dict, Optional
import json

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_url: Optional[str] = None):
        super().__init__(app)
        self.redis_client = None
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
            except Exception:
                pass
        
        self.memory_store: Dict[str, Dict] = {}
        
        self.rate_limits = {
            "/auth/login": {"requests": 5, "window": 300},  # 5 requests per 5 minutes
            "/auth/register": {"requests": 3, "window": 3600},  # 3 requests per hour
            "/auth/register-course": {"requests": 2, "window": 3600},  # 2 requests per hour
            "default": {"requests": 100, "window": 60}  # 100 requests per minute
        }
    
    async def dispatch(self, request: Request, call_next):
        if not os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true":
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        path = request.url.path
        
        rate_config = self.rate_limits.get(path, self.rate_limits["default"])
        
        if self._is_rate_limited(client_ip, path, rate_config):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {rate_config['requests']} per {rate_config['window']} seconds"
                }
            )
        
        response = await call_next(request)
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _is_rate_limited(self, client_ip: str, path: str, config: Dict) -> bool:
        """Check if client is rate limited"""
        key = f"rate_limit:{client_ip}:{path}"
        current_time = int(time.time())
        window_start = current_time - config["window"]
        
        if self.redis_client:
            return self._check_redis_rate_limit(key, current_time, window_start, config)
        else:
            return self._check_memory_rate_limit(key, current_time, window_start, config)
    
    def _check_redis_rate_limit(self, key: str, current_time: int, window_start: int, config: Dict) -> bool:
        """Check rate limit using Redis"""
        try:
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(current_time): current_time})
            pipe.expire(key, config["window"])
            results = pipe.execute()
            
            request_count = results[1]
            return request_count >= config["requests"]
        except Exception:
            return self._check_memory_rate_limit(key, current_time, window_start, config)
    
    def _check_memory_rate_limit(self, key: str, current_time: int, window_start: int, config: Dict) -> bool:
        """Check rate limit using in-memory store"""
        if key not in self.memory_store:
            self.memory_store[key] = {"requests": [], "last_cleanup": current_time}
        
        store = self.memory_store[key]
        
        store["requests"] = [req_time for req_time in store["requests"] if req_time > window_start]
        
        if len(store["requests"]) >= config["requests"]:
            return True
        
        store["requests"].append(current_time)
        store["last_cleanup"] = current_time
        
        return False
