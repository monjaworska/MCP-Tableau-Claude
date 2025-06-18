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
    echo "Environment loaded"
else
    echo "Error: .env file not found"
    exit 1
fi

# Verify required variables
if [ -z "$TABLEAU_SERVER_URL" ]; then
    echo "Error: TABLEAU_SERVER_URL not set"
    exit 1
fi

echo "Starting server..."
echo "Server: $TABLEAU_SERVER_URL"

# Start the MCP server
exec python "./tableau_mcp_server.py" 