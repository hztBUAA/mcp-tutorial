#!/usr/bin/env python3
"""
MCP Demo - Command-line demo for MCP protocol using Azure OpenAI.

This script demonstrates the MCP protocol by connecting an Azure OpenAI-based
MCP host to an MCP server, allowing users to query the system either in
single-query or interactive mode.

Supports both stdio and SSE transport modes for connecting to the MCP server.
"""

import os
import sys
import asyncio
import argparse
import logging
from typing import List, Optional, Literal

from cli.cli import MCPCommandLineClient
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mcp_demo.log')
    ]
)
logger = logging.getLogger("mcp_demo")

def get_server_command() -> List[str]:
    """
    Get the command to start the MCP server.
    
    Returns:
        List of command parts to start the server
    """
    server_module = "openapi_mcp_server"
    
    server_module_env = os.getenv("MCP_SERVER_MODULE")
    if server_module_env:
        server_module = server_module_env
        
    return [sys.executable, "-m", server_module]

async def main():
    """Main entry point for the MCP demo."""
    parser = argparse.ArgumentParser(description="MCP Demo using Azure OpenAI")
    parser.add_argument(
        "query", 
        nargs="?", 
        help="Query to process (if not provided, runs in interactive mode)"
    )
    parser.add_argument(
        "--interactive", 
        "-i", 
        action="store_true", 
        help="Run in interactive mode"
    )
    parser.add_argument(
        "--server-module", 
        help="Python module path to the MCP server (default: openapi_mcp_server)"
    )
    parser.add_argument(
        "--transport", 
        choices=["stdio", "sse"],
        default=os.getenv("MCP_TRANSPORT", "sse"),
        help="Transport type to use (stdio or sse, default: sse)"
    )
    parser.add_argument(
        "--server-url",
        help="URL of the MCP server (for SSE transport, default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    if args.server_module:
        os.environ["MCP_SERVER_MODULE"] = args.server_module
        
    if args.server_url:
        os.environ["MCP_SERVER_URL"] = args.server_url
        
    os.environ["MCP_TRANSPORT"] = args.transport
    
    try:
        client = MCPCommandLineClient(transport_type=args.transport, )
        
        if args.transport == "stdio":
            server_command = get_server_command()
            logger.info(f"Using stdio transport with server command: {' '.join(server_command)}")
            await client.initialize(server_command=server_command)
        else:  # SSE transport
            server_url = args.server_url or os.getenv("MCP_SERVER_URL", "http://localhost:8000")
            logger.info(f"Using SSE transport with server URL: {server_url}")
            await client.initialize(server_url=server_url)
        
        if args.interactive or not args.query:
            logger.info("Running in interactive mode")
            await client.interactive_mode()
        else:
            logger.info(f"Running single query: {args.query}")
            await client.run_query_with_retry(args.query)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"Error: {str(e)}")
    finally:
        if 'client' in locals():
            await client.close()
        
if __name__ == "__main__":
    asyncio.run(main())
