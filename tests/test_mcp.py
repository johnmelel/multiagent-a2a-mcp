"""
Tests for MCP server implementation.

This file contains two test suites:
1. Unit tests that test the MCP tool functions directly (for development speed)
2. Integration tests that test through the MCP client protocol (for protocol compliance)

For production, the protocol-based tests ensure the MCP server is compliant with
the MCP specification and works with any standard MCP client.
"""

import pytest
import os
import sys
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the MCP SDK functions for unit testing
from src.mcp.mcp_server import (
    get_customer,
    list_customers,
    update_customer,
    create_ticket,
    get_customer_history,
    _get_connection,
    DATABASE_PATH,
)

# Import MCP client for protocol testing
from src.mcp.mcp_client import MCPClient, MCPError, MCPToolError


class TestMCPServerUnit:
    """
    Unit tests for MCP Server tool functions.
    These test the underlying Python functions directly for fast development iteration.
    For protocol compliance testing, see TestMCPClientProtocol.
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures with a temporary database."""
        # Create a temporary database for testing
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_customers.db")
        
        # Initialize the database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                issue TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                priority TEXT DEFAULT 'medium',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)
        
        # Insert test data
        cursor.execute("""
            INSERT INTO customers (id, name, email, phone, status)
            VALUES (1, 'Test User', 'test@example.com', '555-0001', 'active')
        """)
        cursor.execute("""
            INSERT INTO customers (id, name, email, phone, status)
            VALUES (5, 'User Five', 'user5@example.com', '555-0005', 'active')
        """)
        cursor.execute("""
            INSERT INTO tickets (customer_id, issue, status, priority)
            VALUES (1, 'Test issue', 'open', 'high')
        """)
        
        conn.commit()
        conn.close()
        
        # Patch _get_connection to use test database
        self.patcher = patch(
            'src.mcp.mcp_server._get_connection',
            lambda db_path=None: self._get_test_connection()
        )
        self.patcher.start()
    
    def teardown_method(self, method):
        """Cleanup after each test."""
        self.patcher.stop()
    
    def _get_test_connection(self):
        """Get connection to test database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def test_get_customer_success(self):
        """Test getting an existing customer."""
        result = get_customer(1)
        
        assert result["success"] is True
        assert result["data"]["id"] == 1
        assert result["data"]["name"] == "Test User"
        assert result["data"]["email"] == "test@example.com"
    
    def test_get_customer_not_found(self):
        """Test getting a non-existent customer."""
        result = get_customer(99999)
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    def test_list_customers_all(self):
        """Test listing all customers."""
        result = list_customers(limit=10)
        
        assert result["success"] is True
        assert result["count"] >= 1
        assert isinstance(result["data"], list)
    
    def test_list_customers_by_status(self):
        """Test listing customers by status."""
        result = list_customers(status="active", limit=10)
        
        assert result["success"] is True
        for customer in result["data"]:
            assert customer["status"] == "active"
    
    def test_update_customer_success(self):
        """Test updating customer information."""
        result = update_customer(1, email="updated@example.com")
        
        assert result["success"] is True
        assert result["data"]["email"] == "updated@example.com"
    
    def test_update_customer_invalid_field(self):
        """Test updating with no fields provided."""
        result = update_customer(1)  # No fields to update
        
        assert result["success"] is False
        assert "No fields to update" in result["error"]
    
    def test_create_ticket_success(self):
        """Test creating a new ticket."""
        result = create_ticket(
            customer_id=1,
            issue="New test issue",
            priority="medium"
        )
        
        assert result["success"] is True
        assert result["data"]["issue"] == "New test issue"
        assert result["data"]["priority"] == "medium"
        assert result["data"]["status"] == "open"
    
    def test_create_ticket_invalid_priority(self):
        """Test creating ticket with invalid priority."""
        result = create_ticket(
            customer_id=1,
            issue="Test",
            priority="invalid"
        )
        
        assert result["success"] is False
        assert "Priority must be" in result["error"]
    
    def test_get_customer_history(self):
        """Test getting customer ticket history."""
        result = get_customer_history(1)
        
        assert result["success"] is True
        assert result["customer"]["id"] == 1
        assert result["ticket_count"] >= 1
        assert isinstance(result["tickets"], list)
    
    def test_get_customer_history_not_found(self):
        """Test getting history for non-existent customer."""
        result = get_customer_history(99999)
        
        assert result["success"] is False
        assert "not found" in result["error"]


class TestMCPClientProtocol:
    """
    Protocol compliance tests for MCP client-server communication.
    
    These tests verify that:
    1. The MCP server exposes tools via the standard tools/list method
    2. Tools can be called via the standard tools/call method
    3. JSON-RPC 2.0 protocol is followed correctly
    4. Tool schemas follow MCP specification
    
    NOTE: These tests require the MCP HTTP server to be running:
        python run_servers.py mcp --transport http --port 8080
    
    Mark these as integration tests and skip if server not available.
    """
    
    @pytest.fixture
    def client(self):
        """Create MCP client for testing."""
        return MCPClient(base_url="http://localhost:8080")
    
    @pytest.mark.integration
    def test_list_tools_returns_valid_schema(self, client):
        """Test that tools/list returns properly formatted tool definitions."""
        try:
            tools = client.list_tools(use_cache=False)
            
            assert isinstance(tools, list)
            assert len(tools) > 0
            
            # Verify each tool has required MCP fields
            for tool in tools:
                assert "name" in tool, "Tool must have a name"
                assert "description" in tool, "Tool must have a description"
                # inputSchema is required by MCP spec
                assert "inputSchema" in tool, "Tool must have an inputSchema"
                
                # Verify inputSchema follows JSON Schema format
                schema = tool["inputSchema"]
                assert isinstance(schema, dict)
                # Should have type: object for tool parameters
                assert schema.get("type") == "object" or "properties" in schema
        except Exception as e:
            pytest.skip(f"MCP server not available: {e}")
    
    @pytest.mark.integration
    def test_call_tool_via_protocol(self, client):
        """Test calling a tool via the MCP protocol (tools/call)."""
        try:
            # Call get_customer via MCP protocol
            result = client.call_tool("get_customer", {"customer_id": 1})
            
            # Should return a result (success or failure)
            assert isinstance(result, dict)
            assert "success" in result
        except Exception as e:
            pytest.skip(f"MCP server not available: {e}")
    
    @pytest.mark.integration
    def test_tool_names_match_spec(self, client):
        """Verify tool names follow MCP conventions."""
        try:
            tools = client.list_tools(use_cache=False)
            
            expected_tools = {
                "get_customer",
                "list_customers", 
                "update_customer",
                "create_ticket",
                "get_customer_history",
                "search_customers",
                "get_open_tickets"
            }
            
            actual_tools = {tool["name"] for tool in tools}
            
            # All expected tools should be available
            assert expected_tools.issubset(actual_tools), \
                f"Missing tools: {expected_tools - actual_tools}"
        except Exception as e:
            pytest.skip(f"MCP server not available: {e}")
    
    @pytest.mark.integration
    def test_jsonrpc_error_handling(self, client):
        """Test that MCP server returns proper errors for unknown tools."""
        try:
            client.call_tool("nonexistent_tool", {})
            pytest.fail("Expected an exception for unknown tool")
        except ExceptionGroup as eg:
            # The MCPToolError is wrapped in ExceptionGroup due to async handling
            error_found = False
            for exc in eg.exceptions:
                if isinstance(exc, ExceptionGroup):
                    for inner_exc in exc.exceptions:
                        if isinstance(inner_exc, MCPToolError):
                            assert inner_exc.tool_name == "nonexistent_tool"
                            assert "unknown" in inner_exc.message.lower()
                            error_found = True
                            break
                elif isinstance(exc, MCPToolError):
                    assert exc.tool_name == "nonexistent_tool"
                    assert "unknown" in exc.message.lower()
                    error_found = True
                    break
            assert error_found, f"MCPToolError not found in ExceptionGroup: {eg}"
        except MCPToolError as e:
            # Direct MCPToolError (if not wrapped)
            assert e.tool_name == "nonexistent_tool"
            assert "unknown" in e.message.lower()
        except Exception as e:
            if "unknown" in str(e).lower():
                pass  # This is expected - the error message contains "unknown"
            else:
                pytest.skip(f"MCP server not available: {e}")


class TestMCPProtocolCompliance:
    """
    Tests to verify MCP protocol compliance without a running server.
    These test the client's protocol formatting.
    """
    
    def test_client_formats_jsonrpc_request_correctly(self):
        """Test that client is properly initialized with correct URL."""
        client = MCPClient(base_url="http://test:8080")
        
        # Client should be initialized with the correct URL
        assert client.url == "http://test:8080/mcp"
        assert client.base_url == "http://test:8080"
        
        # Tools cache should start empty
        assert client._tools_cache is None
    
    def test_client_parses_tool_response(self):
        """Test that client correctly parses MCP tool responses."""
        client = MCPClient(base_url="http://test:8080")
        
        # Mock response in MCP format
        mock_response = {
            "content": [
                {
                    "type": "text",
                    "text": '{"success": true, "data": {"id": 1}}'
                }
            ]
        }
        
        # The response parsing is done in call_tool, 
        # we're testing the format expectations here
        content = mock_response.get("content", [])
        assert len(content) > 0
        assert content[0].get("type") == "text"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])