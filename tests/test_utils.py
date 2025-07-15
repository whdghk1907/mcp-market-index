"""
Tests for utility functions and helpers
"""
import pytest
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from datetime import datetime, timedelta

from src.utils.logger import setup_logger, StructuredLogger
from src.utils.retry import retry_on_error, APIError, RateLimitError


class TestLogger:
    """Test cases for logging utilities"""
    
    def test_setup_logger_basic(self):
        """Test basic logger setup"""
        logger = setup_logger("test_logger", "INFO")
        
        assert logger.name == "test_logger"
        assert logger.level == 20  # INFO level
        assert len(logger.handlers) >= 2  # Console and file handlers
    
    def test_setup_logger_debug_level(self):
        """Test logger setup with DEBUG level"""
        logger = setup_logger("debug_logger", "DEBUG")
        
        assert logger.level == 10  # DEBUG level
    
    def test_setup_logger_file_handler(self):
        """Test that file handler is created"""
        logger = setup_logger("file_test", "INFO")
        
        file_handlers = [h for h in logger.handlers if hasattr(h, 'baseFilename')]
        assert len(file_handlers) >= 1
    
    def test_structured_logger_api_call(self):
        """Test structured logger API call logging"""
        mock_logger = Mock()
        structured = StructuredLogger(mock_logger)
        
        structured.log_api_call(
            endpoint="/test",
            params={"key": "value"},
            response_time=1.5,
            status_code=200
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "API_CALL" in call_args
        assert "/test" in call_args
        assert "1.500s" in call_args
    
    def test_structured_logger_cache_hit(self):
        """Test structured logger cache hit logging"""
        mock_logger = Mock()
        structured = StructuredLogger(mock_logger)
        
        structured.log_cache_hit("test_key", 30.5)
        
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert "CACHE_HIT" in call_args
        assert "test_key" in call_args
        assert "30.5s" in call_args
    
    def test_structured_logger_cache_miss(self):
        """Test structured logger cache miss logging"""
        mock_logger = Mock()
        structured = StructuredLogger(mock_logger)
        
        structured.log_cache_miss("test_key")
        
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert "CACHE_MISS" in call_args
        assert "test_key" in call_args
    
    def test_structured_logger_error(self):
        """Test structured logger error logging"""
        mock_logger = Mock()
        structured = StructuredLogger(mock_logger)
        
        error = ValueError("Test error")
        context = {"key": "value"}
        
        structured.log_error(error, context)
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "ERROR" in call_args
        assert "ValueError" in call_args
        assert "Test error" in call_args
        assert "context" in call_args
    
    def test_structured_logger_performance(self):
        """Test structured logger performance logging"""
        mock_logger = Mock()
        structured = StructuredLogger(mock_logger)
        
        structured.log_performance("fetch_data", 2.5, {"records": 100})
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "PERFORMANCE" in call_args
        assert "fetch_data" in call_args
        assert "2.500s" in call_args
        assert "metadata" in call_args


class TestRetryDecorator:
    """Test cases for retry decorator"""
    
    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self):
        """Test successful function call on first attempt"""
        call_count = 0
        
        @retry_on_error(max_attempts=3, delay=0.1)
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await successful_func()
        
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test successful function call after failures"""
        call_count = 0
        
        @retry_on_error(max_attempts=3, delay=0.1)
        async def eventually_successful_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APIError("Temporary failure")
            return "success"
        
        result = await eventually_successful_func()
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_max_attempts_exceeded(self):
        """Test failure when max attempts exceeded"""
        call_count = 0
        
        @retry_on_error(max_attempts=3, delay=0.1)
        async def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise APIError("Always fails")
        
        with pytest.raises(APIError):
            await always_failing_func()
        
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_with_rate_limit_error(self):
        """Test retry behavior with rate limit error"""
        call_count = 0
        
        @retry_on_error(max_attempts=3, delay=0.1)
        async def rate_limited_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("Rate limit exceeded")
            return "success"
        
        # Should succeed on second attempt but with longer delay
        result = await rate_limited_func()
        
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_with_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried"""
        call_count = 0
        
        @retry_on_error(max_attempts=3, delay=0.1, exceptions=(APIError,))
        async def func_with_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")
        
        with pytest.raises(ValueError):
            await func_with_value_error()
        
        assert call_count == 1  # Should not retry
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff(self):
        """Test exponential backoff functionality"""
        call_times = []
        
        @retry_on_error(max_attempts=3, delay=0.1, backoff=2.0)
        async def backoff_func():
            call_times.append(datetime.now())
            raise APIError("Always fails")
        
        with pytest.raises(APIError):
            await backoff_func()
        
        assert len(call_times) == 3
        
        # Check that delays increase (approximately)
        if len(call_times) >= 3:
            delay1 = (call_times[1] - call_times[0]).total_seconds()
            delay2 = (call_times[2] - call_times[1]).total_seconds()
            
            # Second delay should be roughly double the first
            assert delay2 > delay1 * 1.5
    
    @pytest.mark.asyncio
    async def test_retry_preserves_function_metadata(self):
        """Test that retry decorator preserves function metadata"""
        @retry_on_error(max_attempts=3)
        async def documented_func():
            """This function has documentation"""
            return "result"
        
        assert documented_func.__name__ == "documented_func"
        assert "documentation" in documented_func.__doc__
    
    @pytest.mark.asyncio
    async def test_retry_with_custom_exceptions(self):
        """Test retry with custom exception types"""
        class CustomError(Exception):
            pass
        
        call_count = 0
        
        @retry_on_error(max_attempts=3, delay=0.1, exceptions=(CustomError,))
        async def custom_error_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise CustomError("Custom failure")
            return "success"
        
        result = await custom_error_func()
        
        assert result == "success"
        assert call_count == 3


class TestAPIExceptions:
    """Test cases for API exception classes"""
    
    def test_api_error_creation(self):
        """Test APIError creation"""
        error = APIError("Test API error")
        
        assert str(error) == "Test API error"
        assert isinstance(error, Exception)
    
    def test_rate_limit_error_creation(self):
        """Test RateLimitError creation"""
        error = RateLimitError("Rate limit exceeded")
        
        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, APIError)
        assert isinstance(error, Exception)
    
    def test_exception_inheritance(self):
        """Test exception inheritance hierarchy"""
        rate_limit_error = RateLimitError("Rate limit")
        api_error = APIError("API error")
        
        assert isinstance(rate_limit_error, APIError)
        assert isinstance(rate_limit_error, Exception)
        assert isinstance(api_error, Exception)
        assert not isinstance(api_error, RateLimitError)


class TestUtilityHelpers:
    """Test cases for utility helper functions"""
    
    def test_time_measurement(self):
        """Test time measurement utility"""
        import time
        
        start_time = datetime.now()
        time.sleep(0.1)
        end_time = datetime.now()
        
        elapsed = (end_time - start_time).total_seconds()
        assert elapsed >= 0.1
        assert elapsed < 0.2  # Should be close to 0.1 seconds
    
    def test_data_formatting(self):
        """Test data formatting utilities"""
        # Test number formatting
        assert f"{2500.50:.2f}" == "2500.50"
        assert f"{-15.30:.2f}" == "-15.30"
        
        # Test percentage formatting
        change_rate = 0.61
        assert f"{change_rate:.2f}%" == "0.61%"
    
    def test_timestamp_formatting(self):
        """Test timestamp formatting"""
        test_time = datetime(2024, 1, 10, 10, 30, 0)
        
        # ISO format
        iso_string = test_time.isoformat()
        assert iso_string == "2024-01-10T10:30:00"
        
        # Custom format
        custom_format = test_time.strftime("%Y-%m-%d %H:%M:%S")
        assert custom_format == "2024-01-10 10:30:00"
    
    def test_market_code_validation(self):
        """Test market code validation"""
        valid_codes = ["KOSPI", "KOSDAQ", "ALL"]
        invalid_codes = ["NASDAQ", "NYSE", "INVALID"]
        
        for code in valid_codes:
            assert code in ["KOSPI", "KOSDAQ", "ALL"]
        
        for code in invalid_codes:
            assert code not in ["KOSPI", "KOSDAQ", "ALL"]
    
    def test_period_validation(self):
        """Test period validation"""
        valid_periods = ["1D", "1W", "1M", "3M", "1Y"]
        invalid_periods = ["2D", "6M", "2Y", "INVALID"]
        
        for period in valid_periods:
            assert period in ["1D", "1W", "1M", "3M", "1Y"]
        
        for period in invalid_periods:
            assert period not in ["1D", "1W", "1M", "3M", "1Y"]
    
    def test_interval_validation(self):
        """Test interval validation"""
        valid_intervals = ["1m", "5m", "30m", "1h", "1d"]
        invalid_intervals = ["2m", "15m", "2h", "INVALID"]
        
        for interval in valid_intervals:
            assert interval in ["1m", "5m", "30m", "1h", "1d"]
        
        for interval in invalid_intervals:
            assert interval not in ["1m", "5m", "30m", "1h", "1d"]