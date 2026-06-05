"""
WebSocket Connection Manager for ws.v2 protocol.

This module provides connection state tracking, message history, ping/pong heartbeat,
and authentication for WebSocket connections.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from enum import Enum

from fastapi import WebSocket

from app.core.logging import StructuredLogger

logger = StructuredLogger("ws_connection_manager")


class ConnectionStatus(str, Enum):
    """Status of a WebSocket connection."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    AUTHENTICATED = "authenticated"
    ERROR = "error"


class WebSocketVersion(str, Enum):
    """Supported WebSocket protocol versions."""
    V1 = "ws.v1"
    V2 = "ws.v2"


@dataclass
class MessageRecord:
    """A single message in the connection history."""
    message_id: str
    timestamp: float
    direction: str  # "in" or "out"
    message_type: str  # "text", "json", "binary", "system"
    content: Any
    command: Optional[str] = None
    status: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "direction": self.direction,
            "message_type": self.message_type,
            "content": self.content,
            "command": self.command,
            "status": self.status,
        }


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    connection_id: str
    websocket: WebSocket
    session_id: str
    user_id: str
    client_host: str
    client_port: int
    status: ConnectionStatus = ConnectionStatus.CONNECTING
    version: WebSocketVersion = WebSocketVersion.V2
    connected_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    last_ping: float = 0.0
    last_pong: float = 0.0
    authentication_token: Optional[str] = None
    is_authenticated: bool = False
    message_history: List[MessageRecord] = field(default_factory=list)
    message_count: int = 0
    error_count: int = 0
    ping_count: int = 0
    pong_count: int = 0
    ping_timeout: float = 30.0  # seconds
    idle_timeout: float = 300.0  # seconds
    
    def update_last_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = time.time()
    
    def add_message(self, record: MessageRecord) -> None:
        """Add a message to the history."""
        self.message_history.append(record)
        self.message_count += 1
        
        # Keep only last 1000 messages
        if len(self.message_history) > 1000:
            self.message_history = self.message_history[-1000:]
    
    def get_message_history(self, limit: int = 100) -> List[MessageRecord]:
        """Get recent message history."""
        return self.message_history[-limit:]
    
    def is_idle(self) -> bool:
        """Check if connection is idle."""
        return time.time() - self.last_activity > self.idle_timeout
    
    def is_ping_timed_out(self) -> bool:
        """Check if ping/pong heartbeat is timed out."""
        if self.last_pong == 0.0:
            return False
        return time.time() - self.last_pong > self.ping_timeout
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "connection_id": self.connection_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "client": f"{self.client_host}:{self.client_port}",
            "status": self.status.value,
            "version": self.version.value,
            "connected_at": self.connected_at,
            "last_activity": self.last_activity,
            "is_authenticated": self.is_authenticated,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "ping_count": self.ping_count,
            "pong_count": self.pong_count,
        }


class WebSocketConnectionManager:
    """
    Manager for WebSocket connections.
    
    Provides:
    - Connection state tracking
    - Message history management
    - Ping/pong heartbeat monitoring
    - Connection authentication
    - Multiple WebSocket version support
    - Connection cleanup
    """
    
    def __init__(
        self,
        ping_interval: float = 20.0,
        ping_timeout: float = 30.0,
        idle_timeout: float = 300.0,
        max_connections: int = 10000,
    ):
        self._connections: Dict[str, ConnectionInfo] = {}
        self._active_connections: Set[str] = set()
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._idle_timeout = idle_timeout
        self._max_connections = max_connections
        self._lock = asyncio.Lock()
        self._ping_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def start(self) -> None:
        """Start the connection manager."""
        async with self._lock:
            if self._running:
                return
            self._running = True
            self._ping_task = asyncio.create_task(self._ping_monitor())
            self._cleanup_task = asyncio.create_task(self._cleanup_idle_connections())
            logger.info("WebSocket connection manager started")
    
    async def stop(self) -> None:
        """Stop the connection manager."""
        async with self._lock:
            self._running = False
            if self._ping_task:
                self._ping_task.cancel()
                try:
                    await self._ping_task
                except asyncio.CancelledError:
                    pass
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            logger.info("WebSocket connection manager stopped")
    
    async def register_connection(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
        version: WebSocketVersion = WebSocketVersion.V2,
    ) -> ConnectionInfo:
        """Register a new WebSocket connection."""
        client_host = websocket.client.host if websocket.client else "unknown"
        client_port = websocket.client.port if websocket.client else 0
        
        connection_id = str(uuid.uuid4())
        
        connection = ConnectionInfo(
            connection_id=connection_id,
            websocket=websocket,
            session_id=session_id,
            user_id=user_id,
            client_host=client_host,
            client_port=client_port,
            version=version,
            ping_timeout=self._ping_timeout,
            idle_timeout=self._idle_timeout,
        )
        
        async with self._lock:
            self._connections[connection_id] = connection
            self._active_connections.add(connection_id)
            connection.status = ConnectionStatus.CONNECTED
            
            logger.info(
                "Connection registered",
                connection_id=connection_id,
                session_id=session_id,
                user_id=user_id,
                client=f"{client_host}:{client_port}",
                version=version.value,
            )
        
        return connection
    
    async def unregister_connection(self, connection_id: str) -> bool:
        """Unregister a WebSocket connection."""
        async with self._lock:
            if connection_id not in self._connections:
                return False
            
            connection = self._connections[connection_id]
            connection.status = ConnectionStatus.DISCONNECTED
            self._active_connections.discard(connection_id)
            
            # Close the WebSocket if it's still open
            try:
                if not connection.websocket.client.connected:
                    await connection.websocket.close()
            except Exception:
                pass
            
            del self._connections[connection_id]
            
            logger.info(
                "Connection unregistered",
                connection_id=connection_id,
                session_id=connection.session_id,
                user_id=connection.user_id,
            )
        
        return True
    
    async def get_connection(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get a connection by ID."""
        async with self._lock:
            return self._connections.get(connection_id)
    
    async def get_connections_by_session(self, session_id: str) -> List[ConnectionInfo]:
        """Get all connections for a session."""
        async with self._lock:
            return [
                conn for conn in self._connections.values()
                if conn.session_id == session_id
            ]
    
    async def get_connections_by_user(self, user_id: str) -> List[ConnectionInfo]:
        """Get all connections for a user."""
        async with self._lock:
            return [
                conn for conn in self._connections.values()
                if conn.user_id == user_id
            ]
    
    async def get_all_connections(self) -> List[ConnectionInfo]:
        """Get all active connections."""
        async with self._lock:
            return list(self._connections.values())
    
    async def get_connection_count(self) -> int:
        """Get the number of active connections."""
        async with self._lock:
            return len(self._connections)
    
    async def is_at_capacity(self) -> bool:
        """Check if the connection limit has been reached."""
        async with self._lock:
            return len(self._connections) >= self._max_connections
    
    async def authenticate_connection(
        self,
        connection_id: str,
        token: str,
    ) -> bool:
        """Authenticate a WebSocket connection."""
        async with self._lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return False
            
            # Here you would validate the token against your authentication system
            # For now, we'll just store it and mark as authenticated
            connection.authentication_token = token
            connection.is_authenticated = True
            connection.status = ConnectionStatus.AUTHENTICATED
            
            logger.info(
                "Connection authenticated",
                connection_id=connection_id,
                user_id=connection.user_id,
            )
        
        return True
    
    async def record_message(
        self,
        connection_id: str,
        direction: str,
        message_type: str,
        content: Any,
        command: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[MessageRecord]:
        """Record a message for a connection."""
        async with self._lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return None
            
            record = MessageRecord(
                message_id=str(uuid.uuid4()),
                timestamp=time.time(),
                direction=direction,
                message_type=message_type,
                content=content,
                command=command,
                status=status,
            )
            
            connection.add_message(record)
            connection.update_last_activity()
            
            return record
    
    async def record_ping(self, connection_id: str) -> bool:
        """Record a ping sent to a connection."""
        async with self._lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return False
            
            connection.ping_count += 1
            connection.last_ping = time.time()
            connection.update_last_activity()
            
            return True
    
    async def record_pong(self, connection_id: str) -> bool:
        """Record a pong received from a connection."""
        async with self._lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return False
            
            connection.pong_count += 1
            connection.last_pong = time.time()
            connection.update_last_activity()
            
            return True
    
    async def record_error(self, connection_id: str, error: str) -> bool:
        """Record an error for a connection."""
        async with self._lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return False
            
            connection.error_count += 1
            logger.warning(
                "Connection error",
                connection_id=connection_id,
                error=error,
                session_id=connection.session_id,
            )
            
            return True
    
    async def _ping_monitor(self) -> None:
        """Monitor connections for ping/pong heartbeat."""
        while self._running:
            await asyncio.sleep(self._ping_interval)
            
            disconnected = []
            async with self._lock:
                for connection_id, connection in self._connections.items():
                    if connection.is_ping_timed_out():
                        logger.warning(
                            "Connection ping timeout",
                            connection_id=connection_id,
                            session_id=connection.session_id,
                            user_id=connection.user_id,
                            last_pong=connection.last_pong,
                        )
                        disconnected.append(connection_id)
            
            # Disconnect timed out connections
            for connection_id in disconnected:
                try:
                    await self.unregister_connection(connection_id)
                except Exception as e:
                    logger.error(
                        "Error disconnecting timed out connection",
                        connection_id=connection_id,
                        error=str(e),
                    )
    
    async def _cleanup_idle_connections(self) -> None:
        """Clean up idle connections."""
        while self._running:
            await asyncio.sleep(60)  # Check every minute
            
            idle_connections = []
            async with self._lock:
                for connection_id, connection in self._connections.items():
                    if connection.is_idle() and connection.status != ConnectionStatus.AUTHENTICATED:
                        idle_connections.append(connection_id)
            
            # Disconnect idle connections
            for connection_id in idle_connections:
                try:
                    connection = await self.get_connection(connection_id)
                    if connection:
                        logger.info(
                            "Connection idle timeout",
                            connection_id=connection_id,
                            session_id=connection.session_id,
                            last_activity=connection.last_activity,
                        )
                    await self.unregister_connection(connection_id)
                except Exception as e:
                    logger.error(
                        "Error disconnecting idle connection",
                        connection_id=connection_id,
                        error=str(e),
                    )
    
    async def broadcast(
        self,
        message: Any,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        exclude_connection: Optional[str] = None,
    ) -> int:
        """Broadcast a message to connections."""
        count = 0
        async with self._lock:
            connections_to_notify = []
            
            if user_id:
                connections_to_notify = [
                    conn for conn in self._connections.values()
                    if conn.user_id == user_id
                ]
            elif session_id:
                connections_to_notify = [
                    conn for conn in self._connections.values()
                    if conn.session_id == session_id
                ]
            else:
                connections_to_notify = list(self._connections.values())
            
            if exclude_connection:
                connections_to_notify = [
                    conn for conn in connections_to_notify
                    if conn.connection_id != exclude_connection
                ]
            
            for connection in connections_to_notify:
                try:
                    if connection.status in [ConnectionStatus.CONNECTED, ConnectionStatus.AUTHENTICATED]:
                        await connection.websocket.send_json(message)
                        count += 1
                except Exception as e:
                    logger.error(
                        "Error broadcasting message",
                        connection_id=connection.connection_id,
                        error=str(e),
                    )
        
        return count
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics."""
        async with self._lock:
            total_connections = len(self._connections)
            authenticated_connections = sum(
                1 for conn in self._connections.values()
                if conn.is_authenticated
            )
            
            return {
                "total_connections": total_connections,
                "authenticated_connections": authenticated_connections,
                "max_connections": self._max_connections,
                "capacity_percentage": (total_connections / self._max_connections) * 100 if self._max_connections > 0 else 0,
                "ping_interval": self._ping_interval,
                "ping_timeout": self._ping_timeout,
                "idle_timeout": self._idle_timeout,
            }


# Singleton instance
_connection_manager: Optional[WebSocketConnectionManager] = None


async def get_connection_manager() -> WebSocketConnectionManager:
    """Get or create the singleton connection manager."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = WebSocketConnectionManager()
        await _connection_manager.start()
    return _connection_manager


async def reset_connection_manager() -> None:
    """Reset the singleton connection manager (useful for testing)."""
    global _connection_manager
    if _connection_manager:
        await _connection_manager.stop()
        _connection_manager = None
