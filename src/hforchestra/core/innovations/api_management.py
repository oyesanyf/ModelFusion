"""
API Management System
Handles rate limiting, quotas, and fallback strategies for various APIs.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class APIQuota:
    """Represents API quota information."""
    limit: int
    remaining: int
    reset_time: datetime
    
@dataclass
class APIConfig:
    """API configuration and limits."""
    name: str
    rate_limit: int  # requests per minute
    quota_limit: int  # total requests per day
    fallback_model: Optional[str] = None
    retry_delay: int = 60  # seconds

class APIManager:
    """Manages API access, rate limiting, and fallbacks."""
    
    def __init__(self):
        self.quotas: Dict[str, APIQuota] = {}
        self.request_timestamps: Dict[str, list] = {}
        self.configs: Dict[str, APIConfig] = {
            'gemini-2.5-flash': APIConfig(
                name='gemini-2.5-flash',
                rate_limit=10,
                quota_limit=60,
                fallback_model='gemini-2.5-pro',
                retry_delay=30
            ),
            'gemini-2.5-pro': APIConfig(
                name='gemini-2.5-pro',
                rate_limit=6,
                quota_limit=60,
                fallback_model=None,
                retry_delay=60
            )
        }
        
    async def execute_with_fallback(self, 
                                  api_call: Callable,
                                  model: str,
                                  *args,
                                  **kwargs) -> Any:
        """Execute API call with rate limiting and fallback handling."""
        try:
            await self._check_rate_limit(model)
            return await api_call(*args, **kwargs)
            
        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                logger.warning(f"Rate limit exceeded for {model}, attempting fallback")
                fallback_model = self.configs[model].fallback_model
                
                if fallback_model:
                    logger.info(f"Falling back to {fallback_model}")
                    kwargs['model'] = fallback_model
                    await asyncio.sleep(self.configs[model].retry_delay)
                    return await self.execute_with_fallback(api_call, fallback_model, *args, **kwargs)
                else:
                    retry_delay = self.configs[model].retry_delay
                    logger.info(f"No fallback available for {model}, retrying in {retry_delay}s")
                    await asyncio.sleep(retry_delay)
                    return await self.execute_with_fallback(api_call, model, *args, **kwargs)
            else:
                raise
                
    async def _check_rate_limit(self, model: str) -> None:
        """Check and enforce rate limits."""
        now = datetime.now()
        config = self.configs[model]
        
        # Initialize timestamps if needed
        if model not in self.request_timestamps:
            self.request_timestamps[model] = []
            
        # Clean old timestamps
        self.request_timestamps[model] = [
            ts for ts in self.request_timestamps[model]
            if now - ts < timedelta(minutes=1)
        ]
        
        # Check rate limit
        if len(self.request_timestamps[model]) >= config.rate_limit:
            oldest = min(self.request_timestamps[model])
            wait_time = 60 - (now - oldest).seconds
            if wait_time > 0:
                logger.info(f"Rate limit reached for {model}, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
                
        # Record request
        self.request_timestamps[model].append(now)
        
    def update_quota(self, model: str, remaining: int, reset_time: datetime) -> None:
        """Update quota information for an API."""
        self.quotas[model] = APIQuota(
            limit=self.configs[model].quota_limit,
            remaining=remaining,
            reset_time=reset_time
        )
        
    def get_quota(self, model: str) -> Optional[APIQuota]:
        """Get current quota information for an API."""
        return self.quotas.get(model)
        
    def is_rate_limited(self, model: str) -> bool:
        """Check if model is currently rate limited."""
        if model not in self.request_timestamps:
            return False
            
        now = datetime.now()
        recent_requests = len([
            ts for ts in self.request_timestamps[model]
            if now - ts < timedelta(minutes=1)
        ])
        
        return recent_requests >= self.configs[model].rate_limit
