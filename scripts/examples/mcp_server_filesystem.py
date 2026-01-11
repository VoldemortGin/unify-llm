"""
MCP Server Example: File System Tools

This example shows how to create an MCP server that exposes
file system operations as tools.
"""

import asyncio
import os
import json
from pathlib import Path
from typing import Dict, Any
from unify_llm.mcp import MCPServer, MCPServerConfig, StdioTransport


async def main():
    """Run the file system MCP server."""

    # Create server
    server = MCPServer(MCPServerConfig(
        server_name="filesystem-tools",
        server_version="1.0.0"
    ))

    # Tool: List directory contents
    @server.tool(
        name="list_directory",
        description="List contents of a directory",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list"
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "Show hidden files",
                    "default": False
                }
            },
            "required": ["path"]
        }
    )
    async def list_directory(path: str, show_hidden: bool = False) -> Dict[str, Any]:
        """List directory contents."""
        try:
            dir_path = Path(path)
            if not dir_path.exists():
                return {"error": f"Path does not exist: {path}"}

            if not dir_path.is_dir():
                return {"error": f"Path is not a directory: {path}"}

            items = []
            for item in dir_path.iterdir():
                # Skip hidden files unless requested
                if not show_hidden and item.name.startswith('.'):
                    continue

                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None
                })

            return {
                "path": str(dir_path.absolute()),
                "items": items,
                "count": len(items)
            }
        except Exception as e:
            return {"error": str(e)}

    # Tool: Read file
    @server.tool(
        name="read_file",
        description="Read contents of a text file",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path to read"
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding",
                    "default": "utf-8"
                }
            },
            "required": ["path"]
        }
    )
    async def read_file(path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Read file contents."""
        try:
            file_path = Path(path)
            if not file_path.exists():
                return {"error": f"File does not exist: {path}"}

            if not file_path.is_file():
                return {"error": f"Path is not a file: {path}"}

            content = file_path.read_text(encoding=encoding)

            return {
                "path": str(file_path.absolute()),
                "content": content,
                "size": len(content),
                "lines": content.count('\n') + 1
            }
        except Exception as e:
            return {"error": str(e)}

    # Tool: Write file
    @server.tool(
        name="write_file",
        description="Write content to a file",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path to write"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write"
                },
                "create_dirs": {
                    "type": "boolean",
                    "description": "Create parent directories if needed",
                    "default": False
                }
            },
            "required": ["path", "content"]
        }
    )
    async def write_file(path: str, content: str, create_dirs: bool = False) -> Dict[str, Any]:
        """Write file contents."""
        try:
            file_path = Path(path)

            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            file_path.write_text(content, encoding='utf-8')

            return {
                "path": str(file_path.absolute()),
                "size": len(content),
                "success": True
            }
        except Exception as e:
            return {"error": str(e), "success": False}

    # Tool: Search files
    @server.tool(
        name="search_files",
        description="Search for files matching a pattern",
        input_schema={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory to search in"
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g., '*.py', '**/*.txt')"
                }
            },
            "required": ["directory", "pattern"]
        }
    )
    async def search_files(directory: str, pattern: str) -> Dict[str, Any]:
        """Search for files matching pattern."""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return {"error": f"Directory does not exist: {directory}"}

            matches = list(dir_path.glob(pattern))

            results = [
                {
                    "path": str(m.absolute()),
                    "name": m.name,
                    "type": "directory" if m.is_dir() else "file"
                }
                for m in matches
            ]

            return {
                "directory": str(dir_path.absolute()),
                "pattern": pattern,
                "matches": results,
                "count": len(results)
            }
        except Exception as e:
            return {"error": str(e)}

    # Resource: Current working directory
    @server.resource(
        uri="file://cwd",
        mime_type="text/plain",
        description="Current working directory"
    )
    async def get_cwd() -> str:
        """Get current working directory."""
        return os.getcwd()

    # Resource: Environment info
    @server.resource(
        uri="system://env",
        mime_type="application/json",
        description="Environment information"
    )
    async def get_env_info() -> str:
        """Get environment information."""
        info = {
            "platform": os.name,
            "cwd": os.getcwd(),
            "user": os.getenv("USER", "unknown"),
            "home": os.getenv("HOME", "unknown")
        }
        return json.dumps(info, indent=2)

    # Prompt: File summary template
    @server.prompt(
        name="summarize_file",
        description="Generate a prompt to summarize a file",
        arguments=[
            {
                "name": "file_path",
                "description": "Path to the file to summarize",
                "required": True
            }
        ]
    )
    async def summarize_file_prompt(file_path: str) -> Dict[str, Any]:
        """Generate file summary prompt."""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes files."
                },
                {
                    "role": "user",
                    "content": f"Please read and summarize the file at: {file_path}"
                }
            ]
        }

    print("🚀 File System MCP Server Starting...")
    print(f"   Server: {server.config.server_name} v{server.config.server_version}")
    print("\n📋 Available Tools:")
    print("   - list_directory: List directory contents")
    print("   - read_file: Read text file")
    print("   - write_file: Write to file")
    print("   - search_files: Search for files")
    print("\n📦 Available Resources:")
    print("   - file://cwd: Current working directory")
    print("   - system://env: Environment information")
    print("\n📝 Available Prompts:")
    print("   - summarize_file: File summary template")
    print("\n✅ Server ready! Listening on stdio...")

    # Start server with stdio transport
    transport = StdioTransport()
    await server.start(transport)


if __name__ == "__main__":
    asyncio.run(main())
