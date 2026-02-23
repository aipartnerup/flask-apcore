# Schema Explorer & Output Formats Design

Date: 2026-02-23

## Problem

`flask apcore scan --output yaml` generates schema files, but there is no URL to view them in a browser. Schemas are only consumable by MCP clients or as static YAML files. Developers need HTTP endpoints, an HTML viewer, and additional CLI output formats.

## Decision

Implement four features in flask-apcore (not in apcore-python or apcore-mcp-python), using **Approach B: Separated Blueprint + CLI Writers** with shared serialization.

### Why flask-apcore

- Schema HTTP API and HTML page require Flask Blueprint — framework-specific.
- OpenAPI export needs HTTP path/method info — only available in flask-apcore scanners.
- `--output json/openapi` extends the existing flask-apcore CLI.
- apcore-mcp is for MCP protocol bridging only; apcore core is framework-agnostic.

## Architecture

```
src/flask_apcore/
├── serializers.py              # NEW: shared serialization (pure functions, no Flask dep)
├── output/
│   ├── __init__.py             # MODIFY: add json/openapi to get_writer()
│   ├── registry_writer.py     # MODIFY: enrich metadata with http_method, url_rule
│   ├── yaml_writer.py         # unchanged
│   ├── json_writer.py         # NEW: --output json
│   └── openapi_writer.py      # NEW: --output openapi
├── web/
│   ├── __init__.py            # NEW: create_explorer_blueprint() factory
│   ├── api.py                 # NEW: JSON API endpoints
│   └── views.py               # NEW: HTML explorer page
├── config.py                  # MODIFY: add explorer_enabled, explorer_url_prefix
├── extension.py               # MODIFY: conditionally register explorer Blueprint
├── cli.py                     # MODIFY: --output Choice adds "json", "openapi"
└── __init__.py                # unchanged
```

## Feature 1: Shared Serializers (`serializers.py`)

Pure functions, no Flask dependency. Used by both CLI writers and web endpoints.

```python
def module_to_dict(module: ScannedModule) -> dict:
    """ScannedModule -> flat dict with all fields."""

def modules_to_dicts(modules: list[ScannedModule]) -> list[dict]:
    """Batch conversion."""

def descriptor_to_dict(descriptor: ModuleDescriptor) -> dict:
    """ModuleDescriptor (from Registry) -> dict for web API."""

def descriptors_to_dicts(descriptors: list[ModuleDescriptor]) -> list[dict]:
    """Batch conversion for web API."""

def modules_to_openapi(
    modules: list[ScannedModule], *, title: str, version: str
) -> dict:
    """ScannedModule list -> OpenAPI 3.1 spec dict.
    - Each module maps to a path: {url_rule} + {http_method}
    - input_schema -> requestBody (POST/PUT/PATCH) or parameters (GET/DELETE)
    - output_schema -> responses.200.content
    - annotations -> x-apcore-annotations extension field
    - tags mapped directly
    """

def descriptors_to_openapi(
    descriptors: list[ModuleDescriptor], *, title: str, version: str
) -> dict:
    """ModuleDescriptor list -> OpenAPI 3.1 spec dict (for web API)."""
```

## Feature 2: CLI Output Formats

### `json_writer.py`

```python
class JSONWriter:
    def write(self, modules, output_dir, dry_run=False) -> list[dict]:
        """Write all modules to single {output_dir}/apcore-modules.json.
        Calls serializers.modules_to_dicts().
        """
```

Single file output (unlike YAML per-module files). JSON is typically consumed as a whole.

### `openapi_writer.py`

```python
class OpenAPIWriter:
    def write(self, modules, output_dir, dry_run=False) -> dict:
        """Write OpenAPI 3.1 spec to {output_dir}/openapi.json.
        Calls serializers.modules_to_openapi().
        """
```

### `cli.py` changes

- `--output` Choice: `["yaml", "json", "openapi"]`
- json/openapi use the same file-output branch as yaml (pass `output_dir`)

### `output/__init__.py` changes

- `get_writer()`: add `"json"` -> `JSONWriter`, `"openapi"` -> `OpenAPIWriter`

## Feature 3: Web Explorer Blueprint

### Activation

```python
APCORE_EXPLORER_ENABLED = True          # default: False
APCORE_EXPLORER_URL_PREFIX = "/apcore"  # default: "/apcore"
```

Registered conditionally in `init_app()` after CLI command registration.

### `web/api.py` — JSON API

```
GET /apcore/modules              -> module list (summary: module_id, description, tags, http_method, url_rule)
GET /apcore/modules/<module_id>  -> full module detail (input_schema, output_schema, annotations, etc.)
GET /apcore/openapi.json         -> live-generated OpenAPI 3.1 spec
```

Data source: `Registry.iter()` + `Registry.get_definition()` -> `ModuleDescriptor` -> serializers -> JSON response.

### `web/views.py` — HTML Page

```
GET /apcore/                     -> single-page HTML, inline CSS/JS, zero external deps
                                    fetches /apcore/modules on load, renders module list
                                    click module -> fetch /apcore/modules/<id> for details
                                    JSON tree display with <pre> + collapsible JS
```

## Feature 4: RegistryWriter Metadata Fix

Current: `RegistryWriter._to_function_module()` passes `mod.metadata` as-is, losing `http_method` and `url_rule`.

Fix:
```python
metadata = {
    **(mod.metadata or {}),
    "http_method": mod.http_method,
    "url_rule": mod.url_rule,
}
```

This is flask-apcore only. No upstream changes needed — apcore's `FunctionModule.metadata` is `dict[str, Any]` pass-through.

## Configuration Changes (`config.py`)

New fields in `ApcoreSettings`:
- `explorer_enabled: bool = False`
- `explorer_url_prefix: str = "/apcore"`

Config keys:
- `APCORE_EXPLORER_ENABLED`
- `APCORE_EXPLORER_URL_PREFIX`

## Files Not Changed

- `scanners/` — scan logic unchanged
- `schemas/` — schema inference unchanged
- `observability.py` — unrelated
- `context.py` — unrelated
- `registry.py` — unrelated
- `__init__.py` — web is internal, no public export needed
