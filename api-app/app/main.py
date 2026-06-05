"""
Main FastAPI application for the Scalingo Copilot API.

This module provides the primary web interface for the copilot service,
including REST endpoints for logs and WebSocket endpoints for interactive
command processing.
"""
import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.config import settings
from app.core.composition import build_components
from app.copilot.composition import build_copilot_components
from app.core.container import container
from app.core.logging import StructuredLogger
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware, RateLimitConfig
from app.middleware.security_middleware import (
    SecurityHeadersMiddleware,
    CORSConfig,
    create_cors_middleware,
)
from app.domain import Region
from app.models import LogsRequest
from app.presentation.health import router as health_router
from app.presentation.metrics import router as metrics_router

logger = StructuredLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    This handles startup and shutdown events for the application.
    """
    # Startup
    logger.info(
        "Application starting up",
        app_name=settings.app_name,
        version="3.1.0",
        debug_mode=settings.debug,
    )
    
    yield
    
    # Shutdown
    logger.info("Application shutting down")


# OpenAPI configuration
openapi_config = {
    "title": settings.app_name,
    "description": """
# Scalingo Copilot API

This API provides intelligent management capabilities for Scalingo deployments, logs, and infrastructure.

## Authentication

This API uses API key authentication. Include your API key in the `X-API-Key` header or as a query parameter.

## Features

- **Logs Management**: Retrieve, filter, and stream application logs
- **Command Processing**: Execute commands via WebSocket interface
- **Deployment Management**: Manage application deployments
- **App Management**: Control Scalingo applications
- **Memory Management**: Store and retrieve conversation memory
- **Health Checks**: Monitor service health and dependencies

## WebSocket Interface

Connect to `/ws` endpoint for interactive command processing using the v2 protocol.

## Error Handling

All errors return consistent JSON responses with:
- `error`: Error type
- `message`: Human-readable error message
- `status_code`: HTTP status code
- `error_id`: Unique error identifier (for tracking)
- `code`: Machine-readable error code
- `timestamp`: ISO 8601 timestamp
    """,
    "version": "3.1.0",
    "contact": {
        "name": "Scalingo Support",
        "email": "support@scalingo.com",
    },
    "license": {
        "name": "Proprietary",
    },
    "servers": [
        {
            "url": "http://localhost:8000",
            "description": "Development server",
        },
        {
            "url": "https://api.scalingo.com",
            "description": "Production server",
        },
    ],
    "tags": [
        {
            "name": "health",
            "description": "Health check and monitoring endpoints",
        },
        {
            "name": "logs",
            "description": "Application logs retrieval and streaming",
        },
        {
            "name": "api",
            "description": "API information and documentation",
        },
        {
            "name": "websocket",
            "description": "WebSocket endpoints for interactive commands",
        },
    ],
}

# Create FastAPI application
app = FastAPI(
    **openapi_config,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
)

# Add middleware
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(LoggingMiddleware)

# Add authentication middleware (optional, not required by default)
if getattr(settings, 'require_auth', False):
    from app.middleware.auth_middleware import create_auth_middleware
    auth_middleware = create_auth_middleware(require_auth=True)
    app.add_middleware(auth_middleware)

# Add rate limiting middleware
if getattr(settings, 'rate_limit_enabled', True):
    rate_limit_config = RateLimitConfig(
        max_requests=getattr(settings, 'rate_limit_max_requests', 100),
        window_seconds=getattr(settings, 'rate_limit_window_seconds', 60),
    )
    rate_limit_middleware = RateLimitMiddleware(
        app,
        config=rate_limit_config,
        limit_by=getattr(settings, 'rate_limit_by', 'ip'),
        enabled=True,
    )
    app.add_middleware(rate_limit_middleware)

# Add security headers middleware
app.add_middleware(
    SecurityHeadersMiddleware(
        app,
        force_https=getattr(settings, 'force_https', False),
    )
)

# Add CORS middleware
cors_config = CORSConfig.from_settings()
cors_middleware = create_cors_middleware(cors_config)
app.add_middleware(cors_middleware)

# Initialize components
components = build_components()
copilot_components = build_copilot_components()

# Register components in DI container
container.register_singleton(type(components.apps_api), components.apps_api)
container.register_singleton(type(components.logs_service), components.logs_service)

# Configure templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

logger.info(
    "Application initialized",
    app_name=settings.app_name,
    debug_mode=settings.debug,
    websocket_contract="ws.v2-only",
)


# Include health router
app.include_router(health_router)

# Include metrics router
app.include_router(metrics_router)


# Home page
@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    """
    Home page endpoint.
    
    Returns the main HTML page for the copilot interface.
    """
    response = templates.TemplateResponse(request, "index.html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# API info endpoint
@app.get("/api/info", tags=["api"])
async def get_api_info():
    """
    API information endpoint.
    
    Returns metadata about the API service.
    """
    return {
        "name": settings.app_name,
        "version": "3.1.0",
        "description": "Scalingo Copilot API Service",
        "websocket_endpoint": "/ws",
        "documentation": "/api/docs",
        "features": [
            "logs_retrieval",
            "command_processing",
            "deployment_management",
            "app_management",
            "memory_management",
        ],
    }


# Logs endpoints
@app.get("/logs/{app_name}", tags=["logs"])
async def get_app_logs(
    app_name: str,
    region: str,
    n: int = 100,
    filter: str = None,
    stream: bool = False,
):
    """
    Get application logs.
    
    Retrieves logs for a specific application with optional filtering.
    """
    try:
        logs_request = LogsRequest(
            app_name=app_name,
            region=Region(region),
            n=n,
            filter_param=filter,
            stream=stream,
        )
        logs_response = await components.logs_service.get_logs_info(logs_request)
        if not logs_response:
            raise HTTPException(
                status_code=404,
                detail=f"Unable to retrieve logs for {app_name}",
            )

        if stream:
            return {
                "logs_url": logs_response.logs_url,
                "stream": True,
                "app_name": app_name,
                "region": region,
                "parameters": logs_response.parameters,
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(logs_response.logs_url)
            response.raise_for_status()

        logs_content = response.text
        log_lines = logs_content.strip().split("\n") if logs_content.strip() else []

        return {
            "logs": logs_content,
            "log_lines": log_lines,
            "total_lines": len(log_lines),
            "stream": False,
            "app_name": app_name,
            "region": region,
            "parameters": logs_response.parameters,
        }
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid data: {str(exc)}") from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error retrieving logs", app_name=app_name, region=region, error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving logs: {str(exc)}",
        ) from exc


@app.get("/logs/{app_name}/stream", tags=["logs"])
async def stream_app_logs(app_name: str, region: str, filter: str = None):
    """
    Stream application logs in real-time.
    
    Returns a Server-Sent Events stream of log lines.
    """
    try:
        logs_request = LogsRequest(
            app_name=app_name,
            region=Region(region),
            stream=True,
            filter_param=filter,
        )
        logs_response = await components.logs_service.get_logs_info(logs_request)
        if not logs_response:
            raise HTTPException(
                status_code=404,
                detail=f"Unable to retrieve logs for {app_name}",
            )

        async def generate_logs():
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", logs_response.logs_url) as response:
                    async for line in response.aiter_lines():
                        if line.strip():
                            yield f"data: {json.dumps({'log': line})}\n\n"

        return StreamingResponse(
            generate_logs(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error streaming logs: {str(exc)}",
        ) from exc


@app.get("/logs/{app_name}/display", tags=["logs"])
async def display_app_logs(app_name: str, region: str, n: int = 100, filter: str = None):
    """
    Display application logs with preview.
    
    Returns logs with a preview of the last few lines.
    """
    try:
        logs_request = LogsRequest(
            app_name=app_name,
            region=Region(region),
            n=n,
            filter_param=filter,
            stream=False,
        )
        logs_response = await components.logs_service.get_logs_info(logs_request)
        if not logs_response:
            raise HTTPException(
                status_code=404,
                detail=f"Unable to retrieve logs for {app_name}",
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(logs_response.logs_url)
            response.raise_for_status()

        logs_content = response.text
        if not logs_content.strip():
            return {"message": "No logs found for this application.", "logs": ""}

        log_lines = logs_content.strip().split("\n")
        return {
            "app_name": app_name,
            "region": region,
            "total_lines": len(log_lines),
            "filter": filter,
            "logs": logs_content,
            "logs_preview": log_lines[-10:] if len(log_lines) > 10 else log_lines,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving logs: {str(exc)}",
        ) from exc


# WebSocket endpoints for Copilot
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for copilot v2 protocol.
    
    Primary WebSocket endpoint for interactive command processing.
    
    Tags: websocket
    """
    await copilot_components.websocket_handler.handle_connection(websocket)


@app.websocket("/ws/")
async def websocket_endpoint_slash(websocket: WebSocket):
    """
    WebSocket endpoint with trailing slash for copilot v2 protocol.
    
    Alternative endpoint with trailing slash for compatibility.
    
    Tags: websocket
    """
    await copilot_components.websocket_handler.handle_connection(websocket)


# 404 handler
@app.get("/{path:path}")
async def catch_all(path: str):
    """
    Catch-all endpoint for undefined routes.
    
    Returns a 404 response for undefined routes.
    """
    raise HTTPException(
        status_code=404,
        detail=f"Endpoint {path} not found",
    )
