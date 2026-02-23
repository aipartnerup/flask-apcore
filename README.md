# flask-apcore

Flask Extension for [apcore](https://github.com/aipartnerup/apcore-python) (AI-Perceivable Core) integration. Expose your Flask routes as MCP tools with auto-discovery, Pydantic schema inference, and built-in observability.

## Features

- **Route scanning** -- auto-discover Flask routes and convert them to apcore modules
- **Annotation inference** -- `GET` -> readonly, `DELETE` -> destructive, `PUT` -> idempotent
- **Pydantic schema inference** -- input/output schemas extracted from type hints automatically
- **`@module` decorator** -- define standalone AI-callable modules with full schema enforcement
- **YAML binding** -- zero-code module definitions via external `.binding.yaml` files
- **MCP server** -- stdio and streamable-http transports via `flask apcore serve`
- **Observability** -- distributed tracing, metrics, and structured JSON logging
- **Input validation** -- validate tool inputs against Pydantic schemas before execution
- **CLI-first workflow** -- `flask apcore scan` + `flask apcore serve` for zero-intrusion integration

## Requirements

- Python >= 3.11
- Flask >= 3.0

## Installation

```bash
# Core
pip install flask-apcore

# With MCP server support (required for `flask apcore serve`)
pip install flask-apcore[mcp]

# All optional extras
pip install flask-apcore[mcp,smorest,restx]
```

## Quick Start

### 1. Add Apcore to your Flask app

```python
from flask import Flask
from flask_apcore import Apcore

app = Flask(__name__)
Apcore(app)

@app.route("/greet/<name>", methods=["GET"])
def greet(name: str) -> dict:
    """Greet a user by name."""
    return {"message": f"Hello, {name}!"}
```

### 2. Scan routes and start MCP server

```bash
export FLASK_APP=app.py

# Scan Flask routes -> register as apcore modules
flask apcore scan

# Start MCP server (stdio, for Claude Desktop / Cursor)
flask apcore serve
```

That's it. Your Flask routes are now MCP tools.

### 3. Connect an MCP client

For **Claude Desktop**, add to your config:

```json
{
  "mcpServers": {
    "my-flask-app": {
      "command": "flask",
      "args": ["apcore", "serve"],
      "env": { "FLASK_APP": "app.py" }
    }
  }
}
```

For **HTTP transport** (remote access):

```bash
flask apcore serve --http --host 0.0.0.0 --port 9100
```

## Integration Paths

flask-apcore supports three ways to define AI-perceivable modules:

### Route Scanning (zero-intrusion)

Scan existing Flask routes without modifying any code:

```bash
# Direct registration (in-memory)
flask apcore scan

# Generate YAML binding files (persistent)
flask apcore scan --output yaml --dir ./apcore_modules

# Preview without side effects
flask apcore scan --dry-run

# Filter routes by regex
flask apcore scan --include "user.*" --exclude ".*delete"
```

### `@module` Decorator (precise control)

Define standalone modules with full schema enforcement:

```python
from flask_apcore import Apcore, module
from pydantic import BaseModel

class SummaryResult(BaseModel):
    total: int
    active: int

@module(id="user_stats.v1", tags=["analytics"])
def user_stats() -> SummaryResult:
    """Return user statistics."""
    return SummaryResult(total=100, active=42)

app = Flask(__name__)
app.config["APCORE_MODULE_PACKAGES"] = ["myapp.modules"]
Apcore(app)
```

### YAML Binding (zero-code)

Define modules externally in `.binding.yaml` files:

```yaml
# apcore_modules/greet.binding.yaml
bindings:
  - module_id: greet.get
    target: app.greet
    description: "Greet a user by name"
```

Set `APCORE_AUTO_DISCOVER=True` (default) to load bindings on startup.

## CLI Commands

### `flask apcore scan`

Scan Flask routes and generate apcore module definitions.

```
Options:
  -s, --source [auto|native|smorest|restx]  Scanner source (default: auto)
  -o, --output [yaml]                       Output format; omit for direct registration
  -d, --dir PATH                            Output directory (default: APCORE_MODULE_DIR)
  --dry-run                                 Preview without writing or registering
  --include REGEX                           Only include matching module IDs
  --exclude REGEX                           Exclude matching module IDs
```

### `flask apcore serve`

Start an MCP server exposing registered modules as tools.

```
Options:
  --stdio                  Use stdio transport (default)
  --http                   Use streamable-http transport
  --host TEXT              HTTP host (default: 127.0.0.1)
  -p, --port INT           HTTP port (default: 9100)
  --name TEXT              MCP server name (default: apcore-mcp)
  --validate-inputs        Validate tool inputs against schemas
  --log-level [DEBUG|INFO|WARNING|ERROR]
```

## Configuration

All settings use the `APCORE_` prefix in `app.config`:

```python
app.config.update(
    # Core
    APCORE_AUTO_DISCOVER=True,          # Auto-load bindings and @module packages
    APCORE_MODULE_DIR="apcore_modules/",# Directory for binding files
    APCORE_MODULE_PACKAGES=[],          # Python packages to scan for @module functions
    APCORE_SCANNER_SOURCE="auto",       # Scanner: auto, native, smorest, restx

    # MCP Server
    APCORE_SERVE_TRANSPORT="stdio",     # Transport: stdio, streamable-http, sse
    APCORE_SERVE_HOST="127.0.0.1",      # HTTP host
    APCORE_SERVE_PORT=9100,             # HTTP port
    APCORE_SERVER_NAME="apcore-mcp",    # MCP server name
    APCORE_SERVE_VALIDATE_INPUTS=False, # Validate inputs against schemas

    # Observability
    APCORE_TRACING_ENABLED=False,       # Enable distributed tracing
    APCORE_TRACING_EXPORTER="stdout",   # Exporter: stdout, memory, otlp
    APCORE_METRICS_ENABLED=False,       # Enable metrics collection
    APCORE_LOGGING_ENABLED=False,       # Enable structured logging
    APCORE_LOGGING_FORMAT="json",       # Format: json, text
)
```

## Observability

Enable tracing, metrics, and structured logging:

```python
app.config.update(
    APCORE_TRACING_ENABLED=True,
    APCORE_TRACING_EXPORTER="otlp",
    APCORE_TRACING_OTLP_ENDPOINT="http://localhost:4317",
    APCORE_METRICS_ENABLED=True,
    APCORE_LOGGING_ENABLED=True,
    APCORE_LOGGING_FORMAT="json",
)
```

These are wired into the apcore Executor as middleware, providing tracing spans, latency metrics, and structured log entries for every module execution.

## Docker Demo

A complete runnable demo is included in `examples/demo/`. It demonstrates the full pipeline: Flask CRUD routes with Pydantic schemas, route scanning, annotation inference, `@module` registration, MCP server, and observability.

```bash
cd examples/demo
docker compose up --build
```

After startup you'll see:

```
=== Scanning Flask routes ===
[flask-apcore] Found 5 API routes.
[flask-apcore] Generated 5 module definitions.

=== Starting MCP server on port 9100 ===
[flask-apcore] Starting MCP server 'task-manager-mcp' via streamable-http...
[flask-apcore] 6 modules registered.
INFO:     Uvicorn running on http://0.0.0.0:9100
```

Verify:

```bash
curl http://localhost:9100/health
# {"status":"ok","uptime_seconds":5.2,"module_count":6}
```

See [examples/demo/README.md](examples/demo/README.md) for full details.

## Public API

```python
from flask_apcore import (
    Apcore,             # Flask Extension
    module,             # @module decorator
    Registry,           # Module registry
    Executor,           # Module executor with middleware pipeline
    Context,            # Request context
    Identity,           # User identity
    ACL,                # Access control list
    Config,             # Executor configuration
    Middleware,          # Middleware base class
    ModuleAnnotations,  # Behavioral hints (readonly, destructive, etc.)
    ModuleDescriptor,   # Module metadata
)
```

## Development

```bash
git clone https://github.com/aipartnerup/flask-apcore.git
cd flask-apcore
pip install -e ".[dev,mcp]"
pytest
```

## License

Apache-2.0
