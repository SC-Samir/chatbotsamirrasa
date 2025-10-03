"""
Service de gestion des applications.
"""
from typing import Optional, Dict, Any, List
from app.scalingo_manager import ScalingoManager


class AppManagementService:
    """Service pour la gestion des applications."""
    
    def __init__(self, scalingo_manager: ScalingoManager):
        self.scalingo_manager = scalingo_manager
    
    def restart_app(self, app_name: str, region: str, scope: List[str] = None) -> Optional[Dict[str, Any]]:
        """Redémarre une application."""
        return self.scalingo_manager.restart_app(app_name, region, scope)
    
    def scale_app(self, app_name: str, region: str, containers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Met à l'échelle une application."""
        return self.scalingo_manager.scale_app(app_name, region, containers)
    
    def delete_app(self, app_name: str, region: str) -> bool:
        """Supprime une application."""
        return self.scalingo_manager.delete_app(app_name, region)
    
    def get_app_status(self, app_name: str, region: str) -> Optional[Dict[str, Any]]:
        """Récupère le statut d'une application."""
        return self.scalingo_manager.get_app_status(app_name, region)
    
    def get_containers_status(self, app_name: str, region: str) -> Optional[Dict[str, Any]]:
        """Récupère le statut des conteneurs."""
        return self.scalingo_manager.get_containers_status(app_name, region)
    
    def validate_scale_params(self, container_name: str, container_amount: str) -> Optional[str]:
        """Valide les paramètres de scaling."""
        if not container_name or not container_amount:
            return "To scale, I need the container name and amount (e.g., 'scale web to 3')."
        
        try:
            int(container_amount)
        except ValueError:
            return f"Invalid amount '{container_amount}'. Please provide a number."
        
        return None
    
    def build_container_config(self, container_name: str, amount: int, size: str = None) -> Dict[str, Any]:
        """Construit la configuration d'un conteneur."""
        config = {
            "name": container_name,
            "amount": amount
        }
        if size:
            config["size"] = size.upper()
        return config
    
    def rename_app(self, app_name: str, region: str, new_name: str) -> Optional[Dict[str, Any]]:
        """Renomme une application."""
        return self.scalingo_manager.rename_app(app_name, region, new_name)
    
    def get_app_variables(self, app_name: str, region: str, aliases: bool = True) -> Optional[Dict[str, Any]]:
        """Récupère les variables d'environnement d'une application."""
        return self.scalingo_manager.get_app_variables(app_name, region, aliases)
    
    def add_app_variable(self, app_name: str, region: str, variable_name: str, variable_value: str) -> Optional[Dict[str, Any]]:
        """Ajoute une variable d'environnement à une application."""
        return self.scalingo_manager.add_app_variable(app_name, region, variable_name, variable_value)