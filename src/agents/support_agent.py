"""
Support Agent - Handles support tickets and customer assistance.

This agent specializes in:
- Creating and managing support tickets
- Handling customer complaints and issues
- Escalation handling
- Providing support guidance

It communicates with other agents via A2A and accesses data via MCP.
"""

import json
from typing import Any, Dict, List, Optional

from src.a2a.protocol import A2AMessage, MessageType
from src.mcp.mcp_client import MCPClient, get_mcp_client
from .base_agent import BaseAgent


SUPPORT_SYSTEM_PROMPT = """You are a Support Agent for a customer service system.
Your job is to help resolve customer issues and manage support tickets.

When handling support queries:
1. Acknowledge the customer's concern
2. Provide helpful solutions or next steps
3. Create tickets for issues that need tracking
4. Identify urgent issues that need escalation
5. Be empathetic and professional

Priority levels:
- low: General inquiries, non-urgent requests
- medium: Standard support issues, account questions
- high: Billing issues, service disruptions, complaints

Escalation triggers:
- Multiple unresolved tickets
- Billing/refund requests
- Repeated complaints
- Explicit urgency in request

Response format:
1. Acknowledge the issue
2. Explain what you can do
3. Provide next steps
4. Offer additional help
"""


class SupportAgent(BaseAgent):
    """
    Support Agent for handling support tickets and customer issues.
    
    Uses MCP client for ticket management and responds to
    A2A messages from other agents.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.5):
        """Initialize the Support Agent."""
        super().__init__(
            name="support",
            description="Handles support tickets and customer issue resolution",
            capabilities=["ticket_creation", "ticket_management", "escalation", "support"],
            model=model,
            temperature=temperature,
        )
        
        # Initialize MCP client for ticket operations
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
        customer_data = payload.get("customer_data", {})
        tasks = payload.get("tasks", [])
        
        self.log(f"Processing support query: '{query}'")
        
        # Analyze the support request
        analysis = self._analyze_support_request(query, customer_data)
        
        support_data = {
            "analysis": analysis,
        }
        errors = []
        
        # Handle ticket creation if needed
        if analysis.get("needs_ticket") and customer_id:
            self.log(f"Creating ticket for customer {customer_id}")
            try:
                issue = analysis.get("issue_summary", query[:200])
                priority = analysis.get("priority", "medium")
                
                result = self.mcp_client.create_ticket(
                    customer_id=customer_id,
                    issue=issue,
                    priority=priority
                )
                
                if result.get("success"):
                    support_data["ticket_created"] = result.get("ticket")
                    self.log(f"Ticket created: ID {result.get('ticket', {}).get('id')}")
                else:
                    errors.append("Failed to create ticket")
            except Exception as e:
                self.log(f"Error creating ticket: {e}")
                errors.append(str(e))
        
        # Get customer's existing tickets if available
        if customer_id:
            try:
                history = self.mcp_client.get_customer_history(customer_id)
                if history.get("success"):
                    tickets = history.get("tickets", [])
                    support_data["existing_tickets"] = tickets
                    
                    # Check for escalation needs
                    open_tickets = [t for t in tickets if t.get("status") != "resolved"]
                    if len(open_tickets) >= 3:
                        analysis["escalation_needed"] = True
                        analysis["escalation_reason"] = f"Customer has {len(open_tickets)} open tickets"
            except Exception as e:
                self.log(f"Error fetching customer history: {e}")
        
        # Generate support response
        response_text = self._generate_support_response(
            query, analysis, customer_data, support_data, errors
        )
        
        return {
            "response": response_text,
            "analysis": analysis,
            "data": support_data,
            "errors": errors if errors else None,
        }
    
    def _analyze_support_request(
        self,
        query: str,
        customer_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze the support request to determine actions needed.
        
        Args:
            query: User query
            customer_data: Customer data from CustomerDataAgent
            
        Returns:
            Analysis dictionary
        """
        query_lower = query.lower()
        
        # Default analysis
        analysis = {
            "needs_ticket": False,
            "priority": "medium",
            "category": "general",
            "escalation_needed": False,
            "escalation_reason": None,
            "issue_summary": query[:200] if len(query) > 200 else query,
        }
        
        # Detect priority
        high_priority_keywords = ["urgent", "immediately", "asap", "critical", "emergency", "refund", "charged twice", "billing error"]
        low_priority_keywords = ["question", "wondering", "curious", "when you have time"]
        
        if any(kw in query_lower for kw in high_priority_keywords):
            analysis["priority"] = "high"
            analysis["needs_ticket"] = True
        elif any(kw in query_lower for kw in low_priority_keywords):
            analysis["priority"] = "low"
        
        # Detect category
        if any(kw in query_lower for kw in ["billing", "charge", "payment", "refund", "invoice"]):
            analysis["category"] = "billing"
            analysis["needs_ticket"] = True
        elif any(kw in query_lower for kw in ["account", "upgrade", "downgrade", "subscription"]):
            analysis["category"] = "account"
        elif any(kw in query_lower for kw in ["bug", "error", "not working", "broken", "issue"]):
            analysis["category"] = "technical"
            analysis["needs_ticket"] = True
        elif any(kw in query_lower for kw in ["complaint", "unhappy", "frustrated", "disappointed"]):
            analysis["category"] = "complaint"
            analysis["needs_ticket"] = True
            analysis["escalation_needed"] = True
            analysis["escalation_reason"] = "Customer complaint detected"
        
        # Check if ticket creation is explicitly requested
        if any(kw in query_lower for kw in ["create ticket", "open ticket", "log issue", "report"]):
            analysis["needs_ticket"] = True
        
        return analysis
    
    def _generate_support_response(
        self,
        query: str,
        analysis: Dict[str, Any],
        customer_data: Optional[Dict[str, Any]],
        support_data: Dict[str, Any],
        errors: List[str]
    ) -> str:
        """Generate a support response using the LLM."""
        
        # Build context for LLM
        context = f"""
Query: {query}

Analysis:
- Category: {analysis.get('category')}
- Priority: {analysis.get('priority')}
- Needs Ticket: {analysis.get('needs_ticket')}
- Escalation Needed: {analysis.get('escalation_needed')}
"""
        
        if customer_data:
            context += f"\nCustomer Data:\n{json.dumps(customer_data, indent=2, default=str)}"
        
        if support_data.get("ticket_created"):
            context += f"\n\nTicket Created: #{support_data['ticket_created'].get('id')}"
        
        if support_data.get("existing_tickets"):
            context += f"\n\nExisting Tickets: {len(support_data['existing_tickets'])} tickets found"
        
        if errors:
            context += f"\n\nErrors encountered: {'; '.join(errors)}"
        
        try:
            response = self.call_llm(
                SUPPORT_SYSTEM_PROMPT,
                f"Provide a helpful support response for this situation:\n\n{context}"
            )
            return response
        except Exception as e:
            self.log(f"Error generating response: {e}")
            # Fallback response
            if support_data.get("ticket_created"):
                return f"I've created support ticket #{support_data['ticket_created'].get('id')} for your issue. Our team will follow up shortly."
            return "Thank you for reaching out. I've noted your concern and our team will assist you shortly."
