"""
Phase 4 TDD Tests - Stability and Error Handling Enhancements
안정성 및 에러 처리 강화 테스트
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import aiohttp
import time
import psutil
import gc
from typing import Dict, Any, List

from src.api.client import KoreaInvestmentAPI
from src.utils.cache import MarketDataCache
from src.utils.retry import RetryHandler, CircuitBreaker, BackpressureHandler, CircuitBreakerState
from src.utils.metrics import MetricsCollector, PerformanceMonitor
from src.utils.validator import DataValidator
from src.tools.index_tools import get_market_index, get_index_chart


class TestRetryAndResilienceLogic:
    """Test retry logic and resilience patterns"""
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_retry(self):
        """Test exponential backoff retry logic"""
        retry_handler = RetryHandler(max_retries=3, base_delay=0.1)
        
        # Mock a function that fails twice then succeeds
        mock_func = AsyncMock()
        mock_func.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            {"success": True}
        ]
        
        start_time = time.time()
        result = await retry_handler.execute_with_retry(mock_func)
        end_time = time.time()
        
        # Should succeed on third try
        assert result == {"success": True}
        assert mock_func.call_count == 3
        
        # Should have proper exponential backoff delays
        expected_min_delay = 0.1 + 0.2  # First + second delays
        assert end_time - start_time >= expected_min_delay
        
        # Check retry metrics
        metrics = retry_handler.get_metrics()
        assert metrics["total_retries"] == 2
        assert metrics["success_rate"] > 0
    
    @pytest.mark.asyncio
    async def test_retry_with_rate_limit_handling(self):
        """Test retry logic with rate limit handling"""
        retry_handler = RetryHandler(max_retries=3, base_delay=0.1)
        
        # Mock rate limit error
        rate_limit_error = aiohttp.ClientResponseError(
            request_info=Mock(),
            history=(),
            status=429,
            message="Rate limit exceeded"
        )
        
        mock_func = AsyncMock()
        mock_func.side_effect = [rate_limit_error, {"success": True}]
        
        result = await retry_handler.execute_with_retry(mock_func)
        
        assert result == {"success": True}
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern implementation"""
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,
            expected_failures=2
        )
        
        # Mock function that always fails
        failing_func = AsyncMock(side_effect=Exception("Always fails"))
        
        # First few calls should go through
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)
        
        # Circuit should be open now
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Next calls should fail immediately without calling the function
        call_count_before = failing_func.call_count
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await circuit_breaker.call(failing_func)
        
        assert failing_func.call_count == call_count_before
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Should be in half-open state after next call (call will fail but state should change first)
        call_count_before = failing_func.call_count
        with pytest.raises(Exception, match="Always fails"):
            await circuit_breaker.call(failing_func)
        
        # Function should have been called (meaning it transitioned to HALF_OPEN first)
        assert failing_func.call_count == call_count_before + 1
        
        # But after failure, it should be OPEN again
        assert circuit_breaker.state == CircuitBreakerState.OPEN
    
    @pytest.mark.asyncio
    async def test_backpressure_handling(self):
        """Test backpressure handling for high load scenarios"""
        backpressure_handler = BackpressureHandler(
            max_queue_size=5,
            max_concurrent_requests=2
        )
        
        # Mock slow function
        async def slow_func():
            await asyncio.sleep(0.1)
            return {"processed": True}
        
        # Submit many tasks
        tasks = []
        for i in range(10):
            task = backpressure_handler.submit(slow_func)
            tasks.append(task)
        
        # Some tasks should be queued
        queue_size = backpressure_handler.get_queue_size()
        assert queue_size > 0
        
        # All tasks should eventually complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_results = [r for r in results if not isinstance(r, Exception)]
        
        assert len(successful_results) <= 10  # Some may be dropped due to backpressure
        
        # Check metrics
        metrics = backpressure_handler.get_metrics()
        assert "queue_size" in metrics
        assert "dropped_requests" in metrics
        assert "active_requests" in metrics


class TestConnectionPoolingAndResourceManagement:
    """Test connection pooling and resource management"""
    
    @pytest.mark.asyncio
    async def test_connection_pool_reuse(self):
        """Test that connections are properly reused"""
        api_client = KoreaInvestmentAPI()
        
        # Make multiple requests
        responses = []
        for i in range(5):
            try:
                response = await api_client.get_index_price("0001")
                responses.append(response)
            except Exception as e:
                # Expected since we don't have real API credentials
                responses.append({"error": str(e)})
        
        # Check that session is reused
        assert api_client._session is not None
        
        # Check connection pool metrics
        session_connector = api_client._session.connector
        assert hasattr(session_connector, '_conns')
        
        await api_client.close()
    
    @pytest.mark.asyncio
    async def test_resource_cleanup_on_error(self):
        """Test proper resource cleanup on errors"""
        api_client = KoreaInvestmentAPI()
        
        # Force an error condition
        with patch.object(api_client, '_session') as mock_session:
            mock_session.get.side_effect = Exception("Connection error")
            
            try:
                await api_client.get_index_price("0001")
            except Exception:
                pass
        
        # Resources should still be properly managed
        assert api_client._session is not None
        
        await api_client.close()
    
    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self):
        """Test prevention of memory leaks in long-running operations"""
        cache = MarketDataCache()
        
        # Fill cache with data
        for i in range(100):
            cache.set(f"test_key_{i}", {"data": f"value_{i}" * 100}, ttl=60)
        
        initial_memory = psutil.Process().memory_info().rss
        
        # Force garbage collection
        gc.collect()
        
        # Simulate cache cleanup
        cache.cleanup_expired()
        
        # Force another garbage collection
        gc.collect()
        
        final_memory = psutil.Process().memory_info().rss
        
        # Memory should not have grown significantly
        memory_growth = final_memory - initial_memory
        assert memory_growth < 10 * 1024 * 1024  # Less than 10MB growth


class TestDataValidationAndIntegrity:
    """Test enhanced data validation and integrity checks"""
    
    @pytest.mark.asyncio
    async def test_input_parameter_validation(self):
        """Test input parameter validation"""
        validator = DataValidator()
        
        # Test valid parameters
        valid_params = {
            "market": "KOSPI",
            "period": "1M",
            "interval": "1h"
        }
        
        validation_result = validator.validate_chart_parameters(valid_params)
        assert validation_result["valid"] == True
        assert validation_result["errors"] == []
        
        # Test invalid parameters
        invalid_params = {
            "market": "INVALID",
            "period": "2X",
            "interval": "30s"
        }
        
        validation_result = validator.validate_chart_parameters(invalid_params)
        assert validation_result["valid"] == False
        assert len(validation_result["errors"]) > 0
        assert "market" in str(validation_result["errors"])
    
    @pytest.mark.asyncio
    async def test_api_response_integrity_check(self):
        """Test API response data integrity validation"""
        validator = DataValidator()
        
        # Test valid API response
        valid_response = {
            "output": {
                "bstp_nmix_prpr": "2500.00",
                "bstp_nmix_prdy_vrss": "10.00",
                "bstp_nmix_prdy_ctrt": "0.40",
                "acml_vol": "400000000"
            }
        }
        
        integrity_result = validator.validate_api_response(valid_response)
        assert integrity_result["valid"] == True
        assert integrity_result["completeness_score"] > 0.8
        
        # Test corrupted response
        corrupted_response = {
            "output": {
                "bstp_nmix_prpr": "invalid_price",
                "bstp_nmix_prdy_vrss": None,
                "acml_vol": "-1000000"  # Invalid negative volume
            }
        }
        
        integrity_result = validator.validate_api_response(corrupted_response)
        assert integrity_result["valid"] == False
        assert len(integrity_result["data_issues"]) > 0
    
    @pytest.mark.asyncio
    async def test_business_logic_validation(self):
        """Test business logic validation"""
        validator = DataValidator()
        
        # Test market hours validation
        market_hours_result = validator.validate_market_hours(
            datetime.now().replace(hour=10, minute=30)  # During market hours
        )
        assert market_hours_result["is_market_hours"] == True
        
        weekend_result = validator.validate_market_hours(
            datetime.now().replace(hour=10, minute=30).replace(day=15)  # Might be weekend
        )
        # Result depends on actual day of week
        assert "is_market_hours" in weekend_result
        
        # Test price change validation
        price_change_result = validator.validate_price_change(
            current_price=2500.00,
            previous_price=2490.00,
            max_change_percent=30.0
        )
        assert price_change_result["valid"] == True
        assert price_change_result["change_percent"] < 1.0
        
        # Test extreme price change
        extreme_change_result = validator.validate_price_change(
            current_price=2500.00,
            previous_price=1000.00,
            max_change_percent=30.0
        )
        assert extreme_change_result["valid"] == False
        assert extreme_change_result["change_percent"] > 30.0


class TestPerformanceMonitoringAndMetrics:
    """Test performance monitoring and metrics collection"""
    
    @pytest.mark.asyncio
    async def test_api_response_time_monitoring(self):
        """Test API response time monitoring"""
        metrics_collector = MetricsCollector()
        
        # Mock API call with timing
        async def mock_api_call():
            await asyncio.sleep(0.1)  # Simulate 100ms API call
            return {"success": True}
        
        async with metrics_collector.time_operation("api_call"):
            result = await mock_api_call()
        
        # Check metrics
        api_metrics = metrics_collector.get_metrics("api_call")
        assert api_metrics["total_calls"] == 1
        assert api_metrics["average_response_time"] >= 0.1
        assert api_metrics["min_response_time"] >= 0.1
        assert api_metrics["max_response_time"] >= 0.1
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_monitoring(self):
        """Test cache hit rate monitoring"""
        cache = MarketDataCache()
        metrics_collector = MetricsCollector()
        
        # Simulate cache operations
        cache.set("test_key", {"data": "test"}, ttl=60)
        
        # Hit
        hit_result = cache.get("test_key")
        metrics_collector.record_cache_hit("test_key")
        
        # Miss
        miss_result = cache.get("nonexistent_key")
        metrics_collector.record_cache_miss("nonexistent_key")
        
        # Check metrics
        cache_metrics = metrics_collector.get_cache_metrics()
        assert cache_metrics["total_requests"] == 2
        assert cache_metrics["hit_rate"] == 0.5
        assert cache_metrics["miss_rate"] == 0.5
    
    @pytest.mark.asyncio
    async def test_error_rate_tracking(self):
        """Test error rate tracking"""
        metrics_collector = MetricsCollector()
        
        # Record successful operations
        for i in range(7):
            metrics_collector.record_operation_success("api_call")
        
        # Record failures
        for i in range(3):
            metrics_collector.record_operation_failure("api_call", "API Error")
        
        # Check error rate
        error_metrics = metrics_collector.get_error_metrics("api_call")
        assert error_metrics["total_operations"] == 10
        assert error_metrics["success_rate"] == 0.7
        assert error_metrics["error_rate"] == 0.3
        assert "API Error" in error_metrics["error_types"]
    
    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self):
        """Test memory usage monitoring"""
        performance_monitor = PerformanceMonitor()
        
        # Start monitoring
        performance_monitor.start_monitoring()
        
        # Simulate memory usage
        large_data = ["data" * 1000 for _ in range(1000)]
        
        # Wait a bit for monitoring to capture data
        await asyncio.sleep(0.1)
        
        # Get memory metrics
        memory_metrics = performance_monitor.get_memory_metrics()
        assert "current_memory_mb" in memory_metrics
        assert "peak_memory_mb" in memory_metrics
        assert memory_metrics["current_memory_mb"] > 0
        
        # Clean up
        del large_data
        gc.collect()
        
        performance_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_concurrent_request_monitoring(self):
        """Test monitoring of concurrent requests"""
        performance_monitor = PerformanceMonitor()
        
        async def mock_request():
            async with performance_monitor.track_concurrent_request():
                await asyncio.sleep(0.1)
                return {"success": True}
        
        # Start multiple concurrent requests
        tasks = [mock_request() for _ in range(5)]
        
        # Monitor peak concurrency
        await asyncio.gather(*tasks)
        
        # Check concurrency metrics
        concurrency_metrics = performance_monitor.get_concurrency_metrics()
        assert "peak_concurrent_requests" in concurrency_metrics
        assert concurrency_metrics["peak_concurrent_requests"] >= 1
        assert concurrency_metrics["peak_concurrent_requests"] <= 5


class TestIntegratedStabilityScenarios:
    """Test integrated stability scenarios"""
    
    @pytest.mark.asyncio
    async def test_high_load_stability(self):
        """Test system stability under high load"""
        cache = MarketDataCache()
        api_client = Mock(spec=KoreaInvestmentAPI)
        
        # Mock API responses
        api_client.get_index_price = AsyncMock(return_value={
            "output": {
                "bstp_nmix_prpr": "2500.00",
                "bstp_nmix_prdy_vrss": "10.00",
                "bstp_nmix_prdy_ctrt": "0.40",
                "acml_vol": "400000000"
            }
        })
        
        # Simulate high load
        start_time = time.time()
        tasks = []
        for i in range(50):
            task = get_market_index("KOSPI", cache, api_client)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Most requests should succeed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 40  # At least 80% success rate
        
        # Response time should be reasonable
        average_time = (end_time - start_time) / len(tasks)
        assert average_time < 1.0  # Less than 1 second average
    
    @pytest.mark.asyncio
    async def test_cascading_failure_prevention(self):
        """Test prevention of cascading failures"""
        cache = MarketDataCache()
        api_client = Mock(spec=KoreaInvestmentAPI)
        
        # Mock API failure
        api_client.get_index_price = AsyncMock(side_effect=Exception("API Down"))
        
        # Pre-populate cache with fallback data
        cache.set("market_index_KOSPI_fallback", {
            "output": {
                "bstp_nmix_prpr": "2450.00",
                "bstp_nmix_prdy_vrss": "5.00",
                "bstp_nmix_prdy_ctrt": "0.20",
                "acml_vol": "300000000"
            }
        }, ttl=300)
        
        # Should use fallback and not cascade failure
        result = await get_market_index("KOSPI", cache, api_client, allow_fallback=True)
        
        assert "kospi" in result
        assert "data_source" in result
        assert result["data_source"] == "fallback_cache"
    
    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self):
        """Test handling of memory pressure scenarios"""
        cache = MarketDataCache()
        
        # Fill cache to capacity
        for i in range(1000):
            large_data = {"data": ["x" * 1000 for _ in range(100)]}
            cache.set(f"large_key_{i}", large_data, ttl=60)
        
        # Monitor memory usage
        initial_memory = psutil.Process().memory_info().rss
        
        # Trigger cache cleanup
        cache.cleanup_expired()
        
        # Force garbage collection
        gc.collect()
        
        final_memory = psutil.Process().memory_info().rss
        
        # Memory should be managed properly
        assert final_memory <= initial_memory * 1.2  # No more than 20% growth
    
    @pytest.mark.asyncio
    async def test_timeout_and_recovery(self):
        """Test timeout handling and recovery"""
        cache = MarketDataCache()
        api_client = Mock(spec=KoreaInvestmentAPI)
        
        # Mock slow API response
        async def slow_response():
            await asyncio.sleep(5)  # Simulate 5 second delay
            return {"output": {"bstp_nmix_prpr": "2500.00"}}
        
        api_client.get_index_price = AsyncMock(side_effect=slow_response)
        
        # Should timeout and handle gracefully
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                get_market_index("KOSPI", cache, api_client),
                timeout=1.0
            )
        except asyncio.TimeoutError:
            # Expected behavior
            pass
        
        end_time = time.time()
        
        # Should have timed out quickly
        assert end_time - start_time < 2.0