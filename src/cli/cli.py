import argparse
import asyncio
import sys
import json
import logging
import os
from typing import Dict, Any, List, Optional, Union, Literal, cast
from mcp_host.azure_openai_host import AzureOpenAIMCPHost

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_cli_client")

class MCPCommandLineClient:
    """
    Command-line client for interacting with the MCP host.
    Supports both single query and interactive modes.
    Supports both stdio and SSE transport modes.
    """
    
    def __init__(self, transport_type: Optional[Literal["stdio", "sse"]] = None):
        """
        Initialize the MCP command-line client.
        
        Args:
            transport_type: Transport type to use ("stdio" or "sse")
        """
        self.transport_type: Literal["stdio", "sse"] = cast(
            Literal["stdio", "sse"],
            transport_type or os.getenv("MCP_TRANSPORT", "sse").lower()
        )
        self.host = AzureOpenAIMCPHost()
        
    async def initialize(self, server_command: Optional[List[str]] = None, 
                         server_url: Optional[str] = None) -> None:
        """
        Initialize the client by connecting to the MCP server.
        
        Args:
            server_command: Command to start the MCP server (for stdio transport)
            server_url: URL of the MCP server (for SSE transport)
        """
        logger.info(f"Initializing MCP client with {self.transport_type} transport")
        
        if self.transport_type == "stdio":
            if not server_command:
                raise ValueError("server_command is required for stdio transport")
            await self.host.connect_to_server(server_command=server_command, transport_type="stdio")
            
        elif self.transport_type == "sse":
            server_url = server_url or os.getenv("MCP_SERVER_URL", "http://localhost:8000")
            await self.host.connect_to_server(server_url=server_url, transport_type="sse")
            
        else:
            raise ValueError(f"Unsupported transport type: {self.transport_type}")
            
        logger.info("MCP client initialized successfully")
        
    async def run_query_with_retry(self, query: str, max_retries: int = 10) -> None:
        """
        使用重试机制运行查询
        """
        for i in range(max_retries):
            try:
                await self.run_query(query)
                break
            except RuntimeError as e:
                if "initialization" in str(e).lower() and i < max_retries - 1:
                    logger.warning(f"Initialization not complete, retrying in 1 second... ({i+1}/{max_retries})")
                    await asyncio.sleep(1)
                else:
                    raise
    async def run_query(self, query: str) -> None:
        """
        Run a query through the MCP host and display the results.
        
        Args:
            query: User query to process
        """
        logger.info(f"Running query: {query}")
        
        try:
            responses = await self.host.process_query(query)
            if responses:
                logger.info(f"Received {len(responses)} responses")
                # self._display_responses(responses)
            else:
                logger.warning("No responses received from server")
                print("No responses received from server")
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            print(f"Error: {str(e)}")
            
    def _display_responses(self, responses: List[Dict[str, Any]]) -> None:
        """
        Display the responses from the MCP host.
        
        Args:
            responses: List of responses from the MCP host
        """
        print("\n" + "="*80)
        print(f"QUERY RESULTS ({len(responses)} iterations)")
        print("="*80)
        
        for i, response in enumerate(responses):
            print(f"\n--- Iteration {response.get('iteration', i+1)} ---")
            
            if "error" in response:
                print(f"ERROR: {response['error']}")
                continue
                
            if "content" in response and response["content"]:
                print("\nASSISTANT:")
                print(response["content"])
                
            if "tool_calls" in response and response["tool_calls"]:
                print("\nTOOL CALLS:")
                for j, tool_call in enumerate(response["tool_calls"]):
                    print(f"\n  Tool {j+1}: {tool_call['tool_name']}")
                    print(f"  Arguments: {json.dumps(tool_call['tool_args'], indent=2)}")
                    print(f"  Result: {json.dumps(tool_call['tool_result'], indent=2)}")
                    
        print("\n" + "="*80)
        
    async def interactive_mode(self) -> None:
        """
        Run the client in interactive mode, accepting queries from the user.
        """
        print("\nMCP Interactive Mode")
        print("Type 'exit' or 'quit' to exit")
        print("="*80)
        
        while True:
            try:
                query = input("\nEnter your query: ")
                
                if query.lower() in ["exit", "quit"]:
                    break
                    
                if not query.strip():
                    continue
                    
                await self.run_query(query)
                
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                logger.error(f"Error in interactive mode: {str(e)}")
                print(f"Error: {str(e)}")
                
    async def close(self) -> None:
        """Close the connection to the MCP host."""
        await self.host.disconnect()
        logger.info("Closed connection to MCP host")
