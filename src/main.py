"""
Main entry point for the Multi-Agent Customer Service System.
Supports terminal mode and Gradio web interface.
"""

import argparse
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def check_environment():
    """Check that required environment variables are set."""
    if not os.getenv("OPENAI_API_KEY"):
        print("=" * 60)
        print("ERROR: OPENAI_API_KEY environment variable not set.")
        print("=" * 60)
        print("\nTo fix this:")
        print("1. Copy .env.example to .env")
        print("2. Add your OpenAI API key to the .env file")
        print("\nExample:")
        print("  OPENAI_API_KEY=sk-your-api-key-here")
        print("=" * 60)
        return False
    return True


def check_database():
    """Check that the database exists, create if not."""
    db_path = os.path.join(project_root, "data", "customers.db")
    
    if not os.path.exists(db_path):
        print("Database not found. Initializing...")
        
        # Import and run database setup
        sys.path.insert(0, os.path.join(project_root, "data"))
        from database_setup import DatabaseSetup
        
        db = DatabaseSetup(db_path)
        try:
            db.connect()
            db.create_tables()
            db.insert_sample_data()
            db.verify_data()
            print("Database initialized successfully!\n")
        finally:
            db.close()
    else:
        print(f"Database found: {db_path}")


def run_terminal_mode():
    """Run the system in interactive terminal mode."""
    from src.agents.orchestrator import create_multi_agent_system
    
    print("=" * 60)
    print("  Multi-Agent Customer Service System - Terminal Mode")
    print("  (A2A Communication)")
    print("=" * 60)
    print("\nCommands:")
    print("  'quit' or 'exit' - Stop the application")
    print("  'help'           - Show example queries")
    print("  'clear'          - Clear screen")
    print("-" * 60)
    
    # Initialize the multi-agent system
    system = create_multi_agent_system()
    
    example_queries = [
        "Get customer information for ID 5",
        "I'm customer 12345 and need help upgrading my account",
        "Show me all active customers who have open tickets",
        "I've been charged twice, please refund immediately!",
        "Update my email to new@email.com and show my ticket history",
        "What's the status of all high-priority tickets for premium customers?",
    ]
    
    while True:
        try:
            print()
            query = input("[You]: ").strip()
            
            if not query:
                continue
            
            if query.lower() in ("quit", "exit"):
                print("\nThank you for using the Customer Service System. Goodbye!")
                break
            
            if query.lower() == "help":
                print("\nExample queries you can try:")
                for i, q in enumerate(example_queries, 1):
                    print(f"  {i}. {q}")
                continue
            
            if query.lower() == "clear":
                os.system('cls' if os.name == 'nt' else 'clear')
                continue
            
            print("\nProcessing your request via A2A agents...")
            print("-" * 40)
            
            result = system.process_query(query)
            
            print(f"\n[Assistant]: {result['response']}")
            
            if result.get("agent_logs"):
                print("\nA2A Agent Coordination Log:")
                print("-" * 40)
                for log in result["agent_logs"]:
                    print(f"  {log}")
            
            if result.get("agents_used"):
                print(f"\nAgents used: {', '.join(result['agents_used'])}")
            
            print("-" * 60)
                    
        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again or type 'help' for examples.")


def run_gradio_mode():
    """Run the system with Gradio web interface."""
    from src.ui.gradio_app import create_gradio_app
    
    print("=" * 60)
    print("  Multi-Agent Customer Service System - Web Interface")
    print("  (A2A Communication)")
    print("=" * 60)
    print("\nStarting Gradio server...")
    
    port = int(os.getenv("GRADIO_PORT", "7860"))
    
    # Import theme
    import gradio as gr
    
    app = create_gradio_app()
    app.launch(
        share=False,
        server_name="127.0.0.1",
        server_port=port,
        show_error=True,
        theme=gr.themes.Ocean()
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-Agent Customer Service System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main --mode terminal    Run in terminal mode
  python -m src.main --mode gradio      Run with web interface (default)
  python -m src.main                    Run with web interface

For more information, see README.md
        """
    )
    parser.add_argument(
        "--mode",
        choices=["terminal", "gradio"],
        default="gradio",
        help="Run mode: 'terminal' for CLI or 'gradio' for web UI (default: gradio)"
    )
    
    args = parser.parse_args()
    
    print("\nMulti-Agent Customer Service System")
    print("=" * 60)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check/initialize database
    check_database()
    
    # Run in selected mode
    if args.mode == "terminal":
        run_terminal_mode()
    else:
        run_gradio_mode()


if __name__ == "__main__":
    main()