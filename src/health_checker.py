"""
Health Checker for YamiBot Providers

This module provides health checking functionality to monitor provider status
and automate recovery when providers come back online.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from .providers.base import BaseProvider
from .utils.logger import setup_logging

logger = setup_logging(__name__)

class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"

@dataclass
class HealthCheckResult:
    """Result of a health check"""
    provider_name: str
    status: HealthStatus
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/export"""
        return {
            "provider": self.provider_name,
            "status": self.status.value,
            "response_time": self.response_time,
            "error": self.error_message,
            "timestamp": self.timestamp,
            "is_healthy": self.status == HealthStatus.HEALTHY
        }

class HealthChecker:
    """
    Monitors provider health and manages circuit breaker state transitions
    """
    
    def __init__(self, fallback_manager, circuit_breakers, check_interval: int = 300):
        """
        Initialize health checker
        
        Args:
            fallback_manager: Instance of FallbackManager
            circuit_breakers: Dictionary mapping provider names to CircuitBreaker instances
            check_interval: How often to run health checks (seconds)
        """
        self.fallback_manager = fallback_manager
        self.circuit_breakers = circuit_breakers
        self.check_interval = check_interval
        self.health_check_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Track health check history
        self.check_history: Dict[str, List[HealthCheckResult]] = {}
        
        logger.info(f"HealthChecker initialized with {self.check_interval}s interval")
    
    async def check_provider_health(self, provider_name: str, provider: BaseProvider) -> HealthCheckResult:
        """
        Perform a lightweight health check for a provider
        
        Args:
            provider_name: Name of the provider
            provider: Provider instance to check
            
        Returns:
            HealthCheckResult with status and metadata
        """
        logger.debug(f"Running health check for {provider_name}")
        
        # Skip if provider is not fully initialized
        if not provider or not hasattr(provider, 'query'):
            return HealthCheckResult(
                provider_name=provider_name,
                status=HealthStatus.UNKNOWN,
                error_message="Provider not initialized"
            )
        
        start_time = time.time()
        
        try:
            # Send a lightweight test query
            test_prompt = "health check"
            
            # Use short timeout for health checks
            response = await asyncio.wait_for(
                provider.query(test_prompt, health_check=True),
                timeout=10.0
            )
            
            response_time = time.time() - start_time
            
            # Check if we got a valid response (not None)
            if response and len(response) > 0:
                logger.debug(f"{provider_name} health check passed in {response_time:.2f}s")
                return HealthCheckResult(
                    provider_name=provider_name,
                    status=HealthStatus.HEALTHY,
                    response_time=response_time
                )
            else:
                logger.warning(f"{provider_name} health check returned empty response")
                return HealthCheckResult(
                    provider_name=provider_name,
                    status=HealthStatus.UNHEALTHY,
                    response_time=time.time() - start_time,
                    error_message="Empty response from provider"
                )
                
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            logger.warning(f"{provider_name} health check timed out after {response_time:.2f}s")
            return HealthCheckResult(
                provider_name=provider_name,
                status=HealthStatus.TIMEOUT,
                response_time=response_time,
                error_message="Health check timeout"
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.warning(
                f"{provider_name} health check failed after {response_time:.2f}s: {str(e)}"
            )
            return HealthCheckResult(
                provider_name=provider_name,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                error_message=f"{type(e).__name__}: {str(e)}"
            )
    
    async def run_health_checks(self) -> List[HealthCheckResult]:
        """
        Run health checks for all providers
        
        Returns:
            List of HealthCheckResult objects
        """
        logger.info("Running periodic health checks...")
        
        results = []
        
        # Run health checks for all providers
        for provider_name, provider in self.fallback_manager.providers.items():
            if not provider:  # Skip uninitialized providers
                continue
                
            result = await self.check_provider_health(provider_name, provider)
            results.append(result)
            
            # Add to history
            if provider_name not in self.check_history:
                self.check_history[provider_name] = []
            
            self.check_history[provider_name].append(result)
            
            # Keep only last 10 results
            if len(self.check_history[provider_name]) > 10:
                self.check_history[provider_name] = self.check_history[provider_name][-10:]
            
            # Update circuit breaker if provider recovered
            if provider_name in self.circuit_breakers:
                breaker = self.circuit_breakers[provider_name]
                
                if result.status == HealthStatus.HEALTHY:
                    # Provider responded successfully - reset circuit breaker
                    if breaker.state != CircuitState.CLOSED:
                        old_state = breaker.state
                        breaker.record_success()
                        logger.info(
                            f"{provider_name}: Circuit transitioned from {old_state.value} to CLOSED "
                            f"(health check success)"
                        )
                elif result.status in [HealthStatus.UNHEALTHY, HealthStatus.TIMEOUT]:
                    # Provider is unhealthy - increment failure count
                    if breaker.state == CircuitState.CLOSED:
                        old_count = breaker.failure_count
                        breaker.record_failure()
                        logger.warning(
                            f"{provider_name}: Health check failed. "
                            f"Failure count: {old_count} -> {breaker.failure_count}"
                        )
        
        # Log summary
        healthy_count = sum(1 for r in results if r.status == HealthStatus.HEALTHY)
        logger.info(
            f"Health check complete: {healthy_count}/{len(results)} providers healthy"
        )
        
        return results
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive health summary
        
        Returns:
            Dictionary with health status of all components
        """
        summary = {
            "timestamp": time.time(),
            "providers": {},
            "overall_status": "healthy"
        }
        
        for provider_name in self.fallback_manager.providers.keys():
            if provider_name not in self.circuit_breakers:
                continue
                
            breaker = self.circuit_breakers[provider_name]
            recent_history = self.check_history.get(provider_name, [])
            
            # Count recent healthy/unhealthy checks
            recent_healthy = sum(
                1 for r in recent_history[-3:] 
                if r.status == HealthStatus.HEALTHY
            )
            
            summary["providers"][provider_name] = {
                **breaker.get_status(),
                "recent_health_checks": {
                    "healthy": recent_healthy,
                    "total": min(3, len(recent_history))
                },
                "is_responding": recent_healthy > 0
            }
            
            # Update overall status
            if (breaker.state == CircuitBreaker.CircuitState.OPEN or 
                (not recent_history and breaker.failure_count >= breaker.failure_threshold)):
                summary["overall_status"] = "degraded"
        
        return summary
    
    async def start(self):
        """Start the health check background task"""
        if self.health_check_task is not None and not self.health_check_task.done():
            logger.warning("Health checker is already running")
            return
        
        self._shutdown_event.clear()
        self.health_check_task = asyncio.create_task(self._run_periodic_checks())
        logger.info("Health checker started")
    
    async def stop(self):
        """Stop the health check background task"""
        if self.health_check_task is None or self.health_check_task.done():
            logger.debug("Health checker is not running")
            return
        
        logger.info("Stopping health checker...")
        self._shutdown_event.set()
        
        # Give it a moment to stop gracefully
        try:
            await asyncio.wait_for(self.health_check_task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Health checker did not stop gracefully, cancelling...")
            self.health_check_task.cancel()
        
        logger.info("Health checker stopped")
    
    async def _run_periodic_checks(self):
        """Background task to run periodic health checks"""
        logger.info(f"Starting periodic health checks (every {self.check_interval}s)")
        
        while not self._shutdown_event.is_set():
            try:
                await self.run_health_checks()
                
                # Wait for next interval or shutdown signal
                wait_task = asyncio.create_task(asyncio.sleep(self.check_interval))
                shutdown_task = asyncio.create_task(self._shutdown_event.wait())
                
                # Wait for either the interval to complete or shutdown signal
                done, _ = await asyncio.wait(
                    [wait_task, shutdown_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Clean up tasks
                if wait_task in done:
                    wait_task.result()
                else:
                    wait_task.cancel()
                
                if shutdown_task in done:
                    break
                    
            except asyncio.CancelledError:
                logger.info("Health checker task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health checker: {e}", exc_info=True)
                
                # Continue running even if individual checks fail
                try:
                    await asyncio.sleep(self.check_interval)
                except asyncio.CancelledError:
                    break
        
        logger.info("Health checker background task stopped")