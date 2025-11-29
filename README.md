
# Multi-Agent Customer Service System with A2A Communication and MCP

This project implements a multi-agent customer service system where **multiple single agents** communicate directly with each other using an **Agent-to-Agent (A2A) protocol**. Each agent is an independent unit, built with **LangChain**, and communicates with other agents and the Model Context Protocol (MCP) server for data access. The system does **not** use LangGraph; all agent coordination is handled via explicit A2A messaging.

## Architecture

### Multi-Agent A2A Coordination

- **A2A Protocol**: Agents communicate by sending structured messages to each other (A2A), enabling flexible, decoupled workflows.
- **Independent Agents**: Each agent (Router, CustomerData, Support, etc.) is a standalone process or service, running its own LangChain logic.
- **MCP Server**: Provides a protocol-compliant interface (HTTP/JSON-RPC) for agents to access customer and ticket data.
- **Agent Registry/Discovery**: Agents can discover and address each other via a registry or configuration.

### Agents

- **Router Agent**: Receives user queries, analyzes intent, and routes requests to other agents via A2A messages.
- **Customer Data Agent**: Handles customer data queries by communicating with the MCP server.
- **Support Agent**: Handles support and ticket-related queries, using context from other agents as needed.

### A2A Communication Flow Example

```
User Query → Router Agent (A2A) → Customer Data Agent (A2A) → Support Agent (A2A) → Router Agent → User
```

Agents exchange messages using a defined A2A protocol (e.g., JSON over HTTP, sockets, or in-memory queues). Each agent can be run as a separate process or service.


## Project Structure

```
multiagent-a2a-mcp/
├── src/
│   ├── main.py                 # Entry point (launches agents, UI, or CLI)
│   ├── mcp/
│   │   ├── mcp_server.py       # MCP server (HTTP/JSON-RPC)
│   │   └── mcp_client.py       # MCP client for protocol-compliant access
│   ├── ui/
│   │   └── gradio_app.py       # Gradio web interface
│   └── a2a/
│       ├── protocol.py         # A2A protocol definitions (message formats, etc.)
│       ├── registry.py         # Agent registry/discovery
├── data/
│   ├── database_setup.py       # Database initialization script
│   └── customers.db            # SQLite database (generated)
├── tests/
│   ├── test_mcp.py
│   └── test_a2a.py             # A2A protocol and agent tests
├── run_servers.py              # CLI to run MCP server
├── requirements.txt
├── .env.example
└── README.md
```

---


## A2A Protocol Overview

Agents communicate using a structured A2A protocol. Each message includes:

- `sender`: Agent name
- `recipient`: Target agent name
- `type`: Message type (e.g., `query`, `response`, `data_request`)
- `payload`: Message content (query, data, etc.)
- `conversation_id`: (optional) For tracking multi-step workflows

Example message (JSON):
```json
{
  "sender": "router",
  "recipient": "customer_data",
  "type": "query",
  "payload": {"customer_id": 5},
  "conversation_id": "abc123"
}
```


## MCP Protocol Compliance

Agents access customer and ticket data by communicating with the MCP server using HTTP/JSON-RPC 2.0. This ensures clean separation between agent logic and data access.

```
┌─────────────┐        ┌─────────────┐          ┌─────────────┐
│   Agents    │ ──────▶│ MCP Client  │ ───────▶│ MCP Server  │
│ (A2A)       │ Tools  │ (HTTP/JSON) │ Protocol │  (MCP)      │
└─────────────┘        └─────────────┘          └─────────────┘
                                                                │
                                                         ┌─────▼─────┐
                                                         │  SQLite   │
                                                         │ Database  │
                                                         └───────────┘
```

### Why This Architecture?

1. **Universal Compatibility** - Any MCP client can use the tools
2. **Clean Separation** - Server and client can be deployed independently
3. **Testability** - Components can be tested in isolation
4. **Production Ready** - Matches real-world MCP integrations

### Usage

The MCP server MUST be running for agents to work:

```bash
# Start MCP Server (required)
python run_servers.py mcp --transport http
```

### Code Example

```python
from src.mcp import MCPClient
client = MCPClient()  # Default: http://localhost:8080
result = client.call_tool("get_customer", {"customer_id": 5})
```


## Setup Instructions

### 1. Clone and Navigate to Project

```bash
git clone <repository-url>
cd multiagent-a2a-mcp
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install uv
uv pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy example environment file
copy .env.example .env    # Windows
cp .env.example .env      # macOS/Linux

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=your-api-key-here
```

### 5. Initialize Database

```bash
python data/database_setup.py
```

This creates `data/customers.db` with sample customer and ticket data.

### 6. Run the Application


**Gradio Web Interface (Default):**
```bash
python -m src.main --mode gradio
```
Then open http://localhost:7860 in your browser.

**Terminal Mode:**
```bash
python -m src.main --mode terminal
```

## Database Schema

### Customers Table
| Field       | Type        | Description               |
|-------------|-------------|---------------------------|
| id          | INTEGER     | Primary key               |
| name        | TEXT        | Customer name             |
| email       | TEXT        | Email address             |
| phone       | TEXT        | Phone number              |     
| status      | TEXT        | 'active' or 'disabled'    |
| created_at  | TIMESTAMP   | Creation timestamp        |
| updated_at  | TIMESTAMP   | Last update timestamp     |

### Tickets Table
| Field       | Type        | Description                             |
|-------------|-------------|-----------------------------------------|
| id          | INTEGER     | Primary key                             |
| customer_id | INTEGER     | Foreign key to customers                |
| issue       | TEXT        | Issue description                       |
| status      | TEXT        | 'open', 'in_progress', or 'resolved'    |
| priority    | TEXT        | 'low', 'medium', or 'high'              |
| created_at  | DATETIME    | Creation timestamp                      |

## MCP Tools

| Tool                                           | Description                             |
|------------------------------------------------|-----------------------------------------|
| `get_customer(customer_id)`                    | Retrieve customer by ID                 |
| `list_customers(status, limit)`                | List customers by status                |
| `update_customer(customer_id, data)`           | Update customer records                 |
| `create_ticket(customer_id, issue, priority)`  | Create support ticket                   |
| `get_customer_history(customer_id)`            | Get customer's ticket history           |
| `get_customers_with_open_tickets()`            | Get active customers with open tickets  |
| `get_premium_customers()`                      | Get premium/enterprise customers        |


## Example A2A Scenarios

### Scenario 1: Simple Query (Task Allocation)
```
Query: "Get customer information for ID 5"
Flow: Router Agent (A2A) → Customer Data Agent (A2A) → Router Agent → Response
```

### Scenario 2: Coordinated Query
```
Query: "I'm customer 12345 and need help upgrading my account"
Flow: Router Agent (A2A) → Customer Data Agent (A2A) → Support Agent (A2A) → Router Agent → Response
```

### Scenario 3: Complex Query (Negotiation)
```
Query: "Show me all active customers who have open tickets"
Flow: Router Agent (A2A) → Customer Data Agent (A2A) → Support Agent (A2A) → Router Agent
```

### Scenario 4: Escalation
```
Query: "I've been charged twice, please refund immediately!"
Flow: Router Agent (A2A) → Customer Data Agent (A2A) → Support Agent (A2A, escalation) → Router Agent → Response
```

### Scenario 5: Multi-Intent
```
Query: "Update my email to new@email.com and show my ticket history"
Flow: Router Agent (A2A) → Customer Data Agent (A2A) → Support Agent (A2A) → Router Agent → Response
```

## Running Tests

```bash
pytest tests/ -v --cov=src
```

## Agent Coordination Logs

The system provides detailed logs showing A2A message passing and agent actions:

```
[Router] Received user query: 'Get customer information for ID 5'
[Router] Sending A2A message to CustomerDataAgent
[CustomerDataAgent] Received query via A2A: {"customer_id": 5}
[CustomerDataAgent] Calling MCP: get_customer(customer_id=5)
[CustomerDataAgent] Sending A2A response to Router
[Router] Synthesizing final response from agent outputs...
```

## Dependencies


- **langchain**: LLM framework for each agent
- **gradio**: Web interface
- **python-dotenv**: Environment variable management
- **pytest**: Testing framework


## Learning Objectives Demonstrated

1. **Agent-to-agent (A2A) communication** - Explicit message passing between independent agents
2. **External tool integration via MCP** - SQLite database access through protocol
3. **Multi-agent task allocation** - Router determines which agents handle each query
4. **Context sharing via A2A** - Customer data and context passed between agents as needed
5. **Practical customer service automation** - Real-world multi-step workflows


## Running the End-to-End Demo Jupyter Notebook
Open and run `demo.ipynb` for an interactive walkthrough of all scenarios with detailed A2A coordination logs.

This will run all required scenarios and display:
- Agent coordination logs showing A2A communication
- Query analysis and routing decisions
- Final responses from the system
- Summary of all scenario results

## Conclusion

### What I Learned

### Challenges Faced
