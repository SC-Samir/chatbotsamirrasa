"""
Unit tests for new gateway methods added in Phase 4.5.
"""
from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock, patch

from app.copilot.scalingo_ops.gateway import ScalingoOpsGateway
from app.infrastructure.scalingo.http_client import ScalingoHTTPClient


class TestNewGatewayMethods(unittest.TestCase):
    """Tests for new gateway methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock(spec=ScalingoHTTPClient)
        self.gateway = ScalingoOpsGateway(self.mock_client)
    
    def test_apps_stats(self):
        """Test apps_stats method."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.value = {
            "cpu": 0.5,
            "memory": 512,
            "requests": 1000,
            "response_time": 100,
        }
        self.mock_client.request.return_value = mock_response
        
        result = self.gateway.apps_stats("my-app", "par")
        
        self.mock_client.request.assert_called_once()
        args, kwargs = self.mock_client.request.call_args
        self.assertEqual(args[0], "GET")
        self.assertEqual(str(args[1]), "par")
        self.assertEqual(args[2], "/v1/apps/my-app/stats")
        
        self.assertEqual(result, {
            "cpu": 0.5,
            "memory": 512,
            "requests": 1000,
            "response_time": 100,
        })
    
    def test_apps_stats_failure(self):
        """Test apps_stats method when API call fails."""
        mock_response = MagicMock()
        mock_response.success = False
        mock_response.value = None
        self.mock_client.request.return_value = mock_response
        
        result = self.gateway.apps_stats("my-app", "par")
        
        self.assertEqual(result, {"stats": {}})
    
    def test_apps_backups_list(self):
        """Test apps_backups_list method."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.value = {
            "backups": [
                {"id": "backup-1", "created_at": "2024-01-01", "size": 1024},
                {"id": "backup-2", "created_at": "2024-01-02", "size": 2048},
            ]
        }
        self.mock_client.request.return_value = mock_response
        
        result = self.gateway.apps_backups_list("my-app", "par")
        
        self.mock_client.request.assert_called_once()
        args, kwargs = self.mock_client.request.call_args
        self.assertEqual(args[0], "GET")
        self.assertEqual(args[2], "/v1/apps/my-app/backups")
        
        self.assertEqual(result, {
            "backups": [
                {"id": "backup-1", "created_at": "2024-01-01", "size": 1024},
                {"id": "backup-2", "created_at": "2024-01-02", "size": 2048},
            ]
        })
    
    def test_apps_backups_create(self):
        """Test apps_backups_create method."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.value = {"status": "queued", "backup_id": "backup-1"}
        self.mock_client.request.return_value = mock_response
        
        result = self.gateway.apps_backups_create("my-app", "par")
        
        self.mock_client.request.assert_called_once()
        args, kwargs = self.mock_client.request.call_args
        self.assertEqual(args[0], "POST")
        self.assertEqual(args[2], "/v1/apps/my-app/backups")
        
        self.assertEqual(result, {"status": "queued", "backup_id": "backup-1"})
    
    def test_apps_backups_create_failure(self):
        """Test apps_backups_create method when API call fails."""
        mock_response = MagicMock()
        mock_response.success = False
        mock_response.value = None
        self.mock_client.request.return_value = mock_response
        
        result = self.gateway.apps_backups_create("my-app", "par")
        
        self.assertEqual(result, {"accepted": False})
    
    def test_apps_backups_download(self):
        """Test apps_backups_download method."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.value = {
            "id": "backup-1",
            "url": "https://storage.scalingo.com/backups/backup-1.tar.gz",
            "expires_at": "2024-01-03T00:00:00Z",
        }
        self.mock_client.request.return_value = mock_response
        
        result = self.gateway.apps_backups_download("my-app", "par", "backup-1")
        
        self.mock_client.request.assert_called_once()
        args, kwargs = self.mock_client.request.call_args
        self.assertEqual(args[0], "GET")
        self.assertEqual(args[2], "/v1/apps/my-app/backups/backup-1")
        
        self.assertEqual(result, {
            "id": "backup-1",
            "url": "https://storage.scalingo.com/backups/backup-1.tar.gz",
            "expires_at": "2024-01-03T00:00:00Z",
        })
    
    def test_regions_list(self):
        """Test regions_list method."""
        result = self.gateway.regions_list()
        
        self.mock_client.request.assert_not_called()
        
        self.assertIn("regions", result)
        self.assertEqual(len(result["regions"]), 3)
        
        region_names = [r["name"] for r in result["regions"]]
        self.assertIn("par", region_names)
        self.assertIn("osc", region_names)
        self.assertIn("oci", region_names)
    
    @patch('app.copilot.scalingo_ops.gateway.time')
    def test_scalingo_status(self, mock_time):
        """Test scalingo_status method."""
        mock_time.time.return_value = 1234567890
        
        result = self.gateway.scalingo_status()
        
        self.mock_client.request.assert_not_called()
        
        self.assertEqual(result["status"], "operational")
        self.assertEqual(result["version"], "1.0.0")
        self.assertIn("regions", result)
        self.assertEqual(result["timestamp"], 1234567890)
    
    def test_batch_execute_single_command(self):
        """Test batch_execute with single command."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.value = {"app": {"name": "my-app", "id": "app-123"}}
        self.mock_client.request.return_value = mock_response
        
        commands = [
            {"type": "apps.create", "entities": {"app_name": "my-app", "region": "par"}}
        ]
        
        result = self.gateway.batch_execute(commands)
        
        self.assertIn("batch_results", result)
        self.assertEqual(len(result["batch_results"]), 1)
        self.assertEqual(result["batch_results"][0]["command"], "apps.create")
        self.assertTrue(result["batch_results"][0]["success"])
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["successful"], 1)
    
    def test_batch_execute_multiple_commands(self):
        """Test batch_execute with multiple commands."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.value = {"app": {"name": "my-app", "id": "app-123"}}
        self.mock_client.request.return_value = mock_response
        
        commands = [
            {"type": "apps.create", "entities": {"app_name": "app1", "region": "par"}},
            {"type": "apps.create", "entities": {"app_name": "app2", "region": "par"}},
            {"type": "apps.delete", "entities": {"app_name": "app1", "region": "par"}},
        ]
        
        result = self.gateway.batch_execute(commands)
        
        self.assertEqual(len(result["batch_results"]), 3)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["successful"], 3)
    
    def test_batch_execute_max_size_limit(self):
        """Test batch_execute with max size limit."""
        commands = [
            {"type": "apps.create", "entities": {"app_name": f"app{i}", "region": "par"}}
            for i in range(15)
        ]
        
        result = self.gateway.batch_execute(commands)
        
        self.assertEqual(result["error"], "Batch size exceeded")
        self.assertEqual(result["max_size"], 10)
    
    def test_batch_execute_empty(self):
        """Test batch_execute with empty commands list."""
        result = self.gateway.batch_execute([])
        
        self.assertEqual(result["batch_results"], [])
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["successful"], 0)
    
    def test_batch_execute_unknown_command(self):
        """Test batch_execute with unknown command type."""
        commands = [
            {"type": "unknown.command", "entities": {}},
        ]
        
        result = self.gateway.batch_execute(commands)
        
        self.assertEqual(len(result["batch_results"]), 1)
        self.assertEqual(result["batch_results"][0]["command"], "unknown.command")
        self.assertTrue(result["batch_results"][0]["success"])
        self.assertEqual(result["batch_results"][0]["result"], {"error": "Unknown command type"})


class TestGatewayDeploymentsCreate(unittest.TestCase):
    """Tests for deployments_create with new backup-related methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock(spec=ScalingoHTTPClient)
        self.gateway = ScalingoOpsGateway(self.mock_client)
    
    def test_deployments_create_with_github_repo(self):
        """Test deployments_create with github_repo."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.value = {"deployment": {"id": "dep-123"}}
        self.mock_client.request.return_value = mock_response
        
        result = self.gateway.deployments_create(
            app_name="my-app",
            region="par",
            source_url="",
            github_repo="https://github.com/my-repo.git",
            git_ref="main",
        )
        
        self.mock_client.request.assert_called_once()
        args, kwargs = self.mock_client.request.call_args
        self.assertEqual(args[0], "POST")
        self.assertEqual(args[2], "/v1/apps/my-app/deployments")
        
        # Check that source_url is set from github_repo
        json_payload = kwargs.get("json_payload", {})
        self.assertIn("source_url", json_payload)
        self.assertIn("github.com", json_payload["source_url"])
    
    def test_deployments_create_with_source_url(self):
        """Test deployments_create with explicit source_url."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.value = {"deployment": {"id": "dep-123"}}
        self.mock_client.request.return_value = mock_response
        
        result = self.gateway.deployments_create(
            app_name="my-app",
            region="par",
            source_url="https://example.com/source.tar.gz",
            github_repo="",
            git_ref="main",
        )
        
        self.mock_client.request.assert_called_once()
        args, kwargs = self.mock_client.request.call_args
        json_payload = kwargs.get("json_payload", {})
        
        self.assertEqual(json_payload["source_url"], "https://example.com/source.tar.gz")


if __name__ == "__main__":
    unittest.main()
