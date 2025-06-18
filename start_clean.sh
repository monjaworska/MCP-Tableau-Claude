#!/bin/bash

# Tableau MCP Server startup script
cd "$(dirname "${BASH_SOURCE[0]}")"

# Activate virtual environment
if [ -f "./tableau_mcp_env/bin/activate" ]; then
    source "./tableau_mcp_env/bin/activate"
fi

# Load environment variables from .env file
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
    # Redirect status messages to stderr to avoid interfering with MCP JSON protocol
    echo "Environment loaded" >&2
else
    echo "Error: .env file not found" >&2
    exit 1
fi

# Verify required variables
if [ -z "$TABLEAU_SERVER_URL" ]; then
    echo "Error: TABLEAU_SERVER_URL not set" >&2
    exit 1
fi

# Redirect status messages to stderr to avoid interfering with MCP JSON protocol  
echo "Starting server..." >&2
echo "Server: $TABLEAU_SERVER_URL" >&2

# Start the MCP server
exec python "./tableau_mcp_server.py" 