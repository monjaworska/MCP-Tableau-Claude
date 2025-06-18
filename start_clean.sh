#!/bin/bash

# Tableau MCP Server startup script
# This script loads environment variables from .env file and starts the server

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "./tableau_mcp_env/bin/activate" ]; then
    source "./tableau_mcp_env/bin/activate"
else
    echo "Error: Virtual environment not found at ./tableau_mcp_env/bin/activate" >&2
    echo "Please run: python -m venv tableau_mcp_env && source tableau_mcp_env/bin/activate && pip install -r requirements.txt" >&2
    exit 1
fi

# Load environment variables from .env file
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "Loaded environment variables from .env file"
else
    echo "Error: .env file not found!" >&2
    echo "Please create a .env file with your Tableau Server credentials." >&2
    echo "See README.md for setup instructions." >&2
    exit 1
fi

# Verify required environment variables
if [ -z "$TABLEAU_SERVER_URL" ]; then
    echo "Error: TABLEAU_SERVER_URL not set in .env file" >&2
    exit 1
fi

if [ -z "$TABLEAU_TOKEN_NAME" ] || [ -z "$TABLEAU_TOKEN_VALUE" ]; then
    if [ -z "$TABLEAU_USERNAME" ] || [ -z "$TABLEAU_PASSWORD" ]; then
        echo "Error: Either token (TABLEAU_TOKEN_NAME + TABLEAU_TOKEN_VALUE) or username/password (TABLEAU_USERNAME + TABLEAU_PASSWORD) must be set in .env file" >&2
        exit 1
    fi
fi

echo "Starting Tableau MCP Server..."
echo "Server: $TABLEAU_SERVER_URL"

# Start the MCP server
exec python "./tableau_mcp_server.py" 