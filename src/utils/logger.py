"""
Logging utilities for MCP Market Index Server
"""
import logging
import logging.handlers
import sys
import json
import os
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from enum import Enum
from contextlib import contextmanager


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Setup logger with console and file handlers
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"{name.replace('.', '_')}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger


class StructuredLogger:
    """Structured logging helper"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_api_call(self, endpoint: str, params: dict, response_time: float, status_code: Optional[int] = None):
        """Log API call with structured data"""
        self.logger.info(
            f"API_CALL endpoint={endpoint} params={params} "
            f"response_time={response_time:.3f}s status_code={status_code}"
        )
    
    def log_cache_hit(self, key: str, ttl_remaining: float):
        """Log cache hit"""
        self.logger.debug(f"CACHE_HIT key={key} ttl_remaining={ttl_remaining:.1f}s")
    
    def log_cache_miss(self, key: str):
        """Log cache miss"""
        self.logger.debug(f"CACHE_MISS key={key}")
    
    def log_error(self, error: Exception, context: dict = None):
        """Log error with context"""
        context_str = f" context={context}" if context else ""
        self.logger.error(f"ERROR {type(error).__name__}: {str(error)}{context_str}")
    
    def log_performance(self, operation: str, duration: float, metadata: dict = None):
        """Log performance metrics"""
        metadata_str = f" metadata={metadata}" if metadata else ""
        self.logger.info(f"PERFORMANCE operation={operation} duration={duration:.3f}s{metadata_str}")


class LogLevel(Enum):
    """Log levels enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormatter(logging.Formatter):
    """Structured JSON log formatter"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                'filename', 'module', 'lineno', 'funcName', 'created', 
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'exc_info', 'exc_text', 'stack_info'
            ]:
                extra_fields[key] = value
        
        if extra_fields:
            log_data.update(extra_fields)
        
        # Add traceback if present
        if hasattr(record, 'exc_text') and record.exc_text:
            log_data["traceback"] = record.exc_text
        
        return json.dumps(log_data, ensure_ascii=False)


class FileRotationHandler(logging.handlers.RotatingFileHandler):
    """Enhanced file rotation handler"""
    
    def __init__(self, file_path: str, max_size_mb: float = 10.0, 
                 max_files: int = 5, rotation_interval: Optional[str] = None):
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.max_files = max_files
        self.rotation_interval = rotation_interval
        self.last_rotation = datetime.now()
        
        super().__init__(
            filename=file_path,
            maxBytes=self.max_size_bytes,
            backupCount=max_files
        )
    
    def should_rotate(self) -> bool:
        """Check if rotation should occur"""
        # Size-based rotation
        if self.stream and self.stream.tell() >= self.maxBytes:
            return True
        
        # Time-based rotation
        if self.rotation_interval:
            now = datetime.now()
            if self.rotation_interval == "daily":
                return now.date() > self.last_rotation.date()
            elif self.rotation_interval == "hourly":
                return now.hour != self.last_rotation.hour
        
        return False
    
    def do_rotate(self):
        """Perform rotation"""
        if self.should_rotate():
            super().doRollover()
            self.last_rotation = datetime.now()
    
    def emit(self, record: logging.LogRecord):
        """Emit log record with rotation check"""
        try:
            self.do_rotate()
            super().emit(record)
        except Exception:
            self.handleError(record)
    
    def cleanup_old_files(self):
        """Clean up old log files beyond max_files"""
        log_dir = Path(self.baseFilename).parent
        log_name = Path(self.baseFilename).stem
        
        # Find all rotated log files
        log_files = list(log_dir.glob(f"{log_name}*"))
        
        # Sort by creation time and keep only max_files
        log_files.sort(key=lambda x: x.stat().st_ctime, reverse=True)
        
        for old_file in log_files[self.max_files:]:
            try:
                old_file.unlink()
            except OSError:
                pass


class LogConfig:
    """Log configuration class"""
    
    def __init__(self):
        self.level = LogLevel.INFO
        self.format_type = "json"
        self.file_handler_enabled = True
        self.console_handler_enabled = True
        self.file_path = "logs/app.log"
        self.max_size_mb = 10.0
        self.max_files = 5
        self.rotation_interval = None
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'LogConfig':
        """Create config from dictionary"""
        config = cls()
        
        if "level" in config_dict:
            config.level = LogLevel(config_dict["level"])
        
        if "format" in config_dict:
            config.format_type = config_dict["format"]
        
        handlers = config_dict.get("handlers", {})
        
        # File handler config
        file_config = handlers.get("file", {})
        config.file_handler_enabled = file_config.get("enabled", True)
        config.file_path = file_config.get("path", "logs/app.log")
        
        rotation = file_config.get("rotation", {})
        config.max_size_mb = rotation.get("max_size_mb", 10.0)
        config.max_files = rotation.get("max_files", 5)
        config.rotation_interval = rotation.get("interval")
        
        # Console handler config
        console_config = handlers.get("console", {})
        config.console_handler_enabled = console_config.get("enabled", True)
        
        return config
    
    @classmethod
    def from_environment(cls) -> 'LogConfig':
        """Create config from environment variables"""
        config = cls()
        
        # Environment variable mappings
        if "LOG_LEVEL" in os.environ:
            config.level = LogLevel(os.environ["LOG_LEVEL"])
        
        if "LOG_FILE_PATH" in os.environ:
            config.file_path = os.environ["LOG_FILE_PATH"]
        
        if "LOG_MAX_SIZE_MB" in os.environ:
            config.max_size_mb = float(os.environ["LOG_MAX_SIZE_MB"])
        
        if "LOG_MAX_FILES" in os.environ:
            config.max_files = int(os.environ["LOG_MAX_FILES"])
        
        if "LOG_ROTATION_INTERVAL" in os.environ:
            config.rotation_interval = os.environ["LOG_ROTATION_INTERVAL"]
        
        return config


class StructuredLogger:
    """Enhanced structured logging helper"""
    
    def __init__(self, name: str, config: Optional[LogConfig] = None):
        self.name = name
        self.config = config or LogConfig()
        self.logger = logging.getLogger(name)
        self._context_storage = threading.local()
        
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger with handlers"""
        self.logger.setLevel(getattr(logging, self.config.level.value))
        self.logger.handlers.clear()
        
        # Setup handlers based on config
        if self.config.console_handler_enabled:
            self._add_console_handler()
        
        if self.config.file_handler_enabled:
            self._add_file_handler()
    
    def _add_console_handler(self):
        """Add console handler"""
        handler = logging.StreamHandler(sys.stdout)
        
        if self.config.format_type == "json":
            handler.setFormatter(LogFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
        
        self.logger.addHandler(handler)
    
    def _add_file_handler(self):
        """Add file handler with rotation"""
        # Ensure log directory exists
        Path(self.config.file_path).parent.mkdir(parents=True, exist_ok=True)
        
        handler = FileRotationHandler(
            file_path=self.config.file_path,
            max_size_mb=self.config.max_size_mb,
            max_files=self.config.max_files,
            rotation_interval=self.config.rotation_interval
        )
        
        handler.setFormatter(LogFormatter())
        self.logger.addHandler(handler)
    
    @contextmanager
    def context(self, **context_data):
        """Context manager for adding context to logs"""
        old_context = getattr(self._context_storage, 'context', {})
        new_context = {**old_context, **context_data}
        self._context_storage.context = new_context
        
        try:
            yield
        finally:
            self._context_storage.context = old_context
    
    def _get_context(self) -> Dict[str, Any]:
        """Get current context"""
        return getattr(self._context_storage, 'context', {})
    
    def _log_with_context(self, level: int, message: str, **extra):
        """Log message with context"""
        context = self._get_context()
        all_extra = {**context, **extra}
        self.logger.log(level, message, extra=all_extra)
    
    def debug(self, message: str, **extra):
        """Log debug message"""
        self._log_with_context(logging.DEBUG, message, **extra)
    
    def info(self, message: str, **extra):
        """Log info message"""
        self._log_with_context(logging.INFO, message, **extra)
    
    def warning(self, message: str, **extra):
        """Log warning message"""
        self._log_with_context(logging.WARNING, message, **extra)
    
    def error(self, message: str, **extra):
        """Log error message"""
        self._log_with_context(logging.ERROR, message, **extra)
    
    def critical(self, message: str, **extra):
        """Log critical message"""
        self._log_with_context(logging.CRITICAL, message, **extra)
    
    def exception(self, message: str, **extra):
        """Log exception with traceback"""
        self._log_with_context(logging.ERROR, message, exc_info=True, **extra)


def create_logger(name: str, level: LogLevel = LogLevel.INFO, 
                 file_path: Optional[str] = None, 
                 console_output: bool = True) -> StructuredLogger:
    """
    Factory function to create consistent loggers
    
    Args:
        name: Logger name
        level: Log level
        file_path: File path for file handler
        console_output: Enable console output
        
    Returns:
        Configured StructuredLogger
    """
    config = LogConfig()
    config.level = level
    config.console_handler_enabled = console_output
    
    if file_path:
        config.file_path = file_path
        config.file_handler_enabled = True
    
    return StructuredLogger(name, config)