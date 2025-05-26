# openapi-mcp-server MCP server

For openapi api abilities exports.

## Configuration
```env
# credentials
BOR_ACCESS_KEY=your_access_key_here  # Required
BOR_BASE_URL=https://openapi.dp.tech  # Optional，default base_url：https://openapi.dp.tech
```


## Components

### Resources

The server implements a simple note storage system with:
- Custom note:// URI scheme for accessing individual notes
- Each note resource has a name, description and text/plain mimetype

### Prompts

The server provides a single prompt:
- summarize-notes: Creates summaries of all stored notes
  - Optional "style" argument to control detail level (brief/detailed)
  - Generates prompt combining all current notes with style preference

### Tools

The server implements one tool:
- add-note: Adds a new note to the server
  - Takes "name" and "content" as required string arguments
  - Updates server state and notifies clients of resource changes

## Configuration

[TODO: Add configuration details specific to your implementation]

## Quickstart

### Install

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  ```
  "mcpServers": {
    "openapi-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/hzt/MCP/openapi-mcp-server",
        "run",
        "openapi-mcp-server"
      ]
    }
  }
  ```
</details>

<details>
  <summary>Published Servers Configuration</summary>
  ```
  "mcpServers": {
    "openapi-mcp-server": {
      "command": "uvx",
      "args": [
        "openapi-mcp-server"
      ]
    }
  }
  ```
</details>

## MCP Demo

The MCP Demo provides a command-line interface for interacting with the MCP server using Azure OpenAI as the MCP host.

### Installation

1. Clone the repository:
```bash
git clone https://github.com/dptech-corp/hztBUAA-project-2.git
cd hztBUAA-project-2
```

2. Install dependencies:
```bash
pip install -e .
```

3. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Edit `.env` to add your Azure OpenAI API key and other configuration

```bash
cp .env.example .env
# Edit .env with your preferred editor
```

### Usage

The MCP Demo can be run in two modes and supports two transport types:

#### Transport Types

- **SSE Transport** (default): Connects to a running MCP server via HTTP/SSE
- **stdio Transport**: Starts the MCP server as a subprocess and communicates via stdio

#### Single Query Mode

```bash
# Using default SSE transport
python mcp_demo.py "Your query here"

# Using stdio transport
python mcp_demo.py --transport stdio "Your query here"

# Specifying a custom server URL for SSE transport
python mcp_demo.py --server-url http://localhost:8000 "Your query here"
```

Example:
```bash
python mcp_demo.py "Find papers about machine learning"
```

#### Interactive Mode

```bash
# Using default SSE transport
python mcp_demo.py --interactive
# or simply
python mcp_demo.py

# Using stdio transport
python mcp_demo.py --transport stdio --interactive
```

This will start an interactive session where you can enter multiple queries.

### Configuration

The MCP Demo uses the following environment variables:

```
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_MODEL=gpt-4
AZURE_OPENAI_DEPLOYMENT=your-deployment-name

# MCP Configuration
MCP_SERVER_MODULE=openapi_mcp_server
MAX_ITERATIONS=10
TEMPERATURE=0.7

# Bohrium API Configuration (used by MCP server)
BOR_ACCESS_KEY=your_bohrium_api_key  # Get from bohrium.com
BOR_BASE_URL=https://openapi.dp.tech  # Default Bohrium API base URL
```

## Development

### Building and Publishing

To prepare the package for distribution:

1. Sync dependencies and update lockfile:
```bash
uv sync
```

2. Build package distributions:
```bash
uv build
```

This will create source and wheel distributions in the `dist/` directory.

3. Publish to PyPI:
```bash
uv publish
```

Note: You'll need to set PyPI credentials via environment variables or command flags:
- Token: `--token` or `UV_PUBLISH_TOKEN`
- Or username/password: `--username`/`UV_PUBLISH_USERNAME` and `--password`/`UV_PUBLISH_PASSWORD`

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).


You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /home/hzt/MCP/openapi-mcp-server run openapi-mcp-server
```


Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.
