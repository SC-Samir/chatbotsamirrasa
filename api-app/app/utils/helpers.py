"""
Common utility functions.
"""
import time
import urllib.parse
from typing import Dict, Any, List, Optional

from app.domain import AppId, Region
from app.infrastructure.scalingo import AppsAPI, ScalingoHTTPClient, build_default_token_provider


def build_logs_url(base_url: str, params: Dict[str, Any]) -> str:
    """Builds a URL with query parameters."""
    if '?' in base_url:
        separator = '&'
    else:
        separator = '?'
    
    query_string = urllib.parse.urlencode(params)
    return f"{base_url}{separator}{query_string}"


def extract_entities_from_intent(entities: list) -> Dict[str, Any]:
    """Extracts entities from a Rasa intent response."""
    return {e["entity"]: e["value"] for e in entities}


def format_git_ref_message(git_ref: str) -> str:
    """Formats a message for the Git reference."""
    return f" (ref: {git_ref})" if git_ref != "master" else ""


def get_context_used_message(context: Dict[str, Any], entities: Dict[str, Any]) -> str:
    """Generates a message indicating the context used."""
    used_context = []
    if not entities.get("app_name") and context.get("app_name"):
        used_context.append(f"app: {context['app_name']}")
    if not entities.get("region") and context.get("region"):
        used_context.append(f"region: {context['region']}")
    if not entities.get("github_repo") and context.get("github_repo"):
        used_context.append(f"repo: {context['github_repo']}")
    
    return f"💭 I remember: {', '.join(used_context)}" if used_context else ""


def format_logs_info_message(app_name: str, filter_param: Optional[str], n: int, stream: bool) -> str:
    """Formats an information message for logs."""
    filter_info = f" (filtered by: {filter_param})" if filter_param else ""
    lines_info = f" ({n} lines)" if n != 100 else ""
    stream_info = " streaming" if stream else ""
    
    return f"📋 Retrieving logs for *{app_name}*{filter_info}{lines_info}{stream_info}..."


def detect_streaming_intent(text: str) -> bool:
    """Detects if the user wants streaming."""
    return "stream" in text.lower() or "streamer" in text.lower()


def restart_app_with_polling(app_name: str, region: str, scope: Optional[List[str]] = None, max_wait_time: int = 300, check_interval: int = 10) -> bool:
    """
    Restart an application and wait for it to be ready.
    
    Args:
        app_name: Name of the application
        region: Region of the application
        scope: Array of containers to restart (optional)
        max_wait_time: Maximum time to wait in seconds (default: 5 minutes)
        check_interval: Time between status checks in seconds (default: 10 seconds)
        
    Returns:
        bool: True if restart completed successfully, False otherwise
    """
    # Initialize AppsAPI
    token_provider = build_default_token_provider()
    scalingo_http_client = ScalingoHTTPClient(token_provider)
    apps_api = AppsAPI(scalingo_http_client)
    
    region_vo = Region(region)
    app_id = AppId(app_name)
    
    # Start the restart
    restart_result = apps_api.restart_app(app_id, region_vo, scope)
    
    # Check if restart was successful
    if not restart_result.success:
        return False
    
    # Wait a moment for the restart to begin
    time.sleep(2)
    
    # Immediate check to detect very fast restarts
    app_status_result = apps_api.get_app_status(app_id, region_vo)
    if app_status_result.success and app_status_result.value:
        app_data = app_status_result.value
        status = app_data.status
        
        if status == "running":
            # Also check the containers
            containers_result = apps_api.get_containers_status(app_id, region_vo)
            if containers_result.success and containers_result.value:
                containers = containers_result.value
                containers_running = sum(1 for container in containers if container.state == "running")
                
                if containers_running > 0:
                    return True
    
    # Poll app and containers state until timeout.
    deadline = time.time() + max_wait_time
    while time.time() < deadline:
        app_status_result = apps_api.get_app_status(app_id, region_vo)
        if app_status_result.success and app_status_result.value:
            app_data = app_status_result.value
            status = app_data.status

            if status == "running":
                containers_result = apps_api.get_containers_status(app_id, region_vo)
                if containers_result.success and containers_result.value:
                    containers = containers_result.value
                    containers_running = sum(1 for container in containers if container.state == "running")
                    if containers_running > 0:
                        return True
        time.sleep(check_interval)

    return False
