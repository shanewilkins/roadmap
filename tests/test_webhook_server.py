"""Tests for GitHub webhook server functionality."""

import asyncio
import json
import os
import tempfile
import hashlib
import hmac
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp.web import Application

from roadmap.core import RoadmapCore
from roadmap.webhook_server import GitHubWebhookServer, WebhookCLI


class TestGitHubWebhookServer:
    """Test GitHub webhook server functionality."""

    @pytest.fixture
    def webhook_server(self, mock_core):
        """Create a webhook server for testing."""
        with patch('roadmap.webhook_server.EnhancedGitHubIntegration') as mock_github_integration:
            # Mock the integration instance with proper return values
            mock_integration_instance = Mock()
            mock_integration_instance.is_github_enabled.return_value = True
            mock_integration_instance.handle_push_event.return_value = []
            mock_integration_instance.handle_pull_request_event.return_value = []
            mock_integration_instance.handle_issue_event.return_value = {"handled": True, "updated_issues": []}
            mock_integration_instance.handle_issue_comment_event.return_value = {"handled": True, "updated_issues": []}
            mock_github_integration.return_value = mock_integration_instance
            
            server = GitHubWebhookServer(roadmap_core=mock_core, secret="test_secret")
            # Ensure the github_integration attribute is properly mocked
            server.github_integration = mock_integration_instance
            return server

    def test_initialization(self, mock_core):
        """Test webhook server initialization."""
        with patch('roadmap.webhook_server.EnhancedGitHubIntegration'):
            server = GitHubWebhookServer(roadmap_core=mock_core, secret="secret123")
            
            assert server.core == mock_core
            assert server.secret == "secret123"
            assert server.app is not None
            assert isinstance(server.app, Application)

    def test_create_app(self, webhook_server):
        """Test aiohttp app creation."""
        app = webhook_server._create_app()
        
        assert app is not None
        assert isinstance(app, Application)
        # Check routes exist
        routes = [route.method + ' ' + route.resource.canonical for route in app.router.routes()]
        assert 'GET /' in routes
        assert 'GET /health' in routes
        assert 'POST /webhook/github' in routes

    @pytest.mark.asyncio
    async def test_index_route(self, webhook_server, aiohttp_client):
        """Test index route returns HTML page."""
        client = await aiohttp_client(webhook_server.app)
        
        resp = await client.get('/')
        assert resp.status == 200
        text = await resp.text()
        assert 'Roadmap GitHub Webhook' in text
        assert 'Webhook server is running' in text

    @pytest.mark.asyncio
    async def test_health_check_route(self, webhook_server, aiohttp_client):
        """Test health check endpoint."""
        client = await aiohttp_client(webhook_server.app)
        
        resp = await client.get('/health')
        assert resp.status == 200
        data = await resp.json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'github_integration' in data
        assert 'webhook_secret_configured' in data

    @pytest.mark.asyncio
    async def test_webhook_route_missing_signature(self, webhook_server, aiohttp_client):
        """Test webhook endpoint without signature header."""
        client = await aiohttp_client(webhook_server.app)
        
        resp = await client.post('/webhook/github', 
                                json={'test': 'data'},
                                headers={'X-GitHub-Event': 'push'})
        
        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_webhook_route_invalid_signature(self, webhook_server, aiohttp_client):
        """Test webhook endpoint with invalid signature."""
        client = await aiohttp_client(webhook_server.app)
        
        payload = {'test': 'data'}
        resp = await client.post('/webhook/github',
                               json=payload,
                               headers={
                                   'X-Hub-Signature-256': 'sha256=invalid',
                                   'X-GitHub-Event': 'push'
                               })
        
        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_webhook_route_valid_signature(self, webhook_server, aiohttp_client):
        """Test webhook endpoint with valid signature."""
        client = await aiohttp_client(webhook_server.app)
        
        payload = {'action': 'opened', 'issue': {'number': 1}}
        payload_bytes = json.dumps(payload).encode()
        signature = hmac.new(
            webhook_server.secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        with patch.object(webhook_server, '_handle_event', new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = {'handled': True}
            
            resp = await client.post('/webhook/github',
                                   data=payload_bytes,
                                   headers={
                                       'X-Hub-Signature-256': f'sha256={signature}',
                                       'X-GitHub-Event': 'issues',
                                       'Content-Type': 'application/json'
                                   })
            
            assert resp.status == 200
            data = await resp.json()
            assert data['status'] == 'processed'
            mock_handle.assert_called_once()

    def test_verify_signature_valid(self, webhook_server):
        """Test signature verification with valid signature."""
        payload = b'test payload'
        signature = hmac.new(
            webhook_server.secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        result = webhook_server._verify_signature(payload, f'sha256={signature}')
        assert result is True

    def test_verify_signature_invalid(self, webhook_server):
        """Test signature verification with invalid signature."""
        payload = b'test payload'
        
        result = webhook_server._verify_signature(payload, 'sha256=invalid')
        assert result is False

    def test_verify_signature_malformed(self, webhook_server):
        """Test signature verification with malformed signature."""
        payload = b'test payload'
        
        result = webhook_server._verify_signature(payload, 'invalid_format')
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_event_push(self, webhook_server):
        """Test handling push events."""
        event_data = {
            'ref': 'refs/heads/main',
            'commits': [{'message': 'Test commit'}]
        }
        
        with patch.object(webhook_server.github_integration, 'handle_push_event') as mock_handle:
            mock_handle.return_value = ['issue1', 'issue2']
            
            result = await webhook_server._handle_event('push', event_data)
            
            assert result['handled'] is True
            assert result['updated_issues'] == ['issue1', 'issue2']
            mock_handle.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_handle_event_pull_request(self, webhook_server):
        """Test handling pull request events."""
        event_data = {
            'action': 'opened',
            'pull_request': {
                'number': 1,
                'title': 'Test PR'
            }
        }
        
        with patch.object(webhook_server.github_integration, 'handle_pull_request_event') as mock_handle:
            mock_handle.return_value = ['issue1']
            
            result = await webhook_server._handle_event('pull_request', event_data)
            
            assert result['handled'] is True
            assert result['updated_issues'] == ['issue1']
            mock_handle.assert_called_once_with(event_data['pull_request'], 'opened')

    @pytest.mark.asyncio
    async def test_handle_event_issues(self, webhook_server):
        """Test handling issues events."""
        event_data = {
            'action': 'opened',
            'issue': {
                'number': 1,
                'title': 'Test Issue',
                'body': 'Test content'
            }
        }
        
        with patch.object(webhook_server, '_handle_issues_event', new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = {'handled': True, 'updated_issues': ['issue1']}
            
            result = await webhook_server._handle_event('issues', event_data)
            
            assert result['handled'] is True
            mock_handle.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_handle_event_issue_comment(self, webhook_server):
        """Test handling issue comment events."""
        event_data = {
            'action': 'created',
            'issue': {'number': 1},
            'comment': {'body': 'Test comment'}
        }
        
        with patch.object(webhook_server, '_handle_issue_comment_event', new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = {'handled': True, 'updated_issues': []}
            
            result = await webhook_server._handle_event('issue_comment', event_data)
            
            assert result['handled'] is True
            mock_handle.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_handle_event_unsupported(self, webhook_server):
        """Test handling unsupported event types."""
        with patch.object(webhook_server, 'logger') as mock_logger:
            result = await webhook_server._handle_event('unsupported_event', {})
            
            assert result['handled'] is False
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_handle_issues_event_opened(self, webhook_server):
        """Test handling issue opened event."""
        event_data = {
            'action': 'opened',
            'issue': {
                'number': 1,
                'title': 'Test Issue',
                'body': 'Test content',
                'labels': []
            }
        }
        
        result = await webhook_server._handle_issues_event(event_data)
        assert result['handled'] is True

    @pytest.mark.asyncio
    async def test_handle_issues_event_closed(self, webhook_server):
        """Test handling issue closed event."""
        event_data = {
            'action': 'closed',
            'issue': {
                'number': 1,
                'title': 'Test Issue'
            }
        }
        
        result = await webhook_server._handle_issues_event(event_data)
        assert result['handled'] is True

    @pytest.mark.asyncio
    async def test_handle_issue_comment_event(self, webhook_server):
        """Test handling issue comment event."""
        event_data = {
            'action': 'created',
            'issue': {'number': 1},
            'comment': {
                'body': 'Test comment',
                'user': {'login': 'testuser'}
            }
        }
        
        result = await webhook_server._handle_issue_comment_event(event_data)
        assert result['handled'] is True


class TestWebhookCLI:
    """Test webhook CLI functionality."""

    def test_start_server(self, temp_dir):
        """Test starting webhook server."""
        with patch('roadmap.webhook_server.RoadmapCore') as mock_core_class:
            with patch('roadmap.webhook_server.GitHubWebhookServer') as mock_server_class:
                mock_core = Mock()
                mock_server = Mock()
                mock_core_class.return_value = mock_core
                mock_server_class.return_value = mock_server
                
                WebhookCLI.start_server(
                    host="localhost",
                    port=8080,
                    secret="test_secret"
                )
                
                mock_server_class.assert_called_once_with(mock_core, "test_secret")
                mock_server.run.assert_called_once_with("localhost", 8080)

    def test_test_webhook_with_payload_file(self, temp_dir):
        """Test webhook testing with payload file."""
        # Create test payload file
        payload_file = temp_dir / "test_payload.json"
        test_payload = {
            "action": "opened",
            "issue": {
                "number": 1,
                "title": "Test Issue"
            }
        }
        payload_file.write_text(json.dumps(test_payload))
        
        with patch('roadmap.webhook_server.RoadmapCore') as mock_core_class:
            with patch('roadmap.webhook_server.GitHubWebhookServer') as mock_server_class:
                mock_core = Mock()
                mock_server = Mock()
                mock_core_class.return_value = mock_core
                mock_server_class.return_value = mock_server
                
                # Mock the async _handle_event method
                async def mock_handle_event(event_type, data):
                    return {"handled": True, "result": "test"}
                
                mock_server._handle_event = mock_handle_event
                
                WebhookCLI.test_webhook(str(payload_file), "issues")
                
                mock_server_class.assert_called_once_with(mock_core)


# The aiohttp_client fixture is already provided by pytest-aiohttp


class TestWebhookServerIntegration:
    """Integration tests for webhook server."""

    @pytest.mark.asyncio
    async def test_full_webhook_lifecycle(self, temp_workspace_with_core, aiohttp_client):
        """Test complete webhook server lifecycle."""
        workspace_dir, core = temp_workspace_with_core
        
        with patch('roadmap.webhook_server.EnhancedGitHubIntegration') as mock_github_integration:
            # Mock the integration instance with proper return values
            mock_integration_instance = Mock()
            mock_integration_instance.is_github_enabled.return_value = True
            mock_integration_instance.handle_push_event.return_value = []
            mock_integration_instance.handle_pull_request_event.return_value = []
            mock_integration_instance.handle_issue_event.return_value = {"handled": True, "updated_issues": []}
            mock_integration_instance.handle_issue_comment_event.return_value = {"handled": True, "updated_issues": []}
            mock_github_integration.return_value = mock_integration_instance
            
            server = GitHubWebhookServer(
                roadmap_core=core,
                secret="test_secret"
            )
            # Ensure the github_integration attribute is properly mocked
            server.github_integration = mock_integration_instance
            
            # Test that server can be created and configured
            assert server.app is not None
            assert server.core == core
            
            # Test routes are accessible
            client = await aiohttp_client(server.app)
            
            # Test index
            resp = await client.get('/')
            assert resp.status == 200
            text = await resp.text()
            assert 'Webhook server is running' in text
            
            # Test health check
            resp = await client.get('/health')
            assert resp.status == 200
            data = await resp.json()
            assert data['status'] == 'healthy'

    @pytest.mark.asyncio
    async def test_webhook_event_processing(self, temp_workspace_with_core, aiohttp_client):
        """Test processing actual webhook events."""
        workspace_dir, core = temp_workspace_with_core
        
        with patch('roadmap.webhook_server.EnhancedGitHubIntegration'):
            server = GitHubWebhookServer(
                roadmap_core=core,
                secret="webhook_secret"
            )
            
            # Create realistic GitHub webhook payload
            payload_data = {
                'action': 'opened',
                'issue': {
                    'number': 123,
                    'title': 'New Feature Request',
                    'body': 'Please add this feature',
                    'labels': [{'name': 'enhancement'}],
                    'assignee': None,
                    'milestone': None
                },
                'repository': {
                    'name': 'test-repo',
                    'full_name': 'test/test-repo'
                }
            }
            
            payload_bytes = json.dumps(payload_data).encode()
            signature = hmac.new(
                server.secret.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            
            client = await aiohttp_client(server.app)
            
            with patch.object(server, '_handle_event', new_callable=AsyncMock) as mock_handle:
                mock_handle.return_value = {'handled': True, 'updated_issues': []}
                
                resp = await client.post('/webhook/github',
                                       data=payload_bytes,
                                       headers={
                                           'X-Hub-Signature-256': f'sha256={signature}',
                                           'X-GitHub-Event': 'issues',
                                           'Content-Type': 'application/json'
                                       })
                
                assert resp.status == 200
                data = await resp.json()
                assert data['status'] == 'processed'
                mock_handle.assert_called_once()