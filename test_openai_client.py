#!/usr/bin/env python3
"""
Test script for Azure OpenAI client initialization.
This script tests the basic initialization of the Azure OpenAI client.
"""

import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

def main():
    """Test Azure OpenAI client initialization."""
    print("Testing Azure OpenAI client initialization...")
    
    print("Available environment variables:")
    for key in os.environ:
        if "AZURE" in key or "OPENAI" in key:
            print(f"  {key}: [REDACTED]")
    
    try:
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        print("Client initialized successfully!")
        
        print(f"Client type: {type(client)}")
        print(f"API version: {client.api_version}")
        
    except Exception as e:
        print(f"Error initializing client: {str(e)}")
        print(f"Error type: {type(e)}")
        
if __name__ == "__main__":
    main()
