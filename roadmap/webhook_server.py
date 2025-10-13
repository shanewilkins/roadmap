"""Webhook server for real-time GitHub integration."""

import asyncio
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from aiohttp import web
from aiohttp.web import Application, Request, Response

from .core import RoadmapCore
from .enhanced_github_integration import EnhancedGitHubIntegration


class GitHubWebhookServer:
    """Webhook server for handling GitHub events."""
    
    def __init__(self, roadmap_core: RoadmapCore, secret: Optional[str] = None):
        """Initialize webhook server.
        
        Args:
            roadmap_core: RoadmapCore instance
            secret: Webhook secret for signature verification
        """
        self.core = roadmap_core
        self.github_integration = EnhancedGitHubIntegration(roadmap_core)
        self.secret = secret or os.getenv("GITHUB_WEBHOOK_SECRET")
        self.app = self._create_app()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _create_app(self) -> Application:
        """Create aiohttp application with routes."""
        app = web.Application()
        
        # Add routes
        app.router.add_post("/webhook/github", self.handle_github_webhook)
        app.router.add_get("/health", self.health_check)
        app.router.add_get("/", self.index)
        
        # Add middleware
        app.middlewares.append(self.logging_middleware)
        
        return app
    
    @web.middleware
    async def logging_middleware(self, request: Request, handler) -> Response:
        """Logging middleware for requests."""
        start_time = datetime.now()
        
        try:
            response = await handler(request)
            duration = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(
                f"{request.method} {request.path} "
                f"{response.status} {duration:.3f}s"
            )
            
            return response
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(
                f"{request.method} {request.path} "
                f"ERROR {duration:.3f}s: {e}"
            )
            raise
    
    async def index(self, request: Request) -> Response:
        """Index page showing webhook status."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Roadmap GitHub Webhook</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
                .success { background-color: #d4edda; color: #155724; }
                .info { background-color: #d1ecf1; color: #0c5460; }
            </style>
        </head>
        <body>
            <h1>🚀 Roadmap GitHub Webhook</h1>
            <div class="status success">
                ✅ Webhook server is running
            </div>
            <div class="status info">
                📋 Supported events: push, pull_request, issues, issue_comment
            </div>
            <h2>Endpoints</h2>
            <ul>
                <li><code>POST /webhook/github</code> - GitHub webhook handler</li>
                <li><code>GET /health</code> - Health check</li>
            </ul>
            <h2>Setup</h2>
            <p>Configure your GitHub repository webhook to point to:</p>
            <code>https://your-domain.com/webhook/github</code>
        </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")
    
    async def health_check(self, request: Request) -> Response:
        """Health check endpoint."""
        status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "github_integration": self.github_integration.is_github_enabled(),
            "webhook_secret_configured": bool(self.secret)
        }
        
        return web.json_response(status)
    
    async def handle_github_webhook(self, request: Request) -> Response:
        """Handle GitHub webhook events."""
        try:
            # Get headers
            event_type = request.headers.get("X-GitHub-Event")
            signature = request.headers.get("X-Hub-Signature-256")
            delivery_id = request.headers.get("X-GitHub-Delivery")
            
            # Read payload
            payload = await request.read()
            
            # Verify signature if secret is configured
            if self.secret:
                if not signature:
                    self.logger.warning(f"Missing signature for delivery {delivery_id}")
                    return web.Response(status=401, text="Missing signature")
                    
                if not self._verify_signature(payload, signature):
                    self.logger.warning(f"Invalid signature for delivery {delivery_id}")
                    return web.Response(status=401, text="Invalid signature")
            
            # Parse JSON payload
            try:
                data = json.loads(payload.decode())
            except json.JSONDecodeError:
                self.logger.error(f"Invalid JSON payload for delivery {delivery_id}")
                return web.Response(status=400, text="Invalid JSON")
            
            # Log event
            self.logger.info(
                f"Received {event_type} event (delivery: {delivery_id})"
            )
            
            # Handle event
            result = await self._handle_event(event_type, data)
            
            # Return response
            response_data = {
                "status": "processed",
                "event_type": event_type,
                "delivery_id": delivery_id,
                "result": result
            }
            
            return web.json_response(response_data)
            
        except Exception as e:
            self.logger.error(f"Error handling webhook: {e}")
            return web.Response(status=500, text=f"Error: {e}")
    
    def _verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature."""
        if not signature.startswith("sha256="):
            return False
            
        expected_signature = signature[7:]  # Remove 'sha256=' prefix
        
        computed_signature = hmac.new(
            self.secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, computed_signature)
    
    async def _handle_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle specific GitHub event types."""
        result = {"handled": False, "updated_issues": []}
        
        try:
            if event_type == "push":
                result["updated_issues"] = self.github_integration.handle_push_event(data)
                result["handled"] = True
                
            elif event_type == "pull_request":
                action = data.get("action", "")
                pr_data = data.get("pull_request", {})
                result["updated_issues"] = self.github_integration.handle_pull_request_event(pr_data, action)
                result["handled"] = True
                
            elif event_type == "issues":
                result = await self._handle_issues_event(data)
                
            elif event_type == "issue_comment":
                result = await self._handle_issue_comment_event(data)
                
            else:
                self.logger.info(f"Unhandled event type: {event_type}")
                
        except Exception as e:
            self.logger.error(f"Error handling {event_type} event: {e}")
            result["error"] = str(e)
            
        return result
    
    async def _handle_issues_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GitHub issues events."""
        result = {"handled": False, "updated_issues": []}
        
        action = data.get("action", "")
        issue = data.get("issue", {})
        
        # For now, we'll focus on sync from roadmap to GitHub
        # Future enhancement: sync GitHub issues back to roadmap
        
        if action in ["opened", "edited", "closed", "reopened"]:
            self.logger.info(f"GitHub issue {action}: #{issue.get('number')}")
            result["handled"] = True
            # TODO: Implement GitHub -> roadmap sync
            
        return result
    
    async def _handle_issue_comment_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GitHub issue comment events."""
        result = {"handled": False, "updated_issues": []}
        
        action = data.get("action", "")
        comment = data.get("comment", {})
        issue = data.get("issue", {})
        
        if action == "created":
            self.logger.info(
                f"Comment added to issue #{issue.get('number')}: "
                f"{comment.get('body', '')[:50]}..."
            )
            result["handled"] = True
            # TODO: Implement comment sync to roadmap issues
            
        return result
    
    def run(self, host: str = "0.0.0.0", port: int = 8080):
        """Run the webhook server."""
        self.logger.info(f"Starting webhook server on {host}:{port}")
        web.run_app(self.app, host=host, port=port)


class WebhookCLI:
    """CLI interface for webhook server management."""
    
    @staticmethod
    def start_server(host: str = "0.0.0.0", port: int = 8080, secret: Optional[str] = None):
        """Start the webhook server."""
        core = RoadmapCore()
        server = GitHubWebhookServer(core, secret)
        server.run(host, port)
    
    @staticmethod
    def test_webhook(payload_file: str, event_type: str = "push"):
        """Test webhook handling with a local payload file."""
        import asyncio
        
        # Load test payload
        with open(payload_file, 'r') as f:
            payload = json.load(f)
        
        # Create server instance
        core = RoadmapCore()
        server = GitHubWebhookServer(core)
        
        # Handle event
        async def test():
            result = await server._handle_event(event_type, payload)
            print(f"Test result: {json.dumps(result, indent=2)}")
        
        asyncio.run(test())


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode
        if len(sys.argv) > 2:
            WebhookCLI.test_webhook(sys.argv[2])
        else:
            print("Usage: python webhook_server.py test <payload_file>")
    else:
        # Start server
        WebhookCLI.start_server()