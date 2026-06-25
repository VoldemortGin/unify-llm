"""Transport layer implementations for MCP."""


from __future__ import annotations

import asyncio
import json
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import aiohttp


class MCPTransport(ABC):
    """Abstract base class for MCP transport implementations."""

    @abstractmethod
    async def send(self, message: dict[str, Any]) -> None:
        """Send a message through the transport."""
        pass

    @abstractmethod
    async def receive(self) -> dict[str, Any]:
        """Receive a message from the transport."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the transport connection."""
        pass


class StdioTransport(MCPTransport):
    """Standard input/output transport for MCP.

    Used for local process communication via stdin/stdout.
    """

    def __init__(self):
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        """Connect to stdio streams."""
        loop = asyncio.get_event_loop()
        self._reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(self._reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        transport, protocol = await loop.connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        self._writer = asyncio.StreamWriter(transport, protocol, None, loop)

    async def send(self, message: dict[str, Any]) -> None:
        """Send a JSON-RPC message to stdout."""
        if not self._writer:
            raise RuntimeError("Transport not connected")

        data = json.dumps(message) + "\n"
        self._writer.write(data.encode('utf-8'))
        await self._writer.drain()

    async def receive(self) -> dict[str, Any]:
        """Receive a JSON-RPC message from stdin."""
        if not self._reader:
            raise RuntimeError("Transport not connected")

        line = await self._reader.readline()
        if not line:
            raise EOFError("Connection closed")

        return json.loads(line.decode('utf-8'))

    async def close(self) -> None:
        """Close the transport."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()


class SSETransport(MCPTransport):
    """Server-Sent Events transport for MCP.

    Used for server-to-client streaming over HTTP.
    """

    def __init__(self, url: str):
        self.url = url
        self._session: aiohttp.ClientSession | None = None
        self._response: aiohttp.ClientResponse | None = None
        self._queue: asyncio.Queue = asyncio.Queue()

    async def connect(self) -> None:
        """Connect to the SSE endpoint."""
        self._session = aiohttp.ClientSession()
        self._response = await self._session.get(self.url)

    async def send(self, message: dict[str, Any]) -> None:
        """Send a message (via POST to companion endpoint)."""
        if not self._session:
            raise RuntimeError("Transport not connected")

        # SSE is unidirectional; send via POST
        send_url = self.url.replace('/events', '/messages')
        async with self._session.post(send_url, json=message) as resp:
            resp.raise_for_status()

    async def receive(self) -> dict[str, Any]:
        """Receive a message from the SSE stream."""
        if not self._response:
            raise RuntimeError("Transport not connected")

        async for line in self._response.content:
            line = line.decode('utf-8').strip()
            if line.startswith('data: '):
                data = line[6:]  # Remove 'data: ' prefix
                return json.loads(data)

        raise EOFError("SSE connection closed")

    async def close(self) -> None:
        """Close the SSE connection."""
        if self._response:
            self._response.close()
        if self._session:
            await self._session.close()


class WebSocketTransport(MCPTransport):
    """WebSocket transport for MCP.

    Used for bidirectional communication over WebSocket.
    """

    def __init__(self, url: str):
        self.url = url
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None

    async def connect(self) -> None:
        """Connect to the WebSocket endpoint."""
        self._session = aiohttp.ClientSession()
        self._ws = await self._session.ws_connect(self.url)

    async def send(self, message: dict[str, Any]) -> None:
        """Send a message through the WebSocket."""
        if not self._ws:
            raise RuntimeError("Transport not connected")

        await self._ws.send_json(message)

    async def receive(self) -> dict[str, Any]:
        """Receive a message from the WebSocket."""
        if not self._ws:
            raise RuntimeError("Transport not connected")

        msg = await self._ws.receive()

        if msg.type == aiohttp.WSMsgType.TEXT:
            return json.loads(msg.data)
        elif msg.type == aiohttp.WSMsgType.CLOSED:
            raise EOFError("WebSocket connection closed")
        else:
            raise RuntimeError(f"Unexpected message type: {msg.type}")

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()
