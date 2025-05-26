# Python

import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
# ... other imports

async def run_client(sse_url):
    try:
        async with sse_client(sse_url) as streams:
            print("SSE connection established.")
            read_stream, write_stream = streams
            async with ClientSession(read_stream, write_stream) as session:
                print("ClientSession created.")
                try:
                    print("--> Calling session.initialize()...")
                    await session.initialize() # <----- Explicit call added here!!!
                    print("<-- session.initialize() completed.")

                    tools = await session.list_tools()
                    print(f"Tools: {tools}")
                    # Now safe to proceed with tool calls
                    print("Session initialized, safe to call tools.")



                    # Example tool call:
                    # response = await session.call_tool("some_tool", {"arg": "value"})
                    # print(f"Tool response: {response}")

                except Exception as init_error:
                    print(f"Error during session.initialize(): {init_error}")

    except Exception as conn_error:
        print(f"Connection error: {conn_error}")

# Example usage:
asyncio.run(run_client("http://localhost:8000/sse"))