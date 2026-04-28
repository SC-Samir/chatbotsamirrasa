"""
Middleware de gestion des erreurs.
"""
import traceback
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.exceptions import (
    ScalingoAPIError,
    LogsServiceError,
    DeploymentError,
    ConfigurationError,
    ValidationError
)
from app.core.logging import StructuredLogger
from app.domain import DomainValidationError, OperationExecutionError, FailureReason

logger = StructuredLogger("error_middleware")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware pour la gestion centralisée des erreurs."""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except HTTPException:
            # Les erreurs HTTP de FastAPI sont déjà gérées
            raise
        except OperationExecutionError as e:
            error = e.error
            status_code = error.status_code or 500
            if error.reason == FailureReason.VALIDATION:
                status_code = 400
            elif error.reason == FailureReason.AUTH:
                status_code = 401
            elif error.reason == FailureReason.NOT_FOUND:
                status_code = 404
            elif error.reason == FailureReason.CONFLICT:
                status_code = 409
            elif error.reason == FailureReason.TRANSIENT:
                status_code = 503

            logger.error(
                "Operation execution error",
                url=str(request.url),
                reason=error.reason.value,
                status_code=status_code,
                details=error.details,
            )
            return JSONResponse(
                status_code=status_code,
                content={
                    "error": "OperationExecutionError",
                    "reason": error.reason.value,
                    "message": error.message,
                    "details": error.details,
                },
            )
        except DomainValidationError as e:
            logger.error("Domain validation error", url=str(request.url), message=str(e))
            return JSONResponse(
                status_code=400,
                content={"error": "DomainValidationError", "message": str(e)},
            )
        except ScalingoAPIError as e:
            logger.error(
                "Erreur API Scalingo",
                url=str(request.url),
                status_code=e.status_code,
                details=e.details
            )
            return JSONResponse(
                status_code=e.status_code or 502,
                content={
                    "error": "ScalingoAPIError",
                    "message": e.message,
                    "details": e.details
                }
            )
        except LogsServiceError as e:
            logger.error(
                "Erreur service de logs",
                url=str(request.url),
                app_name=e.app_name,
                details=e.details
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "LogsServiceError",
                    "message": e.message,
                    "app_name": e.app_name,
                    "details": e.details
                }
            )
        except DeploymentError as e:
            logger.error(
                "Erreur de déploiement",
                url=str(request.url),
                app_name=e.app_name,
                deployment_id=e.deployment_id,
                details=e.details
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "DeploymentError",
                    "message": e.message,
                    "app_name": e.app_name,
                    "deployment_id": e.deployment_id,
                    "details": e.details
                }
            )
        except ConfigurationError as e:
            logger.error(
                "Erreur de configuration",
                url=str(request.url),
                config_key=e.config_key
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "ConfigurationError",
                    "message": e.message,
                    "config_key": e.config_key
                }
            )
        except ValidationError as e:
            logger.error(
                "Erreur de validation",
                url=str(request.url),
                field=e.field,
                value=e.value
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "ValidationError",
                    "message": e.message,
                    "field": e.field,
                    "value": e.value
                }
            )
        except Exception as e:
            logger.error(
                "Erreur inattendue",
                url=str(request.url),
                error=str(e),
                traceback=traceback.format_exc()
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "InternalServerError",
                    "message": "Une erreur interne s'est produite",
                    "details": str(e) if logger.logger.level <= 10 else "Détails masqués en production"
                }
            )
