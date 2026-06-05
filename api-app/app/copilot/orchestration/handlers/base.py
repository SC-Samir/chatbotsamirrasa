"""
Base classes for command handlers.

This module provides the foundation for all command handlers in the
orchestration engine, including the base handler class and decorator
for registering handlers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar, cast

from app.copilot.contracts import CommandContext, CommandRequest, CommandResult
from app.copilot.memory.service import MemoryService
from app.copilot.scalingo_ops.gateway import ScalingoOpsGateway

# Type variable for handler return type
T = TypeVar('T')

# Handler type alias
Handler = Callable[[CommandRequest], CommandResult]


@dataclass(frozen=True)
class HandlerConfig:
    """
    Configuration for a command handler.
    
    This class holds metadata about a command handler that is used
    for validation, routing, and documentation purposes.
    """
    # Entities required for this command
    required_entities: Tuple[str, ...] = ()
    
    # Whether this command is idempotent (can be safely retried)
    idempotent: bool = True
    
    # Whether this command requires app and region to be specified
    requires_app_region: bool = False
    
    # Whether this command modifies state
    is_mutating: bool = False
    
    # Whether this command is destructive (requires confirmation)
    is_destructive: bool = False
    
    # Human-readable description of the command
    description: str = ""
    
    # Example usage
    example: str = ""


@dataclass(frozen=True)
class HandlerRegistry:
    """
    Registry of all command handlers.
    
    This class maintains a mapping from command names to their
    corresponding handler functions and metadata.
    """
    handlers: Dict[str, Handler] = field(default_factory=dict)
    metadata: Dict[str, HandlerConfig] = field(default_factory=dict)
    
    def register(
        self,
        command_name: str,
        handler: Handler,
        config: Optional[HandlerConfig] = None,
    ) -> None:
        """Register a handler for a command."""
        self.handlers[command_name] = handler
        if config:
            self.metadata[command_name] = config
    
    def get_handler(self, command_name: str) -> Optional[Handler]:
        """Get the handler for a command."""
        return self.handlers.get(command_name)
    
    def get_metadata(self, command_name: str) -> Optional[HandlerConfig]:
        """Get the metadata for a command."""
        return self.metadata.get(command_name)
    
    def is_destructive(self, command_name: str) -> bool:
        """Check if a command is destructive."""
        meta = self.metadata.get(command_name)
        return bool(meta and meta.is_destructive)
    
    def get_all_commands(self) -> list[str]:
        """Get list of all registered command names."""
        return list(self.handlers.keys())


class BaseCommandHandler:
    """
    Base class for all command handlers.
    
    This class provides common functionality and access to shared
    dependencies like the Scalingo gateway and memory service.
    """
    
    def __init__(
        self,
        gateway: ScalingoOpsGateway,
        memory: MemoryService,
    ):
        """
        Initialize the handler.
        
        Args:
            gateway: Gateway to Scalingo API operations
            memory: Memory service for session and fact storage
        """
        self.gateway = gateway
        self.memory = memory
    
    def _resolve_app_region(
        self,
        request: CommandRequest,
    ) -> Tuple[str, str]:
        """
        Resolve app name and region from request and context.
        
        Args:
            request: The command request
            
        Returns:
            Tuple of (app_name, region)
            
        Raises:
            ValueError: If app_name and region cannot be determined
        """
        snapshot = self.memory.snapshot(request.context.user_id, request.context.session_id)
        entities = dict(snapshot.session.get("entities", {}))
        entities.update(snapshot.facts)
        entities.update(request.entities)

        app_name = str(entities.get("app_name") or "")
        region = str(entities.get("region") or request.context.region_scope or "")
        if not app_name or not region:
            raise ValueError("app_name and region are required")
        return app_name, region
    
    def _get_entities(
        self,
        request: CommandRequest,
        required: Tuple[str, ...],
    ) -> Dict[str, Any]:
        """
        Get entities from request, merging with session facts.
        
        Args:
            request: The command request
            required: Required entity keys
            
        Returns:
            Dictionary of merged entities
        """
        snapshot = self.memory.snapshot(request.context.user_id, request.context.session_id)
        entities = dict(snapshot.session.get("entities", {}))
        entities.update(snapshot.facts)
        entities.update(request.entities)
        return entities
    
    def _missing_entities(
        self,
        request: CommandRequest,
        required: Tuple[str, ...],
        requires_app_region: bool = False,
    ) -> Tuple[str, ...]:
        """
        Check for missing required entities.
        
        Args:
            request: The command request
            required: Required entity keys
            requires_app_region: Whether app and region are required
            
        Returns:
            Tuple of missing entity names
        """
        missing: list[str] = []
        
        if requires_app_region:
            try:
                self._resolve_app_region(request)
            except ValueError:
                if not request.entities.get("app_name") and not request.context.app_scope:
                    missing.append("app_name")
                if not request.entities.get("region") and not request.context.region_scope:
                    missing.append("region")
        
        for key in required:
            if request.entities.get(key) is None or str(request.entities.get(key)).strip() == "":
                missing.append(key)
        
        return tuple(sorted(set(missing)))
    
    @staticmethod
    def _as_bool(value: Any) -> Optional[bool]:
        """
        Convert a value to boolean.
        
        Args:
            value: The value to convert
            
        Returns:
            Boolean value, or None if conversion is not possible
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            norm = value.strip().lower()
            if norm in {"true", "1", "yes", "on", "enabled"}:
                return True
            if norm in {"false", "0", "no", "off", "disabled"}:
                return False
        return None
    
    def _with_mutation_preview(
        self,
        request: CommandRequest,
        result: CommandResult,
    ) -> CommandResult:
        """
        Add mutation preview to result.
        
        Args:
            request: The command request
            result: The original result
            
        Returns:
            Result with preview information added
        """
        preview = self._preview_for(request)
        return CommandResult(
            event_type=result.event_type,
            status=result.status,
            human_message=f"Action preview: {preview}. {result.human_message}",
            structured_payload={**result.structured_payload, "preview": preview},
            next_actions=result.next_actions,
            risk_level=result.risk_level,
            action_id=result.action_id,
        )
    
    def _preview_for(self, request: CommandRequest) -> str:
        """
        Generate a preview string for a command.
        
        Args:
            request: The command request
            
        Returns:
            Preview string describing the command
        """
        payload = {k: v for k, v in request.entities.items() if k not in {"confirm_token"}}
        return f"{request.command} with {payload}"


# Protocol for handler classes
class CommandHandler:
    """
    Protocol for command handler classes.
    
    All command handlers should implement the 'handle' method
    that takes a CommandRequest and returns a CommandResult.
    """
    
    def handle(self, request: CommandRequest) -> CommandResult:
        """
        Handle a command request.
        
        Args:
            request: The command request
            
        Returns:
            The command result
        """
        raise NotImplementedError


def handler(
    command_name: str,
    config: Optional[HandlerConfig] = None,
) -> Callable[[type], type]:
    """
    Decorator to register a handler class with a command name.
    
    This decorator can be used to automatically register handler
    classes with the command engine.
    
    Args:
        command_name: The command name to register
        config: Optional handler configuration
        
    Returns:
        Decorator function
        
    Usage:
        @handler("apps.list", HandlerConfig(required_entities=("region",)))
        class AppListHandler(BaseCommandHandler):
            def handle(self, request: CommandRequest) -> CommandResult:
                # implementation
                pass
    """
    def decorator(cls: type) -> type:
        # Store the command name and config as class attributes
        setattr(cls, "_command_name", command_name)
        setattr(cls, "_handler_config", config or HandlerConfig())
        return cls
    return decorator
