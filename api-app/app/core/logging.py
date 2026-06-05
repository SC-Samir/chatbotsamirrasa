"""
Configuration du système de logging.

Structured logging configuration for the application.
Provides a StructuredLogger class that formats logs with consistent structure.
"""
import json
import logging
import sys
import threading
from contextlib import contextmanager
from typing import Any, Dict, Optional

from app.config import settings


# Thread-local storage for request context
_request_context = threading.local()


class RequestContext:
    """
    Request context for structured logging.
    
    Contains information that should be included in all log messages
    for a given request, such as request ID, user ID, session ID, etc.
    """
    
    def __init__(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        **extra: Any,
    ):
        self.request_id = request_id
        self.user_id = user_id
        self.session_id = session_id
        self.client_ip = client_ip
        self.extra = extra
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        result = {}
        if self.request_id:
            result["request_id"] = self.request_id
        if self.user_id:
            result["user_id"] = self.user_id
        if self.session_id:
            result["session_id"] = self.session_id
        if self.client_ip:
            result["client_ip"] = self.client_ip
        result.update(self.extra)
        return result


@contextmanager
def request_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    client_ip: Optional[str] = None,
    **extra: Any,
):
    """
    Context manager for setting request context.
    
    Usage:
        with request_context(request_id="abc123", user_id="user456"):
            logger.info("Processing request")
    """
    previous = getattr(_request_context, "value", None)
    _request_context.value = RequestContext(
        request_id=request_id,
        user_id=user_id,
        session_id=session_id,
        client_ip=client_ip,
        **extra,
    )
    try:
        yield
    finally:
        _request_context.value = previous


def get_request_context() -> Optional[RequestContext]:
    """Get the current request context."""
    return getattr(_request_context, "value", None)


class StructuredLogger:
    """
    Structured logger for the application.
    
    Formats log messages with consistent structure and includes
    request context automatically. Supports both human-readable
    and JSON output formats.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name
        
        # Set log level based on settings
        level = logging.DEBUG if settings.debug else logging.INFO
        self.logger.setLevel(level)
        
        # Only add handler if no handlers exist
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _get_context_dict(self) -> Dict[str, Any]:
        """Get current request context as dictionary."""
        context = get_request_context()
        if context:
            return context.to_dict()
        return {}
    
    def _format_message(self, message: str, level: str, **kwargs) -> str:
        """Format log message with metadata."""
        # Get request context
        context_dict = self._get_context_dict()
        
        # Merge kwargs with context
        all_fields = {**context_dict, **kwargs}
        
        # If there are additional fields, format them
        if all_fields:
            if settings.debug:
                # In debug mode, include all fields in the message
                metadata = " | ".join([f"{k}={v}" for k, v in all_fields.items()])
                return f"{message} | {metadata}"
            else:
                # In production, just append the message
                # (structured fields are handled by the logging system)
                return message
        return message
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal logging method."""
        formatted_message = self._format_message(message, level, **kwargs)
        
        # Get the appropriate logging method
        log_method = getattr(self.logger, level.lower())
        log_method(formatted_message)
    
    def info(self, message: str, **kwargs):
        """Log an information message."""
        self._log("info", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log an error message."""
        self._log("error", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log a warning message."""
        self._log("warning", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log a debug message."""
        self._log("debug", message, **kwargs)
    
    def to_json(self, message: str, level: str = "info", **kwargs) -> str:
        """
        Format log entry as JSON string.
        
        Useful for external log aggregation systems.
        """
        import datetime
        
        context_dict = self._get_context_dict()
        all_fields = {**context_dict, **kwargs}
        
        log_entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "level": level.upper(),
            "logger": self.name,
            "message": message,
            **all_fields,
        }
        return json.dumps(log_entry)


# Loggers pour différents composants
websocket_logger = StructuredLogger("websocket")
scalingo_logger = StructuredLogger("scalingo")
logs_service_logger = StructuredLogger("logs_service")
intent_logger = StructuredLogger("intent_handler")
