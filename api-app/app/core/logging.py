"""
Configuration du système de logging.

Structured logging configuration for the application.
Provides a StructuredLogger class that formats logs with consistent structure.
"""
import logging
import sys
from typing import Optional
from app.config import settings


class StructuredLogger:
    """Logger structuré pour l'application."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO if not settings.debug else logging.DEBUG)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def info(self, message: str, **kwargs):
        """Log un message d'information."""
        self.logger.info(self._format_message(message, **kwargs))
    
    def error(self, message: str, **kwargs):
        """Log un message d'erreur."""
        self.logger.error(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log un message d'avertissement."""
        self.logger.warning(self._format_message(message, **kwargs))
    
    def debug(self, message: str, **kwargs):
        """Log un message de debug."""
        self.logger.debug(self._format_message(message, **kwargs))
    
    def _format_message(self, message: str, **kwargs) -> str:
        """Formate le message avec les métadonnées."""
        if kwargs:
            metadata = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
            return f"{message} | {metadata}"
        return message


# Loggers pour différents composants
websocket_logger = StructuredLogger("websocket")
scalingo_logger = StructuredLogger("scalingo")
logs_service_logger = StructuredLogger("logs_service")
intent_logger = StructuredLogger("intent_handler")
