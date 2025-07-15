"""
Tests for Cache System
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from src.utils.cache import MarketDataCache, CacheEntry


class TestCacheEntry:
    """Test cases for CacheEntry"""
    
    def test_cache_entry_creation(self):
        """Test creating cache entry"""
        data = {"test": "value"}
        expires = datetime.now() + timedelta(seconds=10)
        
        entry = CacheEntry(data=data, expires=expires)
        
        assert entry.data == data
        assert entry.expires == expires
    
    def test_cache_entry_expired(self):
        """Test cache entry expiration check"""
        data = {"test": "value"}
        expires = datetime.now() - timedelta(seconds=1)  # Already expired
        
        entry = CacheEntry(data=data, expires=expires)
        
        assert entry.expires < datetime.now()


class TestMarketDataCache:
    """Test cases for MarketDataCache"""
    
    @pytest.fixture
    def cache(self):
        """Create fresh cache instance for each test"""
        return MarketDataCache()
    
    @pytest.fixture
    def sample_data(self):
        """Sample data for testing"""
        return {"price": 2500.50, "volume": 1000000}
    
    @pytest.mark.asyncio
    async def test_cache_miss_and_fetch(self, cache, sample_data):
        """Test cache miss triggers fetch function"""
        fetch_called = False
        
        async def fetch_func():
            nonlocal fetch_called
            fetch_called = True
            return sample_data
        
        result = await cache.get_or_fetch("test_key", fetch_func, ttl=5)
        
        assert result == sample_data
        assert fetch_called
    
    @pytest.mark.asyncio
    async def test_cache_hit_no_fetch(self, cache, sample_data):
        """Test cache hit doesn't trigger fetch function"""
        fetch_call_count = 0
        
        async def fetch_func():
            nonlocal fetch_call_count
            fetch_call_count += 1
            return sample_data
        
        # First call - cache miss
        result1 = await cache.get_or_fetch("test_key", fetch_func, ttl=5)
        assert fetch_call_count == 1
        
        # Second call - cache hit
        result2 = await cache.get_or_fetch("test_key", fetch_func, ttl=5)
        assert fetch_call_count == 1  # No additional fetch
        assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, cache, sample_data):
        """Test cache expiration triggers new fetch"""
        fetch_call_count = 0
        
        async def fetch_func():
            nonlocal fetch_call_count
            fetch_call_count += 1
            return {"call": fetch_call_count, **sample_data}
        
        # First call with short TTL
        result1 = await cache.get_or_fetch("test_key", fetch_func, ttl=1)
        assert fetch_call_count == 1
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Second call after expiration
        result2 = await cache.get_or_fetch("test_key", fetch_func, ttl=1)
        assert fetch_call_count == 2
        assert result1["call"] != result2["call"]
    
    @pytest.mark.asyncio
    async def test_concurrent_cache_requests(self, cache, sample_data):
        """Test concurrent requests for same key only trigger one fetch"""
        fetch_call_count = 0
        
        async def slow_fetch_func():
            nonlocal fetch_call_count
            fetch_call_count += 1
            await asyncio.sleep(0.1)  # Simulate slow API call
            return {"call": fetch_call_count, **sample_data}
        
        # Make multiple concurrent requests
        tasks = [
            cache.get_or_fetch("test_key", slow_fetch_func, ttl=5)
            for _ in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All results should be the same
        assert all(result == results[0] for result in results)
        # Only one fetch should have been called
        assert fetch_call_count == 1
    
    @pytest.mark.asyncio
    async def test_different_keys_separate_fetches(self, cache, sample_data):
        """Test different keys trigger separate fetches"""
        fetch_call_count = 0
        
        async def fetch_func():
            nonlocal fetch_call_count
            fetch_call_count += 1
            return {"call": fetch_call_count, **sample_data}
        
        result1 = await cache.get_or_fetch("key1", fetch_func, ttl=5)
        result2 = await cache.get_or_fetch("key2", fetch_func, ttl=5)
        
        assert fetch_call_count == 2
        assert result1["call"] != result2["call"]
    
    def test_direct_get_cache_hit(self, cache, sample_data):
        """Test direct get method with cache hit"""
        # Set data directly
        cache.set("test_key", sample_data, ttl=5)
        
        result = cache.get("test_key")
        assert result == sample_data
    
    def test_direct_get_cache_miss(self, cache):
        """Test direct get method with cache miss"""
        result = cache.get("nonexistent_key")
        assert result is None
    
    def test_direct_get_expired(self, cache, sample_data):
        """Test direct get method with expired entry"""
        # Set data with TTL of 0 (immediately expired)
        cache.set("test_key", sample_data, ttl=0)
        
        result = cache.get("test_key")
        assert result is None
    
    def test_set_and_get(self, cache, sample_data):
        """Test setting and getting cache data"""
        cache.set("test_key", sample_data, ttl=5)
        
        result = cache.get("test_key")
        assert result == sample_data
    
    def test_invalidate_specific_key(self, cache, sample_data):
        """Test invalidating specific cache key"""
        cache.set("key1", sample_data, ttl=5)
        cache.set("key2", {"other": "data"}, ttl=5)
        
        cache.invalidate("key1")
        
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
    
    def test_invalidate_all(self, cache, sample_data):
        """Test invalidating all cache entries"""
        cache.set("key1", sample_data, ttl=5)
        cache.set("key2", {"other": "data"}, ttl=5)
        
        cache.invalidate()  # No key specified - clear all
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_cleanup_expired_entries(self, cache, sample_data):
        """Test cleanup of expired entries"""
        # Add some entries with different TTLs
        cache.set("valid_key", sample_data, ttl=10)
        cache.set("expired_key", sample_data, ttl=0)
        
        # Cleanup expired entries
        cache.cleanup_expired()
        
        assert cache.get("valid_key") is not None
        assert cache.get("expired_key") is None
    
    def test_get_stats_empty_cache(self, cache):
        """Test statistics for empty cache"""
        stats = cache.get_stats()
        
        assert stats["total_keys"] == 0
        assert stats["valid_keys"] == 0
        assert stats["expired_keys"] == 0
        assert stats["memory_usage"] == 0
    
    def test_get_stats_with_data(self, cache, sample_data):
        """Test statistics with cache data"""
        cache.set("valid_key", sample_data, ttl=10)
        cache.set("expired_key", sample_data, ttl=0)
        
        stats = cache.get_stats()
        
        assert stats["total_keys"] == 2
        assert stats["valid_keys"] == 1
        assert stats["expired_keys"] == 1
        assert stats["memory_usage"] > 0
    
    def test_get_cache_info_existing_key(self, cache, sample_data):
        """Test getting cache info for existing key"""
        cache.set("test_key", sample_data, ttl=10)
        
        info = cache.get_cache_info("test_key")
        
        assert info is not None
        assert info["key"] == "test_key"
        assert not info["is_expired"]
        assert info["ttl_remaining"] > 0
        assert info["data_size"] > 0
    
    def test_get_cache_info_nonexistent_key(self, cache):
        """Test getting cache info for nonexistent key"""
        info = cache.get_cache_info("nonexistent_key")
        assert info is None
    
    def test_get_cache_info_expired_key(self, cache, sample_data):
        """Test getting cache info for expired key"""
        cache.set("expired_key", sample_data, ttl=0)
        
        info = cache.get_cache_info("expired_key")
        
        assert info is not None
        assert info["is_expired"]
        assert info["ttl_remaining"] == 0
    
    @pytest.mark.asyncio
    async def test_cache_with_exception_in_fetch(self, cache):
        """Test cache behavior when fetch function raises exception"""
        async def failing_fetch():
            raise ValueError("Fetch failed")
        
        with pytest.raises(ValueError):
            await cache.get_or_fetch("test_key", failing_fetch, ttl=5)
    
    @pytest.mark.asyncio
    async def test_cache_fetch_return_none(self, cache):
        """Test cache behavior when fetch function returns None"""
        async def fetch_none():
            return None
        
        result = await cache.get_or_fetch("test_key", fetch_none, ttl=5)
        assert result is None
        
        # Should still be cached
        result2 = cache.get("test_key")
        assert result2 is None
    
    @pytest.mark.asyncio
    async def test_cache_different_ttl_values(self, cache, sample_data):
        """Test cache with different TTL values"""
        # Test zero TTL (immediately expired)
        async def fetch_func():
            return sample_data
        
        result = await cache.get_or_fetch("test_key", fetch_func, ttl=0)
        assert result == sample_data
        
        # Should be expired immediately
        direct_result = cache.get("test_key")
        assert direct_result is None
    
    @pytest.mark.asyncio
    async def test_cache_large_data(self, cache):
        """Test cache with large data objects"""
        large_data = {"data": "x" * 100000}  # 100KB string
        
        async def fetch_func():
            return large_data
        
        result = await cache.get_or_fetch("large_key", fetch_func, ttl=5)
        assert result == large_data
        
        stats = cache.get_stats()
        assert stats["memory_usage"] > 100000
    
    @pytest.mark.asyncio
    async def test_cache_complex_data_types(self, cache):
        """Test cache with complex data types"""
        complex_data = {
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "tuple": (1, 2, 3),
            "number": 123.456,
            "bool": True,
            "none": None
        }
        
        async def fetch_func():
            return complex_data
        
        result = await cache.get_or_fetch("complex_key", fetch_func, ttl=5)
        assert result == complex_data
        assert isinstance(result["list"], list)
        assert isinstance(result["dict"], dict)
    
    def test_cache_memory_efficiency(self, cache):
        """Test cache doesn't hold references to expired entries unnecessarily"""
        initial_size = len(cache._cache)
        
        # Add many entries with short TTL
        for i in range(100):
            cache.set(f"key_{i}", {"data": i}, ttl=0)
        
        # All should be expired
        cache.cleanup_expired()
        
        # Cache should be back to initial size
        assert len(cache._cache) == initial_size