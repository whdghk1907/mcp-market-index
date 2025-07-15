"""
Monitoring and alerting system
모니터링 및 알림 시스템
"""

import asyncio
import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum

from .logger import StructuredLogger, create_logger
from .metrics import MetricsCollector, PerformanceMonitor


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data structure"""
    metric: str
    value: float
    threshold: float
    severity: AlertSeverity
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat()
        }


class MonitoringCollector:
    """Central monitoring collector"""
    
    def __init__(self):
        self.logger = create_logger("monitoring_collector")
        self.metrics_collector = MetricsCollector()
        self.performance_monitor = PerformanceMonitor()
        self.collected_metrics: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def collect_metrics(self, metrics_data: Dict[str, Any]):
        """Collect metrics data"""
        with self._lock:
            timestamped_metrics = {
                "timestamp": datetime.now().isoformat(),
                **metrics_data
            }
            self.collected_metrics.append(timestamped_metrics)
            
            # Keep only recent metrics (last 1000 entries)
            if len(self.collected_metrics) > 1000:
                self.collected_metrics = self.collected_metrics[-1000:]
    
    def get_recent_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent metrics"""
        with self._lock:
            return self.collected_metrics[-limit:]
    
    def log_metrics_summary(self):
        """Log metrics summary"""
        recent_metrics = self.get_recent_metrics(10)
        if recent_metrics:
            summary = self._calculate_metrics_summary(recent_metrics)
            self.logger.info(
                "Metrics summary collected",
                metrics_count=len(recent_metrics),
                summary=summary
            )
    
    def _calculate_metrics_summary(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics for metrics"""
        if not metrics:
            return {}
        
        # Extract numeric metrics
        numeric_fields = {}
        for metric in metrics:
            for key, value in metric.items():
                if isinstance(value, (int, float)) and key != "timestamp":
                    if key not in numeric_fields:
                        numeric_fields[key] = []
                    numeric_fields[key].append(value)
        
        # Calculate statistics
        summary = {}
        for field, values in numeric_fields.items():
            if values:
                summary[field] = {
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }
        
        return summary


class HealthChecker:
    """System health checker"""
    
    def __init__(self):
        self.logger = create_logger("health_checker")
        self.checks: Dict[str, Callable] = {
            "api": self._check_api_health,
            "cache": self._check_cache_health,
            "database": self._check_database_health,
            "memory": self._check_memory_health,
            "disk": self._check_disk_health
        }
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        overall_healthy = True
        
        for component, check_func in self.checks.items():
            try:
                is_healthy = await self._run_check(check_func)
                health_status["components"][component] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "checked_at": datetime.now().isoformat()
                }
                
                if not is_healthy:
                    overall_healthy = False
                    
            except Exception as e:
                health_status["components"][component] = {
                    "status": "error",
                    "error": str(e),
                    "checked_at": datetime.now().isoformat()
                }
                overall_healthy = False
        
        health_status["status"] = "healthy" if overall_healthy else "unhealthy"
        
        # Log health status
        self.logger.info(
            "Health check completed",
            overall_status=health_status["status"],
            components_status={k: v["status"] for k, v in health_status["components"].items()}
        )
        
        return health_status
    
    async def _run_check(self, check_func: Callable) -> bool:
        """Run individual health check"""
        if asyncio.iscoroutinefunction(check_func):
            return await check_func()
        else:
            return check_func()
    
    def _check_api_health(self) -> bool:
        """Check API health"""
        # Mock API health check
        # In real implementation, this would ping the API endpoints
        return True
    
    def _check_cache_health(self) -> bool:
        """Check cache health"""
        # Mock cache health check
        # In real implementation, this would test cache operations
        return True
    
    def _check_database_health(self) -> bool:
        """Check database health"""
        # Mock database health check
        # In real implementation, this would test database connectivity
        return True
    
    def _check_memory_health(self) -> bool:
        """Check memory health"""
        try:
            memory = psutil.virtual_memory()
            return memory.percent < 90  # Less than 90% memory usage
        except Exception:
            return False
    
    def _check_disk_health(self) -> bool:
        """Check disk health"""
        try:
            disk = psutil.disk_usage('/')
            return disk.percent < 85  # Less than 85% disk usage
        except Exception:
            return False


class AlertManager:
    """Alert management system"""
    
    def __init__(self):
        self.logger = create_logger("alert_manager")
        self.thresholds: Dict[str, float] = {}
        self.alerts_history: deque = deque(maxlen=1000)
        self.rate_limiting: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.max_alerts_per_minute = 10
        self.cooldown_minutes = 5
    
    def configure_thresholds(self, thresholds: Dict[str, float]):
        """Configure alert thresholds"""
        self.thresholds.update(thresholds)
        self.logger.info("Alert thresholds configured", thresholds=thresholds)
    
    def configure_rate_limiting(self, max_alerts_per_minute: int, cooldown_minutes: int):
        """Configure rate limiting for alerts"""
        self.max_alerts_per_minute = max_alerts_per_minute
        self.cooldown_minutes = cooldown_minutes
    
    def check_metrics(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check metrics against thresholds and generate alerts"""
        alerts = []
        
        for metric, value in metrics.items():
            if metric in self.thresholds and isinstance(value, (int, float)):
                threshold = self.thresholds[metric]
                
                if value > threshold:
                    # Check rate limiting
                    if self._should_send_alert(metric):
                        severity = self._determine_severity(metric, value, threshold)
                        alert = Alert(
                            metric=metric,
                            value=value,
                            threshold=threshold,
                            severity=severity,
                            message=f"{metric} value {value} exceeds threshold {threshold}"
                        )
                        
                        alerts.append(alert)
                        self._record_alert(alert)
        
        return alerts
    
    def _should_send_alert(self, metric: str) -> bool:
        """Check if alert should be sent based on rate limiting"""
        now = datetime.now()
        metric_data = self.rate_limiting[metric]
        
        # Check cooldown
        last_alert = metric_data.get("last_alert")
        if last_alert and (now - last_alert).total_seconds() < self.cooldown_minutes * 60:
            return False
        
        # Check rate limit
        recent_alerts = metric_data.get("recent_alerts", [])
        one_minute_ago = now - timedelta(minutes=1)
        recent_alerts = [alert_time for alert_time in recent_alerts if alert_time > one_minute_ago]
        
        if len(recent_alerts) >= self.max_alerts_per_minute:
            return False
        
        return True
    
    def _record_alert(self, alert: Alert):
        """Record alert for rate limiting"""
        now = datetime.now()
        metric_data = self.rate_limiting[alert.metric]
        
        metric_data["last_alert"] = now
        if "recent_alerts" not in metric_data:
            metric_data["recent_alerts"] = []
        metric_data["recent_alerts"].append(now)
        
        # Keep only recent alerts
        one_minute_ago = now - timedelta(minutes=1)
        metric_data["recent_alerts"] = [
            alert_time for alert_time in metric_data["recent_alerts"] 
            if alert_time > one_minute_ago
        ]
        
        # Add to history
        self.alerts_history.append(alert)
        
        # Log alert
        self.logger.warning(
            "Alert generated",
            metric=alert.metric,
            value=alert.value,
            threshold=alert.threshold,
            severity=alert.severity.value
        )
    
    def _determine_severity(self, metric: str, value: float, threshold: float) -> AlertSeverity:
        """Determine alert severity based on how much threshold is exceeded"""
        excess_ratio = (value - threshold) / threshold
        
        if excess_ratio > 0.5:  # 50% above threshold
            return AlertSeverity.CRITICAL
        elif excess_ratio > 0.2:  # 20% above threshold
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by severity"""
        alerts = list(self.alerts_history)
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        # Return alerts from last 24 hours
        one_day_ago = datetime.now() - timedelta(days=1)
        return [alert for alert in alerts if alert.timestamp > one_day_ago]


class DashboardDataProvider:
    """Provide data for monitoring dashboard"""
    
    def __init__(self):
        self.logger = create_logger("dashboard_provider")
        self.monitoring_collector = MonitoringCollector()
        self.health_checker = HealthChecker()
        self.alert_manager = AlertManager()
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        # Get current metrics
        current_metrics = self._get_current_metrics()
        
        # Get historical data
        historical_data = self._get_historical_metrics()
        
        # Get health status
        health_status = await self.health_checker.check_health()
        
        # Get active alerts
        alerts = self.alert_manager.get_active_alerts()
        
        dashboard_data = {
            "current_metrics": current_metrics,
            "historical_data": historical_data,
            "system_health": health_status,
            "alerts": [alert.to_dict() for alert in alerts],
            "summary": self.calculate_summary_stats(historical_data),
            "last_updated": datetime.now().isoformat()
        }
        
        return dashboard_data
    
    def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            # System metrics
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            disk = psutil.disk_usage('/')
            
            return {
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / 1024 / 1024,
                "cpu_percent": cpu_percent,
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / 1024 / 1024 / 1024
            }
        except Exception as e:
            self.logger.error(f"Error getting current metrics: {e}")
            return {}
    
    def _get_historical_metrics(self) -> List[Dict[str, Any]]:
        """Get historical metrics data"""
        return self.monitoring_collector.get_recent_metrics(100)
    
    def format_time_series(self, data: List[Dict[str, Any]], metric_name: str) -> Dict[str, Any]:
        """Format data for time series charts"""
        time_series = {
            "metric": metric_name,
            "data": []
        }
        
        for point in data:
            if "timestamp" in point and metric_name in point:
                time_series["data"].append({
                    "x": point["timestamp"],
                    "y": point[metric_name]
                })
        
        return time_series
    
    def calculate_summary_stats(self, metrics_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics for dashboard"""
        if not metrics_history:
            return {}
        
        summary = {}
        
        # Extract numeric fields
        numeric_fields = {}
        for metric in metrics_history:
            for key, value in metric.items():
                if isinstance(value, (int, float)) and key != "timestamp":
                    if key not in numeric_fields:
                        numeric_fields[key] = []
                    numeric_fields[key].append(value)
        
        # Calculate stats
        for field, values in numeric_fields.items():
            if values:
                summary[field] = {
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "latest": values[-1] if values else 0
                }
        
        return summary


class SystemMetrics:
    """System metrics collector with automatic logging"""
    
    def __init__(self, log_interval: float = 60.0):
        self.logger = create_logger("system_metrics")
        self.log_interval = log_interval
        self.thresholds: Dict[str, float] = {}
        self.is_collecting = False
        self.collection_task: Optional[asyncio.Task] = None
    
    def configure_thresholds(self, thresholds: Dict[str, float]):
        """Configure warning thresholds"""
        self.thresholds = thresholds
    
    def start_collection(self):
        """Start metrics collection"""
        if not self.is_collecting:
            self.is_collecting = True
            self.collection_task = asyncio.create_task(self._collection_loop())
    
    def stop_collection(self):
        """Stop metrics collection"""
        self.is_collecting = False
        if self.collection_task:
            self.collection_task.cancel()
    
    async def _collection_loop(self):
        """Main collection loop"""
        while self.is_collecting:
            try:
                metrics = self._collect_system_metrics()
                
                # Log metrics
                self.logger.info("System metrics collected", **metrics)
                
                # Check thresholds
                self.check_thresholds(metrics)
                
                await asyncio.sleep(self.log_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(self.log_interval)
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        try:
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / 1024 / 1024 / 1024,
                "cpu_percent": cpu_percent,
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / 1024 / 1024 / 1024,
                "process_memory_mb": process_memory.rss / 1024 / 1024,
                "process_cpu_percent": process.cpu_percent()
            }
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return {}
    
    def check_thresholds(self, metrics: Dict[str, Any]):
        """Check metrics against warning thresholds"""
        for metric, value in metrics.items():
            if metric in self.thresholds and isinstance(value, (int, float)):
                threshold = self.thresholds[metric]
                if value > threshold:
                    self.logger.warning(
                        f"{metric.replace('_', ' ').title()} exceeds threshold",
                        metric=metric,
                        value=value,
                        threshold=threshold,
                        percentage_over=((value - threshold) / threshold) * 100
                    )