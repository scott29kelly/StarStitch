#!/usr/bin/env python3
"""
StarStitch API Entry Point
Run this script to start the FastAPI server.

Usage:
    python run_api.py                    # Start with defaults
    python run_api.py --port 8080        # Custom port
    python run_api.py --reload           # Enable hot reload
    python run_api.py --debug            # Enable debug mode
"""

import argparse
import os
import sys
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


def main():
    """Run the API server."""
    parser = argparse.ArgumentParser(
        description="StarStitch API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_api.py                    # Start with defaults (port 8000)
    python run_api.py --port 8080        # Custom port
    python run_api.py --reload           # Enable hot reload for development
    python run_api.py --debug            # Enable debug logging
    python run_api.py --host 0.0.0.0     # Listen on all interfaces
        """
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable hot reload (for development)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose logging",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)",
    )

    args = parser.parse_args()

    # Set debug environment variable if requested
    if args.debug:
        os.environ["STARSTITCH_DEBUG"] = "true"

    # Print startup banner
    print("""
    +-----------------------------------------------------------+
    |                                                           |
    |   * S T A R S T I T C H   A P I  v0.6 *                   |
    |                                                           |
    |   FastAPI Backend with WebSocket Progress Streaming       |
    |                                                           |
    +-----------------------------------------------------------+
    """)

    print(f"    Server: http://{args.host}:{args.port}")
    print(f"    Docs:   http://{args.host}:{args.port}/docs")
    print(f"    Reload: {'Enabled' if args.reload else 'Disabled'}")
    print(f"    Debug:  {'Enabled' if args.debug else 'Disabled'}")
    print()

    # Import and run uvicorn
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level="debug" if args.debug else "info",
    )


if __name__ == "__main__":
    main()
