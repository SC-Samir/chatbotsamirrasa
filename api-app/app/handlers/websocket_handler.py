"""
Handler pour la gestion des connexions WebSocket.
"""
import asyncio
import json
import re

import redis
from fastapi import WebSocket, WebSocketDisconnect
from app.models import AppContext, IntentResponse
from app.handlers.intent_handlers import IntentHandlerManager
from app.config import settings
from app.core.logging import StructuredLogger
from app.infrastructure.rasa import RasaClient

logger = StructuredLogger("websocket_handler")


class WebSocketHandler:
    """Handler for WebSocket connections."""
    
    def __init__(self, rasa_client: RasaClient, intent_handler_manager: IntentHandlerManager):
        self.rasa_client = rasa_client
        self.intent_handler_manager = intent_handler_manager
        self.redis_client = redis.from_url(settings.redis_url)

    @staticmethod
    def _build_logs_fallback_intent(text: str) -> IntentResponse | None:
        """Build fallback intents from common free-text phrasing when NLU misses."""
        candidate = (text or "").strip()
        patterns = [
            (r"^\s*(?:show|get)\s+logs?\s+(?:of|for)\s+([a-z0-9][a-z0-9-]*)\s+(?:on|in)\s+([a-z]{3}-[a-z]+\d)\s*$", "get_logs"),
            (r"^\s*restart\s+(?:app\s+)?([a-z0-9][a-z0-9-]*)\s+(?:on|in)\s+([a-z]{3}-[a-z]+\d)\s*$", "restart"),
            (r"^\s*(?:delete|remove)\s+(?:app\s+)?([a-z0-9][a-z0-9-]*)\s+(?:on|in)\s+([a-z]{3}-[a-z]+\d)\s*$", "delete_app"),
            (r"^\s*(?:list|show|get)\s+(?:env|environment)\s*(?:vars|variables)?\s+(?:for|of)\s+([a-z0-9][a-z0-9-]*)\s+(?:on|in)\s+([a-z]{3}-[a-z]+\d)\s*$", "list_env_vars"),
        ]

        for pattern, intent_name in patterns:
            match = re.match(pattern, candidate, re.IGNORECASE)
            if not match:
                continue
            app_name = match.group(1).lower()
            region = match.group(2).lower()
            return IntentResponse(
                hypotheses=[{"name": intent_name, "confidence": 1.0, "confidence_calibrated": 1.0, "rank": 1, "rationale_features": {"source": 1.0}}],
                final_decision={
                    "action": "accept",
                    "intent": intent_name,
                    "reason": "accepted",
                    "policy": {"source": "regex"},
                    "margin": 1.0,
                },
                entities=[
                    {"entity": "app_name", "value": app_name},
                    {"entity": "region", "value": region},
                ],
                quality_signals={"ambiguity_score": 0.0, "ood_likelihood": 0.0, "calibration_band": "high"},
                text_normalized=candidate,
                model_info={"version": "regex-fallback", "language_profile": "rule-based"},
            )

        return None
    
    async def handle_connection(self, websocket: WebSocket) -> None:
        """Handle a WebSocket connection."""
        await websocket.accept()
        await websocket.send_text("Hello! I'm the ScalingoOps agent. What can I do for you?")
        
        redis_task = None
        
        # Contexte mémorisé
        context = AppContext()
        
        try:
            while True:
                data = await websocket.receive_text()
                
                # Parser le message avec Rasa
                interpretation = await self.rasa_client.parse_message(text=data, retries=1)
                
                intent_response = IntentResponse(**interpretation)
                
                
                # Traiter l'intent
                result = await self.intent_handler_manager.handle_intent(
                    websocket, intent_response, context
                )
                
                # Handle deployment monitoring
                if isinstance(result, dict) and result.get("handled") and result.get("deployment_id"):
                    deployment_id = result["deployment_id"]
                    # Cancel previous Redis task if exists
                    if redis_task:
                        redis_task.cancel()
                    
                    # Start listening to Redis for deployment updates
                    channel = f"deployment:{deployment_id}"
                    redis_task = asyncio.create_task(
                        self.listen_redis_pubsub(websocket, channel)
                    )
                elif not result:
                    if intent_response.decision_action == "clarify":
                        ranking = intent_response.hypotheses[: max(1, settings.nlu_clarification_topk)]
                        suggestions = ", ".join(item.get("name", "unknown") for item in ranking if item.get("name"))
                        await websocket.send_text(
                            f"I’m not fully confident. Did you mean: {suggestions}?"
                        )

                    if settings.nlu_fallback_enable_regex and intent_response.decision_action in {"clarify", "reject"}:
                        fallback_intent = self._build_logs_fallback_intent(data)
                        if fallback_intent:
                            fallback_result = await self.intent_handler_manager.handle_intent(
                                websocket, fallback_intent, context
                            )
                            if fallback_result:
                                continue

                    await websocket.send_text("😕 Command not recognized or incomplete. I need the app name, region and GitHub repo (optional: the git ref).")
                
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected by client")
        except (ValueError, RuntimeError) as exc:
            logger.error("WebSocket processing error", error=str(exc))
            await websocket.send_text("❌ Internal processing error. Please retry.")
        finally:
            if redis_task:
                redis_task.cancel()
    
    async def listen_redis_pubsub(self, websocket: WebSocket, channel: str) -> None:
        """Listen to Redis Pub/Sub messages and send them to the WebSocket."""
        pubsub = self.redis_client.pubsub()
        await asyncio.get_event_loop().run_in_executor(None, pubsub.subscribe, channel)
        
        try:
            while True:
                # Use executor to make blocking Redis call non-blocking
                message = await asyncio.get_event_loop().run_in_executor(
                    None, pubsub.get_message, 0.1
                )
                
                if message and message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        if isinstance(data, dict):
                            if "type" in data and "deployment_id" in data:
                                await websocket.send_json(data)
                            elif "message" in data:
                                await websocket.send_text(data["message"])
                            else:
                                await websocket.send_text(json.dumps(data))
                        else:
                            await websocket.send_text(str(data))
                    except json.JSONDecodeError:
                        # Handle case where message data is not JSON
                        await websocket.send_text(str(message['data']))
                    except (TypeError, ValueError) as exc:
                        logger.error("Error sending Redis message to websocket", error=str(exc))
                        break
                        
                await asyncio.sleep(0.1)  # Small delay to avoid busy waiting
        except asyncio.CancelledError:
            logger.info("Redis Pub/Sub task cancelled", channel=channel)
        except redis.RedisError as exc:
            logger.error("Redis Pub/Sub error", channel=channel, error=str(exc))
        finally:
            try:
                await asyncio.get_event_loop().run_in_executor(None, pubsub.unsubscribe, channel)
                await asyncio.get_event_loop().run_in_executor(None, pubsub.close)
            except redis.RedisError as exc:
                logger.error("Error closing Redis Pub/Sub", channel=channel, error=str(exc))
