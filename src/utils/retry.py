"""
Retry logic and error handling for API calls
"""
import asyncio
import logging
import random
import time
from functools import wraps
from typing import TypeVar, Callable, Union, Tuple, Any, Dict
from dataclasses import dataclass
from enum import Enum
import aiohttp


T = TypeVar('T')
logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base API error"""
    pass


class RateLimitError(APIError):
    """Rate limit exceeded error"""
    pass


def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[type, ...] = (APIError,)
):
    """
    Retry decorator for async functions
    
    Args:
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
        exceptions: Exception types to retry on
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    # Special handling for rate limit errors
                    if isinstance(e, RateLimitError):
                        current_delay = 60.0  # Wait longer for rate limits
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {str(e)}"
                    )
                    
                    # Don't sleep on the last attempt
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            
            # Re-raise the last exception if all attempts failed
            raise last_exception
            
        return wrapper
    return decorator


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class RetryMetrics:
    """Retry operation metrics"""
    total_attempts: int = 0
    total_retries: int = 0
    success_count: int = 0
    failure_count: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.success_count / self.total_attempts


class RetryHandler:
    """Handle retry logic with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.metrics = RetryMetrics()
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            self.metrics.total_attempts += 1
            
            try:
                result = await func(*args, **kwargs)
                self.metrics.success_count += 1
                return result
                
            except Exception as e:
                last_exception = e
                self.metrics.failure_count += 1
                
                if attempt < self.max_retries:
                    self.metrics.total_retries += 1
                    delay = self._calculate_delay(attempt)
                    
                    # Special handling for rate limit errors
                    if self._is_rate_limit_error(e):
                        delay = max(delay, 5.0)  # Minimum 5 seconds for rate limits
                    
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed. Last error: {e}")
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter"""
        delay = self.base_delay * (2 ** attempt)
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0, delay * 0.1)
        return delay + jitter
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is a rate limit error"""
        if isinstance(error, aiohttp.ClientResponseError):
            return error.status == 429
        return "rate limit" in str(error).lower()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get retry metrics"""
        return {
            "total_attempts": self.metrics.total_attempts,
            "total_retries": self.metrics.total_retries,
            "success_count": self.metrics.success_count,
            "failure_count": self.metrics.failure_count,
            "success_rate": self.metrics.success_rate
        }


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0, 
                 expected_failures: int = 10):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_failures = expected_failures
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.success_count = 0
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function through circuit breaker"""
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.expected_failures:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker transitioning to CLOSED")
        else:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker transitioning to OPEN after {self.failure_count} failures")


class BackpressureHandler:
    """Handle backpressure for high load scenarios"""
    
    def __init__(self, max_queue_size: int = 100, max_concurrent_requests: int = 10):
        self.max_queue_size = max_queue_size
        self.max_concurrent_requests = max_concurrent_requests
        
        self.queue = asyncio.Queue(maxsize=max_queue_size)
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.active_requests = 0
        self.dropped_requests = 0
        
        # Start background processor
        self._processor_task = asyncio.create_task(self._process_queue())
    
    async def submit(self, func: Callable, *args, **kwargs) -> Any:
        """Submit task with backpressure handling"""
        try:
            future = asyncio.Future()
            task_item = (func, args, kwargs, future)
            
            self.queue.put_nowait(task_item)
            return await future
            
        except asyncio.QueueFull:
            self.dropped_requests += 1
            raise Exception("Queue full - request dropped due to backpressure")
    
    async def _process_queue(self):
        """Process queued tasks"""
        while True:
            try:
                func, args, kwargs, future = await self.queue.get()
                
                async with self.semaphore:
                    self.active_requests += 1
                    try:
                        result = await func(*args, **kwargs)
                        future.set_result(result)
                    except Exception as e:
                        future.set_exception(e)
                    finally:
                        self.active_requests -= 1
                
                self.queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing queue item: {e}")
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get backpressure metrics"""
        return {
            "queue_size": self.queue.qsize(),
            "active_requests": self.active_requests,
            "dropped_requests": self.dropped_requests,
            "max_queue_size": self.max_queue_size,
            "max_concurrent_requests": self.max_concurrent_requests
        }
    
    def cleanup(self):
        """Clean up resources"""
        if self._processor_task:
            self._processor_task.cancel()