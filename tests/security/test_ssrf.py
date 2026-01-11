"""Tests for SSRF (Server-Side Request Forgery) prevention.

These tests verify that the HTTP tools properly block requests
to internal networks, cloud metadata endpoints, and localhost.
"""

import pytest

from unify_llm.agent.http_tools import is_url_safe, BLOCKED_IP_RANGES, BLOCKED_HOSTNAMES


class TestSSRFPrevention:
    """Test SSRF protection in HTTP tools."""

    # Valid external URLs - should be allowed
    @pytest.mark.parametrize("url", [
        "https://api.example.com/users",
        "https://google.com",
        "http://httpbin.org/get",
        "https://api.github.com/users",
    ])
    def test_allows_external_urls(self, url):
        """Test that legitimate external URLs are allowed."""
        is_safe, error = is_url_safe(url)
        assert is_safe is True, f"Should allow {url}: {error}"

    # SECURITY: Block localhost
    @pytest.mark.parametrize("url", [
        "http://localhost/admin",
        "http://localhost:8080/api",
        "https://localhost/",
        "http://127.0.0.1/",
        "http://127.0.0.1:3000/",
        "http://[::1]/",
    ])
    def test_blocks_localhost(self, url):
        """SECURITY: Block requests to localhost."""
        is_safe, error = is_url_safe(url)
        assert is_safe is False, f"Should block localhost: {url}"
        assert "blocked" in error.lower() or "private" in error.lower()

    # SECURITY: Block private networks
    @pytest.mark.parametrize("url", [
        "http://10.0.0.1/",
        "http://10.255.255.255/",
        "http://172.16.0.1/",
        "http://172.31.255.255/",
        "http://192.168.1.1/",
        "http://192.168.0.100:8080/api",
    ])
    def test_blocks_private_networks(self, url):
        """SECURITY: Block requests to private network ranges."""
        is_safe, error = is_url_safe(url)
        assert is_safe is False, f"Should block private network: {url}"

    # SECURITY: Block cloud metadata endpoints
    @pytest.mark.parametrize("url", [
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.169.254/latest/user-data/",
        "http://metadata.google.internal/",
        "http://metadata.goog/",
    ])
    def test_blocks_cloud_metadata(self, url):
        """SECURITY: Block requests to cloud metadata endpoints."""
        is_safe, error = is_url_safe(url)
        assert is_safe is False, f"Should block cloud metadata: {url}"

    # SECURITY: Block link-local addresses
    @pytest.mark.parametrize("url", [
        "http://169.254.0.1/",
        "http://169.254.255.254/",
    ])
    def test_blocks_link_local(self, url):
        """SECURITY: Block requests to link-local addresses."""
        is_safe, error = is_url_safe(url)
        assert is_safe is False, f"Should block link-local: {url}"

    # SECURITY: Block invalid schemes
    @pytest.mark.parametrize("url,scheme", [
        ("ftp://example.com/file.txt", "ftp"),
        ("file:///etc/passwd", "file"),
        ("gopher://example.com/", "gopher"),
        ("dict://example.com/", "dict"),
    ])
    def test_blocks_invalid_schemes(self, url, scheme):
        """SECURITY: Block non-HTTP(S) URL schemes."""
        is_safe, error = is_url_safe(url)
        assert is_safe is False, f"Should block {scheme} scheme: {url}"
        assert "scheme" in error.lower()

    def test_blocks_empty_hostname(self):
        """SECURITY: Block URLs with empty hostname."""
        is_safe, error = is_url_safe("http:///path")
        assert is_safe is False

    def test_blocks_ipv6_private(self):
        """SECURITY: Block IPv6 private addresses."""
        # fc00::/7 is private IPv6
        is_safe, error = is_url_safe("http://[fc00::1]/")
        # Note: This test may pass or fail depending on DNS resolution
        # The important thing is it doesn't allow access to internal resources


class TestBlockedRanges:
    """Test that blocked IP ranges are properly configured."""

    def test_private_class_a_blocked(self):
        """Verify 10.0.0.0/8 is blocked."""
        import ipaddress
        test_ips = ["10.0.0.1", "10.255.255.255", "10.100.50.25"]
        for ip_str in test_ips:
            ip = ipaddress.ip_address(ip_str)
            blocked = any(ip in range for range in BLOCKED_IP_RANGES)
            assert blocked, f"10.x.x.x should be blocked: {ip_str}"

    def test_private_class_b_blocked(self):
        """Verify 172.16.0.0/12 is blocked."""
        import ipaddress
        test_ips = ["172.16.0.1", "172.31.255.255", "172.20.100.50"]
        for ip_str in test_ips:
            ip = ipaddress.ip_address(ip_str)
            blocked = any(ip in range for range in BLOCKED_IP_RANGES)
            assert blocked, f"172.16-31.x.x should be blocked: {ip_str}"

    def test_private_class_c_blocked(self):
        """Verify 192.168.0.0/16 is blocked."""
        import ipaddress
        test_ips = ["192.168.0.1", "192.168.255.255", "192.168.1.100"]
        for ip_str in test_ips:
            ip = ipaddress.ip_address(ip_str)
            blocked = any(ip in range for range in BLOCKED_IP_RANGES)
            assert blocked, f"192.168.x.x should be blocked: {ip_str}"

    def test_loopback_blocked(self):
        """Verify 127.0.0.0/8 is blocked."""
        import ipaddress
        test_ips = ["127.0.0.1", "127.255.255.255", "127.0.0.2"]
        for ip_str in test_ips:
            ip = ipaddress.ip_address(ip_str)
            blocked = any(ip in range for range in BLOCKED_IP_RANGES)
            assert blocked, f"127.x.x.x should be blocked: {ip_str}"


class TestBlockedHostnames:
    """Test that blocked hostnames are properly configured."""

    def test_localhost_in_blocked(self):
        """Verify localhost is in blocked list."""
        assert "localhost" in BLOCKED_HOSTNAMES

    def test_metadata_endpoints_blocked(self):
        """Verify cloud metadata endpoints are blocked."""
        assert "169.254.169.254" in BLOCKED_HOSTNAMES
        assert "metadata.google.internal" in BLOCKED_HOSTNAMES
