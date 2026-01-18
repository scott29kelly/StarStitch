#!/usr/bin/env python3
"""
StarStitch API Server Runner
Starts the FastAPI server for the StarStitch API.

Usage:
    python run_api.py                    # Start with defaults
    python run_api.py --port 3000        # Custom port
    python run_api.py --reload           # Development mode with auto-reload
"""

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="StarStitch API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_api.py                    # Start on port 8000
    python run_api.py --port 3000        # Start on port 3000
    python run_api.py --reload           # Enable auto-reload for development
    python run_api.py --host 0.0.0.0     # Listen on all interfaces
        """
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )
    
    args = parser.parse_args()
    
    # ASCII banner
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🌟  S T A R S T I T C H  API Server  v0.6              ║
    ║                                                           ║
    ║   RESTful API for AI-Powered Video Morphing               ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    logger.info(f"Starting API server on http://{args.host}:{args.port}")
    logger.info(f"API Documentation: http://localhost:{args.port}/docs")
    logger.info(f"WebSocket: ws://localhost:{args.port}/ws/render/{{job_id}}")
    
    try:
        import uvicorn
        
        uvicorn.run(
            "api.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers if not args.reload else 1,
            log_level="info",
        )
        
    except ImportError:
        logger.error("uvicorn not installed. Run: pip install uvicorn[standard]")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
