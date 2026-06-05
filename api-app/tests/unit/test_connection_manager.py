"""
Unit tests for WebSocket connection manager.
"""
from __future__ import annotations

import asyncio
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.copilot.conversation.connection_manager import (
    WebSocketConnectionManager,
    ConnectionInfo,
    ConnectionStatus,
    WebSocketVersion,
    MessageRecord,
    get_connection_manager,
    reset_connection_manager,
)


class TestConnectionStatus(unittest.TestCase):
    """Tests for ConnectionStatus enum."""
    
    def test_enum_values(self):
        """Test that enum values are correct."""
        self.assertEqual(ConnectionStatus.CONNECTING.value, "connecting")
        self.assertEqual(ConnectionStatus.CONNECTED.value, "connected")
        self.assertEqual(ConnectionStatus.DISCONNECTED.value, "disconnected")
        self.assertEqual(ConnectionStatus.AUTHENTICATED.value, "authenticated")
        self.assertEqual(ConnectionStatus.ERROR.value, "error")


class TestWebSocketVersion(unittest.TestCase):
    """Tests for WebSocketVersion enum."""
    
    def test_enum_values(self):
        """Test that enum values are correct."""
        self.assertEqual(WebSocketVersion.V1.value, "ws.v1")
        self.assertEqual(WebSocketVersion.V2.value, "ws.v2")


class TestMessageRecord(unittest.TestCase):
    """Tests for MessageRecord dataclass."""
    
    def test_to_dict(self):
        """Test MessageRecord to_dict method."""
        record = MessageRecord(
            message_id="test-123",
            timestamp=time.time(),
            direction="in",
            message_type="text",
            content="test message",
            command="test.command",
            status="received",
        )
        
        result = record.to_dict()
        
        self.assertEqual(result["message_id"], "test-123")
        self.assertEqual(result["direction"], "in")
        self.assertEqual(result["message_type"], "text")
        self.assertEqual(result["content"], "test message")
        self.assertEqual(result["command"], "test.command")
        self.assertEqual(result["status"], "received")
        self.assertIn("timestamp", result)


class TestConnectionInfo(unittest.TestCase):
    """Tests for ConnectionInfo dataclass."""
    
    def test_default_values(self):
        """Test default values of ConnectionInfo."""
        websocket = MagicMock()
        websocket.client.host = "localhost"
        websocket.client.port = 8080
        
        connection = ConnectionInfo(
            connection_id="conn-123",
            websocket=websocket,
            session_id="session-123",
            user_id="user-123",
            client_host="localhost",
            client_port=8080,
        )
        
        self.assertEqual(connection.connection_id, "conn-123")
        self.assertEqual(connection.session_id, "session-123")
        self.assertEqual(connection.user_id, "user-123")
        self.assertEqual(connection.client_host, "localhost")
        self.assertEqual(connection.client_port, 8080)
        self.assertEqual(connection.status, ConnectionStatus.CONNECTING)
        self.assertEqual(connection.version, WebSocketVersion.V2)
        self.assertIsNotNone(connection.connected_at)
        self.assertIsNotNone(connection.last_activity)
        self.assertEqual(connection.message_count, 0)
        self.assertEqual(connection.error_count, 0)
    
    def test_add_message(self):
        """Test adding messages to connection."""
        websocket = MagicMock()
        connection = ConnectionInfo(
            connection_id="conn-123",
            websocket=websocket,
            session_id="session-123",
            user_id="user-123",
            client_host="localhost",
            client_port=8080,
        )
        
        record = MessageRecord(
            message_id="msg-1",
            timestamp=time.time(),
            direction="in",
            message_type="text",
            content="test",
        )
        
        connection.add_message(record)
        
        self.assertEqual(connection.message_count, 1)
        self.assertEqual(len(connection.message_history), 1)
        self.assertEqual(connection.message_history[0].message_id, "msg-1")
    
    def test_get_message_history(self):
        """Test getting message history."""
        websocket = MagicMock()
        connection = ConnectionInfo(
            connection_id="conn-123",
            websocket=websocket,
            session_id="session-123",
            user_id="user-123",
            client_host="localhost",
            client_port=8080,
        )
        
        for i in range(10):
            record = MessageRecord(
                message_id=f"msg-{i}",
                timestamp=time.time(),
                direction="in",
                message_type="text",
                content=f"test {i}",
            )
            connection.add_message(record)
        
        history = connection.get_message_history(limit=5)
        
        self.assertEqual(len(history), 5)
        # Should return last 5 messages
        self.assertEqual(history[-1].message_id, "msg-9")
    
    def test_message_history_limit(self):
        """Test that message history is limited to 1000 messages."""
        websocket = MagicMock()
        connection = ConnectionInfo(
            connection_id="conn-123",
            websocket=websocket,
            session_id="session-123",
            user_id="user-123",
            client_host="localhost",
            client_port=8080,
        )
        
        for i in range(1050):
            record = MessageRecord(
                message_id=f"msg-{i}",
                timestamp=time.time(),
                direction="in",
                message_type="text",
                content=f"test {i}",
            )
            connection.add_message(record)
        
        self.assertEqual(len(connection.message_history), 1000)
        self.assertEqual(connection.message_history[0].message_id, "msg-50")
    
    def test_is_idle(self):
        """Test idle detection."""
        websocket = MagicMock()
        connection = ConnectionInfo(
            connection_id="conn-123",
            websocket=websocket,
            session_id="session-123",
            user_id="user-123",
            client_host="localhost",
            client_port=8080,
            idle_timeout=1,  # 1 second timeout
        )
        
        self.assertFalse(connection.is_idle())
        
        # Wait for idle timeout
        time.sleep(1.1)
        
        self.assertTrue(connection.is_idle())
    
    def test_to_dict(self):
        """Test to_dict method."""
        websocket = MagicMock()
        connection = ConnectionInfo(
            connection_id="conn-123",
            websocket=websocket,
            session_id="session-123",
            user_id="user-123",
            client_host="localhost",
            client_port=8080,
            status=ConnectionStatus.CONNECTED,
            version=WebSocketVersion.V2,
        )
        
        result = connection.to_dict()
        
        self.assertEqual(result["connection_id"], "conn-123")
        self.assertEqual(result["session_id"], "session-123")
        self.assertEqual(result["user_id"], "user-123")
        self.assertEqual(result["client"], "localhost:8080")
        self.assertEqual(result["status"], "connected")
        self.assertEqual(result["version"], "ws.v2")


@patch('app.copilot.conversation.connection_manager.asyncio')
class TestWebSocketConnectionManager(unittest.TestCase):
    """Tests for WebSocketConnectionManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = WebSocketConnectionManager(
            ping_interval=0.1,
            ping_timeout=0.2,
            idle_timeout=0.5,
            max_connections=10,
        )
    
    def tearDown(self):
        """Clean up after tests."""
        pass
    
    def test_register_connection(self, mock_asyncio):
        """Test registering a connection."""
        websocket = MagicMock()
        websocket.client.host = "localhost"
        websocket.client.port = 8080
        
        connection = asyncio.run(self.manager.register_connection(
            websocket=websocket,
            session_id="session-123",
            user_id="user-123",
            version=WebSocketVersion.V2,
        ))
        
        self.assertEqual(connection.connection_id, connection.connection_id)
        self.assertEqual(connection.session_id, "session-123")
        self.assertEqual(connection.user_id, "user-123")
        self.assertEqual(connection.client_host, "localhost")
        self.assertEqual(connection.client_port, 8080)
        self.assertEqual(connection.status, ConnectionStatus.CONNECTED)
    
    def test_get_connection(self, mock_asyncio):
        """Test getting a connection by ID."""
        websocket = MagicMock()
        websocket.client.host = "localhost"
        websocket.client.port = 8080
        
        connection = asyncio.run(self.manager.register_connection(
            websocket=websocket,
            session_id="session-123",
            user_id="user-123",
        ))
        
        retrieved = asyncio.run(self.manager.get_connection(connection.connection_id))
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.connection_id, connection.connection_id)
    
    def test_get_nonexistent_connection(self, mock_asyncio):
        """Test getting a non-existent connection."""
        result = asyncio.run(self.manager.get_connection("nonexistent"))
        
        self.assertIsNone(result)
    
    def test_unregister_connection(self, mock_asyncio):
        """Test unregistering a connection."""
        websocket = MagicMock()
        websocket.client.host = "localhost"
        websocket.client.port = 8080
        
        connection = asyncio.run(self.manager.register_connection(
            websocket=websocket,
            session_id="session-123",
            user_id="user-123",
        ))
        
        result = asyncio.run(self.manager.unregister_connection(connection.connection_id))
        
        self.assertTrue(result)
        
        retrieved = asyncio.run(self.manager.get_connection(connection.connection_id))
        self.assertIsNone(retrieved)
    
    def test_get_connection_count(self, mock_asyncio):
        """Test getting connection count."""
        self.assertEqual(asyncio.run(self.manager.get_connection_count()), 0)
        
        websocket1 = MagicMock()
        websocket1.client.host = "localhost"
        websocket1.client.port = 8080
        
        websocket2 = MagicMock()
        websocket2.client.host = "localhost"
        websocket2.client.port = 8081
        
        asyncio.run(self.manager.register_connection(
            websocket=websocket1,
            session_id="session-1",
            user_id="user-1",
        ))
        asyncio.run(self.manager.register_connection(
            websocket=websocket2,
            session_id="session-2",
            user_id="user-2",
        ))
        
        self.assertEqual(asyncio.run(self.manager.get_connection_count()), 2)
    
    def test_authenticate_connection(self, mock_asyncio):
        """Test authenticating a connection."""
        websocket = MagicMock()
        websocket.client.host = "localhost"
        websocket.client.port = 8080
        
        connection = asyncio.run(self.manager.register_connection(
            websocket=websocket,
            session_id="session-123",
            user_id="user-123",
        ))
        
        result = asyncio.run(self.manager.authenticate_connection(
            connection.connection_id,
            "test-token",
        ))
        
        self.assertTrue(result)
        
        retrieved = asyncio.run(self.manager.get_connection(connection.connection_id))
        self.assertTrue(retrieved.is_authenticated)
        self.assertEqual(retrieved.authentication_token, "test-token")
        self.assertEqual(retrieved.status, ConnectionStatus.AUTHENTICATED)
    
    def test_record_message(self, mock_asyncio):
        """Test recording a message."""
        websocket = MagicMock()
        connection = asyncio.run(self.manager.register_connection(
            websocket=websocket,
            session_id="session-123",
            user_id="user-123",
        ))
        
        record = asyncio.run(self.manager.record_message(
            connection_id=connection.connection_id,
            direction="in",
            message_type="text",
            content="test message",
            command="test.command",
            status="received",
        ))
        
        self.assertIsNotNone(record)
        self.assertEqual(record.direction, "in")
        self.assertEqual(record.content, "test message")
        
        retrieved = asyncio.run(self.manager.get_connection(connection.connection_id))
        self.assertEqual(retrieved.message_count, 1)
    
    def test_record_ping_pong(self, mock_asyncio):
        """Test recording ping and pong."""
        websocket = MagicMock()
        connection = asyncio.run(self.manager.register_connection(
            websocket=websocket,
            session_id="session-123",
            user_id="user-123",
        ))
        
        asyncio.run(self.manager.record_ping(connection.connection_id))
        asyncio.run(self.manager.record_pong(connection.connection_id))
        
        retrieved = asyncio.run(self.manager.get_connection(connection.connection_id))
        
        self.assertEqual(retrieved.ping_count, 1)
        self.assertEqual(retrieved.pong_count, 1)
    
    def test_get_stats(self, mock_asyncio):
        """Test getting manager statistics."""
        websocket = MagicMock()
        asyncio.run(self.manager.register_connection(
            websocket=websocket,
            session_id="session-1",
            user_id="user-1",
        ))
        asyncio.run(self.manager.register_connection(
            websocket=websocket,
            session_id="session-2",
            user_id="user-2",
        ))
        
        stats = asyncio.run(self.manager.get_stats())
        
        self.assertEqual(stats["total_connections"], 2)
        self.assertEqual(stats["max_connections"], 10)
    
    def test_broadcast(self, mock_asyncio):
        """Test broadcasting messages."""
        websocket1 = MagicMock()
        websocket1.client.connected = True
        websocket2 = MagicMock()
        websocket2.client.connected = True
        
        conn1 = asyncio.run(self.manager.register_connection(
            websocket=websocket1,
            session_id="session-1",
            user_id="user-1",
        ))
        conn2 = asyncio.run(self.manager.register_connection(
            websocket=websocket2,
            session_id="session-2",
            user_id="user-2",
        ))
        
        count = asyncio.run(self.manager.broadcast(
            message={"type": "test"},
            user_id="user-1",
        ))
        
        self.assertEqual(count, 1)
        websocket1.send_json.assert_called_once()
        websocket2.send_json.assert_not_called()
    
    def test_broadcast_to_all(self, mock_asyncio):
        """Test broadcasting to all connections."""
        websocket1 = MagicMock()
        websocket1.client.connected = True
        websocket2 = MagicMock()
        websocket2.client.connected = True
        
        asyncio.run(self.manager.register_connection(
            websocket=websocket1,
            session_id="session-1",
            user_id="user-1",
        ))
        asyncio.run(self.manager.register_connection(
            websocket=websocket2,
            session_id="session-2",
            user_id="user-2",
        ))
        
        count = asyncio.run(self.manager.broadcast(
            message={"type": "test"},
        ))
        
        self.assertEqual(count, 2)
        websocket1.send_json.assert_called_once()
        websocket2.send_json.assert_called_once()


class TestSingletonFunctions(unittest.IsolatedAsyncioTestCase):
    """Tests for singleton functions."""
    
    async def test_get_connection_manager_singleton(self):
        """Test that get_connection_manager returns the same instance."""
        await reset_connection_manager()
        
        manager1 = await get_connection_manager()
        manager2 = await get_connection_manager()
        
        self.assertIs(manager1, manager2)
    
    async def test_reset_connection_manager(self):
        """Test resetting the connection manager."""
        manager1 = await get_connection_manager()
        await reset_connection_manager()
        manager2 = await get_connection_manager()
        
        self.assertIsNot(manager1, manager2)


if __name__ == "__main__":
    unittest.main()
