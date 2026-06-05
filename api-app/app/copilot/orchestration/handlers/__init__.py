"""
Command handlers for the orchestration engine.

This package contains all the command handlers organized by domain.
Each handler module implements the logic for a specific category of commands.
"""

from .base import BaseCommandHandler, CommandHandler, HandlerConfig, HandlerRegistry, handler

# App handlers
from .app_handlers import (
    AppCreateHandler,
    AppDeleteHandler,
    AppGetHandler,
    AppListHandler,
    AppRenameHandler,
    AppRestartHandler,
    AppSetForceHttpsHandler,
    AppSetRouterLogsHandler,
    AppSetStickySessionHandler,
    AppChangeProjectHandler,
)

# Deployment handlers
from .deployment_handlers import (
    DeploymentCreateHandler,
    DeploymentDetailsHandler,
    DeploymentListHandler,
    DeploymentOutputHandler,
    DeploymentCacheResetHandler,
    DeploymentRollbackHandler,
)

# Container handlers
from .container_handlers import (
    ContainerListHandler,
    ContainerScaleHandler,
    ContainerStopHandler,
    ContainerSignalHandler,
)

# Memory handlers
from .memory_handlers import (
    MemoryShowHandler,
    MemoryForgetHandler,
    MemoryPinHandler,
)

# Autoscaler handlers
from .autoscaler_handlers import (
    AutoscalerCreateHandler,
    AutoscalerDeleteHandler,
    AutoscalerListHandler,
    AutoscalerUpdateHandler,
)

# Domain handlers
from .domain_handlers import (
    DomainCreateHandler,
    DomainDeleteHandler,
    DomainListHandler,
)

# Collaborator handlers
from .collaborator_handlers import (
    CollaboratorDeleteHandler,
    CollaboratorInviteHandler,
    CollaboratorListHandler,
    CollaboratorUpdateRoleHandler,
)

# Event handlers
from .event_handlers import EventListHandler

# Log drain handlers
from .log_drain_handlers import (
    LogDrainCreateHandler,
    LogDrainDeleteHandler,
    LogDrainListHandler,
)

# Notifier handlers
from .notifier_handlers import (
    NotifierCreateHandler,
    NotifierDeleteHandler,
    NotifierListHandler,
    NotifierUpdateHandler,
)

# Environment variable handlers
from .env_var_handlers import (
    EnvVarListHandler,
    EnvVarSetHandler,
    EnvVarUnsetHandler,
)

# Addon handlers
from .addon_handlers import (
    AddonAddHandler,
    AddonListHandler,
    AddonRemoveHandler,
)

# Project handlers
from .project_handlers import ProjectListHandler

# One-off handlers
from .one_off_handlers import OneOffRunHandler

# Confirmation handler
from .confirm_handler import ConfirmHandler

__all__ = [
    # Base classes
    "BaseCommandHandler",
    "CommandHandler",
    "HandlerConfig",
    "HandlerRegistry",
    "handler",
    # App handlers
    "AppCreateHandler",
    "AppDeleteHandler",
    "AppGetHandler",
    "AppListHandler",
    "AppRenameHandler",
    "AppRestartHandler",
    "AppSetForceHttpsHandler",
    "AppSetRouterLogsHandler",
    "AppSetStickySessionHandler",
    "AppChangeProjectHandler",
    # Deployment handlers
    "DeploymentCreateHandler",
    "DeploymentDetailsHandler",
    "DeploymentListHandler",
    "DeploymentOutputHandler",
    "DeploymentCacheResetHandler",
    "DeploymentRollbackHandler",
    # Container handlers
    "ContainerListHandler",
    "ContainerScaleHandler",
    "ContainerStopHandler",
    "ContainerSignalHandler",
    # Memory handlers
    "MemoryShowHandler",
    "MemoryForgetHandler",
    "MemoryPinHandler",
    # Autoscaler handlers
    "AutoscalerCreateHandler",
    "AutoscalerDeleteHandler",
    "AutoscalerListHandler",
    "AutoscalerUpdateHandler",
    # Domain handlers
    "DomainCreateHandler",
    "DomainDeleteHandler",
    "DomainListHandler",
    # Collaborator handlers
    "CollaboratorDeleteHandler",
    "CollaboratorInviteHandler",
    "CollaboratorListHandler",
    "CollaboratorUpdateRoleHandler",
    # Event handlers
    "EventListHandler",
    # Log drain handlers
    "LogDrainCreateHandler",
    "LogDrainDeleteHandler",
    "LogDrainListHandler",
    # Notifier handlers
    "NotifierCreateHandler",
    "NotifierDeleteHandler",
    "NotifierListHandler",
    "NotifierUpdateHandler",
    # Env var handlers
    "EnvVarListHandler",
    "EnvVarSetHandler",
    "EnvVarUnsetHandler",
    # Addon handlers
    "AddonAddHandler",
    "AddonListHandler",
    "AddonRemoveHandler",
    # Project handlers
    "ProjectListHandler",
    # One-off handlers
    "OneOffRunHandler",
    # Confirm handler
    "ConfirmHandler",
]
