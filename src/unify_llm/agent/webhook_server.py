"""Webhook server for receiving HTTP triggers (n8n-style).

This module provides a lightweight webhook server that can receive HTTP requests
and trigger workflows, similar to n8n's webhook functionality.
"""


from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from unify_llm.agent.triggers import WebhookTrigger

logger = logging.getLogger(__name__)


# SECURITY: API Key authentication configuration
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


class WebhookAuthConfig:
    """Configuration for webhook authentication.

    Security Note:
        Always configure authentication in production environments.
        Set API keys via environment variable or configure_auth() method.
    """

    def __init__(self):
        self.enabled = True  # SECURITY: Authentication enabled by default
        self.api_keys: set[str] = set()
        self.webhook_secrets: dict[str, str] = {}  # webhook_id -> secret

        # Load API key from environment if available
        env_key = os.environ.get('UNIFY_WEBHOOK_API_KEY')
        if env_key:
            self.api_keys.add(env_key)

    def add_api_key(self, key: str) -> None:
        """Add an API key for authentication."""
        self.api_keys.add(key)

    def remove_api_key(self, key: str) -> None:
        """Remove an API key."""
        self.api_keys.discard(key)

    def generate_api_key(self) -> str:
        """Generate a new secure API key."""
        key = secrets.token_urlsafe(32)
        self.api_keys.add(key)
        return key

    def set_webhook_secret(self, webhook_id: str, secret: str) -> None:
        """Set secret for webhook signature validation."""
        self.webhook_secrets[webhook_id] = secret

    def validate_api_key(self, key: str | None) -> bool:
        """Validate an API key."""
        if not self.enabled:
            return True
        if not self.api_keys:
            # SECURITY: If no keys configured and auth enabled, deny by default
            logger.warning("Webhook auth enabled but no API keys configured - denying access")
            return False
        return key in self.api_keys

    def validate_signature(self, webhook_id: str, payload: bytes, signature: str) -> bool:
        """Validate webhook signature using HMAC-SHA256."""
        secret = self.webhook_secrets.get(webhook_id)
        if not secret:
            return True  # No signature required for this webhook
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)


# Global auth config instance
_auth_config = WebhookAuthConfig()


class WebhookServer:
    """Webhook server for triggering workflows via HTTP (n8n-style).

    Example:
        ```python
        from unify_llm.agent.webhook_server import WebhookServer
        from unify_llm.agent.triggers import WebhookTrigger, TriggerConfig, TriggerType

        # Create server
        server = WebhookServer(host="0.0.0.0", port=5678)

        # Register webhook
        def handle_webhook(event):
            print(f"Webhook triggered: {event.data}")

        config = TriggerConfig(
            id="webhook_1",
            name="My Webhook",
            type=TriggerType.WEBHOOK,
            workflow_id="workflow_1",
            config={"path": "/webhook/test", "method": "POST"}
        )

        trigger = WebhookTrigger(config, handle_webhook)
        server.register_webhook(trigger)

        # Start server
        await server.start()
        ```
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 5678, auth_config: WebhookAuthConfig | None = None):
        """Initialize webhook server.

        Args:
            host: Server host
            port: Server port
            auth_config: Authentication configuration. If None, uses global config.

        Security Note:
            Authentication is enabled by default. Configure API keys via:
            - Environment variable: UNIFY_WEBHOOK_API_KEY
            - server.auth_config.add_api_key("your-key")
            - server.auth_config.generate_api_key()
        """
        self.host = host
        self.port = port
        self.webhooks: dict[str, WebhookTrigger] = {}
        self._server = None
        self.auth_config = auth_config or _auth_config

        # Create FastAPI app with lifespan
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Manage application lifespan."""
            logger.info("Starting webhook server...")
            yield
            logger.info("Shutting down webhook server...")

        self.app = FastAPI(
            title="UnifyLLM Webhook Server",
            lifespan=lifespan
        )

        # Add middleware
        self._setup_middleware()
        self._setup_routes()

    def _setup_middleware(self):
        """Setup FastAPI middleware for CORS, compression, and request tracking."""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=os.environ.get('UNIFY_CORS_ORIGINS', '*').split(','),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # GZip compression for responses > 1KB
        self.app.add_middleware(GZipMiddleware, minimum_size=1000)

        # Request timing and ID middleware
        @self.app.middleware("http")
        async def add_request_tracking(request: Request, call_next):
            """Add request ID and timing headers."""
            request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
            start_time = time.time()

            response = await call_next(request)

            process_time = time.time() - start_time
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}"

            return response

    def _setup_routes(self):
        """Setup FastAPI routes with authentication."""

        async def verify_api_key(api_key: str | None = Depends(API_KEY_HEADER)) -> str:
            """Dependency to verify API key."""
            if not self.auth_config.validate_api_key(api_key):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or missing API key",
                    headers={"WWW-Authenticate": "ApiKey"}
                )
            return api_key or ""

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint (no auth required)."""
            return {"status": "healthy", "webhooks": len(self.webhooks)}

        @self.app.get("/webhooks")
        async def list_webhooks(api_key: str = Depends(verify_api_key)):
            """List all registered webhooks (requires authentication)."""
            return {
                "webhooks": [
                    {
                        "id": webhook.config.id,
                        "name": webhook.config.name,
                        "path": webhook.path,
                        "method": webhook.method,
                        "enabled": webhook.config.enabled
                    }
                    for webhook in self.webhooks.values()
                ]
            }

        @self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        async def handle_webhook(
            path: str,
            request: Request,
            api_key: str = Depends(verify_api_key),
            x_webhook_signature: str | None = Header(None)
        ):
            """Handle incoming webhook requests with authentication."""
            full_path = f"/{path}"

            # Find matching webhook
            webhook = None
            for wh in self.webhooks.values():
                if wh.path == full_path and wh.method == request.method:
                    webhook = wh
                    break

            if not webhook:
                raise HTTPException(
                    status_code=404,
                    detail=f"No webhook found for {request.method} {full_path}"
                )

            if not webhook.config.enabled:
                raise HTTPException(
                    status_code=403,
                    detail="Webhook is disabled"
                )

            # Parse request data
            try:
                raw_body = await request.body()
                body = await request.json() if request.headers.get("content-type") == "application/json" else raw_body
            except Exception:
                raw_body = b""
                body = None

            # SECURITY: Validate webhook signature if configured
            if x_webhook_signature:
                if not self.auth_config.validate_signature(webhook.config.id, raw_body, x_webhook_signature):
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid webhook signature"
                    )

            webhook_data = {
                "method": request.method,
                "path": full_path,
                "headers": dict(request.headers),
                "query_params": dict(request.query_params),
                "body": body,
                "client_host": request.client.host if request.client else None
            }

            # Trigger webhook
            response_data = webhook.handle_request(webhook_data)

            return JSONResponse(content=response_data)

    def register_webhook(self, webhook: WebhookTrigger) -> None:
        """Register a webhook trigger.

        Args:
            webhook: WebhookTrigger instance
        """
        self.webhooks[webhook.config.id] = webhook
        logger.info(f"Registered webhook: {webhook.method} {webhook.path}")

    def unregister_webhook(self, webhook_id: str) -> None:
        """Unregister a webhook.

        Args:
            webhook_id: Webhook ID
        """
        if webhook_id in self.webhooks:
            del self.webhooks[webhook_id]
            logger.info(f"Unregistered webhook: {webhook_id}")

    async def start(self) -> None:
        """Start the webhook server."""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        self._server = uvicorn.Server(config)
        logger.info(f"Starting webhook server on {self.host}:{self.port}")
        await self._server.serve()

    async def stop(self) -> None:
        """Stop the webhook server."""
        if self._server:
            self._server.should_exit = True
            logger.info("Stopping webhook server")

    def run_sync(self) -> None:
        """Run server synchronously (blocking).

        Example:
            ```python
            server = WebhookServer()
            server.register_webhook(webhook)
            server.run_sync()  # Blocks until stopped
            ```
        """
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port
        )


class WebhookClient:
    """Client for testing webhooks.

    Example:
        ```python
        from unify_llm.agent.webhook_server import WebhookClient

        client = WebhookClient(base_url="http://localhost:5678")

        # Send webhook
        response = await client.send_webhook(
            path="/webhook/test",
            method="POST",
            data={"message": "Hello!"}
        )
        ```
    """

    def __init__(self, base_url: str = "http://localhost:5678"):
        """Initialize webhook client.

        Args:
            base_url: Base URL of webhook server
        """
        self.base_url = base_url.rstrip("/")

    async def send_webhook(
        self,
        path: str,
        method: str = "POST",
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Send a webhook request.

        Args:
            path: Webhook path
            method: HTTP method
            data: Request data
            headers: Request headers

        Returns:
            Response data
        """
        import httpx

        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                json=data,
                headers=headers
            )

            return {
                "status_code": response.status_code,
                "data": response.json() if response.headers.get("content-type") == "application/json" else response.text
            }

    async def list_webhooks(self) -> dict[str, Any]:
        """List all registered webhooks.

        Returns:
            Webhook list
        """
        import httpx

        url = f"{self.base_url}/webhooks"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.json()

    async def health_check(self) -> dict[str, Any]:
        """Check server health.

        Returns:
            Health status
        """
        import httpx

        url = f"{self.base_url}/health"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.json()
