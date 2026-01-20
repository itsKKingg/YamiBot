"""
Rate Limiter for YamiBot

This module tracks API usage and enforces rate limits for each provider
to prevent exceeding quotas and ensure fair usage across providers.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncio

from .utils.logger import setup_logging

logger = setup_logging(__name__)

class RateLimiter:
    """
    Tracks and enforces rate limits for AI providers
    """
    
    def __init__(self):
        """
        Initialize rate limiter with empty tracking dictionaries
        """
        # Track daily requests: {provider_name: {date: count}}
        self.daily_requests: Dict[str, Dict[str, int]] = {}
        
        # Track RPS limits: {provider_name: [(timestamp, count)]}
        self.rps_tracking: Dict[str, list] = {}
        
        # Provider-specific limits
        self.provider_limits = {
            "groq": {
                "daily": 14400,
                "rps": None  # No RPS limit for Groq
            },
            "cerebras": {
                "daily": 14400,
                "rps": None  # No RPS limit for Cerebras
            },
            "google": {
                "daily": 1000,
                "rps": None  # No RPS limit for Google
            },
            "openrouter": {
                "daily": None,  # No daily limit for OpenRouter
                "rps": None  # No RPS limit for OpenRouter
            },
            "mistral": {
                "daily": None,  # No daily limit for Mistral
                "rps": 1  # 1 request per second limit
            }
        }
        
        # Last reset time for daily quotas
        self.last_reset = self._get_midnight_utc()
    
    def _get_midnight_utc(self) -> datetime:
        """
        Get the current UTC midnight timestamp
        
        Returns:
            datetime object for UTC midnight
        """
        now = datetime.utcnow()
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def _get_current_date_key(self) -> str:
        """
        Get the current date as a string key for tracking
        
        Returns:
            String representation of current date (YYYY-MM-DD)
        """
        return datetime.utcnow().strftime("%Y-%m-%d")
    
    def _check_and_reset_daily_quotas(self) -> None:
        """
        Check if daily quotas need to be reset (at midnight UTC)
        """
        now = datetime.utcnow()
        current_midnight = self._get_midnight_utc()
        
        # If we've passed midnight UTC, reset quotas
        if current_midnight > self.last_reset:
            logger.info("Resetting daily quotas at midnight UTC")
            self.daily_requests = {}
            self.last_reset = current_midnight
    
    async def check_limit(self, provider_name: str) -> bool:
        """
        Check if a request can be made to the specified provider
        without exceeding rate limits
        
        Args:
            provider_name: Name of the provider to check
            
        Returns:
            True if request is allowed, False if rate limited
        """
        self._check_and_reset_daily_quotas()
        
        # Get limits for this provider
        limits = self.provider_limits.get(provider_name)
        if not limits:
            logger.warning(f"No rate limits configured for provider: {provider_name}")
            return True
        
        # Check daily limit
        if limits["daily"] is not None:
            if not self._check_daily_limit(provider_name, limits["daily"]):
                return False
        
        # Check RPS limit
        if limits["rps"] is not None:
            if not self._check_rps_limit(provider_name, limits["rps"]):
                return False
        
        return True
    
    def _check_daily_limit(self, provider_name: str, daily_limit: int) -> bool:
        """
        Check daily request limit for a provider
        
        Args:
            provider_name: Name of the provider
            daily_limit: Maximum allowed requests per day
            
        Returns:
            True if under limit, False if rate limited
        """
        date_key = self._get_current_date_key()
        
        # Initialize provider tracking if not exists
        if provider_name not in self.daily_requests:
            self.daily_requests[provider_name] = {}
        
        # Initialize date tracking if not exists
        if date_key not in self.daily_requests[provider_name]:
            self.daily_requests[provider_name][date_key] = 0
        
        current_count = self.daily_requests[provider_name][date_key]
        
        if current_count >= daily_limit:
            logger.warning(f"Daily limit reached for {provider_name}: {current_count}/{daily_limit}")
            return False
        
        return True
    
    def _check_rps_limit(self, provider_name: str, rps_limit: int) -> bool:
        """
        Check requests per second limit for a provider
        
        Args:
            provider_name: Name of the provider
            rps_limit: Maximum requests per second allowed
            
        Returns:
            True if under limit, False if rate limited
        """
        current_time = time.time()
        
        # Initialize provider tracking if not exists
        if provider_name not in self.rps_tracking:
            self.rps_tracking[provider_name] = []
        
        # Clean up old entries (older than 1 second)
        self.rps_tracking[provider_name] = [
            ts for ts in self.rps_tracking[provider_name] 
            if current_time - ts < 1.0
        ]
        
        # Check if we're at the limit
        if len(self.rps_tracking[provider_name]) >= rps_limit:
            logger.warning(f"RPS limit reached for {provider_name}: {rps_limit} req/sec")
            return False
        
        # Add current request
        self.rps_tracking[provider_name].append(current_time)
        return True
    
    def record_request(self, provider_name: str) -> None:
        """
        Record a successful request for tracking purposes
        
        Args:
            provider_name: Name of the provider that handled the request
        """
        self._check_and_reset_daily_quotas()
        
        # Only track daily requests for providers with daily limits
        limits = self.provider_limits.get(provider_name)
        if limits and limits["daily"] is not None:
            date_key = self._get_current_date_key()
            
            if provider_name not in self.daily_requests:
                self.daily_requests[provider_name] = {}
            
            if date_key not in self.daily_requests[provider_name]:
                self.daily_requests[provider_name][date_key] = 0
            
            self.daily_requests[provider_name][date_key] += 1
            
            logger.debug(f"Recorded request for {provider_name}. Daily count: {self.daily_requests[provider_name][date_key]}/{limits['daily']}")
    
    def get_remaining_quota(self, provider_name: str) -> Dict[str, Any]:
        """
        Get remaining quota information for a provider
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Dictionary with remaining quota information
        """
        self._check_and_reset_daily_quotas()
        
        limits = self.provider_limits.get(provider_name)
        if not limits:
            return {"error": "Provider not found"}
        
        result = {}
        
        # Daily quota info
        if limits["daily"] is not None:
            date_key = self._get_current_date_key()
            current_count = 0
            
            if provider_name in self.daily_requests and date_key in self.daily_requests[provider_name]:
                current_count = self.daily_requests[provider_name][date_key]
            
            result["daily"] = {
                "limit": limits["daily"],
                "used": current_count,
                "remaining": max(0, limits["daily"] - current_count)
            }
        
        # RPS quota info
        if limits["rps"] is not None:
            result["rps"] = {
                "limit": limits["rps"],
                "current": len(self.rps_tracking.get(provider_name, []))
            }
        
        return result
    
    def get_all_quotas(self) -> Dict[str, Any]:
        """
        Get quota information for all providers
        
        Returns:
            Dictionary with quota information for all providers
        """
        self._check_and_reset_daily_quotas()
        
        result = {}
        for provider_name in self.provider_limits:
            result[provider_name] = self.get_remaining_quota(provider_name)
        
        return result
    
    async def start_monitoring(self) -> None:
        """
        Start background monitoring for rate limits
        This can be extended to include periodic checks and alerts
        """
        logger.info("Starting rate limit monitoring")
        
        # For now, just log the current state
        while True:
            await asyncio.sleep(3600)  # Check hourly
            quotas = self.get_all_quotas()
            logger.info("Current rate limit status:")
            for provider, quota_info in quotas.items():
                if "daily" in quota_info:
                    logger.info(f"  {provider}: {quota_info['daily']['used']}/{quota_info['daily']['limit']} daily requests")
                if "rps" in quota_info:
                    logger.info(f"  {provider}: {quota_info['rps']['current']}/{quota_info['rps']['limit']} RPS")