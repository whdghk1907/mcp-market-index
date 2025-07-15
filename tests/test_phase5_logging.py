"""
Phase 5 TDD Tests - Logging and Monitoring Implementation
로깅 및 모니터링 구현 테스트
"""

import pytest
import asyncio
import json
import os
import tempfile
import time
from unittest.mock import Mock, patch, mock_open
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
import logging

from src.utils.logger import (
    StructuredLogger, 
    LogFormatter, 
    FileRotationHandler,
    LogConfig,
    LogLevel,
    create_logger
)
from src.utils.monitoring import (
    MonitoringCollector,
    HealthChecker,
    AlertManager,
    DashboardDataProvider,
    SystemMetrics,
    AlertSeverity
)
from src.utils.metrics import MetricsCollector, PerformanceMonitor


class TestStructuredLogging:
    """Test structured logging system"""
    
    def test_structured_log_formatter(self):
        """Test structured log formatting"""
        formatter = LogFormatter()
        
        # Create log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Add extra context
        record.user_id = "user_123"
        record.request_id = "req_456"
        record.market = "KOSPI"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        # Check structured format
        assert "timestamp" in log_data
        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["logger"] == "test_logger"
        assert log_data["module"] == "file"
        assert log_data["line"] == 123
        
        # Check context fields
        assert log_data["user_id"] == "user_123"
        assert log_data["request_id"] == "req_456"
        assert log_data["market"] == "KOSPI"
    
    def test_log_level_filtering(self):
        """Test log level filtering"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # Create logger with INFO level
            logger = create_logger(
                name="test_logger",
                level=LogLevel.INFO,
                file_path=str(log_file)
            )
            
            # Log messages at different levels
            logger.debug("Debug message")  # Should be filtered out
            logger.info("Info message")     # Should be included
            logger.warning("Warning message")  # Should be included
            logger.error("Error message")   # Should be included
            
            # Read log file
            with open(log_file, 'r') as f:
                log_content = f.read()
            
            # Check filtering
            assert "Debug message" not in log_content
            assert "Info message" in log_content
            assert "Warning message" in log_content
            assert "Error message" in log_content
    
    def test_console_and_file_output(self):
        """Test logging to both console and file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # Create logger with both handlers
            logger = create_logger(
                name="test_logger",
                level=LogLevel.INFO,
                file_path=str(log_file),
                console_output=True
            )
            
            test_message = "Test dual output message"
            
            # Capture console output
            with patch('sys.stdout') as mock_stdout:
                logger.info(test_message)
                
                # Check console output
                mock_stdout.write.assert_called()
                console_calls = [call.args[0] for call in mock_stdout.write.call_args_list]
                console_output = ''.join(console_calls)
                assert test_message in console_output
            
            # Check file output
            with open(log_file, 'r') as f:
                file_content = f.read()
            assert test_message in file_content
    
    def test_log_context_injection(self):
        """Test automatic context injection"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            logger = create_logger(
                name="test_logger",
                level=LogLevel.INFO,
                file_path=str(log_file)
            )
            
            # Set context
            context = {
                "correlation_id": "corr_123",
                "user_id": "user_456",
                "market": "KOSDAQ"
            }
            
            with logger.context(**context):
                logger.info("Test context message")
            
            # Read log file and check context was included
            with open(log_file, 'r') as f:
                log_content = f.read()
            
            log_data = json.loads(log_content.strip())
            
            # Check that context fields are present in the log
            assert log_data["correlation_id"] == "corr_123"
            assert log_data["user_id"] == "user_456"
            assert log_data["market"] == "KOSDAQ"
            assert log_data["message"] == "Test context message"
    
    def test_exception_logging(self):
        """Test exception logging with stack traces"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            logger = create_logger(
                name="test_logger",
                level=LogLevel.ERROR,
                file_path=str(log_file)
            )
            
            # Log an exception
            try:
                raise ValueError("Test exception")
            except ValueError:
                logger.exception("An error occurred")
            
            # Check log file contains stack trace
            with open(log_file, 'r') as f:
                log_content = f.read()
            
            log_data = json.loads(log_content.strip())
            assert log_data["level"] == "ERROR"
            assert log_data["message"] == "An error occurred"
            assert "exception" in log_data
            assert "ValueError: Test exception" in log_data["exception"]
            assert "traceback" in log_data


class TestFileRotationAndManagement:
    """Test log file rotation and management"""
    
    def test_log_file_rotation_by_size(self):
        """Test log file rotation based on file size"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # Create rotation handler with small max size
            rotation_handler = FileRotationHandler(
                file_path=str(log_file),
                max_size_mb=0.001,  # Very small for testing
                max_files=3
            )
            
            # Write enough data to trigger rotation
            large_message = "x" * 2000  # 2KB message
            
            for i in range(10):
                rotation_handler.emit(logging.LogRecord(
                    name="test",
                    level=logging.INFO,
                    pathname="test.py",
                    lineno=1,
                    msg=large_message,
                    args=(),
                    exc_info=None
                ))
            
            # Check that rotation occurred
            log_files = list(Path(temp_dir).glob("test.log*"))
            assert len(log_files) > 1  # Should have rotated files
            
            # Check max files limit
            assert len(log_files) <= 4  # Original + 3 rotated
    
    def test_log_file_rotation_by_time(self):
        """Test log file rotation based on time"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # Create rotation handler with time-based rotation
            rotation_handler = FileRotationHandler(
                file_path=str(log_file),
                rotation_interval="daily",
                max_files=5
            )
            
            # Mock different days
            with patch('src.utils.logger.datetime') as mock_datetime:
                # Day 1
                mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0, 0)
                mock_datetime.strftime = datetime.strftime
                
                rotation_handler.emit(logging.LogRecord(
                    name="test", level=logging.INFO, pathname="test.py",
                    lineno=1, msg="Day 1 message", args=(), exc_info=None
                ))
                
                # Day 2
                mock_datetime.now.return_value = datetime(2024, 1, 2, 10, 0, 0)
                
                rotation_handler.emit(logging.LogRecord(
                    name="test", level=logging.INFO, pathname="test.py",
                    lineno=1, msg="Day 2 message", args=(), exc_info=None
                ))
            
            # Should create time-based rotation
            rotation_handler.should_rotate()
    
    def test_log_cleanup_old_files(self):
        """Test cleanup of old log files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create old log files
            for i in range(10):
                old_file = Path(temp_dir) / f"old_{i}.log"
                old_file.write_text(f"Old log file {i}")
            
            rotation_handler = FileRotationHandler(
                file_path=str(Path(temp_dir) / "test.log"),
                max_files=3
            )
            
            # Cleanup old files
            rotation_handler.cleanup_old_files()
            
            # Check that only max_files remain
            remaining_files = list(Path(temp_dir).glob("*.log"))
            assert len(remaining_files) <= 3


class TestMonitoringAndMetrics:
    """Test monitoring and metrics collection integration"""
    
    @pytest.mark.asyncio
    async def test_monitoring_collector_integration(self):
        """Test monitoring collector with logging"""
        monitoring = MonitoringCollector()
        
        # Mock metrics data
        metrics_data = {
            "api_response_time": 0.150,
            "cache_hit_rate": 0.85,
            "error_rate": 0.02,
            "memory_usage_mb": 256.5,
            "concurrent_requests": 12
        }
        
        # Collect metrics
        monitoring.collect_metrics(metrics_data)
        
        # Should log the collection
        with patch.object(monitoring.logger, 'info') as mock_log:
            monitoring.log_metrics_summary()
            
            mock_log.assert_called()
            call_args = mock_log.call_args[0][0]
            assert "Metrics summary" in call_args
    
    @pytest.mark.asyncio
    async def test_health_checker(self):
        """Test system health checking"""
        health_checker = HealthChecker()
        
        # Mock healthy components
        with patch.object(health_checker, '_check_api_health', return_value=True), \
             patch.object(health_checker, '_check_cache_health', return_value=True), \
             patch.object(health_checker, '_check_database_health', return_value=True):
            
            health_status = await health_checker.check_health()
            
            assert health_status["status"] == "healthy"
            assert health_status["components"]["api"]["status"] == "healthy"
            assert health_status["components"]["cache"]["status"] == "healthy"
            assert health_status["components"]["database"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_checker_unhealthy(self):
        """Test health checker with unhealthy components"""
        health_checker = HealthChecker()
        
        # Mock unhealthy API
        with patch.object(health_checker, '_check_api_health', return_value=False), \
             patch.object(health_checker, '_check_cache_health', return_value=True), \
             patch.object(health_checker, '_check_database_health', return_value=True):
            
            health_status = await health_checker.check_health()
            
            assert health_status["status"] == "unhealthy"
            assert health_status["components"]["api"]["status"] == "unhealthy"
    
    def test_alert_manager_threshold_alerts(self):
        """Test alert manager threshold-based alerts"""
        alert_manager = AlertManager()
        
        # Configure thresholds
        alert_manager.configure_thresholds({
            "error_rate": 0.05,          # 5% error rate threshold
            "response_time": 1.0,        # 1 second response time threshold
            "memory_usage": 500.0        # 500MB memory threshold
        })
        
        # Test normal metrics (no alerts)
        normal_metrics = {
            "error_rate": 0.02,
            "response_time": 0.5,
            "memory_usage": 300.0
        }
        
        alerts = alert_manager.check_metrics(normal_metrics)
        assert len(alerts) == 0
        
        # Test threshold breaches
        bad_metrics = {
            "error_rate": 0.08,          # Above threshold
            "response_time": 1.5,        # Above threshold
            "memory_usage": 600.0        # Above threshold
        }
        
        alerts = alert_manager.check_metrics(bad_metrics)
        assert len(alerts) == 3
        
        # Check alert details
        error_alert = next(a for a in alerts if a.metric == "error_rate")
        assert error_alert.severity == AlertSeverity.CRITICAL
        assert error_alert.value == 0.08
        assert error_alert.threshold == 0.05
    
    def test_alert_manager_rate_limiting(self):
        """Test alert rate limiting to prevent spam"""
        alert_manager = AlertManager()
        
        # Configure rate limiting
        alert_manager.configure_rate_limiting(
            max_alerts_per_minute=3,
            cooldown_minutes=5
        )
        
        # Send multiple alerts for same metric
        bad_metrics = {"error_rate": 0.1}
        
        alerts_sent = []
        for i in range(10):
            alerts = alert_manager.check_metrics(bad_metrics)
            alerts_sent.extend(alerts)
        
        # Should be rate limited
        assert len(alerts_sent) <= 3


class TestDashboardDataProvider:
    """Test dashboard data provider"""
    
    @pytest.mark.asyncio
    async def test_dashboard_data_aggregation(self):
        """Test dashboard data aggregation"""
        dashboard = DashboardDataProvider()
        
        # Mock historical data
        with patch.object(dashboard, '_get_historical_metrics') as mock_historical:
            mock_historical.return_value = [
                {"timestamp": "2024-01-01T10:00:00", "response_time": 0.1, "error_rate": 0.01},
                {"timestamp": "2024-01-01T10:01:00", "response_time": 0.2, "error_rate": 0.02},
                {"timestamp": "2024-01-01T10:02:00", "response_time": 0.15, "error_rate": 0.01}
            ]
            
            dashboard_data = await dashboard.get_dashboard_data()
            
            assert "current_metrics" in dashboard_data
            assert "historical_data" in dashboard_data
            assert "alerts" in dashboard_data
            assert "system_health" in dashboard_data
    
    def test_dashboard_data_time_series(self):
        """Test time series data formatting for dashboard"""
        dashboard = DashboardDataProvider()
        
        # Raw metrics data
        raw_data = [
            {"timestamp": "2024-01-01T10:00:00", "value": 0.1},
            {"timestamp": "2024-01-01T10:01:00", "value": 0.2},
            {"timestamp": "2024-01-01T10:02:00", "value": 0.15}
        ]
        
        time_series = dashboard.format_time_series(raw_data, "response_time")
        
        assert time_series["metric"] == "response_time"
        assert len(time_series["data"]) == 3
        assert time_series["data"][0]["x"] == "2024-01-01T10:00:00"
        assert time_series["data"][0]["y"] == 0.1
    
    def test_dashboard_summary_statistics(self):
        """Test dashboard summary statistics calculation"""
        dashboard = DashboardDataProvider()
        
        metrics_history = [
            {"response_time": 0.1, "error_rate": 0.01, "memory_usage": 200},
            {"response_time": 0.2, "error_rate": 0.02, "memory_usage": 250},
            {"response_time": 0.15, "error_rate": 0.01, "memory_usage": 225}
        ]
        
        summary = dashboard.calculate_summary_stats(metrics_history)
        
        assert summary["response_time"]["avg"] == 0.15
        assert summary["response_time"]["min"] == 0.1
        assert summary["response_time"]["max"] == 0.2
        
        assert summary["error_rate"]["avg"] == pytest.approx(0.0133, rel=1e-2)
        assert summary["memory_usage"]["avg"] == 225.0


class TestSystemMetricsIntegration:
    """Test system metrics integration with logging"""
    
    @pytest.mark.asyncio
    async def test_system_metrics_logging(self):
        """Test automatic system metrics logging"""
        system_metrics = SystemMetrics(log_interval=1)  # 1 second for testing
        
        with patch.object(system_metrics.logger, 'info') as mock_log:
            # Start metrics collection
            system_metrics.start_collection()
            
            # Wait for at least one collection cycle
            await asyncio.sleep(1.2)
            
            # Stop collection
            system_metrics.stop_collection()
            
            # Should have logged metrics
            mock_log.assert_called()
            
            # Check log content
            call_args = [call.args[0] for call in mock_log.call_args_list]
            metrics_logs = [log for log in call_args if "System metrics" in log]
            assert len(metrics_logs) > 0
    
    def test_metrics_threshold_warnings(self):
        """Test metrics threshold warning logs"""
        system_metrics = SystemMetrics()
        
        # Configure warning thresholds
        system_metrics.configure_thresholds({
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0
        })
        
        with patch.object(system_metrics.logger, 'warning') as mock_warning:
            # Simulate high CPU usage
            high_metrics = {
                "cpu_percent": 85.0,  # Above threshold
                "memory_percent": 70.0,
                "disk_percent": 60.0
            }
            
            system_metrics.check_thresholds(high_metrics)
            
            # Should log warning
            mock_warning.assert_called()
            warning_message = mock_warning.call_args[0][0]
            assert "CPU usage" in warning_message
            assert "85.0%" in warning_message


class TestLogConfiguration:
    """Test log configuration and setup"""
    
    def test_log_config_from_dict(self):
        """Test log configuration from dictionary"""
        config_dict = {
            "level": "INFO",
            "format": "json",
            "handlers": {
                "file": {
                    "enabled": True,
                    "path": "/tmp/test.log",
                    "rotation": {
                        "max_size_mb": 10,
                        "max_files": 5
                    }
                },
                "console": {
                    "enabled": True,
                    "format": "simple"
                }
            }
        }
        
        log_config = LogConfig.from_dict(config_dict)
        
        assert log_config.level == LogLevel.INFO
        assert log_config.format_type == "json"
        assert log_config.file_handler_enabled == True
        assert log_config.console_handler_enabled == True
        assert log_config.file_path == "/tmp/test.log"
        assert log_config.max_size_mb == 10
        assert log_config.max_files == 5
    
    def test_log_config_environment_override(self):
        """Test log configuration override from environment"""
        with patch.dict(os.environ, {
            'LOG_LEVEL': 'DEBUG',
            'LOG_FILE_PATH': '/custom/log/path.log',
            'LOG_MAX_SIZE_MB': '20'
        }):
            config = LogConfig.from_environment()
            
            assert config.level == LogLevel.DEBUG
            assert config.file_path == '/custom/log/path.log'
            assert config.max_size_mb == 20
    
    def test_logger_factory_creation(self):
        """Test logger factory for consistent logger creation"""
        # Test with default config
        logger1 = create_logger("service1")
        logger2 = create_logger("service2")
        
        # Should be different loggers but same configuration
        assert logger1.name == "service1"
        assert logger2.name == "service2"
        
        # Test with custom config
        custom_logger = create_logger(
            "custom",
            level=LogLevel.DEBUG,
            file_path="/tmp/custom.log"
        )
        
        assert custom_logger.level == logging.DEBUG