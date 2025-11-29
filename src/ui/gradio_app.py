"""
Gradio UI for the Multi-Agent Customer Service System.
Provides a web interface for interacting with agents via A2A communication.
Compatible with Gradio 6.x
"""


import gradio as gr
from typing import List, Tuple

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.agents.orchestrator import create_multi_agent_system


# Create multi-agent system once at module load
_system = None


def get_system():
    """Get or create the multi-agent system singleton."""
    global _system
    if _system is None:
        _system = create_multi_agent_system()
    return _system


def process_message(message: str, history: List[dict]) -> Tuple[str, str]:
    """
    Process a user message through the multi-agent system via A2A.
    
    Args:
        message: User's message
        history: Chat history
        
    Returns:
        Tuple of (response, agent_logs_text)
    """
    if not message.strip():
        return "Please enter a message.", "No query submitted."
    
    system = get_system()
    result = system.process_query(message)
    
    response = result.get("response", "Sorry, I couldn't process your request.")
    agent_logs = result.get("agent_logs", [])
    agents_used = result.get("agents_used", [])
    
    logs_text = "\n".join(agent_logs) if agent_logs else "No agent logs available."
    if agents_used:
        logs_text += f"\n\n[Agents used: {', '.join(agents_used)}]"
    
    return response, logs_text


def respond(message: str, history: List[dict], logs: str):
    """Handle user message and update chat."""
    if not message.strip():
        return history, "", "Please enter a message."
    
    response, logs_text = process_message(message, history)
    
    # Gradio 6.x uses dict format for messages
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": response}
    ]
    
    return history, "", logs_text


def clear_chat():
    """Clear the chat history."""
    return [], "", ""


def set_example(example: str):
    """Set example query in the input box."""
    return example


def create_gradio_app() -> gr.Blocks:
    """
    Create the Gradio application.
    
    Returns:
        Gradio Blocks application
    """
    with gr.Blocks(title="Multi-Agent Customer Service System (A2A)") as app:
        gr.Markdown("""
        # Multi-Agent Customer Service System
        ## Agent-to-Agent (A2A) Communication
        
        Welcome to our AI-powered customer service! This system uses multiple specialized agents 
        that coordinate via **A2A (Agent-to-Agent) messaging**:
        
        - **Router Agent**: Analyzes your query and coordinates responses via A2A
        - **Customer Data Agent**: Retrieves and updates customer information via MCP
        - **Support Agent**: Handles support queries, escalations, and recommendations
        
        Try one of the example queries below or type your own!
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    label="Conversation",
                    height=400
                )
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Type your query here...",
                        scale=4,
                        show_label=False,
                        container=False
                    )
                    submit_btn = gr.Button("Send", variant="primary", scale=1)
                
                clear_btn = gr.Button("Clear Chat", variant="secondary")
                
            with gr.Column(scale=1):
                gr.Markdown("### A2A Agent Coordination Logs")
                logs_display = gr.Textbox(
                    label="Agent Logs",
                    lines=15,
                    max_lines=20,
                    show_label=False,
                    interactive=False
                )
        
        gr.Markdown("### Test Scenarios & Example Queries")
        gr.Markdown("Click any scenario button to load the example query:")
        
        # Test scenarios table with inline example buttons
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("**1. Simple (Single Agent)**")
                ex1_btn = gr.Button("Get customer information for ID 5", size="sm")
            with gr.Column(scale=1):
                gr.Markdown("**2. Coordinated (Multi-Agent)**")
                ex2_btn = gr.Button("I'm customer 12345 and need help upgrading my account", size="sm")
            with gr.Column(scale=1):
                gr.Markdown("**3. Complex (Data + Support)**")
                ex3_btn = gr.Button("Show me all active customers who have open tickets", size="sm")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("**4. Escalation (Priority)**")
                ex4_btn = gr.Button("I've been charged twice, please refund immediately!", size="sm")
            with gr.Column(scale=1):
                gr.Markdown("**5. Multi-Intent (Parallel)**")
                ex5_btn = gr.Button("Update my email to new@email.com and show my ticket history", size="sm")
            with gr.Column(scale=1):
                gr.Markdown("**6. Report (Multi-Step)**")
                ex6_btn = gr.Button("What's the status of all high-priority tickets for premium customers?", size="sm")
        
        # Connect submit events
        submit_btn.click(
            respond,
            inputs=[msg_input, chatbot, logs_display],
            outputs=[chatbot, msg_input, logs_display]
        )
        
        msg_input.submit(
            respond,
            inputs=[msg_input, chatbot, logs_display],
            outputs=[chatbot, msg_input, logs_display]
        )
        
        clear_btn.click(
            clear_chat,
            outputs=[chatbot, msg_input, logs_display]
        )
        
        # Example button handlers
        ex1_btn.click(lambda: "Get customer information for ID 5", outputs=msg_input)
        ex2_btn.click(lambda: "I'm customer 12345 and need help upgrading my account", outputs=msg_input)
        ex3_btn.click(lambda: "Show me all active customers who have open tickets", outputs=msg_input)
        ex4_btn.click(lambda: "I've been charged twice, please refund immediately!", outputs=msg_input)
        ex5_btn.click(lambda: "Update my email to new@email.com and show my ticket history", outputs=msg_input)
        ex6_btn.click(lambda: "What's the status of all high-priority tickets for premium customers?", outputs=msg_input)
    
    return app


def launch_gradio_app(share: bool = False, port: int = 7860):
    """
    Launch the Gradio application.
    
    Args:
        share: Whether to create a public link
        port: Port to run on
    """
    app = create_gradio_app()
    url = f"http://127.0.0.1:{port}/"
    print("\n==============================")
    print(f"Gradio app running at: {url}")
    print("==============================\n")
    app.launch(share=share, server_name="127.0.0.1", server_port=port, theme=gr.themes.Ocean())


if __name__ == "__main__":
    launch_gradio_app()