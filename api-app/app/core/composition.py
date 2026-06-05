"""
Application composition root.

This module provides the dependency injection composition for the main
application components, including HTTP clients, APIs, and services.

It supports both synchronous and asynchronous operation modes.
"""
from dataclasses import dataclass
from typing import Optional, Union

import httpx

from app.config import settings
from app.infrastructure.rasa import RasaClient
from app.infrastructure.scalingo import (
    AppsAPI,
    AsyncAppsAPI,
    AsyncScalingoHTTPClient,
    ScalingoHTTPClient,
    build_default_token_provider,
)
from app.services.logs_service import LogsService


@dataclass(frozen=True)
class AppComponents:
    """
    Synchronous application components.
    
    Use this for traditional synchronous operation.
    """
    rasa_client: RasaClient
    apps_api: AppsAPI
    logs_service: LogsService


@dataclass(frozen=True)
class AsyncAppComponents:
    """
    Asynchronous application components.
    
    Use this for async contexts like FastAPI or asyncio applications.
    """
    rasa_client: RasaClient
    apps_api: AsyncAppsAPI
    logs_service: LogsService
    async_http_client: AsyncScalingoHTTPClient


def build_components() -> AppComponents:
    """
    Build synchronous application components.
    
    Returns:
        AppComponents instance with all synchronous dependencies
    """
    rasa_client = RasaClient(
        base_url=settings.rasa_url,
        timeout_ms=settings.rasa_timeout_ms,
        auth_token=settings.rasa_auth_token,
    )

    token_provider = build_default_token_provider()
    scalingo_http_client = ScalingoHTTPClient(token_provider)
    apps_api = AppsAPI(scalingo_http_client)
    shared_http_client = httpx.AsyncClient(timeout=httpx.Timeout(20.0))

    logs_service = LogsService(apps_api, shared_http_client)
    return AppComponents(
        rasa_client=rasa_client,
        apps_api=apps_api,
        logs_service=logs_service,
    )


async def build_async_components() -> AsyncAppComponents:
    """
    Build asynchronous application components.
    
    Returns:
        AsyncAppComponents instance with all async dependencies
    """
    rasa_client = RasaClient(
        base_url=settings.rasa_url,
        timeout_ms=settings.rasa_timeout_ms,
        auth_token=settings.rasa_auth_token,
    )

    token_provider = build_default_token_provider()
    async_http_client = AsyncScalingoHTTPClient(token_provider)
    
    # Enter the async context manager
    await async_http_client.__aenter__()
    
    apps_api = AsyncAppsAPI(async_http_client)
    
    # Create a separate HTTP client for logs service
    logs_http_client = httpx.AsyncClient(timeout=httpx.Timeout(20.0))
    logs_service = LogsService(apps_api, logs_http_client)
    
    return AsyncAppComponents(
        rasa_client=rasa_client,
        apps_api=apps_api,
        logs_service=logs_service,
        async_http_client=async_http_client,
    )


async def close_async_components(components: AsyncAppComponents) -> None:
    """
    Clean up async components.
    
    Args:
        components: The async components to clean up
    """
    await components.async_http_client.close()


def build_components_for_context(async_context: bool = False) -> Union[AppComponents, AsyncAppComponents]:
    """
    Build components appropriate for the given context.
    
    Args:
        async_context: If True, build async components; otherwise build sync components
        
    Returns:
        AppComponents or AsyncAppComponents depending on async_context
    """
    if async_context:
        # For async contexts, we need to use the async builder
        # Note: This is a helper that returns a coroutine
        return build_async_components()
    else:
        return build_components()


# Singleton instances for convenience
_components: Optional[AppComponents] = None


def get_components() -> AppComponents:
    """
    Get or create singleton synchronous components.
    
    Returns:
        Shared AppComponents instance
    """
    global _components
    if _components is None:
        _components = build_components()
    return _components


# Async singleton
_async_components: Optional[AsyncAppComponents] = None


async def get_async_components() -> AsyncAppComponents:
    """
    Get or create singleton async components.
    
    Returns:
        Shared AsyncAppComponents instance
    """
    global _async_components
    if _async_components is None:
        _async_components = await build_async_components()
    return _async_components
