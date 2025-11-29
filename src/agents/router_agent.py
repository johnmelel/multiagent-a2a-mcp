"""
Router Agent - Orchestrates queries and routes to specialist agents via A2A.

The Router Agent is the entry point for user queries. It:
1. Analyzes the user's intent
2. Determines which specialist agents should handle the query
3. Coordinates with other agents via A2A messages
4. Synthesizes the final response
"""

import json
from typing import Any, Dict, List, Optional

from src.a2a.protocol import A2AMessage, MessageType
from .base_agent import BaseAgent


ROUTER_SYSTEM_PROMPT = """You are a Router Agent for a customer service system.
Your job is to analyze user queries and determine which specialist agents should handle them.

Available agents:
- customer_data_agent: Handles customer information lookup, updates, and history
- support_agent: Handles support tickets, escalations, and issue resolution

For each query, analyze:
1. What is the user asking for?
2. Does it require customer data lookup? (customer_data_agent)
3. Does it require support/ticket handling? (support_agent)
4. What information should be passed to each agent?

Respond in JSON format:
{
    "analysis": "Brief analysis of the query",
    "intents": ["list", "of", "intents"],
    "requires_customer_data": true/false,
    "requires_support": true/false,
    "customer_id": null or integer (if mentioned in query),
    "routing_plan": [
        {"agent": "agent_name", "task": "what to do", "priority": 1}
    ]
}
"""

SYNTHESIS_PROMPT = """You are synthesizing responses from multiple agents into a coherent reply.

User Query: {query}

Agent Responses:
{agent_responses}

Create a helpful, natural response that:
1. Addresses all parts of the user's query
2. Integrates information from all agents seamlessly
3. Is friendly and professional
4. Highlights any important information or required actions

Respond directly to the user (not in JSON).
"""


class RouterAgent(BaseAgent):
    """
    Router Agent for orchestrating multi-agent workflows.
    
    Receives user queries, analyzes intent, routes to specialist agents
    via A2A communication, and synthesizes the final response.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.3):
        """Initialize the Router Agent."""
        super().__init__(
            name="router",
            description="Orchestrates queries and routes to specialist agents",
            capabilities=["routing", "orchestration", "synthesis"],
            model=model,
            temperature=temperature,
        )
    
    async def process(self, message: A2AMessage) -> Optional[Dict[str, Any]]:
        """
        Process incoming A2A messages.
        
        For the router, this handles internal coordination messages.
        User queries come through the handle_user_query method.
        """
        payload = message.payload
        
        if message.type == MessageType.QUERY:
            # Handle query from another agent or system
            query = payload.get("query", "")
            result = await self.handle_user_query(query, message.conversation_id)
            return result
        
        return {"status": "processed", "message": "Router received message"}
    
    async def handle_user_query(
        self,
        query: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle a user query by routing to appropriate agents.
        
        Args:
            query: The user's query text
            conversation_id: Optional conversation ID for tracking
            
        Returns:
            Dictionary with response and metadata
        """
        self.log(f"Analyzing query: '{query}'")
        
        # Step 1: Analyze the query
        analysis = self._analyze_query(query)
        self.log(f"Analysis: {analysis.get('analysis', 'N/A')}")
        self.log(f"Requires customer data: {analysis.get('requires_customer_data')}")
        self.log(f"Requires support: {analysis.get('requires_support')}")
        
        # Step 2: Route to agents based on analysis
        agent_responses = {}
        
        # Route to Customer Data Agent if needed
        if analysis.get("requires_customer_data"):
            self.log("Routing to customer_data_agent via A2A")
            
            customer_response = await self.send_to_agent(
                recipient="customer_data",
                msg_type=MessageType.QUERY,
                payload={
                    "query": query,
                    "customer_id": analysis.get("customer_id"),
                    "tasks": [r for r in analysis.get("routing_plan", []) 
                             if r.get("agent") == "customer_data_agent"],
                },
                conversation_id=conversation_id,
            )
            
            if customer_response and customer_response.type != MessageType.ERROR:
                agent_responses["customer_data"] = customer_response.payload
        
        # Route to Support Agent if needed
        if analysis.get("requires_support"):
            self.log("Routing to support_agent via A2A")
            
            # Include customer data in support request if available
            support_payload = {
                "query": query,
                "customer_id": analysis.get("customer_id"),
                "customer_data": agent_responses.get("customer_data"),
                "tasks": [r for r in analysis.get("routing_plan", []) 
                         if r.get("agent") == "support_agent"],
            }
            
            support_response = await self.send_to_agent(
                recipient="support",
                msg_type=MessageType.QUERY,
                payload=support_payload,
                conversation_id=conversation_id,
            )
            
            if support_response and support_response.type != MessageType.ERROR:
                agent_responses["support"] = support_response.payload
        
        # Step 3: Synthesize final response
        self.log("Synthesizing final response")
        final_response = self._synthesize_response(query, analysis, agent_responses)
        
        return {
            "response": final_response,
            "analysis": analysis,
            "agent_responses": agent_responses,
            "agents_used": list(agent_responses.keys()),
        }
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze the user query to determine routing.
        
        Args:
            query: User query text
            
        Returns:
            Analysis dictionary with routing decisions
        """
        try:
            response = self.call_llm(ROUTER_SYSTEM_PROMPT, query)
            
            # Parse JSON response
            # Handle potential markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            analysis = json.loads(response.strip())
            return analysis
            
        except (json.JSONDecodeError, Exception) as e:
            self.log(f"Error parsing LLM response, using fallback analysis: {e}")
            # Fallback analysis based on keywords
            return self._fallback_analysis(query)
    
    def _fallback_analysis(self, query: str) -> Dict[str, Any]:
        """Fallback analysis using keyword matching."""
        query_lower = query.lower()
        
        # Extract customer ID if present
        customer_id = None
        import re
        id_match = re.search(r'(?:customer|id|#)\s*(\d+)', query_lower)
        if id_match:
            customer_id = int(id_match.group(1))
        
        # Determine routing based on keywords
        customer_keywords = ["customer", "account", "email", "phone", "history", "info", "update", "profile"]
        support_keywords = ["ticket", "support", "issue", "problem", "help", "refund", "complaint", "urgent"]
        
        requires_customer = any(kw in query_lower for kw in customer_keywords) or customer_id is not None
        requires_support = any(kw in query_lower for kw in support_keywords)
        
        # If neither, default to customer data
        if not requires_customer and not requires_support:
            requires_customer = True
        
        return {
            "analysis": "Fallback keyword-based analysis",
            "intents": ["general_query"],
            "requires_customer_data": requires_customer,
            "requires_support": requires_support,
            "customer_id": customer_id,
            "routing_plan": [],
        }
    
    def _synthesize_response(
        self,
        query: str,
        analysis: Dict[str, Any],
        agent_responses: Dict[str, Any]
    ) -> str:
        """
        Synthesize responses from multiple agents.
        
        Args:
            query: Original user query
            analysis: Query analysis results
            agent_responses: Responses from each agent
            
        Returns:
            Synthesized response text
        """
        if not agent_responses:
            return "I apologize, but I couldn't process your request. Please try again."
        
        # Format agent responses for synthesis
        responses_text = ""
        for agent_name, response in agent_responses.items():
            responses_text += f"\n{agent_name.upper()} AGENT:\n"
            if isinstance(response, dict):
                if "response" in response:
                    responses_text += f"{response['response']}\n"
                else:
                    responses_text += f"{json.dumps(response, indent=2)}\n"
            else:
                responses_text += f"{response}\n"
        
        prompt = SYNTHESIS_PROMPT.format(
            query=query,
            agent_responses=responses_text
        )
        
        try:
            return self.call_llm(
                "You synthesize agent responses into helpful user replies.",
                prompt
            )
        except Exception as e:
            self.log(f"Error synthesizing response: {e}")
            # Return the first available response
            for response in agent_responses.values():
                if isinstance(response, dict) and "response" in response:
                    return response["response"]
            return "Request processed. Please check the details above."
