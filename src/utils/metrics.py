"""
Metrics collection and performance monitoring
메트릭 수집 및 성능 모니터링
"""

import time
import asyncio
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import defaultdict, deque
import psutil
import gc
import logging

logger = logging.getLogger(__name__)


@dataclass
class OperationMetrics:
    """Metrics for a specific operation"""
    total_calls: int = 0
    total_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    @property
    def average_response_time(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_time / self.total_calls
    
    def record_time(self, duration: float):
        """Record a timing measurement"""
        self.total_calls += 1
        self.total_time += duration
        self.min_response_time = min(self.min_response_time, duration)
        self.max_response_time = max(self.max_response_time, duration)
        self.response_times.append(duration)


@dataclass
class CacheMetrics:
    """Cache operation metrics"""
    hits: int = 0
    misses: int = 0
    
    @property
    def total_requests(self) -> int:
        return self.hits + self.misses
    
    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests
    
    @property
    def miss_rate(self) -> float:
        return 1.0 - self.hit_rate


@dataclass
class ErrorMetrics:
    """Error tracking metrics"""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    error_types: Dict[str, int] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        if self.total_operations == 0:
            return 0.0
        return self.successful_operations / self.total_operations
    
    @property
    def error_rate(self) -> float:
        return 1.0 - self.success_rate
    
    def record_success(self):
        """Record successful operation"""
        self.total_operations += 1
        self.successful_operations += 1
    
    def record_failure(self, error_type: str):
        """Record failed operation"""
        self.total_operations += 1
        self.failed_operations += 1
        self.error_types[error_type] = self.error_types.get(error_type, 0) + 1


class MetricsCollector:
    """Collect and manage application metrics"""
    
    def __init__(self):
        self.operation_metrics: Dict[str, OperationMetrics] = defaultdict(OperationMetrics)
        self.cache_metrics = CacheMetrics()
        self.error_metrics: Dict[str, ErrorMetrics] = defaultdict(ErrorMetrics)
        self._lock = threading.Lock()
    
    @asynccontextmanager
    async def time_operation(self, operation_name: str):
        """Context manager for timing operations"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            with self._lock:
                self.operation_metrics[operation_name].record_time(duration)
    
    def get_metrics(self, operation_name: str) -> Dict[str, Any]:
        """Get metrics for a specific operation"""
        with self._lock:
            metrics = self.operation_metrics[operation_name]
            return {
                "total_calls": metrics.total_calls,
                "average_response_time": metrics.average_response_time,
                "min_response_time": metrics.min_response_time if metrics.min_response_time != float('inf') else 0.0,
                "max_response_time": metrics.max_response_time
            }
    
    def record_cache_hit(self, key: str):
        """Record cache hit"""
        with self._lock:
            self.cache_metrics.hits += 1
    
    def record_cache_miss(self, key: str):
        """Record cache miss"""
        with self._lock:
            self.cache_metrics.misses += 1
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache metrics"""
        with self._lock:
            return {
                "total_requests": self.cache_metrics.total_requests,
                "hits": self.cache_metrics.hits,
                "misses": self.cache_metrics.misses,
                "hit_rate": self.cache_metrics.hit_rate,
                "miss_rate": self.cache_metrics.miss_rate
            }
    
    def record_operation_success(self, operation_name: str):
        """Record successful operation"""
        with self._lock:
            self.error_metrics[operation_name].record_success()
    
    def record_operation_failure(self, operation_name: str, error_type: str):
        """Record failed operation"""
        with self._lock:
            self.error_metrics[operation_name].record_failure(error_type)
    
    def get_error_metrics(self, operation_name: str) -> Dict[str, Any]:
        """Get error metrics for operation"""
        with self._lock:
            metrics = self.error_metrics[operation_name]
            return {
                "total_operations": metrics.total_operations,
                "successful_operations": metrics.successful_operations,
                "failed_operations": metrics.failed_operations,
                "success_rate": metrics.success_rate,
                "error_rate": metrics.error_rate,
                "error_types": dict(metrics.error_types)
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics"""
        with self._lock:
            return {
                "operations": {name: self.get_metrics(name) for name in self.operation_metrics},
                "cache": self.get_cache_metrics(),
                "errors": {name: self.get_error_metrics(name) for name in self.error_metrics}
            }


class PerformanceMonitor:
    """Monitor system performance metrics"""
    
    def __init__(self, monitoring_interval: float = 1.0):
        self.monitoring_interval = monitoring_interval
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Memory tracking
        self.current_memory_mb = 0.0
        self.peak_memory_mb = 0.0
        self.memory_history: deque = deque(maxlen=100)
        
        # Concurrency tracking
        self.current_concurrent_requests = 0
        self.peak_concurrent_requests = 0
        self.concurrency_history: deque = deque(maxlen=100)
        
        self._lock = threading.Lock()
    
    def start_monitoring(self):
        """Start background monitoring"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_task = asyncio.create_task(self._monitor_loop())
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
    
    async def _monitor_loop(self):
        """Background monitoring loop"""
        while self.is_monitoring:
            try:
                # Monitor memory usage
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                with self._lock:
                    self.current_memory_mb = memory_mb
                    self.peak_memory_mb = max(self.peak_memory_mb, memory_mb)
                    self.memory_history.append(memory_mb)
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    def get_memory_metrics(self) -> Dict[str, Any]:
        """Get memory usage metrics"""
        with self._lock:
            return {
                "current_memory_mb": self.current_memory_mb,
                "peak_memory_mb": self.peak_memory_mb,
                "memory_history": list(self.memory_history)
            }
    
    def track_concurrent_request(self):
        """Context manager for tracking concurrent requests"""
        return ConcurrentRequestTracker(self)
    
    def _increment_concurrent_requests(self):
        """Increment concurrent request counter"""
        with self._lock:
            self.current_concurrent_requests += 1
            self.peak_concurrent_requests = max(
                self.peak_concurrent_requests, 
                self.current_concurrent_requests
            )
            self.concurrency_history.append(self.current_concurrent_requests)
    
    def _decrement_concurrent_requests(self):
        """Decrement concurrent request counter"""
        with self._lock:
            self.current_concurrent_requests = max(0, self.current_concurrent_requests - 1)
    
    def get_concurrency_metrics(self) -> Dict[str, Any]:
        """Get concurrency metrics"""
        with self._lock:
            return {
                "current_concurrent_requests": self.current_concurrent_requests,
                "peak_concurrent_requests": self.peak_concurrent_requests,
                "concurrency_history": list(self.concurrency_history)
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all performance metrics"""
        return {
            "memory": self.get_memory_metrics(),
            "concurrency": self.get_concurrency_metrics()
        }


class ConcurrentRequestTracker:
    """Context manager for tracking concurrent requests"""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
    
    def __enter__(self):
        self.monitor._increment_concurrent_requests()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.monitor._decrement_concurrent_requests()
    
    async def __aenter__(self):
        self.monitor._increment_concurrent_requests()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.monitor._decrement_concurrent_requests()


class ResourceMonitor:
    """Monitor system resources and trigger alerts"""
    
    def __init__(self, memory_threshold_mb: float = 500.0, cpu_threshold_percent: float = 80.0):
        self.memory_threshold_mb = memory_threshold_mb
        self.cpu_threshold_percent = cpu_threshold_percent
        self.alerts: List[Dict[str, Any]] = []
    
    def check_resources(self) -> Dict[str, Any]:
        """Check current resource usage"""
        process = psutil.Process()
        
        # Memory check
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # CPU check
        cpu_percent = process.cpu_percent()
        
        # Check thresholds
        alerts = []
        if memory_mb > self.memory_threshold_mb:
            alerts.append({
                "type": "memory",
                "message": f"Memory usage {memory_mb:.1f}MB exceeds threshold {self.memory_threshold_mb}MB",
                "current": memory_mb,
                "threshold": self.memory_threshold_mb
            })
        
        if cpu_percent > self.cpu_threshold_percent:
            alerts.append({
                "type": "cpu",
                "message": f"CPU usage {cpu_percent:.1f}% exceeds threshold {self.cpu_threshold_percent}%",
                "current": cpu_percent,
                "threshold": self.cpu_threshold_percent
            })
        
        self.alerts.extend(alerts)
        
        return {
            "memory_mb": memory_mb,
            "cpu_percent": cpu_percent,
            "alerts": alerts,
            "memory_within_threshold": memory_mb <= self.memory_threshold_mb,
            "cpu_within_threshold": cpu_percent <= self.cpu_threshold_percent
        }
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get all alerts"""
        return self.alerts.copy()
    
    def clear_alerts(self):
        """Clear all alerts"""
        self.alerts.clear()