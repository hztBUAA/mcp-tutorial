#!/usr/bin/env python3
"""
Mock MCP Demo - A simplified version of the MCP demo that uses mock implementations.
This script is for testing the MCP client and host without relying on external services.
"""

import os
import sys
import asyncio
import argparse
import logging
import json
from typing import List, Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mock_demo.log')
    ]
)
logger = logging.getLogger("mock_demo")

class MockMCPHost:
    """Mock implementation of the MCP host for testing."""
    
    def __init__(self):
        """Initialize the mock MCP host."""
        self.tools = [
            {"name": "search_papers", "description": "Search for academic papers"},
            {"name": "get_paper_details", "description": "Get details about a paper"}
        ]
        
    async def connect_to_server(self, **kwargs):
        """Mock connection to the MCP server."""
        logger.info("Connected to mock MCP server")
        
    async def process_query(self, query: str) -> List[Dict[str, Any]]:
        """Process a query and return mock responses."""
        logger.info(f"Processing query: {query}")
        
        responses = []
        
        responses.append({
            "iteration": 1,
            "role": "assistant",
            "content": "I'll search for papers about this topic.",
            "tool_calls": [
                {
                    "tool_name": "search_papers",
                    "tool_args": {"query": query, "limit": 3},
                    "tool_result": {
                        "papers": [
                            {"id": "paper1", "title": "Introduction to Machine Learning"},
                            {"id": "paper2", "title": "Deep Learning Advances"},
                            {"id": "paper3", "title": "Reinforcement Learning Applications"}
                        ]
                    }
                }
            ]
        })
        
        responses.append({
            "iteration": 2,
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "tool_name": "get_paper_details",
                    "tool_args": {"paper_id": "paper1"},
                    "tool_result": {
                        "title": "Introduction to Machine Learning",
                        "authors": ["John Smith", "Jane Doe"],
                        "abstract": "This paper provides an overview of machine learning techniques.",
                        "year": 2022
                    }
                }
            ]
        })
        
        responses.append({
            "iteration": 3,
            "role": "assistant",
            "content": f"Based on my search, I found several papers about {query}. The most relevant one is 'Introduction to Machine Learning' by John Smith and Jane Doe (2022). It provides an overview of machine learning techniques.",
            "tool_calls": None
        })
        
        return responses
        
    async def close(self):
        """Close the connection to the MCP server."""
        logger.info("Closed connection to mock MCP host")

class MockCommandLineClient:
    """Mock command-line client for testing."""
    
    def __init__(self, transport_type: Optional[str] = None):
        """Initialize the mock command-line client."""
        self.transport_type = transport_type or "sse"
        self.host = MockMCPHost()
        
    async def initialize(self, **kwargs):
        """Initialize the client."""
        logger.info(f"Initializing mock client with {self.transport_type} transport")
        await self.host.connect_to_server(**kwargs)
        logger.info("Mock client initialized successfully")
        
    async def run_query(self, query: str):
        """Run a query and display the results."""
        logger.info(f"Running query: {query}")
        
        try:
            responses = await self.host.process_query(query)
            self._display_responses(responses)
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            print(f"Error: {str(e)}")
            
    def _display_responses(self, responses: List[Dict[str, Any]]):
        """Display the responses."""
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
        
    async def interactive_mode(self):
        """Run in interactive mode."""
        print("\nMock MCP Interactive Mode")
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
                
    async def close(self):
        """Close the connection to the host."""
        await self.host.close()
        logger.info("Closed connection to mock host")

async def main():
    """Main entry point for the mock MCP demo."""
    parser = argparse.ArgumentParser(description="Mock MCP Demo")
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
        "--transport", 
        choices=["stdio", "sse"],
        default="sse",
        help="Transport type to use (stdio or sse, default: sse)"
    )
    
    args = parser.parse_args()
    
    try:
        client = MockCommandLineClient(transport_type=args.transport)
        await client.initialize()
        
        if args.interactive or not args.query:
            logger.info("Running in interactive mode")
            await client.interactive_mode()
        else:
            logger.info(f"Running single query: {args.query}")
            await client.run_query(args.query)
            
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
