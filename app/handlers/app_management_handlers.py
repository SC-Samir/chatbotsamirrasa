"""
Handlers pour la gestion des applications.
"""
import asyncio
from typing import Dict, Any, Optional
from fastapi import WebSocket
from app.models import AppContext, IntentResponse
from app.handlers.base_handler import BaseHandler
from app.services.app_management_service import AppManagementService
from app.utils.websocket_helpers import WebSocketHelpers


class RestartHandler(BaseHandler):
    """Handler pour l'intent 'restart'."""
    
    def __init__(self, app_service: AppManagementService, websocket_helpers: WebSocketHelpers):
        super().__init__(websocket_helpers)
        self.app_service = app_service
    
    async def handle(self, websocket: WebSocket, intent_response: IntentResponse, context: AppContext) -> bool:
        if intent_response.intent["name"] != "restart":
            return False
        
        entities = self.context_manager.extract_entities(intent_response)
        
        # Validation des paramètres requis
        params = await self._handle_common_validation(
            websocket, intent_response, context,
            ["app_name", "region"],
            "To restart, I need the app name and region."
        )
        if not params:
            return True
        
        app_name = params["app_name"]
        region = params["region"]
        scope = entities.get("scope")
        
        # Parse scope si fourni
        scope_list = None
        if scope:
            scope_list = [s.strip() for s in scope.split(",")]
            await websocket.send_text(f"🔄 Restarting *{app_name}* on *{region}* (scope: {scope_list})...")
        else:
            await websocket.send_text(f"🔄 Restarting *{app_name}* on *{region}* (restart everything)...")
        
        try:
            success = await self._restart_with_websocket_messages(websocket, app_name, region, scope_list)
            
            if success:
                await self._send_success_message(websocket, f"Application *{app_name}* has been restarted successfully!")
            else:
                await websocket.send_text(f"⏰ Restarting *{app_name}* took longer than expected. Please check status manually.")
                
        except Exception as e:
            await self._send_error_message(websocket, f"Error during restart: {str(e)}")
        
        return True
    
    async def _restart_with_websocket_messages(self, websocket, app_name: str, region: str, scope_list: list = None):
        """Redémarre une application avec des messages WebSocket."""
        await websocket.send_text("📡 Sending restart request...")
        restart_result = self.app_service.restart_app(app_name, region, scope_list)
        
        if restart_result is None:
            await self._send_error_message(websocket, "Application restart failed")
            return False
        
        await self._send_success_message(websocket, "Restart request sent successfully")
        
        # Attendre un moment pour que le redémarrage commence
        await websocket.send_text("⏳ Waiting 2 seconds for restart to begin...")
        await asyncio.sleep(2)
        
        # Vérification immédiate
        await websocket.send_text("🔍 Immediate status check...")
        app_info = self.app_service.get_app_status(app_name, region)
        
        if app_info:
            app_data = app_info.get("app", {})
            status = app_data.get("status")
            
            if status == "running":
                containers_info = self.app_service.get_containers_status(app_name, region)
                if containers_info:
                    containers = containers_info.get("containers", [])
                    containers_running = len([c for c in containers if c.get("state") == "running"])
                    
                    if containers_running > 0:
                        await self._send_success_message(websocket, "Application was already running or restarted very quickly!")
                        return True
                    else:
                        await websocket.send_text("⚠️ App is 'running' but no containers are running")
            else:
                await websocket.send_text(f"⚠️ App is not yet 'running', status: {status}")
        else:
            await self._send_error_message(websocket, "Unable to retrieve app information")
        
        # Polling normal avec messages WebSocket
        await websocket.send_text("🔄 Starting normal polling...")
        return await self._wait_for_restart_with_websocket(websocket, app_name, region)
    
    async def _wait_for_restart_with_websocket(self, websocket, app_name: str, region: str, 
                                             max_wait_time: int = 120, check_interval: int = 3):
        """Attend la fin du redémarrage avec des messages WebSocket."""
        async def check_restart_status():
            return await self.websocket_helpers.check_app_status(websocket, app_name, region)
        
        return await self.websocket_helpers.wait_with_messages(
            websocket, check_restart_status, max_wait_time, check_interval
        )


class ScaleHandler(BaseHandler):
    """Handler pour l'intent 'scale'."""
    
    def __init__(self, app_service: AppManagementService, websocket_helpers: WebSocketHelpers):
        super().__init__(websocket_helpers)
        self.app_service = app_service
    
    async def handle(self, websocket: WebSocket, intent_response: IntentResponse, context: AppContext) -> bool:
        if intent_response.intent["name"] != "scale":
            return False
        
        entities = self.context_manager.extract_entities(intent_response)
        
        # Validation des paramètres requis
        params = await self._handle_common_validation(
            websocket, intent_response, context,
            ["app_name", "region"],
            "To scale, I need the app name and region."
        )
        if not params:
            return True
        
        app_name = params["app_name"]
        region = params["region"]
        container_name = entities.get("container_name")
        container_amount = entities.get("container_amount")
        container_size = entities.get("container_size")
        
        # Validation des paramètres de scaling
        validation_error = self.app_service.validate_scale_params(container_name, container_amount)
        if validation_error:
            await websocket.send_text(f"😕 {validation_error}")
            return True
        
        # Parse du montant
        try:
            amount = int(container_amount)
        except ValueError:
            await websocket.send_text(f"😕 Invalid amount '{container_amount}'. Please provide a number.")
            return True
        
        # Configuration du conteneur
        container_config = self.app_service.build_container_config(container_name, amount, container_size)
        
        size_info = f" with size {container_size.upper()}" if container_size else ""
        await websocket.send_text(f"⚖️ Scaling *{app_name}* on *{region}*: {container_name} → {amount} containers{size_info}...")
        
        try:
            # Envoi de la requête de scaling
            scale_result = self.app_service.scale_app(app_name, region, [container_config])
            
            if scale_result and "error" in scale_result:
                await self._handle_scale_error(websocket, scale_result)
                return True
            elif scale_result:
                await self._handle_scale_success(websocket, scale_result, app_name, region, 
                                                container_name, amount)
            else:
                await self._handle_scale_failure(websocket)
                
        except Exception as e:
            await self._send_error_message(websocket, f"Error during scaling: {str(e)}")
        
        return True
    
    async def _handle_scale_error(self, websocket: WebSocket, scale_result: Dict[str, Any]):
        """Gère les erreurs de scaling."""
        error_type = scale_result.get("error")
        if error_type == "scaling_in_progress":
            await websocket.send_text("⚠️ Application is already scaling!")
            await websocket.send_text("🔄 Another scaling operation is in progress. Please wait for it to complete.")
            await websocket.send_text("💡 You can check the current status and try again in a few moments.")
        elif error_type == "validation_error":
            await websocket.send_text("❌ Scaling request validation failed.")
            await websocket.send_text(f"📋 Error details: {scale_result.get('message', 'Unknown validation error')}")
        else:
            await websocket.send_text(f"❌ Scaling request failed: {scale_result.get('message', 'Unknown error')}")
    
    async def _handle_scale_success(self, websocket: WebSocket, scale_result: Dict[str, Any], 
                                   app_name: str, region: str, container_name: str, amount: int):
        """Gère le succès du scaling."""
        await self._send_success_message(websocket, "Scaling request sent successfully!")
        await websocket.send_text("📡 Scalingo is processing the scaling operation...")
        
        # Affichage de la formation cible
        containers = scale_result.get("containers", [])
        if containers:
            await websocket.send_text("📊 Target formation:")
            for container in containers:
                name = container.get("name", "unknown")
                amount = container.get("amount", 0)
                size = container.get("size", "unknown")
                await websocket.send_text(f"  • {name}: {amount} × {size}")
        
        # Début du monitoring
        await websocket.send_text("🔄 Scaling in progress...")
        
        # Vérification immédiate
        await asyncio.sleep(0.5)
        await websocket.send_text("🔍 Checking container status...")
        
        success = await self._wait_for_scaling_completion(websocket, app_name, region, container_name, amount)
        
        if success:
            await self._send_success_message(websocket, f"Application *{app_name}* has been scaled successfully!")
        else:
            await websocket.send_text(f"⏰ Scaling *{app_name}* took longer than expected. Please check status manually.")
    
    async def _handle_scale_failure(self, websocket: WebSocket):
        """Gère l'échec du scaling."""
        await self._send_error_message(websocket, "Scaling request failed.")
        await websocket.send_text("🔍 Possible causes:")
        await websocket.send_text("  • Application doesn't exist")
        await websocket.send_text("  • Invalid container name (try 'web', 'worker', etc.)")
        await websocket.send_text("  • Invalid region")
        await websocket.send_text("  • Application is not in 'running' state")
        await websocket.send_text("  • Authentication issue")
        await websocket.send_text("💡 Check the server logs for detailed error information.")
    
    async def _wait_for_scaling_completion(self, websocket: WebSocket, app_name: str, region: str, 
                                         container_name: str, target_amount: int):
        """Attend la fin du scaling."""
        async def check_scaling_status():
            return await self.websocket_helpers.check_scaling_status(
                websocket, app_name, region, container_name, target_amount
            )
        
        return await self.websocket_helpers.wait_with_messages(
            websocket, check_scaling_status, max_wait_time=180, check_interval=3
        )


class DeleteAppHandler(BaseHandler):
    """Handler pour l'intent 'delete_app'."""
    
    def __init__(self, app_service: AppManagementService, websocket_helpers: WebSocketHelpers):
        super().__init__(websocket_helpers)
        self.app_service = app_service
    
    async def handle(self, websocket: WebSocket, intent_response: IntentResponse, context: AppContext) -> bool:
        if intent_response.intent["name"] != "delete_app":
            return False
        
        # Validation des paramètres requis
        params = await self._handle_common_validation(
            websocket, intent_response, context,
            ["app_name", "region"],
            "To delete an application, I need the app name and region."
        )
        if not params:
            return True
        
        app_name = params["app_name"]
        region = params["region"]
        
        # Avertissement et confirmation
        await websocket.send_text(f"⚠️ **WARNING**: You are about to delete the application *{app_name}* on *{region}*")
        await websocket.send_text("🗑️ This action is **IRREVERSIBLE** and will permanently delete:")
        await websocket.send_text("  • The application and all its data")
        await websocket.send_text("  • All deployments and logs")
        await websocket.send_text("  • All environment variables")
        await websocket.send_text("  • All associated resources")
        await websocket.send_text("")
        await websocket.send_text("❌ **This cannot be undone!**")
        await websocket.send_text("")
        await websocket.send_text("🔄 Deleting application...")
        
        try:
            success = self.app_service.delete_app(app_name, region)
            
            if success:
                await self._send_success_message(websocket, f"Application *{app_name}* has been successfully deleted from *{region}*!")
                await websocket.send_text("🗑️ All resources have been permanently removed.")
                
                # Nettoyer le contexte
                if context.app_name == app_name:
                    context.app_name = None
            else:
                await self._handle_delete_failure(websocket, app_name)
                
        except Exception as e:
            await self._send_error_message(websocket, f"Error during deletion: {str(e)}")
        
        return True
    
    async def _handle_delete_failure(self, websocket: WebSocket, app_name: str):
        """Gère l'échec de la suppression."""
        await self._send_error_message(websocket, f"Failed to delete application *{app_name}*.")
        await websocket.send_text("🔍 Possible causes:")
        await websocket.send_text("  • Application doesn't exist")
        await websocket.send_text("  • Invalid region")
        await websocket.send_text("  • Insufficient permissions")
        await websocket.send_text("  • Authentication issue")
        await websocket.send_text("💡 Check the server logs for detailed error information.")


class RenameAppHandler(BaseHandler):
    """Handler pour l'intent 'rename_app'."""
    
    def __init__(self, app_service: AppManagementService, websocket_helpers: WebSocketHelpers):
        super().__init__(websocket_helpers)
        self.app_service = app_service
    
    async def handle(self, websocket: WebSocket, intent_response: IntentResponse, context: AppContext) -> bool:
        if intent_response.intent["name"] != "rename_app":
            return False
        
        entities = self.context_manager.extract_entities(intent_response)
        
        # Validation des paramètres requis
        params = await self._handle_common_validation(
            websocket, intent_response, context,
            ["app_name", "region"],
            "To rename an application, I need the app name and region."
        )
        if not params:
            return True
        
        app_name = params["app_name"]
        region = params["region"]
        new_name = entities.get("new_name")
        
        # Validation du nouveau nom
        if not new_name:
            await websocket.send_text("😕 I need the new name for the application.")
            await websocket.send_text("💡 Please provide the new name (e.g., 'rename my-app to my-new-app').")
            return True
        
        # Validation du nom (caractères autorisés, longueur, etc.)
        validation_error = self._validate_new_name(new_name)
        if validation_error:
            await websocket.send_text(f"😕 {validation_error}")
            return True
        
        # Confirmation avant renommage
        await websocket.send_text(f"🔄 Renaming *{app_name}* to *{new_name}* on *{region}*...")
        await websocket.send_text("⚠️ This will change the application URL and may affect deployments.")
        
        try:
            rename_result = self.app_service.rename_app(app_name, region, new_name)
            
            if rename_result and "error" in rename_result:
                await self._handle_rename_error(websocket, rename_result, app_name)
            elif rename_result:
                await self._handle_rename_success(websocket, rename_result, app_name, new_name, context)
            else:
                await self._handle_rename_failure(websocket, app_name)
                
        except Exception as e:
            await self._send_error_message(websocket, f"Error during rename: {str(e)}")
        
        return True
    
    def _validate_new_name(self, new_name: str) -> Optional[str]:
        """Valide le nouveau nom de l'application."""
        if not new_name or not new_name.strip():
            return "The new name cannot be empty."
        
        new_name = new_name.strip()
        
        # Vérification de la longueur
        if len(new_name) < 3:
            return "The new name must be at least 3 characters long."
        
        if len(new_name) > 63:
            return "The new name must be 63 characters or less."
        
        # Vérification des caractères autorisés (lettres, chiffres, tirets)
        import re
        if not re.match(r'^[a-z0-9-]+$', new_name):
            return "The new name can only contain lowercase letters, numbers, and hyphens."
        
        # Ne peut pas commencer ou finir par un tiret
        if new_name.startswith('-') or new_name.endswith('-'):
            return "The new name cannot start or end with a hyphen."
        
        # Ne peut pas avoir de tirets consécutifs
        if '--' in new_name:
            return "The new name cannot contain consecutive hyphens."
        
        return None
    
    async def _handle_rename_error(self, websocket: WebSocket, rename_result: Dict[str, Any], app_name: str):
        """Gère les erreurs de renommage."""
        error_type = rename_result.get("error")
        if error_type == "validation_error":
            await websocket.send_text("❌ Rename request validation failed.")
            await websocket.send_text(f"📋 Error details: {rename_result.get('message', 'Unknown validation error')}")
        elif error_type == "http_409":
            await websocket.send_text("❌ A application with this name already exists.")
            await websocket.send_text("💡 Please choose a different name.")
        elif error_type == "http_404":
            await websocket.send_text("❌ Application not found.")
            await websocket.send_text("💡 Please check the application name and region.")
        else:
            await websocket.send_text(f"❌ Rename request failed: {rename_result.get('message', 'Unknown error')}")
    
    async def _handle_rename_success(self, websocket: WebSocket, rename_result: Dict[str, Any], 
                                   app_name: str, new_name: str, context: AppContext):
        """Gère le succès du renommage."""
        await self._send_success_message(websocket, f"Application *{app_name}* has been successfully renamed to *{new_name}*!")
        
        # Afficher les informations de l'application renommée
        app_data = rename_result.get("app", {})
        if app_data:
            await websocket.send_text("📋 Application details:")
            await websocket.send_text(f"  • Name: {app_data.get('name', new_name)}")
            await websocket.send_text(f"  • Status: {app_data.get('status', 'unknown')}")
            await websocket.send_text(f"  • Region: {app_data.get('region', 'unknown')}")
        
        # Mettre à jour le contexte si nécessaire
        if context.app_name == app_name:
            context.app_name = new_name
            await websocket.send_text(f"🔄 Context updated: current app is now *{new_name}*")
    
    async def _handle_rename_failure(self, websocket: WebSocket, app_name: str):
        """Gère l'échec du renommage."""
        await self._send_error_message(websocket, f"Failed to rename application *{app_name}*.")
        await websocket.send_text("🔍 Possible causes:")
        await websocket.send_text("  • Application doesn't exist")
        await websocket.send_text("  • Invalid region")
        await websocket.send_text("  • New name already exists")
        await websocket.send_text("  • Invalid new name format")
        await websocket.send_text("  • Insufficient permissions")
        await websocket.send_text("  • Authentication issue")
        await websocket.send_text("💡 Check the server logs for detailed error information.")


class ListEnvVarsHandler(BaseHandler):
    """Handler pour l'intent 'list_env_vars'."""
    
    def __init__(self, app_service: AppManagementService, websocket_helpers: WebSocketHelpers):
        super().__init__(websocket_helpers)
        self.app_service = app_service
    
    async def handle(self, websocket: WebSocket, intent_response: IntentResponse, context: AppContext) -> bool:
        if intent_response.intent["name"] != "list_env_vars":
            return False
        
        entities = self.context_manager.extract_entities(intent_response)
        
        # Validation des paramètres requis
        params = await self._handle_common_validation(
            websocket, intent_response, context,
            ["app_name", "region"],
            "To list environment variables, I need the app name and region."
        )
        if not params:
            return True
        
        app_name = params["app_name"]
        region = params["region"]
        
        # Option pour les alias (par défaut True)
        aliases = entities.get("aliases", "true").lower() == "true"
        
        await websocket.send_text(f"🔍 Getting environment variables for *{app_name}* on *{region}*...")
        
        try:
            variables_result = self.app_service.get_app_variables(app_name, region, aliases)
            
            if variables_result and "error" in variables_result:
                await self._handle_variables_error(websocket, variables_result, app_name)
            elif variables_result:
                await self._handle_variables_success(websocket, variables_result, app_name, aliases)
            else:
                await self._handle_variables_failure(websocket, app_name)
                
        except Exception as e:
            await self._send_error_message(websocket, f"Error while getting environment variables: {str(e)}")
        
        return True
    
    async def _handle_variables_error(self, websocket: WebSocket, variables_result: Dict[str, Any], app_name: str):
        """Gère les erreurs lors de la récupération des variables."""
        error_type = variables_result.get("error")
        if error_type == "http_404":
            await websocket.send_text("❌ Application not found.")
            await websocket.send_text("💡 Please check the application name and region.")
        elif error_type == "http_401":
            await websocket.send_text("❌ Authentication failed.")
            await websocket.send_text("💡 Please check your API token.")
        else:
            await websocket.send_text(f"❌ Failed to get environment variables: {variables_result.get('message', 'Unknown error')}")
    
    async def _handle_variables_success(self, websocket: WebSocket, variables_result: Dict[str, Any], 
                                      app_name: str, aliases: bool):
        """Gère le succès de la récupération des variables."""
        variables = variables_result.get("variables", [])
        
        if not variables:
            await websocket.send_text(f"📋 No environment variables found for *{app_name}*.")
            await websocket.send_text("💡 You can add environment variables through the Scalingo dashboard or CLI.")
            return
        
        # Affichage du nombre de variables
        await websocket.send_text(f"📋 Found {len(variables)} environment variable{'s' if len(variables) > 1 else ''} for *{app_name}*:")
        await websocket.send_text("")
        
        # Affichage des variables
        for i, var in enumerate(variables, 1):
            name = var.get("name", "unknown")
            value = var.get("value", "")
            var_id = var.get("id", "")
            
            # Masquer les valeurs sensibles (mots de passe, tokens, etc.)
            display_value = self._mask_sensitive_value(name, value)
            
            await websocket.send_text(f"**{i}.** `{name}`")
            await websocket.send_text(f"   Value: `{display_value}`")
            if var_id:
                await websocket.send_text(f"   ID: `{var_id}`")
            await websocket.send_text("")
        
        # Information sur les alias
        if aliases:
            await websocket.send_text("ℹ️ Variables are shown with interpolated aliases (e.g., `$DATABASE_URL` → actual URL)")
        else:
            await websocket.send_text("ℹ️ Variables are shown without alias interpolation (raw values)")
    
    async def _handle_variables_failure(self, websocket: WebSocket, app_name: str):
        """Gère l'échec de la récupération des variables."""
        await self._send_error_message(websocket, f"Failed to get environment variables for *{app_name}*.")
        await websocket.send_text("🔍 Possible causes:")
        await websocket.send_text("  • Application doesn't exist")
        await websocket.send_text("  • Invalid region")
        await websocket.send_text("  • Insufficient permissions")
        await websocket.send_text("  • Authentication issue")
        await websocket.send_text("💡 Check the server logs for detailed error information.")
    
    def _mask_sensitive_value(self, name: str, value: str) -> str:
        """Masque les valeurs sensibles dans les variables d'environnement."""
        # Liste des noms de variables sensibles
        sensitive_patterns = [
            'password', 'passwd', 'pwd', 'secret', 'key', 'token', 'auth',
            'credential', 'private', 'api_key', 'access_key', 'secret_key'
        ]
        
        name_lower = name.lower()
        
        # Vérifier si le nom contient des mots sensibles
        is_sensitive = any(pattern in name_lower for pattern in sensitive_patterns)
        
        if is_sensitive and value:
            # Masquer la valeur en gardant les premiers et derniers caractères
            if len(value) <= 4:
                return "*" * len(value)
            else:
                return value[:2] + "*" * (len(value) - 4) + value[-2:]
        
        return value


class AddEnvVarHandler(BaseHandler):
    """Handler pour l'intent 'add_env_var'."""
    
    def __init__(self, app_service: AppManagementService, websocket_helpers: WebSocketHelpers):
        super().__init__(websocket_helpers)
        self.app_service = app_service
    
    async def handle(self, websocket: WebSocket, intent_response: IntentResponse, context: AppContext) -> bool:
        if intent_response.intent["name"] != "add_env_var":
            return False
        
        entities = self.context_manager.extract_entities(intent_response)
        
        # Validation des paramètres requis
        params = await self._handle_common_validation(
            websocket, intent_response, context,
            ["app_name", "region"],
            "To add an environment variable, I need the app name and region."
        )
        if not params:
            return True
        
        app_name = params["app_name"]
        region = params["region"]
        variable_name = entities.get("variable_name")
        variable_value = entities.get("variable_value")
        
        # Validation des paramètres de la variable
        validation_error = self._validate_variable_params(variable_name, variable_value)
        if validation_error:
            await websocket.send_text(f"😕 {validation_error}")
            return True
        
        await websocket.send_text(f"🔧 Adding environment variable *{variable_name}* to *{app_name}* on *{region}*...")
        
        try:
            add_result = self.app_service.add_app_variable(app_name, region, variable_name, variable_value)
            
            if add_result and "error" in add_result:
                await self._handle_add_variable_error(websocket, add_result, app_name)
            elif add_result:
                await self._handle_add_variable_success(websocket, add_result, app_name, variable_name)
            else:
                await self._handle_add_variable_failure(websocket, app_name)
                
        except Exception as e:
            await self._send_error_message(websocket, f"Error while adding environment variable: {str(e)}")
        
        return True
    
    def _validate_variable_params(self, variable_name: str, variable_value: str) -> Optional[str]:
        """Valide les paramètres de la variable d'environnement."""
        if not variable_name or not variable_name.strip():
            return "I need the variable name (e.g., 'add RAILS_ENV to my-app')."
        
        if not variable_value:
            return "I need the variable value (e.g., 'add RAILS_ENV=production to my-app')."
        
        variable_name = variable_name.strip()
        
        # Vérification de la longueur du nom
        if len(variable_name) > 64:
            return "Variable name cannot exceed 64 characters."
        
        # Vérification de la longueur de la valeur
        if len(variable_value) > 8192:
            return "Variable value cannot exceed 8192 characters."
        
        # Vérification des caractères autorisés pour le nom
        import re
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', variable_name):
            return "Variable name can only contain letters, numbers, and underscores, and must start with a letter or underscore."
        
        return None
    
    async def _handle_add_variable_error(self, websocket: WebSocket, add_result: Dict[str, Any], app_name: str):
        """Gère les erreurs lors de l'ajout de variable."""
        error_type = add_result.get("error")
        if error_type == "validation_error":
            await websocket.send_text("❌ Environment variable validation failed.")
            await websocket.send_text(f"📋 Error details: {add_result.get('message', 'Unknown validation error')}")
        elif error_type == "http_404":
            await websocket.send_text("❌ Application not found.")
            await websocket.send_text("💡 Please check the application name and region.")
        elif error_type == "http_409":
            await websocket.send_text("❌ A variable with this name already exists.")
            await websocket.send_text("💡 Please choose a different variable name or update the existing one.")
        elif error_type == "http_401":
            await websocket.send_text("❌ Authentication failed.")
            await websocket.send_text("💡 Please check your API token.")
        else:
            await websocket.send_text(f"❌ Failed to add environment variable: {add_result.get('message', 'Unknown error')}")
    
    async def _handle_add_variable_success(self, websocket: WebSocket, add_result: Dict[str, Any], 
                                         app_name: str, variable_name: str):
        """Gère le succès de l'ajout de variable."""
        await self._send_success_message(websocket, f"Environment variable *{variable_name}* has been successfully added to *{app_name}*!")
        
        # Afficher les informations de la variable créée
        variable_data = add_result.get("variable", {})
        if variable_data:
            await websocket.send_text("📋 Variable details:")
            await websocket.send_text(f"  • Name: `{variable_data.get('name', variable_name)}`")
            await websocket.send_text(f"  • ID: `{variable_data.get('id', 'unknown')}`")
            await websocket.send_text(f"  • Value: `{variable_data.get('value', 'hidden')}`")
        
        await websocket.send_text("💡 The application will need to be restarted for the new environment variable to take effect.")
    
    async def _handle_add_variable_failure(self, websocket: WebSocket, app_name: str):
        """Gère l'échec de l'ajout de variable."""
        await self._send_error_message(websocket, f"Failed to add environment variable to *{app_name}*.")
        await websocket.send_text("🔍 Possible causes:")
        await websocket.send_text("  • Application doesn't exist")
        await websocket.send_text("  • Invalid region")
        await websocket.send_text("  • Insufficient permissions")
        await websocket.send_text("  • Authentication issue")
        await websocket.send_text("💡 Check the server logs for detailed error information.")
