"""
Common utility functions.
"""
import urllib.parse
from typing import Dict, Any, Optional


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


def restart_app_with_polling(scalingo_manager, app_name: str, region: str, scope: list = None, max_wait_time: int = 300, check_interval: int = 10) -> bool:
    """
    Restart an application and wait for it to be ready.
    
    Args:
        scalingo_manager: Instance of ScalingoManager
        app_name: Name of the application
        region: Region of the application
        scope: Array of containers to restart (optional)
        max_wait_time: Maximum time to wait in seconds (default: 5 minutes)
        check_interval: Time between status checks in seconds (default: 10 seconds)
        
    Returns:
        bool: True if restart completed successfully, False otherwise
    """
    import time
    
    # Start the restart
    restart_result = scalingo_manager.restart_app(app_name, region, scope)
    
    # The Scalingo API returns an empty string for a successful restart
    # So we consider it a success if we have a response (even empty) and no exception
    if restart_result is None:
        return False
    
    # Wait a moment for the restart to begin
    time.sleep(2)
    
    # Immediate check to detect very fast restarts
    app_info = scalingo_manager.get_app_status(app_name, region)
    if app_info:
        app_data = app_info.get("app", {})
        status = app_data.get("status")
        
        if status == "running":
            # Also check the containers
            containers_info = scalingo_manager.get_containers_status(app_name, region)
            if containers_info:
                containers = containers_info.get("containers", [])
                # Use the 'state' field from the /ps endpoint
                containers_running = 0
                for container in containers:
                    state = container.get("state", "unknown")
                    if state == "running":
                        containers_running += 1
                
                if containers_running > 0:
                    return True
    
    # Poll app and containers state until timeout.
    deadline = time.time() + max_wait_time
    result = False
    while time.time() < deadline:
        app_info = scalingo_manager.get_app_status(app_name, region)
        if app_info:
            app_data = app_info.get("app", {})
            status = app_data.get("status")

            if status == "running":
                containers_info = scalingo_manager.get_containers_status(app_name, region)
                if containers_info:
                    containers = containers_info.get("containers", [])
                    containers_running = sum(1 for container in containers if container.get("state", "unknown") == "running")
                    if containers_running > 0:
                        result = True
                        break
        time.sleep(check_interval)

    return result
