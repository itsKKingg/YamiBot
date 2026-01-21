"""
Cache Utility for YamiBot

This module provides a simple in-memory cache system to reduce
duplicate API calls and improve response times.
"""

import time
from typing import Any, Dict, Optional
from collections import OrderedDict

class Cache:
    """
    Simple in-memory cache with TTL support
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize the cache
        
        Args:
            max_size: Maximum number of items to store in cache
        """
        self.max_size = max_size
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_order = OrderedDict()  # Track access order for LRU eviction
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        Set a value in the cache
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time to live in seconds (default: 1 hour)
        """
        # Remove key from access order if it exists
        if key in self.access_order:
            del self.access_order[key]
        
        # Add to cache
        self.cache[key] = {
            "value": value,
            "expires": time.time() + ttl
        }
        
        # Add to access order
        self.access_order[key] = True
        
        # Enforce max size by removing least recently used items
        while len(self.access_order) > self.max_size:
            oldest_key = next(iter(self.access_order))
            del self.cache[oldest_key]
            del self.access_order[oldest_key]
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key not in self.cache:
            return None
        
        cache_item = self.cache[key]
        
        # Check if expired
        if time.time() > cache_item["expires"]:
            del self.cache[key]
            if key in self.access_order:
                del self.access_order[key]
            return None
        
        # Update access order (move to end for LRU)
        if key in self.access_order:
            del self.access_order[key]
        self.access_order[key] = True
        
        return cache_item["value"]
    
    def delete(self, key: str) -> None:
        """
        Delete a value from the cache
        
        Args:
            key: Cache key to delete
        """
        if key in self.cache:
            del self.cache[key]
        if key in self.access_order:
            del self.access_order[key]
    
    def clear(self) -> None:
        """
        Clear the entire cache
        """
        self.cache.clear()
        self.access_order.clear()
    
    def size(self) -> int:
        """
        Get the current cache size
        
        Returns:
            Number of items in cache
        """
        return len(self.cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "size": self.size(),
            "max_size": self.max_size,
            "hit_rate": "N/A"  # Would need tracking for this
        }

# Create global cache instance
cache = Cache(max_size=500)