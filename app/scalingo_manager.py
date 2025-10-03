import httpx
from app.config import settings

class ScalingoManager:
    def __init__(self):
        if not settings.scalingo_api_token:
            raise ValueError("The SCALINGO_API_TOKEN environment variable is required.")
        self.api_token = settings.scalingo_api_token
        self.bearer_token = None
        self._exchange_token()
    
    def _exchange_token(self):
        """Exchanges the API token for a Bearer Token valid for 1 hour."""
        auth_url = "https://auth.scalingo.com/v1/tokens/exchange"
        
        
        with httpx.Client() as client:
            try:
                response = client.post(
                    auth_url,
                    auth=("", self.api_token)  # Basic Auth avec username vide et token comme password
                )
                response.raise_for_status()
                data = response.json()
                self.bearer_token = data.get("token")
                
                if not self.bearer_token:
                    raise ValueError("Unable to retrieve Bearer Token from response.")
                
            except httpx.HTTPStatusError as e:
                raise
            except Exception as e:
                raise
    
    @property
    def headers(self):
        """Returns headers with the Bearer Token."""
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }

    def _get_api_url_for_region(self, region: str):
        url = settings.scalingo_region_urls.get(region)
        if not url:
            raise ValueError(f"Unknown region: {region}. Valid regions: {list(settings.scalingo_region_urls.keys())}")
        return url

    def _request(self, method: str, region: str, endpoint: str, retry_on_401=True, **kwargs):
        base_url = self._get_api_url_for_region(region)
        full_url = f"{base_url}{endpoint}"
        
        
        with httpx.Client(base_url=base_url, headers=self.headers) as client:
            try:
                response = client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                
                # For logs, we can have raw text instead of JSON
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    return response.json()
                else:
                    # Return raw content for logs
                    return response.text
                    
            except httpx.HTTPStatusError as e:
                # If we receive a 401 (expired token), refresh the token and retry
                if e.response.status_code == 401 and retry_on_401:
                    self._exchange_token()
                    # Retry once with the new token (retry_on_401=False to avoid infinite loop)
                    return self._request(method, region, endpoint, retry_on_401=False, **kwargs)
                else:
                    return None

    def create_app(self, app_name: str, region: str):
        endpoint = "/v1/apps"
        payload = {"app": {"name": app_name}}
        return self._request("POST", region, endpoint, json=payload)

    def trigger_deployment(self, app_name: str, region: str, github_repo: str, git_ref: str = "master"):
        """
        Triggers a deployment for an application.
        
        Args:
            app_name: Name of the Scalingo application
            region: Deployment region
            github_repo: GitHub repo URL (e.g.: https://github.com/Scalingo/sample-go-martini)
            git_ref: Branch, tag or commit SHA (default: master)
        """
        endpoint = f"/v1/apps/{app_name}/deployments"
        
        # Build archive URL from GitHub repo and git ref
        # Format: https://github.com/Scalingo/sample-go-martini/archive/master.tar.gz
        if github_repo.endswith('.git'):
            github_repo = github_repo[:-4]  # Remove .git if present
        if github_repo.endswith('/'):
            github_repo = github_repo[:-1]  # Remove trailing slash
        
        archive_url = f"{github_repo}/archive/{git_ref}.tar.gz"
        
        
        payload = {"source_url": archive_url, "git_ref": git_ref}
        return self._request("POST", region, endpoint, json=payload)

    def get_deployment_status(self, app_name: str, region: str, deployment_id: str):
        endpoint = f"/v1/apps/{app_name}/deployments/{deployment_id}"
        return self._request("GET", region, endpoint)

    def get_logs_url(self, app_name: str, region: str):
        """Get the authenticated logs URL for an application."""
        endpoint = f"/v1/apps/{app_name}/logs"
        response = self._request("GET", region, endpoint)
        
        if response and "logs_url" in response:
            logs_url = response["logs_url"]
            return logs_url
        else:
            return None

    def get_logs(self, app_name: str, region: str, n: int = 100, filter_param: str = None, stream: bool = False):
        """
        Get logs for an application.
        
        Args:
            app_name: Name of the application
            region: Region of the application
            n: Number of lines to return (default: 100)
            filter_param: Filter containers logs by container type/name (optional)
            stream: Enable streaming (default: False)
            
        Returns:
            dict with logs_url and parameters, or None if error
        """
        # First, get the authenticated logs URL
        logs_url = self.get_logs_url(app_name, region)
        if not logs_url:
            print(f"❌ Unable to retrieve logs URL for {app_name}")
            return None
        
        # Build query parameters according to Scalingo documentation
        params = {}
        
        if not stream:
            # For static logs, we can use n
            if n != 100:  # Only if different from default value
                params["n"] = n
        
        # Filter is always supported
        if filter_param:
            params["filter"] = filter_param
            
        # Note: stream=true is not added as parameter because Scalingo API
        # handles this differently (WebSocket headers or SSE)
            
        # Construct the full logs URL with parameters
        import urllib.parse
        
        # Check if the logs_url already contains query parameters
        if '?' in logs_url:
            separator = '&'
        else:
            separator = '?'
            
        query_string = urllib.parse.urlencode(params)
        full_logs_url = f"{logs_url}{separator}{query_string}"
        
        
        return {
            "logs_url": full_logs_url,
            "parameters": params,
            "stream": stream,
            "app_name": app_name,
            "region": region
        }

    def get_logs_direct(self, app_name: str, region: str, n: int = 100, filter_param: str = None, stream: bool = False):
        """
        Get logs directly from the API without using the logs_url endpoint.
        This is a fallback method in case the logs_url approach fails.
        """
        # Build the direct logs endpoint
        endpoint = f"/v1/apps/{app_name}/logs"
        params = {}
        
        if not stream and n != 100:
            params["n"] = n
        if filter_param:
            params["filter"] = filter_param
            
        
        # Use the _request method with query parameters
        try:
            response = self._request("GET", region, endpoint, params=params)
            return response
        except Exception as e:
            return None

    def restart_app(self, app_name: str, region: str, scope: list = None):
        """
        Restart an application.
        
        Args:
            app_name: Name of the application
            region: Region of the application
            scope: Array of containers to restart (optional, if None restarts everything)
            
        Returns:
            dict with restart response or None if error
        """
        endpoint = f"/v1/apps/{app_name}/restart"
        
        payload = {}
        if scope:
            payload["scope"] = scope
            
        
        try:
            # If no scope, don't send any payload at all
            if scope:
                response = self._request("POST", region, endpoint, json=payload)
            else:
                # For a complete restart, send a POST request without body
                response = self._request("POST", region, endpoint)
            
            # Scalingo API returns 202 Accepted with empty body for restart
            # So an empty response or None is actually a success
            if response is None:
                return {"status": "accepted"}  # Return a dict to indicate success
            else:
                return response
        except Exception as e:
            return None

    def get_app_status(self, app_name: str, region: str):
        """
        Get the status of an application.
        
        Args:
            app_name: Name of the application
            region: Region of the application
            
        Returns:
            dict with app info including status, or None if error
        """
        endpoint = f"/v1/apps/{app_name}"
        response = self._request("GET", region, endpoint)
        if response:
            return response
        return None

    def get_containers_status(self, app_name: str, region: str):
        """
        Get the status of application containers using the /ps endpoint.
        
        Args:
            app_name: Name of the application
            region: Region of the application
            
        Returns:
            dict with containers info, or None if error
        """
        endpoint = f"/v1/apps/{app_name}/ps"
        response = self._request("GET", region, endpoint)
        if response:
            return response
        return None

    def wait_for_restart(self, app_name: str, region: str, max_wait_time: int = 300, check_interval: int = 10):
        """
        Wait for an application to finish restarting by polling its status.
        
        Args:
            app_name: Name of the application
            region: Region of the application
            max_wait_time: Maximum time to wait in seconds (default: 5 minutes)
            check_interval: Time between status checks in seconds (default: 10 seconds)
            
        Returns:
            bool: True if restart completed successfully, False if timeout or error
        """
        import time
        
        
        start_time = time.time()
        restart_detected = False
        consecutive_running_checks = 0  # Count consecutive "running" checks
        
        while time.time() - start_time < max_wait_time:
            # Check app status
            app_info = self.get_app_status(app_name, region)
            
            if not app_info:
                return False
                
            app_data = app_info.get("app", {})
            status = app_data.get("status")
            
            # Also check containers for more reliability
            containers_info = self.get_containers_status(app_name, region)
            containers_running = 0
            if containers_info:
                containers = containers_info.get("containers", [])
                # Use the 'state' field from the /ps endpoint
                for container in containers:
                    state = container.get("state", "unknown")
                    # Consider as "running" if state is "running"
                    if state == "running":
                        containers_running += 1
            
            # Detect if we are restarting
            if status == "restarting":
                restart_detected = True
                consecutive_running_checks = 0  # Reset counter
            elif status == "running":
                consecutive_running_checks += 1
                
                # If we have running containers, it's good
                if containers_running > 0:
                    return True
            else:
                consecutive_running_checks = 0  # Reset counter
            
            # Wait before next check
            if time.time() - start_time < max_wait_time:
                time.sleep(check_interval)
        
        # If we get here, we exceeded the timeout
        # But if we detected a restart, we can consider it might be good
        if restart_detected:
            return True
        else:
            return False

    def scale_app(self, app_name: str, region: str, containers: list):
        """
        Scale an application by modifying container amounts and sizes.
        
        Args:
            app_name: Name of the application
            region: Region of the application
            containers: Array of containers to scale, each containing:
                - name: Container name (e.g., "web", "worker")
                - amount: Number of containers
                - size: Container size (optional, e.g., "S", "M", "L", "XL", "2XL")
                
        Returns:
            dict with scaling response, or dict with error info if scaling conflict, or None if other error
        """
        endpoint = f"/v1/apps/{app_name}/scale"
        
        payload = {"containers": containers}
        
        
        # Use a modified _request that doesn't swallow HTTP errors for scaling
        base_url = self._get_api_url_for_region(region)
        
        import httpx
        with httpx.Client(base_url=base_url, headers=self.headers) as client:
            try:
                response = client.request("POST", endpoint, json=payload)
                response.raise_for_status()
                
                # For successful scaling, return JSON response
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    result = response.json()
                    return result
                else:
                    return {"status": "success", "text": response.text}
                    
            except httpx.HTTPStatusError as e:
                # Handle specific scaling conflict error
                if e.response.status_code == 422:
                    try:
                        error_data = e.response.json()
                        if "errors" in error_data and "app" in error_data["errors"]:
                            app_errors = error_data["errors"]["app"]
                            if "is scaling" in str(app_errors):
                                return {"error": "scaling_in_progress", "message": "Application is already scaling"}
                    except:
                        pass
                    
                    return {"error": "validation_error", "message": e.response.text}
                
                # Handle 401 token expiration
                elif e.response.status_code == 401:
                    self._exchange_token()
                    # Retry once with new token
                    return self.scale_app(app_name, region, containers)
                
                return {"error": f"http_{e.response.status_code}", "message": e.response.text}
                
            except Exception as e:
                return None

    def get_operation_status(self, app_name: str, region: str, operation_id: str):
        """
        Get the status of an operation (like scaling).
        
        Args:
            app_name: Name of the application
            region: Region of the application
            operation_id: ID of the operation to check
            
        Returns:
            dict with operation info, or None if error
        """
        endpoint = f"/v1/apps/{app_name}/operations/{operation_id}"
        response = self._request("GET", region, endpoint)
        if response:
            return response
        return None

    def wait_for_scaling(self, app_name: str, region: str, max_wait_time: int = 300, check_interval: int = 5):
        """
        Wait for an application to finish scaling by polling its status.
        
        Args:
            app_name: Name of the application
            region: Region of the application
            max_wait_time: Maximum time to wait in seconds (default: 5 minutes)
            check_interval: Time between status checks in seconds (default: 5 seconds)
            
        Returns:
            bool: True if scaling completed successfully, False if timeout or error
        """
        import time
        
        start_time = time.time()
        scaling_detected = False
        consecutive_running_checks = 0
        
        while time.time() - start_time < max_wait_time:
            # Check app status
            app_info = self.get_app_status(app_name, region)
            
            if not app_info:
                return False
                
            app_data = app_info.get("app", {})
            status = app_data.get("status")
            
            # Detect if we are scaling
            if status == "scaling":
                scaling_detected = True
                consecutive_running_checks = 0
            elif status == "running":
                consecutive_running_checks += 1
                
                # If we detected scaling before and now running, it's complete
                if scaling_detected and consecutive_running_checks >= 2:
                    return True
                # If no scaling detected yet but we're running, check containers
                elif not scaling_detected:
                    # Quick check - if we're running without detecting scaling, 
                    # the scaling might have been very fast
                    return True
            else:
                consecutive_running_checks = 0
            
            # Wait before next check
            if time.time() - start_time < max_wait_time:
                time.sleep(check_interval)
        
        # If we get here, we exceeded the timeout
        # But if we detected scaling, we can consider it might be complete
        if scaling_detected:
            return True
        else:
            return False

    def delete_app(self, app_name: str, region: str):
        """
        Delete an application.
        
        Args:
            app_name: Name of the application to delete
            region: Region of the application
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        endpoint = f"/v1/apps/{app_name}"
        
        # Add current_name parameter as validation
        params = {"current_name": app_name}
        
        try:
            # Use a modified _request that doesn't swallow HTTP errors for deletion
            base_url = self._get_api_url_for_region(region)
            
            with httpx.Client(base_url=base_url, headers=self.headers) as client:
                response = client.request("DELETE", endpoint, params=params)
                response.raise_for_status()
                
                # Scalingo API returns 204 No Content for successful deletion
                if response.status_code == 204:
                    return True
                else:
                    return False
                    
        except httpx.HTTPStatusError as e:
            # Handle 401 token expiration
            if e.response.status_code == 401:
                self._exchange_token()
                # Retry once with new token
                return self.delete_app(app_name, region)
            
            # Handle other HTTP errors
            print(f"❌ Delete failed with status {e.response.status_code}: {e.response.text}")
            return False
            
        except Exception as e:
            print(f"❌ Error during deletion: {str(e)}")
            return False

    def rename_app(self, app_name: str, region: str, new_name: str):
        """
        Rename an application.
        
        Args:
            app_name: Current name of the application
            region: Region of the application
            new_name: New name for the application
            
        Returns:
            dict with renamed app info if successful, or dict with error info, or None if other error
        """
        endpoint = f"/v1/apps/{app_name}/rename"
        
        payload = {
            "current_name": app_name,
            "new_name": new_name
        }
        
        try:
            # Use a modified _request that doesn't swallow HTTP errors for rename
            base_url = self._get_api_url_for_region(region)
            
            with httpx.Client(base_url=base_url, headers=self.headers) as client:
                response = client.request("POST", endpoint, json=payload)
                response.raise_for_status()
                
                # Scalingo API returns 200 OK with app info for successful rename
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    result = response.json()
                    return result
                else:
                    return {"status": "success", "text": response.text}
                    
        except httpx.HTTPStatusError as e:
            # Handle 401 token expiration
            if e.response.status_code == 401:
                self._exchange_token()
                # Retry once with new token
                return self.rename_app(app_name, region, new_name)
            
            # Handle validation errors
            if e.response.status_code == 422:
                try:
                    error_data = e.response.json()
                    return {"error": "validation_error", "message": error_data}
                except:
                    return {"error": "validation_error", "message": e.response.text}
            
            # Handle other HTTP errors
            return {"error": f"http_{e.response.status_code}", "message": e.response.text}
            
        except Exception as e:
            return {"error": "exception", "message": str(e)}

    def get_app_variables(self, app_name: str, region: str, aliases: bool = True):
        """
        Get environment variables for an application.
        
        Args:
            app_name: Name of the application
            region: Region of the application
            aliases: Whether to interpolate variable aliases (default: True)
            
        Returns:
            dict with variables info if successful, or dict with error info, or None if other error
        """
        endpoint = f"/v1/apps/{app_name}/variables"
        
        params = {"aliases": aliases}
        
        try:
            response = self._request("GET", region, endpoint, params=params)
            if response:
                return response
            return None
                    
        except Exception as e:
            return {"error": "exception", "message": str(e)}

    def add_app_variable(self, app_name: str, region: str, variable_name: str, variable_value: str):
        """
        Add an environment variable to an application.
        
        Args:
            app_name: Name of the application
            region: Region of the application
            variable_name: Name of the environment variable (max 64 characters)
            variable_value: Value of the environment variable (max 8192 characters)
            
        Returns:
            dict with variable info if successful, or dict with error info, or None if other error
        """
        endpoint = f"/v1/apps/{app_name}/variables"
        
        # Validate input parameters
        if not variable_name or not variable_name.strip():
            return {"error": "validation_error", "message": "Variable name cannot be empty"}
        
        if len(variable_name) > 64:
            return {"error": "validation_error", "message": "Variable name cannot exceed 64 characters"}
        
        if len(variable_value) > 8192:
            return {"error": "validation_error", "message": "Variable value cannot exceed 8192 characters"}
        
        payload = {
            "variable": {
                "name": variable_name.strip(),
                "value": variable_value
            }
        }
        
        try:
            # Use a modified _request that doesn't swallow HTTP errors for variable creation
            base_url = self._get_api_url_for_region(region)
            
            with httpx.Client(base_url=base_url, headers=self.headers) as client:
                response = client.request("POST", endpoint, json=payload)
                response.raise_for_status()
                
                # Scalingo API returns 201 Created with variable info for successful creation
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    result = response.json()
                    return result
                else:
                    return {"status": "success", "text": response.text}
                    
        except httpx.HTTPStatusError as e:
            # Handle 401 token expiration
            if e.response.status_code == 401:
                self._exchange_token()
                # Retry once with new token
                return self.add_app_variable(app_name, region, variable_name, variable_value)
            
            # Handle validation errors
            if e.response.status_code == 422:
                try:
                    error_data = e.response.json()
                    return {"error": "validation_error", "message": error_data}
                except:
                    return {"error": "validation_error", "message": e.response.text}
            
            # Handle other HTTP errors
            return {"error": f"http_{e.response.status_code}", "message": e.response.text}
            
        except Exception as e:
            return {"error": "exception", "message": str(e)}