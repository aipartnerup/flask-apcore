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
- **MCP Tool Explorer** -- browser UI for inspecting modules via `flask apcore serve --explorer`
- **JWT authentication** -- protect MCP endpoints with Bearer tokens via `--jwt-secret` (apcore-mcp 0.7.0+)

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

Or use the **factory pattern**:

```python
from flask import Flask
from flask_apcore import Apcore

apcore = Apcore()

def create_app():
    app = Flask(__name__)
    # ... register routes / blueprints ...
    apcore.init_app(app)
    return app
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
  --explorer               Enable the MCP Tool Explorer UI
  --explorer-prefix TEXT   URL prefix for explorer (default: /explorer)
  --allow-execute          Allow Try-it execution in the explorer
  --jwt-secret TEXT        JWT secret key for MCP auth (HTTP only)
  --jwt-algorithm ALGO     JWT signing algorithm (default: HS256)
  --jwt-audience TEXT      Expected JWT audience claim
  --jwt-issuer TEXT        Expected JWT issuer claim
```

## Configuration

All settings use the `APCORE_` prefix in `app.config`:

```python
app.config.update(
    # Core
    APCORE_AUTO_DISCOVER=True,          # Auto-load bindings and @module packages
    APCORE_MODULE_DIR="apcore_modules/",# Directory for binding files
    APCORE_BINDING_PATTERN="*.binding.yaml",  # Glob pattern for binding files
    APCORE_MODULE_PACKAGES=[],          # Python packages to scan for @module functions
    APCORE_SCANNER_SOURCE="auto",       # Scanner: auto, native, smorest, restx

    # Middleware & Execution
    APCORE_MIDDLEWARES=[],              # Middleware dotted paths (e.g. ["myapp.mw.AuthMW"])
    APCORE_ACL_PATH=None,              # ACL file path (e.g. "acl.yaml")
    APCORE_CONTEXT_FACTORY=None,       # Custom ContextFactory dotted path
    APCORE_EXECUTOR_CONFIG=None,       # Executor config dict (passed to apcore.Config)
    APCORE_EXTENSIONS=[],              # Extension plugin dotted paths

    # MCP Server
    APCORE_SERVE_TRANSPORT="stdio",     # Transport: stdio, streamable-http, sse
    APCORE_SERVE_HOST="127.0.0.1",      # HTTP host
    APCORE_SERVE_PORT=9100,             # HTTP port
    APCORE_SERVER_NAME="apcore-mcp",    # MCP server name
    APCORE_SERVER_VERSION=None,         # MCP server version string
    APCORE_SERVE_VALIDATE_INPUTS=False, # Validate inputs against schemas
    APCORE_SERVE_LOG_LEVEL=None,        # Log level: DEBUG, INFO, WARNING, ERROR

    # Observability
    APCORE_TRACING_ENABLED=False,       # Enable distributed tracing
    APCORE_TRACING_EXPORTER="stdout",   # Exporter: stdout, memory, otlp
    APCORE_TRACING_OTLP_ENDPOINT=None,  # OTLP collector URL (e.g. "http://localhost:4317")
    APCORE_TRACING_SERVICE_NAME="flask-apcore",  # Service name for traces
    APCORE_METRICS_ENABLED=False,       # Enable metrics collection
    APCORE_METRICS_BUCKETS=None,        # Custom histogram buckets (list of floats)
    APCORE_LOGGING_ENABLED=False,       # Enable structured logging
    APCORE_LOGGING_FORMAT="json",       # Format: json, text
    APCORE_LOGGING_LEVEL="INFO",        # Level: trace, debug, info, warn, error, fatal

    # MCP Serve Explorer
    APCORE_SERVE_EXPLORER=False,             # Enable Tool Explorer UI in MCP server
    APCORE_SERVE_EXPLORER_PREFIX="/explorer", # URL prefix for explorer
    APCORE_SERVE_ALLOW_EXECUTE=False,        # Allow Try-it execution in explorer

    # JWT Authentication (apcore-mcp 0.7.0+, HTTP transports only)
    APCORE_SERVE_JWT_SECRET=None,            # JWT secret key (enables auth when set)
    APCORE_SERVE_JWT_ALGORITHM="HS256",      # Signing algorithm
    APCORE_SERVE_JWT_AUDIENCE=None,          # Expected audience claim
    APCORE_SERVE_JWT_ISSUER=None,            # Expected issuer claim
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

## MCP Tool Explorer

The MCP Tool Explorer is a browser UI provided by [apcore-mcp](https://github.com/aipartnerup/apcore-mcp) for inspecting registered modules and executing them interactively.

> **Security:** Without JWT authentication, Explorer endpoints are unauthenticated. Either enable `--jwt-secret` or only expose in development/staging environments.

```bash
flask apcore serve --http --explorer --allow-execute
```

Browse to `http://127.0.0.1:9100/explorer/` to view the interactive explorer with Try-it execution.

## JWT Authentication

Protect MCP endpoints with JWT Bearer tokens (requires `apcore-mcp>=0.7.0`, HTTP transports only):

```bash
flask apcore serve --http \
    --jwt-secret "change-me-in-production" \
    --jwt-algorithm HS256 \
    --jwt-audience my-api \
    --jwt-issuer https://auth.example.com \
    --explorer --allow-execute
```

When JWT is enabled:
- All MCP endpoints require a valid `Authorization: Bearer <token>` header
- The Explorer UI shows a token input field for authentication
- Health check (`/health`) and Explorer pages remain accessible without a token

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
