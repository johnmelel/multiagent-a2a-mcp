"""
Customer Data Agent - Handles customer information via MCP.

This agent specializes in:
- Customer data lookup and search
- Customer profile updates
- Customer history retrieval
- Account management queries

It communicates with other agents via A2A and accesses data via MCP.
"""

import json
from typing import Any, Dict, List, Optional

from src.a2a.protocol import A2AMessage, MessageType
from src.mcp.mcp_client import MCPClient, get_mcp_client
from .base_agent import BaseAgent


CUSTOMER_DATA_SYSTEM_PROMPT = """You are a Customer Data Agent for a customer service system.
Your job is to help retrieve and manage customer information.

You have access to customer data via MCP tools. Based on the query and available data,
provide helpful information about customers.

When responding:
1. Summarize the key customer information
2. Highlight any relevant details
3. Note any issues or concerns
4. Format the response clearly

Available data fields for customers:
- id, name, email, phone, status (active/disabled), created_at, updated_at

Available data fields for tickets:
- id, customer_id, issue, status (open/in_progress/resolved), priority, created_at
"""


class CustomerDataAgent(BaseAgent):
    """
    Customer Data Agent for handling customer information queries.
    
    Uses MCP client to access customer database and responds to
    A2A messages from other agents.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.3):
        """Initialize the Customer Data Agent."""
        super().__init__(
            name="customer_data",
            description="Handles customer information lookup and management",
            capabilities=["customer_lookup", "customer_update", "customer_history"],
            model=model,
            temperature=temperature,
        )
        
        # Initialize MCP client for database access
        self.mcp_client = get_mcp_client()
    
    async def process(self, message: A2AMessage) -> Optional[Dict[str, Any]]:
        """
        Process incoming A2A messages.
        
        Args:
            message: Incoming A2A message
            
        Returns:
            Response payload
        """
        payload = message.payload
        query = payload.get("query", "")
        customer_id = payload.get("customer_id")
        tasks = payload.get("tasks", [])
        
        self.log(f"Processing query: '{query}'")
        
        # Gather customer data based on query
        customer_data = {}
        errors = []
        
        # Try to get customer data if ID is provided
        if customer_id:
            self.log(f"Looking up customer ID: {customer_id}")
            try:
                result = self.mcp_client.get_customer(customer_id)
                if result.get("success"):
                    customer_data["customer"] = result.get("customer")
                    self.log(f"Found customer: {result.get('customer', {}).get('name', 'Unknown')}")
                else:
                    errors.append(f"Customer {customer_id} not found")
            except Exception as e:
                self.log(f"Error fetching customer: {e}")
                errors.append(str(e))
        
        # Analyze query for additional data needs
        query_lower = query.lower()
        
        # Get customer history if requested
        if "history" in query_lower or "tickets" in query_lower:
            if customer_id:
                self.log(f"Fetching history for customer {customer_id}")
                try:
                    history = self.mcp_client.get_customer_history(customer_id)
                    if history.get("success"):
                        customer_data["history"] = history
                except Exception as e:
                    self.log(f"Error fetching history: {e}")
                    errors.append(str(e))
        
        # List customers if requested
        if "list" in query_lower or "all customers" in query_lower:
            self.log("Listing customers")
            try:
                status = "active" if "active" in query_lower else None
                customers = self.mcp_client.list_customers(status=status, limit=10)
                if customers.get("success"):
                    customer_data["customers_list"] = customers.get("customers", [])
            except Exception as e:
                self.log(f"Error listing customers: {e}")
                errors.append(str(e))
        
        # Search customers if needed
        if "search" in query_lower or "find" in query_lower:
            # Extract search terms
            search_terms = self._extract_search_terms(query)
            if search_terms:
                self.log(f"Searching for: {search_terms}")
                try:
                    results = self.mcp_client.search_customers(search_terms)
                    if results.get("success"):
                        customer_data["search_results"] = results.get("customers", [])
                except Exception as e:
                    self.log(f"Error searching: {e}")
                    errors.append(str(e))
        
        # Handle open tickets query
        if "open tickets" in query_lower:
            self.log("Fetching open tickets")
            try:
                tickets = self.mcp_client.get_open_tickets(limit=20)
                if tickets.get("success"):
                    customer_data["open_tickets"] = tickets.get("tickets", [])
            except Exception as e:
                self.log(f"Error fetching open tickets: {e}")
                errors.append(str(e))
        
        # Handle update requests
        if "update" in query_lower and customer_id:
            update_result = await self._handle_update(query, customer_id)
            if update_result:
                customer_data["update_result"] = update_result
        
        # Generate response using LLM
        response_text = self._generate_response(query, customer_data, errors)
        
        return {
            "response": response_text,
            "data": customer_data,
            "errors": errors if errors else None,
        }
    
    def _extract_search_terms(self, query: str) -> Optional[str]:
        """Extract search terms from a query."""
        import re
        
        # Look for quoted strings first
        quoted = re.findall(r'"([^"]*)"', query)
        if quoted:
            return quoted[0]
        
        # Look for patterns like "search for X" or "find X"
        patterns = [
            r'search\s+(?:for\s+)?(.+)',
            r'find\s+(.+)',
            r'look\s+(?:for\s+|up\s+)?(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                return match.group(1).strip()
        
        return None
    
    async def _handle_update(self, query: str, customer_id: int) -> Optional[Dict[str, Any]]:
        """Handle customer update requests."""
        import re
        
        update_data = {}
        
        # Extract email update
        email_match = re.search(r'email\s+(?:to\s+)?([^\s,]+@[^\s,]+)', query.lower())
        if email_match:
            update_data["email"] = email_match.group(1)
        
        # Extract phone update
        phone_match = re.search(r'phone\s+(?:to\s+)?([0-9\-\+\(\)\s]+)', query.lower())
        if phone_match:
            update_data["phone"] = phone_match.group(1).strip()
        
        # Extract name update
        name_match = re.search(r'name\s+(?:to\s+)?([A-Za-z\s]+)', query)
        if name_match:
            update_data["name"] = name_match.group(1).strip()
        
        if update_data:
            self.log(f"Updating customer {customer_id}: {update_data}")
            try:
                result = self.mcp_client.update_customer(customer_id, **update_data)
                return result
            except Exception as e:
                self.log(f"Error updating customer: {e}")
                return {"success": False, "error": str(e)}
        
        return None
    
    def _generate_response(
        self,
        query: str,
        customer_data: Dict[str, Any],
        errors: List[str]
    ) -> str:
        """Generate a response using the LLM."""
        
        if not customer_data and errors:
            return f"I encountered some issues while processing your request: {'; '.join(errors)}"
        
        if not customer_data:
            return "I couldn't find any relevant customer data for your query. Please provide more details or a customer ID."
        
        # Build context for LLM
        context = f"Query: {query}\n\nAvailable Data:\n"
        context += json.dumps(customer_data, indent=2, default=str)
        
        if errors:
            context += f"\n\nNotes: {'; '.join(errors)}"
        
        try:
            response = self.call_llm(
                CUSTOMER_DATA_SYSTEM_PROMPT,
                f"Based on this customer data, provide a helpful response:\n\n{context}"
            )
            return response
        except Exception as e:
            self.log(f"Error generating response: {e}")
            # Fallback to raw data
            return f"Customer Data Retrieved:\n{json.dumps(customer_data, indent=2, default=str)}"
