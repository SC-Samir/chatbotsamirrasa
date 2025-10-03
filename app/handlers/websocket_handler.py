"""
Handler pour la gestion des connexions WebSocket.
"""
import asyncio
import json
import redis
from typing import Dict, Any, Optional
from fastapi import WebSocket
from rasa.core.agent import Agent
from app.models import AppContext, IntentResponse
from app.handlers.intent_handlers import IntentHandlerManager
from app.config import settings


class WebSocketHandler:
    """Handler for WebSocket connections."""
    
    def __init__(self, agent: Agent, intent_handler_manager: IntentHandlerManager):
        self.agent = agent
        self.intent_handler_manager = intent_handler_manager
        self.redis_client = redis.from_url(settings.redis_url)
    
    async def handle_connection(self, websocket: WebSocket) -> None:
        """Handle a WebSocket connection."""
        await websocket.accept()
        await websocket.send_text("Hello! I'm the ScalingoOps agent. What can I do for you?")
        
        current_deployment_id = None
        redis_task = None
        
        # Contexte mémorisé
        context = AppContext()
        
        try:
            while True:
                data = await websocket.receive_text()
                
                # Parser le message avec Rasa
                interpretation = await self.agent.parse_message(message_data=data)
                
                intent_response = IntentResponse(
                    intent=interpretation["intent"],
                    entities=interpretation["entities"],
                    text=data
                )
                
                
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
                    current_deployment_id = deployment_id
                elif not result:
                    await websocket.send_text("😕 Command not recognized or incomplete. I need the app name, region and GitHub repo (optional: the git ref).")
                
        except Exception as e:
            print(f"WebSocket error: {e}")
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
                        await websocket.send_text(data['message'])
                    except json.JSONDecodeError:
                        # Handle case where message data is not JSON
                        await websocket.send_text(str(message['data']))
                    except Exception as e:
                        print(f"Error sending message to WebSocket: {e}")
                        break
                        
                await asyncio.sleep(0.1)  # Small delay to avoid busy waiting
        except asyncio.CancelledError:
            print(f"Redis Pub/Sub task cancelled for channel: {channel}")
        except Exception as e:
            print(f"Error Redis Pub/Sub: {e}")
        finally:
            try:
                await asyncio.get_event_loop().run_in_executor(None, pubsub.unsubscribe, channel)
                await asyncio.get_event_loop().run_in_executor(None, pubsub.close)
            except Exception as e:
                print(f"Error closing Redis Pub/Sub: {e}")
