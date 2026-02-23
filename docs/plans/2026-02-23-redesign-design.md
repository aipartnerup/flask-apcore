# flask-apcore Redesign for apcore v0.6.0 + apcore-mcp v0.4.0

## Context

flask-apcore is a Flask extension bridging Flask applications with apcore's AI-perceivable module framework. Both upstream dependencies have released major updates:

- **apcore v0.6.0**: ExtensionManager, AsyncTaskManager, CancelToken, W3C TraceContext, Observability (Tracing/Metrics/Logger), ModuleAnnotations, SchemaExporter profiles, Executor.from_registry()
- **apcore-mcp v0.4.0**: MCPServer non-blocking wrapper, serve() hooks, metrics_collector, validate_inputs, resource handlers, report_progress/elicit helpers, health/metrics endpoints

The initial flask-apcore draft targeted apcore>=0.5.0 and apcore-mcp>=0.3.0 and did not expose most of these new features. This redesign ships as v0.1.0.

## Decision

Full restructure. Rewrite all modules and tests to leverage the complete new API surface. Keep the Scanner subsystem (Flask route auto-scanning is the core differentiator) but upgrade its output. Only support binding.yaml as the file output format.

## Architecture: Layered Thin Adapter

```
Flask App
  └─ Apcore Extension (init_app)
       ├─ ConfigLayer: APCORE_* → ApcoreSettings (frozen dataclass)
       ├─ RegistryLayer: Registry + ExtensionManager auto-assembly
       ├─ ObservabilityLayer: auto-register Tracing/Metrics/Logger middleware
       ├─ ContextBridge: Flask request → apcore Identity/Context + W3C TraceContext
       ├─ Scanner: Flask routes → ScannedModule → Registry or .binding.yaml
       └─ CLI: scan (register/generate) + serve (full apcore-mcp parameter passthrough)
```

## Project Structure

```
src/flask_apcore/
├── __init__.py              Public API: Apcore + re-export apcore core types
├── config.py                ApcoreSettings with all new config fields
├── extension.py             Layered assembly (Registry + Extensions + Observability)
├── registry.py              get_registry/get_executor + ExtensionManager integration
├── context.py               FlaskContextFactory + W3C TraceContext propagation
├── cli.py                   scan (direct register + yaml output) + serve (full params)
├── observability.py         Auto-setup Tracing/Metrics/Logger from config
├── scanners/
│   ├── __init__.py          get_scanner() factory
│   ├── base.py              ScannedModule with annotations/documentation/metadata
│   └── native.py            NativeFlaskScanner with annotation inference
├── schemas/
│   ├── __init__.py          SchemaDispatcher (3 backends)
│   ├── _constants.py        FLASK_TYPE_MAP
│   ├── pydantic_backend.py  Pydantic BaseModel → JSON Schema
│   ├── marshmallow_backend.py  marshmallow Schema → JSON Schema
│   └── typehints_backend.py    Python type hints → JSON Schema
└── output/
    ├── __init__.py          get_writer() factory
    ├── yaml_writer.py       .binding.yaml file generation
    └── registry_writer.py   Direct registration to Registry (default)
```

Removed from current codebase:
- `output/python_writer.py` (Python @module file generation)
- `schemas/yaml_backend.py` (replaced by apcore BindingLoader)

## Configuration System (config.py)

`ApcoreSettings` frozen dataclass with all APCORE_* config keys:

### Existing (retained)

| Config Key | Field | Default | Description |
|------------|-------|---------|-------------|
| APCORE_MODULE_DIR | module_dir | "apcore_modules/" | Directory for binding files |
| APCORE_MODULE_PACKAGES | module_packages | [] | Packages to scan for @module |
| APCORE_AUTO_DISCOVER | auto_discover | True | Auto-discover on init |
| APCORE_BINDING_PATTERN | binding_pattern | "*.binding.yaml" | Glob for binding files |
| APCORE_SCANNER_SOURCE | scanner_source | "auto" | auto/native/smorest/restx |
| APCORE_MIDDLEWARES | middlewares | [] | Dotted paths to middleware classes |
| APCORE_ACL_PATH | acl_path | None | Path to ACL YAML file |
| APCORE_EXECUTOR_CONFIG | executor_config | None | Executor config dict |
| APCORE_CONTEXT_FACTORY | context_factory | None | Dotted path to custom factory |

### MCP Serve

| Config Key | Field | Default | Description |
|------------|-------|---------|-------------|
| APCORE_SERVE_TRANSPORT | serve_transport | "stdio" | stdio/streamable-http/sse |
| APCORE_SERVE_HOST | serve_host | "127.0.0.1" | Host for HTTP transport |
| APCORE_SERVE_PORT | serve_port | 9100 | Port for HTTP transport |
| APCORE_SERVER_NAME | server_name | "apcore-mcp" | MCP server name |
| APCORE_SERVE_VALIDATE_INPUTS | serve_validate_inputs | False | Pre-validate tool inputs |
| APCORE_SERVE_LOG_LEVEL | serve_log_level | None | apcore-mcp logger level |

### Observability (new)

| Config Key | Field | Default | Description |
|------------|-------|---------|-------------|
| APCORE_TRACING_ENABLED | tracing_enabled | False | Enable TracingMiddleware |
| APCORE_TRACING_EXPORTER | tracing_exporter | "stdout" | stdout/memory/otlp |
| APCORE_TRACING_OTLP_ENDPOINT | tracing_otlp_endpoint | None | OTLP collector endpoint |
| APCORE_TRACING_SERVICE_NAME | tracing_service_name | "flask-apcore" | Service name for spans |
| APCORE_METRICS_ENABLED | metrics_enabled | False | Enable MetricsMiddleware |
| APCORE_METRICS_BUCKETS | metrics_buckets | None | Histogram bucket boundaries |
| APCORE_LOGGING_ENABLED | logging_enabled | False | Enable ObsLoggingMiddleware |
| APCORE_LOGGING_FORMAT | logging_format | "json" | json/text |
| APCORE_LOGGING_LEVEL | logging_level | "INFO" | Context logger level |

### Extensions (new)

| Config Key | Field | Default | Description |
|------------|-------|---------|-------------|
| APCORE_EXTENSIONS | extensions | [] | Dotted paths to extension classes |

## Extension Initialization Flow (extension.py)

```
init_app(app)
│
├─ 1. load_settings(app)          Validate all APCORE_* config
│
├─ 2. Registry()                  Create app-scoped Registry
│
├─ 3. ExtensionManager assembly
│   ├─ Load custom extensions from APCORE_EXTENSIONS
│   ├─ Register event listeners (register/unregister)
│   └─ Store reference for advanced users
│
├─ 4. Observability auto-setup
│   ├─ if tracing_enabled: create TracingMiddleware + Exporter
│   ├─ if metrics_enabled: create MetricsMiddleware + MetricsCollector
│   └─ if logging_enabled: create ObsLoggingMiddleware
│   (middlewares stored in ext_data, injected into Executor on creation)
│
├─ 5. Register CLI commands (scan + serve)
│
├─ 6. Auto-discover (if enabled)
│   ├─ Load .binding.yaml files from APCORE_MODULE_DIR
│   └─ Scan APCORE_MODULE_PACKAGES for @module functions
│
└─ 7. Store in app.extensions["apcore"]
      {registry, executor: None, settings, extension_manager,
       observability_middlewares, metrics_collector}
```

Executor remains lazily created on first `get_executor()` call, combining user middlewares + observability middlewares.

## Context Bridge (context.py)

FlaskContextFactory creates apcore Context from Flask request:

1. **Identity extraction** (priority unchanged):
   - flask-login current_user
   - g.user
   - request.authorization
   - anonymous fallback

2. **W3C TraceContext propagation** (new):
   - Extract `traceparent` header from request.headers
   - Pass to `Context.create(trace_parent=trace_parent)`
   - If absent, apcore auto-generates new trace_id

3. **push_app_context_for_module()** retained for MCP async execution.

## CLI Commands (cli.py)

### `flask apcore scan`

```
Options:
  -s, --source    auto|native|smorest|restx    (default: auto)
  -o, --output    yaml                          (optional; omit for direct registration)
  -d, --dir       PATH                          (output dir, only with --output yaml)
  --dry-run                                     (preview without action)
  --include       REGEX                         (filter module IDs)
  --exclude       REGEX                         (filter module IDs)
```

Default behavior: scan routes and register directly to Registry.
With `--output yaml`: generate .binding.yaml files.

### `flask apcore serve`

```
Options:
  --stdio              stdio transport (default)
  --http               streamable-http transport
  --host TEXT           default: APCORE_SERVE_HOST
  --port INT            default: APCORE_SERVE_PORT
  --name TEXT           default: APCORE_SERVER_NAME
  --validate-inputs     validate inputs before execution (new)
  --log-level TEXT      DEBUG|INFO|WARNING|ERROR (new)
```

`metrics_collector` automatically passed from observability config (no CLI flag needed).

## Scanner Upgrade

### ScannedModule dataclass

```python
@dataclass
class ScannedModule:
    module_id: str
    description: str                              # First line of docstring
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    tags: list[str]
    target: str                                    # "module:qualname" format
    http_method: str
    url_rule: str
    version: str = "1.0.0"
    annotations: ModuleAnnotations | None = None   # NEW
    documentation: str | None = None               # NEW (full docstring)
    metadata: dict[str, Any] = field(...)          # NEW
    warnings: list[str] = field(...)
```

### NativeFlaskScanner annotation inference

| HTTP Method | Inferred Annotations |
|-------------|---------------------|
| GET | readonly=True |
| DELETE | destructive=True |
| PUT | idempotent=True |
| POST | (none, defaults) |
| PATCH | (none, defaults) |

### Schema backends

Three backends retained (yaml_backend removed):
1. PydanticBackend (highest priority)
2. MarshmallowBackend (optional)
3. TypeHintsBackend (fallback)

## Public API (__init__.py)

```python
from flask_apcore.extension import Apcore
from apcore import module

# Re-export commonly used apcore types
from apcore import (
    Registry, Executor, Context, Identity,
    ModuleAnnotations, ModuleDescriptor,
    Middleware, ACL, Config,
)
```

## Dependency Changes

```toml
requires-python = ">=3.11"     # was >=3.10

dependencies = [
    "flask>=3.0",
    "apcore>=0.6.0",            # was >=0.5.0
    "pydantic>=2.0",
    "PyYAML>=6.0",
]

[project.optional-dependencies]
mcp = ["apcore-mcp>=0.4.0"]    # was >=0.3.0
```

## Test Strategy

All 390 existing tests rewritten. Test files:

```
tests/
├── conftest.py               Shared fixtures
├── test_config.py            All new config fields
├── test_extension.py         init_app layered assembly
├── test_registry.py          get_registry/get_executor/ExtensionManager
├── test_context.py           Identity extraction + W3C TraceContext
├── test_observability.py     Tracing/Metrics/Logger auto-setup
├── test_scanner_base.py      ScannedModule new fields + filter/dedup
├── test_scanner_native.py    NativeFlaskScanner + annotation inference
├── test_schema_dispatcher.py Backend dispatch
├── test_schema_pydantic.py
├── test_schema_marshmallow.py
├── test_schema_typehints.py
├── test_yaml_writer.py       .binding.yaml generation
├── test_registry_writer.py   Direct registry registration
├── test_cli_scan.py          scan command (default register + --output yaml)
├── test_cli_serve.py         serve command (full parameter passthrough)
└── test_integration.py       E2E pipeline
```
