"""
Async command orchestration engine for processing user commands.

This module contains the async command registry and execution engine
that processes incoming commands, validates them, and executes the
corresponding actions against the Scalingo API.

The engine uses a modular handler system where each command type
has its own handler class, making the code more maintainable and testable.
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from app.copilot.contracts import CommandContext, CommandRequest, CommandResult
from app.copilot.memory.service import MemoryService
from app.copilot.orchestration.handlers.async_base import (
    AsyncBaseCommandHandler,
    AsyncCommandHandler,
    AsyncHandlerConfig,
    AsyncHandlerRegistry,
)
from app.copilot.scalingo_ops.gateway import ScalingoOpsGateway


@dataclass(frozen=True)
class AsyncCommandMetadata:
    """
    Metadata for an async command.
    
    This is a legacy class for backward compatibility. New code should use
    AsyncHandlerConfig from the handlers.async_base module.
    """
    required_entities: Tuple[str, ...] = ()
    idempotent: bool = True
    requires_app_region: bool = False
    is_mutating: bool = False
    is_destructive: bool = False


class AsyncCommandEngine:
    """
    Async command execution engine.
    
    This class is responsible for:
    - Maintaining a registry of all available async commands
    - Validating command requests
    - Executing the appropriate async handler for each command
    - Managing confirmation workflows for destructive actions
    """
    
    def __init__(self, gateway: ScalingoOpsGateway, memory: MemoryService):
        """
        Initialize the async command engine.
        
        Args:
            gateway: Gateway to Scalingo API operations
            memory: Memory service for session and fact storage
        """
        self.gateway = gateway
        self.memory = memory
        self.registry = AsyncHandlerRegistry()
        self.metadata: Dict[str, AsyncCommandMetadata] = {}
        
        # Load and register all async handlers
        self._load_handlers()
        
        # Set up legacy metadata for backward compatibility
        self._setup_legacy_metadata()
    
    def _load_handlers(self) -> None:
        """
        Discover and register all async handler classes from the handlers package.
        
        This method scans the handlers directory and registers any class
        that has been decorated with the @async_handler decorator.
        """
        from app.copilot.orchestration import handlers
        
        # Get the handlers package path
        handlers_path = handlers.__path__
        
        # Import all submodules
        for importer, modname, ispkg in pkgutil.iter_modules(handlers_path):
            if modname != "__init__" and modname.startswith("async_") and modname.endswith("_handlers"):
                full_modname = f"{handlers.__name__}.{modname}"
                try:
                    module = importlib.import_module(full_modname)
                    self._register_handlers_from_module(module)
                except ImportError as e:
                    # Log the error but don't fail - this allows for optional handler modules
                    print(f"Warning: Could not import async handler module {full_modname}: {e}")
        
        # Also register handlers defined directly in __init__.py
        self._register_handlers_from_module(handlers)
    
    def _register_handlers_from_module(self, module: Any) -> None:
        """
        Register all async handler classes from a module.
        
        Args:
            module: The module to scan for handler classes
        """
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and hasattr(obj, "_async_command_name"):
                self._register_handler_class(obj)
    
    def _register_handler_class(self, handler_class: Type[AsyncBaseCommandHandler]) -> None:
        """
        Register an async handler class with the engine.
        
        Args:
            handler_class: The async handler class to register
        """
        command_name = getattr(handler_class, "_async_command_name", None)
        config = getattr(handler_class, "_async_handler_config", AsyncHandlerConfig())
        
        if not command_name:
            return
        
        # Create an instance of the handler
        handler_instance = handler_class(self.gateway, self.memory)
        
        # Register the handler's handle_async method
        self.registry.register(command_name, handler_instance.handle_async, config)
        
        # Store metadata for backward compatibility
        self.metadata[command_name] = AsyncCommandMetadata(
            required_entities=config.required_entities,
            idempotent=config.idempotent,
            requires_app_region=config.requires_app_region,
            is_mutating=config.is_mutating,
            is_destructive=config.is_destructive,
        )
    
    def _setup_legacy_metadata(self) -> None:
        """
        Set up legacy metadata for backward compatibility.
        
        This ensures that any code relying on the old metadata format
        continues to work.
        """
        # The metadata is already set up in _load_handlers
        pass
    
    def is_destructive(self, command: str) -> bool:
        """
        Check if a command is destructive.
        
        Args:
            command: The command name to check
            
        Returns:
            True if the command is destructive, False otherwise
        """
        meta = self.metadata.get(command)
        if meta and meta.is_destructive:
            return True
        
        # Also check the registry
        config = self.registry.metadata.get(command)
        if config and config.is_destructive:
            return True
        
        return False
    
    def get_all_commands(self) -> List[str]:
        """
        Get a list of all registered command names.
        
        Returns:
            List of all command names
        """
        return self.registry.get_all_commands()
    
    async def execute(self, command: str, entities: Dict[str, Any], raw_text: str, context: CommandContext) -> CommandResult:
        """
        Execute a command asynchronously.
        
        This is the main entry point for async command execution. It handles:
        - Validation of required entities
        - Confirmation workflows for destructive actions
        - Async handler lookup and execution
        
        Args:
            command: The command name (e.g., "apps.list")
            entities: Dictionary of entities extracted from the user input
            raw_text: The raw user input text
            context: The command context (user, session, etc.)
            
        Returns:
            CommandResult containing the execution result
        """
        req = CommandRequest(command=command, entities=entities, raw_text=raw_text, context=context)
        
        # Check for destructive actions requiring confirmation
        if self.is_destructive(command) and not entities.get("confirm_token"):
            return self._require_confirmation(command, req)
        
        # Validate required entities
        config = self.registry.metadata.get(command)
        if config:
            missing = self._get_missing_entities(config, req)
            if missing:
                return self._create_validation_error(command, missing)
        
        # Get and execute the async handler
        handler = self.registry.get_handler(command)
        if not handler:
            return self._create_unknown_command_error(command)
        
        # Execute the async handler
        return await handler(req)
    
    def _require_confirmation(self, command: str, req: CommandRequest) -> CommandResult:
        """
        Create a confirmation required response for a destructive action.
        
        Args:
            command: The command name
            req: The command request
            
        Returns:
            CommandResult requiring confirmation
        """
        token = self.memory.issue_confirmation_token(
            session_id=req.context.session_id,
            command=command,
            payload={"entities": req.entities, "raw_text": req.raw_text},
        )
        preview = self._preview_for(command, req)
        return CommandResult(
            event_type="command.confirmation_required",
            status="requires_confirmation",
            human_message=f"Action preview: {preview}. Destructive action, confirm with token {token}.",
            structured_payload={"confirm_token": token, "command": command, "preview": preview},
            next_actions=[f"confirm {token}"],
            risk_level="high",
        )
    
    def _get_missing_entities(self, config: AsyncHandlerConfig, req: CommandRequest) -> Tuple[str, ...]:
        """
        Get a list of missing required entities for a command.
        
        Args:
            config: The handler configuration
            req: The command request
            
        Returns:
            Tuple of missing entity names
        """
        missing: List[str] = []
        
        if config.requires_app_region:
            try:
                self._resolve_app_region(req)
            except ValueError:
                if not req.entities.get("app_name") and not req.context.app_scope:
                    missing.append("app_name")
                if not req.entities.get("region") and not req.context.region_scope:
                    missing.append("region")
        
        for key in config.required_entities:
            if req.entities.get(key) is None or str(req.entities.get(key)).strip() == "":
                missing.append(key)
        
        return tuple(sorted(set(missing)))
    
    def _create_validation_error(self, command: str, missing: Tuple[str, ...]) -> CommandResult:
        """
        Create a validation error response.
        
        Args:
            command: The command name
            missing: Tuple of missing entity names
            
        Returns:
            CommandResult with validation error
        """
        return CommandResult(
            event_type="command.validation_error",
            status="warning",
            human_message=f"Missing required fields: {', '.join(missing)}",
            structured_payload={"missing_entities": missing, "command": command},
            next_actions=[f"provide {field}" for field in missing],
            risk_level="low",
        )
    
    def _create_unknown_command_error(self, command: str) -> CommandResult:
        """
        Create an unknown command error response.
        
        Args:
            command: The unknown command name
            
        Returns:
            CommandResult with unknown command error
        """
        return CommandResult(
            event_type="command.unknown",
            status="warning",
            human_message=f"Unsupported command '{command}'.",
            structured_payload={"supported": sorted(self.registry.get_all_commands())},
        )
    
    def _resolve_app_region(self, req: CommandRequest) -> Tuple[str, str]:
        """
        Resolve app name and region from request and context.
        
        Args:
            req: The command request
            
        Returns:
            Tuple of (app_name, region)
            
        Raises:
            ValueError: If app_name and region cannot be determined
        """
        snapshot = self.memory.snapshot(req.context.user_id, req.context.session_id)
        entities = dict(snapshot.session.get("entities", {}))
        entities.update(snapshot.facts)
        entities.update(req.entities)

        app_name = str(entities.get("app_name") or "")
        region = str(entities.get("region") or req.context.region_scope or "")
        if not app_name or not region:
            raise ValueError("app_name and region are required")
        return app_name, region
    
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
    
    @staticmethod
    def _preview_for(command: str, req: CommandRequest) -> str:
        """
        Generate a preview string for a command.
        
        Args:
            command: The command name
            req: The command request
            
        Returns:
            Preview string describing the command
        """
        payload = {k: v for k, v in req.entities.items() if k not in {"confirm_token"}}
        return f"{command} with {payload}"
