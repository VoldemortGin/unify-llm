"""Webhook server for receiving HTTP triggers (n8n-style).

This module provides a lightweight webhook server that can receive HTTP requests
and trigger workflows, similar to n8n's webhook functionality.
"""

from typing import Any, Callable, Dict, Optional
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import logging
from datetime import datetime
import asyncio

from unify_llm.agent.triggers import WebhookTrigger, TriggerEvent

logger = logging.getLogger(__name__)


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

    def __init__(self, host: str = "0.0.0.0", port: int = 5678):
        """Initialize webhook server.

        Args:
            host: Server host
            port: Server port
        """
        self.host = host
        self.port = port
        self.app = FastAPI(title="UnifyLLM Webhook Server")
        self.webhooks: Dict[str, WebhookTrigger] = {}
        self._server = None
        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes."""

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "webhooks": len(self.webhooks)}

        @self.app.get("/webhooks")
        async def list_webhooks():
            """List all registered webhooks."""
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
        async def handle_webhook(path: str, request: Request):
            """Handle incoming webhook requests."""
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
                body = await request.json() if request.headers.get("content-type") == "application/json" else await request.body()
            except:
                body = None

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
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
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

    async def list_webhooks(self) -> Dict[str, Any]:
        """List all registered webhooks.

        Returns:
            Webhook list
        """
        import httpx

        url = f"{self.base_url}/webhooks"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.json()

    async def health_check(self) -> Dict[str, Any]:
        """Check server health.

        Returns:
            Health status
        """
        import httpx

        url = f"{self.base_url}/health"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.json()
