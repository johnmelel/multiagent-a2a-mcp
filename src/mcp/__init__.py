"""
MCP (Model Context Protocol) Module.

This module provides a production-ready MCP implementation using the official `mcp` SDK.
Implements MCP specification 2025-03-26 for full protocol compliance.

## Architecture: Proper MCP Protocol Compliance

All agents communicate with the MCP server via the MCP protocol (HTTP/JSON-RPC 2.0),
NOT by calling Python functions directly. This ensures:
- True MCP protocol compliance
- Universal compatibility with any MCP client/server
- Clean separation between agents and tools

### MCP Server (Standard Compliant)
Run the MCP server (required for agents to work):
    python run_servers.py mcp --transport http

The server implements:
- tools/list: Returns tools with proper inputSchema (JSON Schema format)
- tools/call: Executes tools and returns content array with results
- Full JSON-RPC 2.0 error handling

### MCP Client (for agents)
Agents use the MCP client to call tools via the protocol:
    from src.mcp import MCPClient, get_mcp_client
    
    client = get_mcp_client()
    result = client.call_tool("get_customer", {"customer_id": 5})

### For Claude Desktop / External MCP Clients
Run in stdio mode:
    python run_servers.py mcp --transport stdio

### Interoperability
This implementation works with:
- Any MCP-compliant client (Claude Desktop, custom clients)
- Any MCP-compliant server (swap out our server for another)
"""

from .mcp_server import (
    # MCP Server
    mcp as fastmcp_server,
    run_server,
    run_http_server,
    # Database path (for testing)
    DATABASE_PATH,
)

# MCP Client (protocol-compliant)
from .mcp_client import MCPClient, MCPError, MCPToolError, get_mcp_client, DEFAULT_MCP_URL

__all__ = [
    # MCP Server
    "fastmcp_server",
    "run_server",
    "run_http_server",
    # MCP Client
    "MCPClient",
    "MCPError",
    "MCPToolError",
    "get_mcp_client",
    "DEFAULT_MCP_URL",
    # Database
    "DATABASE_PATH",
]