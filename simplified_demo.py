#!/usr/bin/env python3
"""
Simplified MCP Demo
This script demonstrates the MCP protocol using a simplified implementation.
"""

import os
import sys
import asyncio
import argparse
import logging
from dotenv import load_dotenv
from cli.cli import MCPCommandLineClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("simplified_demo.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("simplified_demo")

async def main():
    """Run the MCP demo."""
    parser = argparse.ArgumentParser(description="MCP Demo")
    parser.add_argument("query", nargs="?", default="Find papers about machine learning",
                        help="Query to process")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="sse",
                        help="Transport type to use")
    parser.add_argument("--server-url", default=None,
                        help="URL of the MCP server (for SSE transport)")
    args = parser.parse_args()
    
    load_dotenv()
    
    try:
        logger.info(f"Using {args.transport} transport with server URL: {args.server_url or 'default'}")
        client = MCPCommandLineClient(transport_type=args.transport)
        
        await client.initialize(server_url=args.server_url)
        
        await client.run_query(args.query)
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"Error: {str(e)}")
    finally:
        if 'client' in locals():
            await client.close()
            logger.info("Closed connection to MCP host")

if __name__ == "__main__":
    asyncio.run(main())
