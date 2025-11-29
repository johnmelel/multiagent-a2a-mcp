"""
Main entry point for running servers.

This script provides commands to run:
- The MCP server (Model Context Protocol) for tool access
- The Gradio UI for interactive web interface
"""

import argparse
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def run_mcp_server(transport: str = "stdio", host: str = "0.0.0.0", port: int = 8080):
    """Run the MCP server."""
    try:
        from src.mcp.mcp_server import run_server, run_http_server
        
        if transport == "stdio":
            print("Starting MCP server with stdio transport...")
            print("This server will communicate via stdin/stdout (for MCP clients)")
            run_server()
        elif transport == "http":
            print(f"Starting MCP server with HTTP transport at http://{host}:{port}/mcp")
            run_http_server(host=host, port=port)
        else:
            print(f"Unknown transport: {transport}. Use 'stdio' or 'http'")
            sys.exit(1)
    except ImportError as e:
        print("Error: MCP SDK not installed. Install with: pip install 'mcp[cli]'")
        print(f"Details: {e}")
        sys.exit(1)


def run_gradio_ui(share: bool = False):
    """Run the Gradio web interface."""
    try:
        from src.ui.gradio_app import create_gradio_app
        
        print("Starting Gradio web interface...")
        app = create_gradio_app()
        app.launch(share=share, server_name="0.0.0.0")
    except ImportError as e:
        print("Error: Gradio not installed or import failed.")
        print(f"Details: {e}")
        sys.exit(1)


def run_all_servers(
    mcp_host: str = "0.0.0.0",
    mcp_port: int = 8080,
    gradio: bool = False
):
    """Run MCP HTTP server and optionally Gradio."""
    import threading
    
    print("=" * 60)
    print("Starting Multi-Agent Customer Service System")
    print("=" * 60)
    print()
    
    # Optionally start Gradio
    if gradio:
        gradio_thread = threading.Thread(
            target=run_gradio_ui,
            args=(False,),
            daemon=True
        )
        gradio_thread.start()
        print("Gradio UI starting...")
        print()
        print("=" * 60)
        print(">>> OPEN GRADIO UI AT: http://localhost:7860")
        print("=" * 60)
        print()
        import time
        time.sleep(2)
    
    # Run MCP HTTP server in main thread
    print(f"MCP Server starting on http://{mcp_host}:{mcp_port}/mcp")
    print()
    print("=" * 60)
    print("All servers are running. Press Ctrl+C to stop.")
    print("=" * 60)
    
    try:
        run_mcp_server(transport="http", host=mcp_host, port=mcp_port)
    except KeyboardInterrupt:
        print("\nShutting down servers...")


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Run MCP server and Gradio UI for the multi-agent customer service system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run MCP server with stdio (for MCP clients like Claude)
  python run_servers.py mcp
  
  # Run MCP server with HTTP transport
  python run_servers.py mcp --transport http --port 8080
  
  # Run Gradio web interface
  python run_servers.py gradio
  
  # Run all servers together
  python run_servers.py all --gradio
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # MCP server command
    mcp_parser = subparsers.add_parser("mcp", help="Run the MCP server")
    mcp_parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport type (default: stdio)"
    )
    mcp_parser.add_argument("--host", default="0.0.0.0", help="Host for HTTP transport")
    mcp_parser.add_argument("--port", type=int, default=8080, help="Port for HTTP transport")
    
    # Gradio UI command
    gradio_parser = subparsers.add_parser("gradio", help="Run the Gradio web interface")
    gradio_parser.add_argument("--share", action="store_true", help="Create public link")
    
    # All servers command
    all_parser = subparsers.add_parser("all", help="Run all servers")
    all_parser.add_argument("--mcp-host", default="0.0.0.0", help="MCP server host")
    all_parser.add_argument("--mcp-port", type=int, default=8080, help="MCP server port")
    all_parser.add_argument("--gradio", action="store_true", help="Also start Gradio UI")
    
    args = parser.parse_args()
    
    if args.command == "mcp":
        run_mcp_server(transport=args.transport, host=args.host, port=args.port)
    elif args.command == "gradio":
        run_gradio_ui(share=args.share)
    elif args.command == "all":
        run_all_servers(
            mcp_host=args.mcp_host,
            mcp_port=args.mcp_port,
            gradio=args.gradio
        )
    else:
        parser.print_help()
        print("\nNo command specified. Use one of: mcp, gradio, all")
        sys.exit(1)


if __name__ == "__main__":
    main()
