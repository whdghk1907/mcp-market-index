"""
Caching utilities for MCP Market Index Server
"""
import asyncio
import threading
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with data and expiration"""
    data: Any
    expires: datetime


class MarketDataCache:
    """
    In-memory cache for market data with TTL support
    """
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._max_size = max_size
        self._cleanup_lock = threading.Lock()
        
    async def get_or_fetch(
        self, 
        key: str, 
        fetch_func: Callable[[], Awaitable[Any]], 
        ttl: int = 5
    ) -> Any:
        """
        Get data from cache or fetch if not available/expired
        
        Args:
            key: Cache key
            fetch_func: Async function to fetch data
            ttl: Time to live in seconds
            
        Returns:
            Cached or freshly fetched data
        """
        # Check cache first
        if key in self._cache:
            entry = self._cache[key]
            if entry.expires > datetime.now():
                return entry.data
        
        # Get or create lock for this key
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
            
        async with self._locks[key]:
            # Double-check cache after acquiring lock (race condition prevention)
            if key in self._cache:
                entry = self._cache[key]
                if entry.expires > datetime.now():
                    return entry.data
            
            # Fetch new data
            data = await fetch_func()
            
            # Store in cache
            expires = datetime.now() + timedelta(seconds=ttl)
            self._cache[key] = CacheEntry(data=data, expires=expires)
            
            # Check if we need to cleanup old entries
            if len(self._cache) > self._max_size:
                self._cleanup_old_entries()
            
            return data
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get data from cache without fetching
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        if key in self._cache:
            entry = self._cache[key]
            if entry.expires > datetime.now():
                return entry.data
        return None
    
    def set(self, key: str, data: Any, ttl: int = 5):
        """
        Set data in cache
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Time to live in seconds
        """
        expires = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = CacheEntry(data=data, expires=expires)
        
        # Check if we need to cleanup old entries
        if len(self._cache) > self._max_size:
            self._cleanup_old_entries()
    
    def invalidate(self, key: str = None):
        """
        Invalidate cache entry or all entries
        
        Args:
            key: Cache key to invalidate, or None for all
        """
        if key:
            self._cache.pop(key, None)
            self._locks.pop(key, None)
        else:
            self._cache.clear()
            self._locks.clear()
    
    def cleanup_expired(self):
        """Remove expired entries from cache"""
        with self._cleanup_lock:
            now = datetime.now()
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.expires <= now
            ]
            
            for key in expired_keys:
                self._cache.pop(key, None)
                self._locks.pop(key, None)
            
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _cleanup_old_entries(self):
        """Remove old entries to keep cache size under limit"""
        with self._cleanup_lock:
            if len(self._cache) <= self._max_size:
                return
            
            # First remove expired entries
            self.cleanup_expired()
            
            # If still over limit, remove oldest entries
            if len(self._cache) > self._max_size:
                # Sort by expiration time and remove oldest
                sorted_items = sorted(
                    self._cache.items(), 
                    key=lambda x: x[1].expires
                )
                
                num_to_remove = len(self._cache) - self._max_size
                for key, _ in sorted_items[:num_to_remove]:
                    self._cache.pop(key, None)
                    self._locks.pop(key, None)
                
                logger.debug(f"Removed {num_to_remove} old cache entries to maintain size limit")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache stats
        """
        now = datetime.now()
        total_keys = len(self._cache)
        valid_keys = sum(
            1 for entry in self._cache.values()
            if entry.expires > now
        )
        expired_keys = total_keys - valid_keys
        
        return {
            "total_keys": total_keys,
            "valid_keys": valid_keys,
            "expired_keys": expired_keys,
            "hit_rate": 0.0,  # Would need to track hits/misses
            "memory_usage": sum(
                len(str(entry.data)) for entry in self._cache.values()
            )
        }
    
    def get_cache_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get information about specific cache entry
        
        Args:
            key: Cache key
            
        Returns:
            Cache entry info or None
        """
        if key not in self._cache:
            return None
            
        entry = self._cache[key]
        now = datetime.now()
        
        return {
            "key": key,
            "expires": entry.expires.isoformat(),
            "ttl_remaining": max(0, (entry.expires - now).total_seconds()),
            "is_expired": entry.expires <= now,
            "data_size": len(str(entry.data))
        }