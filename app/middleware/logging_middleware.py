"""
Middleware de logging des requêtes.
"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import StructuredLogger

logger = StructuredLogger("request_middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware pour logger les requêtes HTTP."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log de la requête entrante
        logger.info(
            "Requête entrante",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None
        )
        
        # Traitement de la requête
        response = await call_next(request)
        
        # Calcul du temps de traitement
        process_time = time.time() - start_time
        
        # Log de la réponse
        logger.info(
            "Requête traitée",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=f"{process_time:.3f}s"
        )
        
        return response
