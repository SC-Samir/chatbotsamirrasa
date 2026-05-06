import json

import httpx
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.config import settings
from app.core.composition import build_components
from app.copilot.composition import build_copilot_components
from app.core.container import container
from app.core.logging import StructuredLogger
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.models import LogsRequest, Region

logger = StructuredLogger("main")

app = FastAPI(
    title=settings.app_name,
    description="Intelligent agent for managing Scalingo deployments and logs",
    version="3.0.0",
)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(LoggingMiddleware)

components = build_components(enable_legacy_intent_stack=settings.enable_legacy_intent_stack)
copilot_components = build_copilot_components()

container.register_singleton(type(components.apps_api), components.apps_api)
container.register_singleton(type(components.logs_service), components.logs_service)
if settings.enable_legacy_intent_stack and components.intent_handler_manager and components.websocket_handler:
    container.register_singleton(type(components.intent_handler_manager), components.intent_handler_manager)
    container.register_singleton(type(components.websocket_handler), components.websocket_handler)

templates = Jinja2Templates(directory="templates")

logger.info(
    "Application initialized",
    app_name=settings.app_name,
    debug_mode=settings.debug,
    redis_url=settings.redis_url,
)
if not settings.enable_legacy_intent_stack:
    logger.info("Legacy intent stack disabled", websocket_contract="ws.v2-only")


@app.get("/")
def get_home(request: Request):
    response = templates.TemplateResponse(request, "index.html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/logs/{app_name}")
async def get_app_logs(
    app_name: str,
    region: str,
    n: int = 100,
    filter: str = None,
    stream: bool = False,
):
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
            raise HTTPException(status_code=404, detail=f"Unable to retrieve logs for {app_name}")

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
        raise HTTPException(status_code=500, detail=f"Error retrieving logs: {str(exc)}") from exc


@app.get("/logs/{app_name}/stream")
async def stream_app_logs(app_name: str, region: str, filter: str = None):
    try:
        logs_request = LogsRequest(
            app_name=app_name,
            region=Region(region),
            stream=True,
            filter_param=filter,
        )
        logs_response = await components.logs_service.get_logs_info(logs_request)
        if not logs_response:
            raise HTTPException(status_code=404, detail=f"Unable to retrieve logs for {app_name}")

        async def generate_logs():
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", logs_response.logs_url) as response:
                    async for line in response.aiter_lines():
                        if line.strip():
                            yield f"data: {json.dumps({'log': line})}\n\n"

        return StreamingResponse(
            generate_logs(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error streaming logs: {str(exc)}") from exc


@app.get("/logs/{app_name}/display")
async def display_app_logs(app_name: str, region: str, n: int = 100, filter: str = None):
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
            raise HTTPException(status_code=404, detail=f"Unable to retrieve logs for {app_name}")

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
        raise HTTPException(status_code=500, detail=f"Error retrieving logs: {str(exc)}") from exc


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await copilot_components.websocket_handler.handle_connection(websocket)


@app.websocket("/ws/")
async def websocket_endpoint_slash(websocket: WebSocket):
    await copilot_components.websocket_handler.handle_connection(websocket)
