#!/bin/bash
set -e

echo "=== Scanning Flask routes ==="
mkdir -p /app/apcore_modules
flask apcore scan --output yaml --dir /app/apcore_modules

echo ""
echo "=== Starting MCP server on port 9100 ==="
flask apcore serve --http --host 0.0.0.0 --port 9100 --validate-inputs --log-level DEBUG
