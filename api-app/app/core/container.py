"""
Conteneur d'injection de dépendances.

Simple dependency injection container for managing singleton
and transient dependencies throughout the application.
"""
from typing import TypeVar, Type, Optional, Dict, Any, Callable
from functools import lru_cache

T = TypeVar('T')


class DIContainer:
    """Conteneur d'injection de dépendances simple."""
    
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
    
    def register_singleton(self, interface: Type[T], implementation: T) -> None:
        """Enregistre un service comme singleton."""
        self._services[interface] = implementation
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Enregistre une factory pour créer des instances."""
        self._factories[interface] = factory
    
    def get(self, interface: Type[T]) -> T:
        """Récupère une instance du service."""
        # Vérifier d'abord les singletons
        if interface in self._services:
            return self._services[interface]
        
        # Vérifier les factories
        if interface in self._factories:
            instance = self._factories[interface]()
            # Optionnel: mettre en cache comme singleton
            self._services[interface] = instance
            return instance
        
        raise ValueError(f"Service {interface} non enregistré dans le conteneur")
    
    def register_transient(self, interface: Type[T], implementation: Type[T]) -> None:
        """Enregistre un service comme transient (nouvelle instance à chaque fois)."""
        self._factories[interface] = lambda: implementation()


# Instance globale du conteneur
container = DIContainer()


def inject(interface: Type[T]) -> T:
    """Décorateur pour l'injection de dépendances."""
    return container.get(interface)
