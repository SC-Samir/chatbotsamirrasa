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
from app.domain import Region
from app.models import LogsRequest

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


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Intelligent agent for managing Scalingo deployments and logs",
    version="3.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
)

# Add middleware
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(LoggingMiddleware)

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


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns a simple JSON response indicating the service is healthy.
    """
    return {
        "status": "healthy",
        "version": "3.1.0",
        "app_name": settings.app_name,
    }


@app.get("/health/detailed", tags=["health"])
async def detailed_health_check():
    """
    Detailed health check endpoint.
    
    Returns comprehensive health information including dependency status.
    """
    health_status = {
        "status": "healthy",
        "version": "3.1.0",
        "app_name": settings.app_name,
        "components": {
            "apps_api": "operational",
            "logs_service": "operational",
            "copilot": "operational",
        },
        "dependencies": {
            "redis": "connected" if settings.redis_url else "not configured",
            "database": "connected" if settings.database_url else "not configured",
        },
    }
    return health_status


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
@app.websocket("/ws", tags=["websocket"])
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for copilot v2 protocol.
    
    Primary WebSocket endpoint for interactive command processing.
    """
    await copilot_components.websocket_handler.handle_connection(websocket)


@app.websocket("/ws/", tags=["websocket"])
async def websocket_endpoint_slash(websocket: WebSocket):
    """
    WebSocket endpoint with trailing slash for copilot v2 protocol.
    
    Alternative endpoint with trailing slash for compatibility.
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
