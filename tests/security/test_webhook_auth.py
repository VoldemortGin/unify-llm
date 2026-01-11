"""Tests for webhook authentication.

These tests verify that the webhook server properly authenticates
requests and prevents unauthorized access.
"""

import hashlib
import hmac

import pytest
from fastapi.testclient import TestClient

from unify_llm.agent.webhook_server import WebhookServer, WebhookAuthConfig


class TestWebhookAuthConfig:
    """Test WebhookAuthConfig class."""

    def test_auth_enabled_by_default(self):
        """SECURITY: Authentication is enabled by default."""
        config = WebhookAuthConfig()
        assert config.enabled is True

    def test_no_keys_denies_access(self):
        """SECURITY: No configured keys means denied access."""
        config = WebhookAuthConfig()
        config.api_keys.clear()  # Ensure no keys
        assert config.validate_api_key("any-key") is False
        assert config.validate_api_key(None) is False

    def test_add_api_key(self):
        """Test adding API keys."""
        config = WebhookAuthConfig()
        config.add_api_key("test-key-123")
        assert config.validate_api_key("test-key-123") is True
        assert config.validate_api_key("wrong-key") is False

    def test_remove_api_key(self):
        """Test removing API keys."""
        config = WebhookAuthConfig()
        config.add_api_key("test-key")
        config.remove_api_key("test-key")
        assert config.validate_api_key("test-key") is False

    def test_generate_api_key(self):
        """Test API key generation."""
        config = WebhookAuthConfig()
        key = config.generate_api_key()
        assert len(key) > 20  # Should be sufficiently long
        assert config.validate_api_key(key) is True

    def test_signature_validation(self):
        """Test webhook signature validation."""
        config = WebhookAuthConfig()
        webhook_id = "test-webhook"
        secret = "my-secret-key"
        config.set_webhook_secret(webhook_id, secret)

        payload = b'{"event": "test"}'
        expected_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        assert config.validate_signature(webhook_id, payload, f"sha256={expected_sig}") is True
        assert config.validate_signature(webhook_id, payload, "sha256=wrong") is False

    def test_signature_not_required_if_not_configured(self):
        """Test that signature is not required if not configured."""
        config = WebhookAuthConfig()
        assert config.validate_signature("any-webhook", b"payload", "any-sig") is True


class TestWebhookServerAuth:
    """Test webhook server authentication."""

    @pytest.fixture
    def auth_config(self):
        """Create auth config with a known API key."""
        config = WebhookAuthConfig()
        config.add_api_key("test-api-key")
        return config

    @pytest.fixture
    def server(self, auth_config):
        """Create webhook server with authentication."""
        return WebhookServer(host="127.0.0.1", port=5678, auth_config=auth_config)

    @pytest.fixture
    def client(self, server):
        """Create test client."""
        return TestClient(server.app)

    def test_health_no_auth_required(self, client):
        """Test health endpoint works without auth."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_webhooks_list_requires_auth(self, client):
        """SECURITY: /webhooks endpoint requires authentication."""
        response = client.get("/webhooks")
        assert response.status_code == 401

    def test_webhooks_list_with_valid_key(self, client):
        """Test /webhooks with valid API key."""
        response = client.get(
            "/webhooks",
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200

    def test_webhooks_list_with_invalid_key(self, client):
        """SECURITY: Invalid API key is rejected."""
        response = client.get(
            "/webhooks",
            headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401

    def test_webhook_endpoint_requires_auth(self, client):
        """SECURITY: Webhook endpoints require authentication."""
        response = client.post("/webhook/test")
        assert response.status_code == 401

    def test_webhook_with_valid_key(self, client):
        """Test webhook endpoint with valid API key returns 404 (no webhook registered)."""
        response = client.post(
            "/webhook/test",
            headers={"X-API-Key": "test-api-key"}
        )
        # Should be 404 because no webhook is registered, not 401
        assert response.status_code == 404


class TestWebhookServerAuthDisabled:
    """Test webhook server with authentication disabled."""

    @pytest.fixture
    def server_no_auth(self):
        """Create webhook server with authentication disabled."""
        config = WebhookAuthConfig()
        config.enabled = False
        return WebhookServer(host="127.0.0.1", port=5678, auth_config=config)

    @pytest.fixture
    def client_no_auth(self, server_no_auth):
        """Create test client for no-auth server."""
        return TestClient(server_no_auth.app)

    def test_webhooks_accessible_when_auth_disabled(self, client_no_auth):
        """Test endpoints work when auth is disabled."""
        response = client_no_auth.get("/webhooks")
        assert response.status_code == 200
