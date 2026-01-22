"""
Model Analytics for YamiBot

This module tracks model performance, usage statistics, and metrics
for all AI models used by the bot.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

from .utils.logger import setup_logging

logger = setup_logging(__name__)


class ModelAnalytics:
    """
    Tracks model performance and usage statistics
    """
    
    def __init__(self):
        """Initialize the analytics tracker"""
        # Request tracking: {(provider, model): {stats}}
        self.model_stats: Dict[tuple, Dict[str, any]] = defaultdict(lambda: {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
            "min_response_time": float('inf'),
            "max_response_time": 0.0,
            "last_used": None,
            "intent_breakdown": defaultdict(int)
        })
        
        # User usage: {user_id: {(provider, model): count}}
        self.user_usage: Dict[int, Dict[tuple, int]] = defaultdict(lambda: defaultdict(int))
        
        # Intent tracking: {intent: {(provider, model): count}}
        self.intent_usage: Dict[str, Dict[tuple, int]] = defaultdict(lambda: defaultdict(int))
        
        # Error tracking: {(provider, model): {error_type: count}}
        self.error_counts: Dict[tuple, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Timestamp for cleanup
        self.start_time = datetime.utcnow()
        
        logger.info("ModelAnalytics initialized")
    
    def track_response(
        self,
        provider: str,
        model: str,
        intent: str,
        response_time: float,
        success: bool,
        user_id: Optional[int] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Track a model response
        
        Args:
            provider: Provider name
            model: Model name
            intent: Detected intent
            response_time: Response time in seconds
            success: Whether the request was successful
            user_id: Optional user ID who made the request
            error: Optional error message if failed
        """
        model_key = (provider.lower(), model.lower())
        stats = self.model_stats[model_key]
        
        # Update basic stats
        stats["total_requests"] += 1
        stats["last_used"] = datetime.utcnow()
        stats["intent_breakdown"][intent] += 1
        
        if success:
            stats["successful_requests"] += 1
            # Update response time stats
            stats["total_response_time"] += response_time
            stats["min_response_time"] = min(stats["min_response_time"], response_time)
            stats["max_response_time"] = max(stats["max_response_time"], response_time)
        else:
            stats["failed_requests"] += 1
            # Track error type
            if error:
                error_type = error.split(":")[0].strip()  # Extract error type
                self.error_counts[model_key][error_type] += 1
        
        # Track user usage
        if user_id:
            self.user_usage[user_id][model_key] += 1
        
        # Track intent usage
        self.intent_usage[intent][model_key] += 1
        
        logger.debug(
            f"Tracked response: {provider}/{model} "
            f"(success={success}, time={response_time:.3f}s, intent={intent})"
        )
    
    def get_model_stats(self, provider: str, model: str) -> Dict[str, any]:
        """
        Get statistics for a specific model
        
        Args:
            provider: Provider name
            model: Model name
            
        Returns:
            Dictionary with model statistics
        """
        model_key = (provider.lower(), model.lower())
        stats = self.model_stats.get(model_key)
        
        if not stats or stats["total_requests"] == 0:
            return {
                "provider": provider,
                "model": model,
                "total_requests": 0,
                "success_rate": 0.0,
                "avg_response_time": 0.0
            }
        
        total = stats["total_requests"]
        successful = stats["successful_requests"]
        
        return {
            "provider": provider,
            "model": model,
            "total_requests": total,
            "successful_requests": successful,
            "failed_requests": stats["failed_requests"],
            "success_rate": (successful / total) * 100,
            "avg_response_time": stats["total_response_time"] / successful if successful > 0 else 0.0,
            "min_response_time": stats["min_response_time"] if stats["min_response_time"] != float('inf') else 0.0,
            "max_response_time": stats["max_response_time"],
            "last_used": stats["last_used"].isoformat() if stats["last_used"] else None,
            "intent_breakdown": dict(stats["intent_breakdown"])
        }
    
    def get_top_models(
        self,
        limit: int = 10,
        by: str = "usage"
    ) -> List[Dict[str, any]]:
        """
        Get top models ranked by a metric
        
        Args:
            limit: Maximum number of models to return
            by: Ranking metric ("usage", "success_rate", "speed")
            
        Returns:
            List of model statistics sorted by the metric
        """
        models = []
        
        for (provider, model), stats in self.model_stats.items():
            if stats["total_requests"] == 0:
                continue
            
            model_info = self.get_model_stats(provider, model)
            models.append(model_info)
        
        if by == "usage":
            models.sort(key=lambda x: x["total_requests"], reverse=True)
        elif by == "success_rate":
            models.sort(key=lambda x: x["success_rate"], reverse=True)
        elif by == "speed":
            models.sort(key=lambda x: x["avg_response_time"] if x["avg_response_time"] > 0 else float('inf'))
        else:
            models.sort(key=lambda x: x["total_requests"], reverse=True)
        
        return models[:limit]
    
    def get_intent_model_performance(self, intent: str) -> Dict[str, any]:
        """
        Get model performance for a specific intent
        
        Args:
            intent: Intent type to analyze
            
        Returns:
            Dictionary with intent-specific model performance
        """
        if intent not in self.intent_usage:
            return {"intent": intent, "models": []}
        
        intent_models = []
        intent_total = sum(self.intent_usage[intent].values())
        
        for (provider, model), count in self.intent_usage[intent].items():
            stats = self.get_model_stats(provider, model)
            stats["usage_percentage"] = (count / intent_total * 100) if intent_total > 0 else 0
            intent_models.append(stats)
        
        # Sort by usage
        intent_models.sort(key=lambda x: x["total_requests"], reverse=True)
        
        return {
            "intent": intent,
            "total_requests": intent_total,
            "models": intent_models
        }
    
    def get_user_stats(self, user_id: int) -> Dict[str, any]:
        """
        Get statistics for a specific user
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary with user-specific statistics
        """
        if user_id not in self.user_usage:
            return {
                "user_id": user_id,
                "total_requests": 0,
                "models_used": []
            }
        
        user_models = []
        user_total = sum(self.user_usage[user_id].values())
        
        for (provider, model), count in self.user_usage[user_id].items():
            stats = self.get_model_stats(provider, model)
            stats["usage_count"] = count
            stats["usage_percentage"] = (count / user_total * 100) if user_total > 0 else 0
            user_models.append(stats)
        
        # Sort by usage
        user_models.sort(key=lambda x: x["usage_count"], reverse=True)
        
        return {
            "user_id": user_id,
            "total_requests": user_total,
            "models_used": user_models
        }
    
    def export_stats(self) -> Dict[str, any]:
        """
        Export all statistics for logging or monitoring
        
        Returns:
            Dictionary with all analytics data
        """
        total_requests = sum(
            stats["total_requests"] for stats in self.model_stats.values()
        )
        total_successful = sum(
            stats["successful_requests"] for stats in self.model_stats.values()
        )
        total_failed = sum(
            stats["failed_requests"] for stats in self.model_stats.values()
        )
        
        return {
            "summary": {
                "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
                "total_requests": total_requests,
                "total_successful": total_successful,
                "total_failed": total_failed,
                "overall_success_rate": (total_successful / total_requests * 100) if total_requests > 0 else 0.0,
                "unique_models_tracked": len(self.model_stats),
                "unique_users": len(self.user_usage)
            },
            "top_models": self.get_top_models(limit=5, by="usage"),
            "intent_breakdown": {
                intent: {
                    "total_requests": sum(usage.values()),
                    "models_count": len(usage)
                }
                for intent, usage in self.intent_usage.items()
            }
        }
    
    def get_error_summary(self, provider: Optional[str] = None, model: Optional[str] = None) -> List[Dict[str, any]]:
        """
        Get error summary for models
        
        Args:
            provider: Optional provider filter
            model: Optional model filter
            
        Returns:
            List of error summaries
        """
        errors = []
        
        for (prov, mod), error_counts in self.error_counts.items():
            if provider and prov != provider.lower():
                continue
            if model and mod != model.lower():
                continue
            
            for error_type, count in error_counts.items():
                errors.append({
                    "provider": prov,
                    "model": mod,
                    "error_type": error_type,
                    "count": count
                })
        
        # Sort by count descending
        errors.sort(key=lambda x: x["count"], reverse=True)
        
        return errors
    
    async def start_periodic_logging(self, interval_seconds: int = 300) -> None:
        """
        Start a background task to periodically log analytics
        
        Args:
            interval_seconds: Interval between logging runs
        """
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                stats = self.export_stats()
                
                logger.info(
                    f"Model Analytics - Requests: {stats['summary']['total_requests']} "
                    f"(Success: {stats['summary']['overall_success_rate']:.1f}%), "
                    f"Models: {stats['summary']['unique_models_tracked']}, "
                    f"Users: {stats['summary']['unique_users']}"
                )
                
            except Exception as e:
                logger.error(f"Error in periodic analytics logging: {e}", exc_info=True)
    
    def reset_stats(self, provider: Optional[str] = None, model: Optional[str] = None) -> int:
        """
        Reset statistics for models
        
        Args:
            provider: Optional provider filter
            model: Optional model filter
            
        Returns:
            Number of model stats reset
        """
        count = 0
        
        keys_to_reset = []
        for (prov, mod) in self.model_stats.keys():
            if provider and prov != provider.lower():
                continue
            if model and mod != model.lower():
                continue
            keys_to_reset.append((prov, mod))
        
        for key in keys_to_reset:
            del self.model_stats[key]
            if key in self.error_counts:
                del self.error_counts[key]
            count += 1
        
        logger.info(f"Reset stats for {count} models")
        return count
