"""
MCP Server implementation using official MCP Python SDK (FastMCP).
Provides tools for customer and ticket management via Model Context Protocol.

This server implements the MCP specification (2025-03-26):
- JSON-RPC 2.0 protocol for all communications
- tools/list method for tool discovery with proper inputSchema
- tools/call method for tool invocation
- Proper capability negotiation during initialization
- Multiple transport support: stdio (for Claude Desktop), HTTP/SSE (for web clients)

Protocol Compliance:
- All tools expose inputSchema following JSON Schema format
- Tool results return content array with type: "text"
- Error handling follows MCP error reporting conventions
- Server declares 'tools' capability on initialization

This MCP server is fully compatible with:
- Claude Desktop and other MCP-compliant AI assistants
- Any standard MCP client (JavaScript SDK, Python SDK, etc.)
- Custom MCP clients built to the specification
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

# Database path relative to project root
DATABASE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "customers.db"
)


@dataclass
class DatabaseContext:
    """Application context with database connection."""
    db_path: str


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[DatabaseContext]:
    """Manage application lifecycle with database context."""
    # Initialize on startup
    db_path = os.environ.get("MCP_DATABASE_PATH", DATABASE_PATH)
    try:
        yield DatabaseContext(db_path=db_path)
    finally:
        # Cleanup on shutdown (nothing to clean for SQLite)
        pass


# Create the MCP server with FastMCP
mcp = FastMCP(
    "CustomerServiceMCP",
    lifespan=app_lifespan,
    instructions="""
    Customer Service MCP Server providing tools for:
    - Customer information lookup and management
    - Support ticket creation and tracking
    - Customer history and interaction logs
    """
)


def _get_connection(db_path: str = DATABASE_PATH) -> sqlite3.Connection:
    """Get database connection with row factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool()
def get_customer(customer_id: int) -> Dict[str, Any]:
    """
    Get customer information by ID.
    
    Args:
        customer_id: The customer's unique identifier
        
    Returns:
        Customer data dictionary with success status
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM customers WHERE id = ?",
            (customer_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "success": True,
                "data": dict(row)
            }
        else:
            return {
                "success": False,
                "error": f"Customer with ID {customer_id} not found"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
def list_customers(
    status: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    List customers with optional status filter.
    
    Args:
        status: Filter by 'active' or 'disabled' (optional)
        limit: Maximum number of results (default: 10)
        
    Returns:
        List of customers with count
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute(
                "SELECT * FROM customers WHERE status = ? LIMIT ?",
                (status, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM customers LIMIT ?",
                (limit,)
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        return {
            "success": True,
            "data": [dict(row) for row in rows],
            "count": len(rows)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
def update_customer(
    customer_id: int,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update customer information.
    
    Args:
        customer_id: The customer's unique identifier
        name: New name for the customer (optional)
        email: New email for the customer (optional)
        phone: New phone for the customer (optional)
        status: New status 'active' or 'disabled' (optional)
        
    Returns:
        Success status and updated customer data
    """
    update_fields = {}
    if name is not None:
        update_fields["name"] = name
    if email is not None:
        update_fields["email"] = email
    if phone is not None:
        update_fields["phone"] = phone
    if status is not None:
        update_fields["status"] = status
    
    if not update_fields:
        return {
            "success": False,
            "error": "No fields to update. Provide at least one of: name, email, phone, status"
        }
    
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        # Build update query
        set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
        values = list(update_fields.values())
        values.append(datetime.now().isoformat())
        values.append(customer_id)
        
        cursor.execute(
            f"UPDATE customers SET {set_clause}, updated_at = ? WHERE id = ?",
            values
        )
        
        if cursor.rowcount == 0:
            conn.close()
            return {
                "success": False,
                "error": f"Customer with ID {customer_id} not found"
            }
        
        conn.commit()
        
        # Fetch updated record
        cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
        row = cursor.fetchone()
        conn.close()
        
        return {
            "success": True,
            "message": "Customer updated successfully",
            "data": dict(row)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
def create_ticket(
    customer_id: int,
    issue: str,
    priority: str = "medium"
) -> Dict[str, Any]:
    """
    Create a new support ticket for a customer.
    
    Args:
        customer_id: The customer's unique identifier
        issue: Description of the issue
        priority: Priority level - 'low', 'medium', or 'high' (default: medium)
        
    Returns:
        Created ticket data with success status
    """
    if priority not in ("low", "medium", "high"):
        return {
            "success": False,
            "error": "Priority must be 'low', 'medium', or 'high'"
        }
    
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        # Verify customer exists
        cursor.execute(
            "SELECT id FROM customers WHERE id = ?",
            (customer_id,)
        )
        if not cursor.fetchone():
            conn.close()
            return {
                "success": False,
                "error": f"Customer with ID {customer_id} not found"
            }
        
        cursor.execute(
            """
            INSERT INTO tickets (customer_id, issue, status, priority, created_at)
            VALUES (?, ?, 'open', ?, ?)
            """,
            (customer_id, issue, priority, datetime.now().isoformat())
        )
        
        ticket_id = cursor.lastrowid
        conn.commit()
        
        cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        row = cursor.fetchone()
        conn.close()
        
        return {
            "success": True,
            "message": "Ticket created successfully",
            "data": dict(row)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
def get_customer_history(customer_id: int) -> Dict[str, Any]:
    """
    Get customer information and all their support tickets.
    
    Args:
        customer_id: The customer's unique identifier
        
    Returns:
        Customer data with list of all their tickets
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        # Get customer info
        cursor.execute(
            "SELECT * FROM customers WHERE id = ?",
            (customer_id,)
        )
        customer = cursor.fetchone()
        
        if not customer:
            conn.close()
            return {
                "success": False,
                "error": f"Customer with ID {customer_id} not found"
            }
        
        # Get tickets
        cursor.execute(
            """
            SELECT * FROM tickets 
            WHERE customer_id = ? 
            ORDER BY created_at DESC
            """,
            (customer_id,)
        )
        tickets = cursor.fetchall()
        conn.close()
        
        return {
            "success": True,
            "customer": dict(customer),
            "tickets": [dict(t) for t in tickets],
            "ticket_count": len(tickets)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
def search_customers(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search customers by name or email.
    
    Args:
        query: Search term to match against name or email
        limit: Maximum number of results (default: 10)
        
    Returns:
        List of matching customers
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        search_term = f"%{query}%"
        cursor.execute(
            """
            SELECT * FROM customers 
            WHERE name LIKE ? OR email LIKE ?
            LIMIT ?
            """,
            (search_term, search_term, limit)
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        return {
            "success": True,
            "data": [dict(row) for row in rows],
            "count": len(rows),
            "query": query
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
def get_open_tickets(limit: int = 20) -> Dict[str, Any]:
    """
    Get all open support tickets.
    
    Args:
        limit: Maximum number of results (default: 20)
        
    Returns:
        List of open tickets with customer information
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT t.*, c.name as customer_name, c.email as customer_email
            FROM tickets t
            JOIN customers c ON t.customer_id = c.id
            WHERE t.status = 'open'
            ORDER BY 
                CASE t.priority 
                    WHEN 'high' THEN 1 
                    WHEN 'medium' THEN 2 
                    WHEN 'low' THEN 3 
                END,
                t.created_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        return {
            "success": True,
            "data": [dict(row) for row in rows],
            "count": len(rows)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def run_server():
    """Run the MCP server with stdio transport (default for MCP)."""
    mcp.run(transport="stdio")


def run_http_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the MCP server with HTTP transport for testing."""
    import uvicorn
    # FastMCP.run() doesn't accept host/port directly for streamable-http
    # We need to use uvicorn to run the ASGI app with custom host/port
    app = mcp.streamable_http_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    # Run with stdio transport by default
    run_server()
