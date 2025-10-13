"""Simplified tests for GitHub webhook server functionality."""

import asyncio
import json
import os
import tempfile
import hashlib
import hmac
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from roadmap.core import RoadmapCore
from roadmap.models import Issue
from roadmap.webhook_server import GitHubWebhookServer


class TestGitHubWebhookServer:
    """Test cases for GitHubWebhookServer class."""

    @pytest.fixture
    def webhook_server(self, mock_core):
        """Create webhook server instance."""
        with patch('roadmap.webhook_server.EnhancedGitHubIntegration'):
            server = GitHubWebhookServer(
                roadmap_core=mock_core,
                secret="test_secret_key"
            )
            return server

    def test_initialization(self, mock_core):
        """Test webhook server initialization."""
        with patch('roadmap.webhook_server.EnhancedGitHubIntegration'):
            server = GitHubWebhookServer(
                roadmap_core=mock_core,
                secret="test_secret"
            )
            
            assert server.core == mock_core
            assert server.secret == "test_secret"
            assert server.app is not None

    def test_create_app(self, webhook_server):
        """Test app creation and route setup."""
        app = webhook_server._create_app()
        
        # Check that app is created
        assert app is not None
        
        # Check that routes are configured (basic check)
        routes = list(app.router.routes())
        assert len(routes) >= 3  # At least 3 routes defined
        
        # Check route methods
        route_methods = [route.method for route in routes]
        assert 'GET' in route_methods
        assert 'POST' in route_methods

    def test_verify_signature_valid(self, webhook_server):
        """Test signature verification with valid signature."""
        payload = b'{"test": "data"}'
        signature = hmac.new(
            webhook_server.secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        assert webhook_server._verify_signature(payload, f"sha256={signature}")

    def test_verify_signature_invalid(self, webhook_server):
        """Test signature verification with invalid signature."""
        payload = b'{"test": "data"}'
        assert not webhook_server._verify_signature(payload, "sha256=invalid")

    def test_verify_signature_malformed(self, webhook_server):
        """Test signature verification with malformed signature."""
        payload = b'{"test": "data"}'
        assert not webhook_server._verify_signature(payload, "invalid_format")
        assert not webhook_server._verify_signature(payload, "")

    @pytest.mark.asyncio
    async def test_handle_issues_event_opened(self, webhook_server):
        """Test handling new issue opened event."""
        event_data = {
            'action': 'opened',
            'issue': {
                'number': 123,
                'title': 'New Issue',
                'body': 'Issue description',
                'labels': [{'name': 'bug'}],
                'assignee': {'login': 'user1'},
                'milestone': {'title': 'v1.0'}
            }
        }
        
        result = await webhook_server._handle_issues_event(event_data)
        
        # Based on the actual implementation, it just marks as handled
        assert result['handled']
        assert 'updated_issues' in result
        assert result['updated_issues'] == []  # Not implemented yet

    @pytest.mark.asyncio
    async def test_handle_issues_event_closed(self, webhook_server):
        """Test handling issue closed event."""
        event_data = {
            'action': 'closed',
            'issue': {'number': 456}
        }
        
        result = await webhook_server._handle_issues_event(event_data)
        
        # Based on the actual implementation, it just marks as handled
        assert result['handled']
        assert 'updated_issues' in result

    @pytest.mark.asyncio
    async def test_handle_event_push(self, webhook_server):
        """Test handling push event."""
        event_data = {'commits': [{'message': 'Test commit'}]}
        
        with patch.object(webhook_server.github_integration, 'handle_push_event') as mock_push:
            mock_push.return_value = ['issue1', 'issue2']
            
            result = await webhook_server._handle_event('push', event_data)
            
            assert result['handled']
            assert result['updated_issues'] == ['issue1', 'issue2']
            mock_push.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_handle_event_unsupported(self, webhook_server):
        """Test handling unsupported event type."""
        result = await webhook_server._handle_event('unsupported_event', {})
        
        assert not result['handled']
        assert result['updated_issues'] == []

    @pytest.mark.asyncio
    async def test_handle_issue_comment_event(self, webhook_server):
        """Test handling issue comment events."""
        event_data = {
            'action': 'created',
            'comment': {'body': 'Test comment'},
            'issue': {'number': 123}
        }
        
        result = await webhook_server._handle_issue_comment_event(event_data)
        
        assert result['handled']
        assert 'updated_issues' in result

    @pytest.mark.asyncio  
    async def test_handle_pull_request_event(self, webhook_server):
        """Test handling pull request events."""
        event_data = {
            'action': 'opened',
            'pull_request': {
                'number': 456,
                'title': 'Test PR'
            }
        }
        
        with patch.object(webhook_server.github_integration, 'handle_pull_request_event') as mock_pr:
            mock_pr.return_value = ['issue3']
            
            result = await webhook_server._handle_event('pull_request', event_data)
            
            assert result['handled']
            assert result['updated_issues'] == ['issue3']
            mock_pr.assert_called_once()


class TestWebhookCLI:
    """Test CLI integration for webhook server."""

    # Using centralized temp_dir fixture from conftest.py

    def test_webhook_cli_module_imports(self, temp_dir):
        """Test webhook CLI module can be imported."""
        try:
            from roadmap import cli
            assert hasattr(cli, 'main')  # Check basic CLI structure
        except ImportError:
            pytest.skip("CLI module structure not available")

    def test_webhook_payload_simulation(self, temp_dir, github_webhook_payload):
        """Test webhook payload processing simulation using centralized test data."""
        # Create test payload using factory
        payload_data = github_webhook_payload('issues', 
                                             action='opened',
                                             issue={'number': 123, 'title': 'Test Issue'})
        
        # Write to file
        payload_file = temp_dir / 'test_payload.json'
        payload_file.write_text(json.dumps(payload_data))
        
        # Test payload creation and validation
        assert payload_file.exists()
        loaded_data = json.loads(payload_file.read_text())
        assert loaded_data['action'] == 'opened'
        assert loaded_data['issue']['number'] == 123
        assert 'repository' in loaded_data  # Factory includes standard fields


class TestWebhookServerIntegration:
    """Integration tests for webhook server."""

    # Using centralized temp_workspace fixture from conftest.py

    def test_webhook_configuration(self, temp_workspace, lightweight_mock_core, patch_github_integration):
        """Test webhook server configuration using performance-optimized fixtures."""
        workspace_dir = temp_workspace
        
        server = GitHubWebhookServer(
            roadmap_core=lightweight_mock_core,
            secret="test_secret"
        )
        
        # Test basic configuration
        assert server.core == lightweight_mock_core
        assert server.secret == "test_secret"
        assert server.app is not None

    def test_webhook_payload_processing(self, temp_workspace, mock_core):
        """Test webhook payload processing logic."""
        workspace_dir = temp_workspace
        
        with patch('roadmap.webhook_server.EnhancedGitHubIntegration'):
            server = GitHubWebhookServer(
                roadmap_core=mock_core,
                secret="webhook_secret"
            )
            
            # Test payload signature generation
            payload_data = {
                'action': 'opened',
                'issue': {
                    'number': 123,
                    'title': 'Test Issue'
                }
            }
            
            payload_bytes = json.dumps(payload_data).encode()
            signature = hmac.new(
                server.secret.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            
            # Verify signature validation works
            assert server._verify_signature(payload_bytes, f'sha256={signature}')
            assert not server._verify_signature(payload_bytes, 'sha256=invalid')