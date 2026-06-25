"""HTTP tools for making API requests (n8n-style HTTP Request node).

This module provides HTTP client functionality similar to n8n's HTTP Request node,
allowing agents to make HTTP requests to external APIs.
"""


from __future__ import annotations

import ipaddress
import json
import logging
import socket
from enum import Enum
from typing import Dict, List, Optional, Set, Union
from urllib.parse import urlparse

import httpx

from unify_llm.agent.tools import Tool, ToolParameter, ToolParameterType, ToolResult

logger = logging.getLogger(__name__)


# SECURITY: Blocked IP ranges to prevent SSRF attacks
BLOCKED_IP_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),      # Private network
    ipaddress.ip_network('172.16.0.0/12'),   # Private network
    ipaddress.ip_network('192.168.0.0/16'),  # Private network
    ipaddress.ip_network('127.0.0.0/8'),     # Loopback
    ipaddress.ip_network('169.254.0.0/16'),  # Link-local (AWS metadata)
    ipaddress.ip_network('0.0.0.0/8'),       # Current network
    ipaddress.ip_network('100.64.0.0/10'),   # Carrier-grade NAT
    ipaddress.ip_network('::1/128'),         # IPv6 loopback
    ipaddress.ip_network('fc00::/7'),        # IPv6 private
    ipaddress.ip_network('fe80::/10'),       # IPv6 link-local
]

# SECURITY: Blocked hostnames
BLOCKED_HOSTNAMES: set[str] = {
    'localhost',
    'metadata.google.internal',
    'metadata.goog',
    '169.254.169.254',  # AWS/GCP metadata endpoint
}


def is_url_safe(url: str) -> tuple[bool, str]:
    """Validate URL to prevent SSRF attacks.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_safe, error_message)
    """
    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme not in ('http', 'https'):
            return False, f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed."

        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: no hostname"

        # Check blocked hostnames
        hostname_lower = hostname.lower()
        if hostname_lower in BLOCKED_HOSTNAMES:
            return False, f"Blocked hostname: {hostname}"

        # Resolve hostname to IP and check against blocked ranges
        try:
            ip_addresses = socket.getaddrinfo(hostname, None)
            for addr_info in ip_addresses:
                ip_str = addr_info[4][0]
                try:
                    ip = ipaddress.ip_address(ip_str)
                    for blocked_range in BLOCKED_IP_RANGES:
                        if ip in blocked_range:
                            return False, f"SSRF blocked: {hostname} resolves to private/internal IP {ip_str}"
                except ValueError:
                    continue
        except socket.gaierror:
            # DNS resolution failed - allow the request to proceed
            # The HTTP client will handle the error appropriately
            pass

        return True, ""

    except Exception as e:
        return False, f"URL validation error: {str(e)}"


class HTTPMethod(str, Enum):
    """HTTP request methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AuthType(str, Enum):
    """Authentication types."""
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"


class ResponseFormat(str, Enum):
    """Response format types."""
    JSON = "json"
    TEXT = "text"
    BINARY = "binary"
    AUTO = "auto"


async def http_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    body: Dict | str | None = None,
    auth_type: str = "none",
    auth_user: str | None = None,
    auth_password: str | None = None,
    auth_token: str | None = None,
    timeout: int = 30,
    follow_redirects: bool = True,
    response_format: str = "auto"
) -> ToolResult:
    """Make an HTTP request (n8n-style HTTP Request node).

    Args:
        url: Request URL
        method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
        headers: Request headers
        query_params: Query parameters
        body: Request body (dict for JSON or string for raw)
        auth_type: Authentication type (none, basic, bearer, api_key)
        auth_user: Username for basic auth
        auth_password: Password for basic auth
        auth_token: Token for bearer/api_key auth
        timeout: Request timeout in seconds
        follow_redirects: Whether to follow redirects
        response_format: Response format (json, text, binary, auto)

    Returns:
        ToolResult with response data

    Example:
        ```python
        # GET request
        result = await http_request(
            url="https://api.example.com/users",
            method="GET",
            query_params={"page": "1", "limit": "10"}
        )

        # POST request with JSON body
        result = await http_request(
            url="https://api.example.com/users",
            method="POST",
            headers={"Content-Type": "application/json"},
            body={"name": "John", "email": "john@example.com"}
        )

        # Authenticated request
        result = await http_request(
            url="https://api.example.com/protected",
            method="GET",
            auth_type="bearer",
            auth_token="your-token-here"
        )
        ```
    """
    # SECURITY: Validate URL to prevent SSRF attacks
    is_safe, error_msg = is_url_safe(url)
    if not is_safe:
        return ToolResult(
            success=False,
            error=f"Security error: {error_msg}",
            metadata={"method": method, "url": url, "blocked": True}
        )

    try:
        # Prepare headers
        request_headers = headers or {}

        # Add authentication
        if auth_type == "basic" and auth_user and auth_password:
            # httpx will handle basic auth
            auth = (auth_user, auth_password)
        elif auth_type == "bearer" and auth_token:
            request_headers["Authorization"] = f"Bearer {auth_token}"
            auth = None
        elif auth_type == "api_key" and auth_token:
            request_headers["Authorization"] = auth_token
            auth = None
        else:
            auth = None

        # Prepare body
        request_body = None
        if body:
            if isinstance(body, dict):
                request_body = json.dumps(body)
                if "Content-Type" not in request_headers:
                    request_headers["Content-Type"] = "application/json"
            else:
                request_body = body

        # Make request
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=follow_redirects
        ) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=request_headers,
                params=query_params,
                content=request_body,
                auth=auth
            )

        # Parse response
        response_data = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "url": str(response.url)
        }

        # Parse body based on format
        if response_format == "json" or (
            response_format == "auto" and
            "application/json" in response.headers.get("content-type", "")
        ):
            try:
                response_data["body"] = response.json()
            except (json.JSONDecodeError, ValueError):
                response_data["body"] = response.text
        elif response_format == "binary":
            response_data["body"] = response.content
            response_data["body_size"] = len(response.content)
        else:
            response_data["body"] = response.text

        # Check if successful
        success = 200 <= response.status_code < 300

        return ToolResult(
            success=success,
            output=response_data,
            metadata={
                "method": method,
                "url": url,
                "status_code": response.status_code
            }
        )

    except httpx.TimeoutException as e:
        return ToolResult(
            success=False,
            error=f"Request timeout: {str(e)}",
            metadata={"method": method, "url": url}
        )
    except httpx.RequestError as e:
        return ToolResult(
            success=False,
            error=f"Request error: {str(e)}",
            metadata={"method": method, "url": url}
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Unexpected error: {str(e)}",
            metadata={"method": method, "url": url}
        )


def create_http_request_tool() -> Tool:
    """Create HTTP Request tool (n8n-style).

    Returns:
        HTTP Request tool

    Example:
        ```python
        from unify_llm.agent import ToolRegistry
        from unify_llm.agent.http_tools import create_http_request_tool

        registry = ToolRegistry()
        http_tool = create_http_request_tool()
        registry.register(http_tool)
        ```
    """
    return Tool(
        name="http_request",
        description="Make HTTP requests to external APIs. Supports GET, POST, PUT, DELETE, PATCH methods with authentication.",
        parameters={
            "url": ToolParameter(
                type=ToolParameterType.STRING,
                description="The URL to send the request to",
                required=True
            ),
            "method": ToolParameter(
                type=ToolParameterType.STRING,
                description="HTTP method (GET, POST, PUT, DELETE, PATCH)",
                required=False,
                enum=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                default="GET"
            ),
            "headers": ToolParameter(
                type=ToolParameterType.OBJECT,
                description="Request headers as key-value pairs",
                required=False
            ),
            "query_params": ToolParameter(
                type=ToolParameterType.OBJECT,
                description="Query parameters as key-value pairs",
                required=False
            ),
            "body": ToolParameter(
                type=ToolParameterType.OBJECT,
                description="Request body (JSON object or string)",
                required=False
            ),
            "auth_type": ToolParameter(
                type=ToolParameterType.STRING,
                description="Authentication type",
                required=False,
                enum=["none", "basic", "bearer", "api_key"],
                default="none"
            ),
            "auth_token": ToolParameter(
                type=ToolParameterType.STRING,
                description="Authentication token (for bearer/api_key auth)",
                required=False
            ),
            "timeout": ToolParameter(
                type=ToolParameterType.INTEGER,
                description="Request timeout in seconds",
                required=False,
                default=30
            ),
            "response_format": ToolParameter(
                type=ToolParameterType.STRING,
                description="Expected response format",
                required=False,
                enum=["json", "text", "binary", "auto"],
                default="auto"
            )
        },
        func=http_request
    )


# Convenience functions for common HTTP methods

async def http_get(url: str, **kwargs) -> ToolResult:
    """Make a GET request.

    Args:
        url: Request URL
        **kwargs: Additional arguments for http_request

    Returns:
        ToolResult with response
    """
    return await http_request(url=url, method="GET", **kwargs)


async def http_post(url: str, body: Dict | None = None, **kwargs) -> ToolResult:
    """Make a POST request.

    Args:
        url: Request URL
        body: Request body
        **kwargs: Additional arguments for http_request

    Returns:
        ToolResult with response
    """
    return await http_request(url=url, method="POST", body=body, **kwargs)


async def http_put(url: str, body: Dict | None = None, **kwargs) -> ToolResult:
    """Make a PUT request.

    Args:
        url: Request URL
        body: Request body
        **kwargs: Additional arguments for http_request

    Returns:
        ToolResult with response
    """
    return await http_request(url=url, method="PUT", body=body, **kwargs)


async def http_delete(url: str, **kwargs) -> ToolResult:
    """Make a DELETE request.

    Args:
        url: Request URL
        **kwargs: Additional arguments for http_request

    Returns:
        ToolResult with response
    """
    return await http_request(url=url, method="DELETE", **kwargs)


def create_all_http_tools() -> list[Tool]:
    """Create all HTTP-related tools.

    Returns:
        List of HTTP tools
    """
    return [
        create_http_request_tool()
    ]
