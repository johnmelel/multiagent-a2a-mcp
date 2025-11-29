"""
MCP Client for connecting to any standard MCP server.

This client implements the MCP specification using the official MCP Python SDK
for proper protocol compliance with the streamable HTTP transport.

Protocol Compliance:
- Uses official MCP SDK for session management
- Properly handles the streamable HTTP protocol
- Supports both sync and async operations
- Handles tool discovery and invocation

This client is designed to be universal and work with ANY MCP server:
- The official MCP server implementations
- Custom MCP servers built to the specification
- Third-party MCP servers from the ecosystem

Agents MUST use this client (or equivalent) to access MCP tools - never call
MCP server functions directly as Python imports. This ensures:
- True protocol compliance
- Interoperability with any MCP server
- Clean separation between agents and tool implementations
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


# Default MCP server URL - configurable via environment variable
DEFAULT_MCP_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8080/mcp")


class MCPClient:
    """
    MCP Client that communicates with MCP server using the official MCP SDK.
    
    This client follows the MCP specification for tool discovery and invocation
    using the streamable HTTP transport.
    """
    
    def __init__(self, base_url: str = DEFAULT_MCP_URL):
        """
        Initialize the MCP client.
        
        Args:
            base_url: URL of the MCP server endpoint (default: http://localhost:8080/mcp)
        """
        self.url = base_url.rstrip("/")
        if not self.url.endswith("/mcp"):
            self.url = f"{self.url}/mcp"
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
    
    @property
    def base_url(self) -> str:
        """Return base URL for compatibility."""
        return self.url.rsplit("/mcp", 1)[0]
    
    async def _run_session(self, callback):
        """
        Run a callback within an MCP session.
        
        Args:
            callback: Async function that takes a ClientSession
            
        Returns:
            Result from the callback
        """
        async with streamablehttp_client(self.url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await callback(session)
    
    def _run_sync(self, coro):
        """Run an async coroutine synchronously."""
        try:
            asyncio.get_running_loop()
            # If we're already in an async context, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        except RuntimeError:
            # No running loop, we can use asyncio.run
            return asyncio.run(coro)
    
    async def _list_tools_async(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server (async)."""
        async def get_tools(session: ClientSession):
            result = await session.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                }
                for tool in result.tools
            ]
        return await self._run_session(get_tools)
    
    async def _call_tool_async(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a tool on the MCP server (async)."""
        async def call(session: ClientSession):
            result = await session.call_tool(name, arguments or {})
            
            # Check for tool execution errors
            if result.isError:
                content = result.content
                error_msg = "Tool execution failed"
                if content and len(content) > 0:
                    first_content = content[0]
                    if hasattr(first_content, 'text'):
                        error_msg = first_content.text
                raise MCPToolError(name, error_msg)
            
            # Extract content from MCP response format
            content = result.content
            if content and len(content) > 0:
                first_content = content[0]
                if hasattr(first_content, 'text'):
                    # Parse JSON text content
                    try:
                        return json.loads(first_content.text)
                    except json.JSONDecodeError:
                        return first_content.text
                return first_content
            
            return result
        
        return await self._run_session(call)
    
    def list_tools(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        List available tools from the MCP server.
        
        Args:
            use_cache: Whether to use cached tools list
            
        Returns:
            List of tool definitions with name, description, and input schema
        """
        if use_cache and self._tools_cache is not None:
            return self._tools_cache
        
        tools = self._run_sync(self._list_tools_async())
        self._tools_cache = tools
        return tools
    
    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """
        Call a tool on the MCP server via tools/call method.
        
        Args:
            name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            The tool's result (parsed from content array)
            
        Raises:
            MCPToolError: If the tool execution failed (isError: true)
        """
        return self._run_sync(self._call_tool_async(name, arguments))
    
    # Convenience methods for customer service tools
    
    def get_customer(self, customer_id: int) -> Dict[str, Any]:
        """Get customer information by ID."""
        return self.call_tool("get_customer", {"customer_id": customer_id})
    
    def list_customers(self, status: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """List customers with optional filters."""
        args = {"limit": limit}
        if status:
            args["status"] = status
        return self.call_tool("list_customers", args)
    
    def update_customer(
        self,
        customer_id: int,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update customer information."""
        args = {"customer_id": customer_id}
        if name is not None:
            args["name"] = name
        if email is not None:
            args["email"] = email
        if phone is not None:
            args["phone"] = phone
        if status is not None:
            args["status"] = status
        return self.call_tool("update_customer", args)
    
    def create_ticket(
        self,
        customer_id: int,
        issue: str,
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """Create a new support ticket."""
        return self.call_tool("create_ticket", {
            "customer_id": customer_id,
            "issue": issue,
            "priority": priority
        })
    
    def get_customer_history(self, customer_id: int) -> Dict[str, Any]:
        """Get customer info and all their tickets."""
        return self.call_tool("get_customer_history", {"customer_id": customer_id})
    
    def search_customers(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search customers by name or email."""
        return self.call_tool("search_customers", {"query": query, "limit": limit})
    
    def get_open_tickets(self, limit: int = 20) -> Dict[str, Any]:
        """Get all open support tickets."""
        return self.call_tool("get_open_tickets", {"limit": limit})


class MCPError(Exception):
    """
    Exception raised when MCP server returns a protocol-level error.
    These are JSON-RPC 2.0 errors for issues like unknown tools or invalid arguments.
    """
    
    def __init__(self, error: Dict[str, Any]):
        if isinstance(error, dict):
            self.code = error.get("code", -1)
            self.message = error.get("message", "Unknown error")
            self.data = error.get("data")
        else:
            self.code = -1
            self.message = str(error)
            self.data = None
        super().__init__(f"MCP Error {self.code}: {self.message}")


class MCPToolError(Exception):
    """
    Exception raised when a tool execution fails (isError: true in response).
    These are tool-level errors like API failures, invalid input data, or business logic errors.
    """
    
    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        self.message = message
        super().__init__(f"Tool '{tool_name}' failed: {message}")


# Singleton client instance
_client: Optional[MCPClient] = None


def get_mcp_client(base_url: str = DEFAULT_MCP_URL) -> MCPClient:
    """
    Get or create a singleton MCP client.
    
    Args:
        base_url: Base URL of the MCP server
        
    Returns:
        MCPClient instance
    """
    global _client
    if _client is None or _client.url != base_url:
        _client = MCPClient(base_url)
    return _client
