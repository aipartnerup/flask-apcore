# flask-apcore v0.1.0 Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Full restructure of flask-apcore to leverage apcore v0.6.0 and apcore-mcp v0.4.0 — new observability, extensions, TraceContext, annotations, and full MCP parameter passthrough.

**Architecture:** Layered thin adapter. Extension init_app() orchestrates Config → Registry → ExtensionManager → Observability → CLI → Auto-discover. Scanner subsystem retained but upgraded with ModuleAnnotations and dual output (direct Registry registration + YAML). Only binding.yaml file output (Python writer removed).

**Tech Stack:** Flask>=3.0, apcore>=0.6.0, apcore-mcp>=0.4.0 (optional), pydantic>=2.0, PyYAML>=6.0, Python>=3.11

**Reference docs:**
- Design: `docs/plans/2026-02-23-redesign-design.md`
- apcore source: `../apcore-python/src/apcore/`
- apcore-mcp source: `../apcore-mcp-python/src/apcore_mcp/`

---

## Phase 1: Foundation

### Task 1: Clean slate and update pyproject.toml

**Files:**
- Modify: `pyproject.toml`
- Delete: `src/flask_apcore/output/python_writer.py`
- Delete: `src/flask_apcore/schemas/yaml_backend.py`
- Delete: all files under `tests/` (will be rewritten)
- Delete: `planning/` directory (obsolete)

**Step 1: Update pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "flask-apcore"
version = "0.1.0"
description = "Flask Extension for apcore AI-Perceivable Core integration"
requires-python = ">=3.11"
license = "MIT"
authors = [
    { name = "aipartnerup", email = "tercel.yi@gmail.com" },
]
dependencies = [
    "flask>=3.0",
    "apcore>=0.6.0",
    "pydantic>=2.0",
    "PyYAML>=6.0",
]

[project.optional-dependencies]
smorest = ["flask-smorest>=0.42"]
restx = ["flask-restx>=1.0"]
mcp = ["apcore-mcp>=0.4.0"]
dev = [
    "pytest>=7.0",
    "pytest-flask>=1.0",
    "ruff>=0.1",
    "mypy>=1.0",
    "pre-commit>=3.0",
    "coverage>=7.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/flask_apcore"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
src = ["src"]
target-version = "py311"
line-length = 120

[tool.mypy]
python_version = "3.11"
strict = true
```

**Step 2: Delete obsolete files**

```bash
rm -f src/flask_apcore/output/python_writer.py
rm -f src/flask_apcore/schemas/yaml_backend.py
rm -rf tests/
rm -rf planning/
mkdir tests
```

**Step 3: Create empty placeholder files for new modules**

```bash
touch src/flask_apcore/observability.py
touch src/flask_apcore/output/registry_writer.py
```

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: clean slate for v0.1.0 redesign

Remove python_writer, yaml_backend, all tests, planning dir.
Bump deps: apcore>=0.6.0, apcore-mcp>=0.4.0, python>=3.11."
```

---

### Task 2: Config system (config.py)

**Files:**
- Rewrite: `src/flask_apcore/config.py`
- Create: `tests/test_config.py`

**Step 1: Write failing tests for config**

```python
# tests/test_config.py
"""Tests for ApcoreSettings and load_settings()."""
from __future__ import annotations

import pytest
from flask import Flask

from flask_apcore.config import ApcoreSettings, load_settings


@pytest.fixture()
def app():
    return Flask(__name__)


class TestDefaults:
    """load_settings() returns correct defaults when no config set."""

    def test_default_settings(self, app):
        s = load_settings(app)
        assert isinstance(s, ApcoreSettings)
        assert s.module_dir == "apcore_modules/"
        assert s.auto_discover is True
        assert s.serve_transport == "stdio"
        assert s.serve_host == "127.0.0.1"
        assert s.serve_port == 9100
        assert s.server_name == "apcore-mcp"
        assert s.binding_pattern == "*.binding.yaml"
        assert s.scanner_source == "auto"
        assert s.module_packages == []
        assert s.middlewares == []
        assert s.acl_path is None
        assert s.context_factory is None
        assert s.server_version is None
        assert s.executor_config is None
        assert s.extensions == []
        # Serve new
        assert s.serve_validate_inputs is False
        assert s.serve_log_level is None
        # Observability
        assert s.tracing_enabled is False
        assert s.tracing_exporter == "stdout"
        assert s.tracing_otlp_endpoint is None
        assert s.tracing_service_name == "flask-apcore"
        assert s.metrics_enabled is False
        assert s.metrics_buckets is None
        assert s.logging_enabled is False
        assert s.logging_format == "json"
        assert s.logging_level == "INFO"


class TestServeSettings:
    def test_valid_transport(self, app):
        for t in ("stdio", "streamable-http", "sse"):
            app.config["APCORE_SERVE_TRANSPORT"] = t
            s = load_settings(app)
            assert s.serve_transport == t

    def test_invalid_transport(self, app):
        app.config["APCORE_SERVE_TRANSPORT"] = "websocket"
        with pytest.raises(ValueError, match="APCORE_SERVE_TRANSPORT"):
            load_settings(app)

    def test_port_bounds(self, app):
        app.config["APCORE_SERVE_PORT"] = 0
        with pytest.raises(ValueError, match="APCORE_SERVE_PORT"):
            load_settings(app)

        app.config["APCORE_SERVE_PORT"] = 65536
        with pytest.raises(ValueError, match="APCORE_SERVE_PORT"):
            load_settings(app)

    def test_validate_inputs(self, app):
        app.config["APCORE_SERVE_VALIDATE_INPUTS"] = True
        s = load_settings(app)
        assert s.serve_validate_inputs is True

    def test_validate_inputs_invalid(self, app):
        app.config["APCORE_SERVE_VALIDATE_INPUTS"] = "yes"
        with pytest.raises(ValueError, match="APCORE_SERVE_VALIDATE_INPUTS"):
            load_settings(app)

    def test_log_level_valid(self, app):
        app.config["APCORE_SERVE_LOG_LEVEL"] = "DEBUG"
        s = load_settings(app)
        assert s.serve_log_level == "DEBUG"

    def test_log_level_invalid(self, app):
        app.config["APCORE_SERVE_LOG_LEVEL"] = "VERBOSE"
        with pytest.raises(ValueError, match="APCORE_SERVE_LOG_LEVEL"):
            load_settings(app)


class TestObservabilitySettings:
    def test_tracing_enabled(self, app):
        app.config["APCORE_TRACING_ENABLED"] = True
        s = load_settings(app)
        assert s.tracing_enabled is True

    def test_tracing_exporter_valid(self, app):
        for exp in ("stdout", "memory", "otlp"):
            app.config["APCORE_TRACING_EXPORTER"] = exp
            s = load_settings(app)
            assert s.tracing_exporter == exp

    def test_tracing_exporter_invalid(self, app):
        app.config["APCORE_TRACING_EXPORTER"] = "jaeger"
        with pytest.raises(ValueError, match="APCORE_TRACING_EXPORTER"):
            load_settings(app)

    def test_metrics_enabled(self, app):
        app.config["APCORE_METRICS_ENABLED"] = True
        s = load_settings(app)
        assert s.metrics_enabled is True

    def test_metrics_buckets(self, app):
        buckets = [0.1, 0.5, 1.0]
        app.config["APCORE_METRICS_BUCKETS"] = buckets
        s = load_settings(app)
        assert s.metrics_buckets == buckets

    def test_logging_format_valid(self, app):
        for fmt in ("json", "text"):
            app.config["APCORE_LOGGING_FORMAT"] = fmt
            s = load_settings(app)
            assert s.logging_format == fmt

    def test_logging_format_invalid(self, app):
        app.config["APCORE_LOGGING_FORMAT"] = "xml"
        with pytest.raises(ValueError, match="APCORE_LOGGING_FORMAT"):
            load_settings(app)

    def test_logging_level_valid(self, app):
        for lvl in ("trace", "debug", "info", "warn", "error", "fatal"):
            app.config["APCORE_LOGGING_LEVEL"] = lvl
            s = load_settings(app)
            assert s.logging_level == lvl

    def test_logging_level_invalid(self, app):
        app.config["APCORE_LOGGING_LEVEL"] = "verbose"
        with pytest.raises(ValueError, match="APCORE_LOGGING_LEVEL"):
            load_settings(app)


class TestExtensionsSettings:
    def test_extensions_default(self, app):
        s = load_settings(app)
        assert s.extensions == []

    def test_extensions_valid(self, app):
        app.config["APCORE_EXTENSIONS"] = ["myapp.ext.MyExtension"]
        s = load_settings(app)
        assert s.extensions == ["myapp.ext.MyExtension"]

    def test_extensions_invalid_type(self, app):
        app.config["APCORE_EXTENSIONS"] = "not_a_list"
        with pytest.raises(ValueError, match="APCORE_EXTENSIONS"):
            load_settings(app)


class TestExistingSettings:
    """Ensure existing settings still work."""

    def test_module_dir(self, app):
        app.config["APCORE_MODULE_DIR"] = "/custom/path"
        s = load_settings(app)
        assert s.module_dir == "/custom/path"

    def test_module_dir_invalid(self, app):
        app.config["APCORE_MODULE_DIR"] = 123
        with pytest.raises(ValueError, match="APCORE_MODULE_DIR"):
            load_settings(app)

    def test_scanner_source(self, app):
        app.config["APCORE_SCANNER_SOURCE"] = "native"
        s = load_settings(app)
        assert s.scanner_source == "native"

    def test_scanner_source_invalid(self, app):
        app.config["APCORE_SCANNER_SOURCE"] = "fastapi"
        with pytest.raises(ValueError, match="APCORE_SCANNER_SOURCE"):
            load_settings(app)

    def test_acl_path(self, app):
        app.config["APCORE_ACL_PATH"] = "/etc/acl.yaml"
        s = load_settings(app)
        assert s.acl_path == "/etc/acl.yaml"

    def test_middlewares(self, app):
        app.config["APCORE_MIDDLEWARES"] = ["myapp.mid.Log"]
        s = load_settings(app)
        assert s.middlewares == ["myapp.mid.Log"]

    def test_frozen(self, app):
        s = load_settings(app)
        with pytest.raises(AttributeError):
            s.module_dir = "other"  # type: ignore[misc]
```

**Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_config.py -v
```

**Step 3: Implement config.py**

Rewrite `src/flask_apcore/config.py` with the full ApcoreSettings dataclass including all new fields (serve_validate_inputs, serve_log_level, tracing_enabled, tracing_exporter, tracing_otlp_endpoint, tracing_service_name, metrics_enabled, metrics_buckets, logging_enabled, logging_format, logging_level, extensions) and validation in load_settings().

Key validation rules:
- `serve_validate_inputs`: bool
- `serve_log_level`: None or one of DEBUG/INFO/WARNING/ERROR/CRITICAL
- `tracing_enabled/metrics_enabled/logging_enabled`: bool
- `tracing_exporter`: one of stdout/memory/otlp
- `tracing_service_name`: non-empty string
- `metrics_buckets`: None or list of floats
- `logging_format`: one of json/text
- `logging_level`: one of trace/debug/info/warn/error/fatal
- `extensions`: list of strings

**Step 4: Run tests — expect PASS**

```bash
pytest tests/test_config.py -v
```

**Step 5: Commit**

```bash
git add src/flask_apcore/config.py tests/test_config.py
git commit -m "feat: rewrite config.py with all v0.6.0 settings"
```

---

### Task 3: Test fixtures (conftest.py)

**Files:**
- Create: `tests/conftest.py`

**Step 1: Write conftest.py**

```python
# tests/conftest.py
"""Shared test fixtures for flask-apcore."""
from __future__ import annotations

import pytest
from flask import Flask


@pytest.fixture()
def app(tmp_path):
    """Minimal Flask app with APCORE_MODULE_DIR pointed to tmp_path."""
    a = Flask(__name__)
    a.config["TESTING"] = True
    a.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
    a.config["APCORE_AUTO_DISCOVER"] = False
    return a


@pytest.fixture()
def app_ctx(app):
    """Push an application context."""
    with app.app_context() as ctx:
        yield ctx


@pytest.fixture()
def initialized_app(app):
    """Flask app with Apcore initialized (auto-discover off)."""
    from flask_apcore import Apcore

    Apcore(app)
    return app
```

**Step 2: Verify conftest loads**

```bash
pytest tests/test_config.py -v --co
```

**Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add shared conftest fixtures"
```

---

## Phase 2: Core Infrastructure

### Task 4: Observability module (observability.py)

**Files:**
- Rewrite: `src/flask_apcore/observability.py`
- Create: `tests/test_observability.py`

**Step 1: Write failing tests**

```python
# tests/test_observability.py
"""Tests for observability auto-setup."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from flask_apcore.config import ApcoreSettings, load_settings
from flask_apcore.observability import setup_observability


def _make_settings(**overrides) -> ApcoreSettings:
    """Create ApcoreSettings with defaults + overrides via load_settings."""
    from flask import Flask

    app = Flask(__name__)
    for k, v in overrides.items():
        app.config[f"APCORE_{k.upper()}"] = v
    return load_settings(app)


class TestSetupObservability:
    def test_nothing_enabled(self):
        settings = _make_settings()
        ext_data: dict = {}
        setup_observability(settings, ext_data)
        assert ext_data["observability_middlewares"] == []
        assert ext_data.get("metrics_collector") is None

    def test_tracing_stdout(self):
        settings = _make_settings(tracing_enabled=True, tracing_exporter="stdout")
        ext_data: dict = {}
        setup_observability(settings, ext_data)
        mws = ext_data["observability_middlewares"]
        assert len(mws) == 1
        assert type(mws[0]).__name__ == "TracingMiddleware"

    def test_tracing_memory(self):
        settings = _make_settings(tracing_enabled=True, tracing_exporter="memory")
        ext_data: dict = {}
        setup_observability(settings, ext_data)
        assert len(ext_data["observability_middlewares"]) == 1

    def test_metrics_enabled(self):
        settings = _make_settings(metrics_enabled=True)
        ext_data: dict = {}
        setup_observability(settings, ext_data)
        mws = ext_data["observability_middlewares"]
        assert len(mws) == 1
        assert type(mws[0]).__name__ == "MetricsMiddleware"
        assert ext_data["metrics_collector"] is not None

    def test_logging_enabled(self):
        settings = _make_settings(logging_enabled=True)
        ext_data: dict = {}
        setup_observability(settings, ext_data)
        mws = ext_data["observability_middlewares"]
        assert len(mws) == 1
        assert type(mws[0]).__name__ == "ObsLoggingMiddleware"

    def test_all_enabled(self):
        settings = _make_settings(
            tracing_enabled=True,
            metrics_enabled=True,
            logging_enabled=True,
        )
        ext_data: dict = {}
        setup_observability(settings, ext_data)
        mws = ext_data["observability_middlewares"]
        assert len(mws) == 3
        names = [type(m).__name__ for m in mws]
        assert "TracingMiddleware" in names
        assert "MetricsMiddleware" in names
        assert "ObsLoggingMiddleware" in names

    def test_metrics_custom_buckets(self):
        settings = _make_settings(
            metrics_enabled=True,
            metrics_buckets=[0.1, 0.5, 1.0],
        )
        ext_data: dict = {}
        setup_observability(settings, ext_data)
        collector = ext_data["metrics_collector"]
        assert collector is not None
```

**Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_observability.py -v
```

**Step 3: Implement observability.py**

```python
# src/flask_apcore/observability.py
"""Observability auto-setup from APCORE_* config."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask_apcore.config import ApcoreSettings

logger = logging.getLogger("flask_apcore")


def setup_observability(settings: ApcoreSettings, ext_data: dict[str, Any]) -> None:
    """Create observability middlewares based on config and store in ext_data."""
    middlewares: list[Any] = []

    if settings.tracing_enabled:
        exporter = _create_tracing_exporter(settings)
        from apcore import TracingMiddleware

        middlewares.append(TracingMiddleware(exporter=exporter))
        logger.debug("TracingMiddleware enabled (exporter=%s)", settings.tracing_exporter)

    if settings.metrics_enabled:
        from apcore import MetricsCollector, MetricsMiddleware

        kwargs: dict[str, Any] = {}
        if settings.metrics_buckets is not None:
            kwargs["buckets"] = settings.metrics_buckets
        collector = MetricsCollector(**kwargs)
        middlewares.append(MetricsMiddleware(collector=collector))
        ext_data["metrics_collector"] = collector
        logger.debug("MetricsMiddleware enabled")

    if settings.logging_enabled:
        from apcore import ObsLoggingMiddleware

        middlewares.append(ObsLoggingMiddleware())
        logger.debug("ObsLoggingMiddleware enabled")

    ext_data["observability_middlewares"] = middlewares


def _create_tracing_exporter(settings: ApcoreSettings) -> Any:
    """Create the appropriate span exporter based on config."""
    exporter_type = settings.tracing_exporter

    if exporter_type == "stdout":
        from apcore import StdoutExporter

        return StdoutExporter()
    elif exporter_type == "memory":
        from apcore import InMemoryExporter

        return InMemoryExporter()
    elif exporter_type == "otlp":
        from apcore import OTLPExporter

        kwargs: dict[str, Any] = {}
        if settings.tracing_otlp_endpoint is not None:
            kwargs["endpoint"] = settings.tracing_otlp_endpoint
        if settings.tracing_service_name:
            kwargs["service_name"] = settings.tracing_service_name
        return OTLPExporter(**kwargs)
    else:
        from apcore import StdoutExporter

        return StdoutExporter()
```

**Step 4: Run tests — expect PASS**

```bash
pytest tests/test_observability.py -v
```

**Step 5: Commit**

```bash
git add src/flask_apcore/observability.py tests/test_observability.py
git commit -m "feat: add observability auto-setup module"
```

---

### Task 5: Registry module (registry.py)

**Files:**
- Rewrite: `src/flask_apcore/registry.py`
- Create: `tests/test_registry.py`

**Step 1: Write failing tests**

Test get_registry(), get_executor() with observability middleware injection, and get_context_factory(). Tests should verify:
- get_registry() returns the registry from app.extensions
- get_registry() raises RuntimeError when not initialized
- get_executor() lazily creates Executor with user + observability middlewares
- get_executor() caches the executor
- get_context_factory() returns FlaskContextFactory by default
- get_context_factory() resolves custom dotted path

**Step 2: Implement registry.py**

Keep the existing structure but:
- When creating Executor, merge `_resolve_middlewares(settings.middlewares)` + `ext_data["observability_middlewares"]`
- Store `extension_manager` in ext_data
- Use `from apcore import Executor` (same as before)

**Step 3: Run tests — expect PASS**

**Step 4: Commit**

```bash
git commit -m "feat: rewrite registry.py with observability middleware injection"
```

---

### Task 6: Context bridge (context.py)

**Files:**
- Rewrite: `src/flask_apcore/context.py`
- Create: `tests/test_context.py`

**Step 1: Write failing tests**

Test FlaskContextFactory:
- Anonymous context when no request
- flask-login identity extraction
- g.user identity extraction
- request.authorization identity extraction
- W3C traceparent header extraction → TraceParent passed to Context.create()
- Missing traceparent → no trace_parent arg (apcore generates new trace_id)
- push_app_context_for_module() retained

Key test for TraceContext:

```python
def test_traceparent_extraction(self, app):
    factory = FlaskContextFactory()
    with app.test_request_context(
        headers={"traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"}
    ):
        from flask import request
        ctx = factory.create_context(request)
        assert ctx.trace_id == "0af7651916cd43dd8448eb211c80319c"
```

**Step 2: Implement context.py**

Same structure as current but add TraceContext extraction:

```python
from apcore import TraceContext

# In create_context():
trace_parent = None
if request is not None:
    headers = dict(request.headers)
    trace_parent = TraceContext.extract(headers)

return Context.create(identity=identity, trace_parent=trace_parent)
```

**Step 3: Run tests — expect PASS**

**Step 4: Commit**

```bash
git commit -m "feat: rewrite context.py with W3C TraceContext propagation"
```

---

## Phase 3: Extension

### Task 7: Extension class (extension.py)

**Files:**
- Rewrite: `src/flask_apcore/extension.py`
- Create: `tests/test_extension.py`

**Step 1: Write failing tests**

Test the full init_app flow:
- Direct init: `Apcore(app)`
- Factory pattern: `Apcore().init_app(app)`
- Config validation runs
- Registry created and stored in app.extensions
- ExtensionManager created and stored
- CLI commands registered
- Auto-discover disabled: no bindings loaded
- Auto-discover enabled with tmp module_dir: bindings loaded
- Observability middlewares created when enabled
- get_registry() and get_executor() convenience methods

**Step 2: Implement extension.py**

Follow the init_app flow from the design doc. Key changes from current:
- Create ExtensionManager and store it
- Call setup_observability()
- Store metrics_collector separately
- ExtensionManager stored in ext_data

```python
from apcore import Registry, ExtensionManager
from flask_apcore.config import load_settings
from flask_apcore.observability import setup_observability
from flask_apcore.registry import get_executor, get_registry
```

**Step 3: Run tests — expect PASS**

**Step 4: Commit**

```bash
git commit -m "feat: rewrite extension.py with layered init_app flow"
```

---

## Phase 4: Scanner

### Task 8: Scanner base (scanners/base.py)

**Files:**
- Rewrite: `src/flask_apcore/scanners/base.py`
- Create: `tests/test_scanner_base.py`

**Step 1: Write failing tests**

Test ScannedModule dataclass:
- All fields including new: annotations, documentation, metadata
- Default values
- BaseScanner.filter_modules() with include/exclude regex
- BaseScanner._deduplicate_ids()

```python
from apcore import ModuleAnnotations

def test_scanned_module_with_annotations():
    m = ScannedModule(
        module_id="users.get",
        description="Get user",
        input_schema={},
        output_schema={},
        tags=["users"],
        target="myapp.views:get_user",
        http_method="GET",
        url_rule="/users/<int:id>",
        annotations=ModuleAnnotations(readonly=True),
        documentation="Get a user by ID.\n\nReturns full user profile.",
        metadata={"source": "native"},
    )
    assert m.annotations.readonly is True
    assert m.documentation is not None
    assert m.metadata["source"] == "native"
```

**Step 2: Implement scanners/base.py**

Same structure but add `annotations`, `documentation`, `metadata` fields to ScannedModule.

**Step 3: Run tests — expect PASS**

**Step 4: Commit**

```bash
git commit -m "feat: upgrade ScannedModule with annotations/documentation/metadata"
```

---

### Task 9: Schema system (schemas/)

**Files:**
- Rewrite: `src/flask_apcore/schemas/__init__.py`
- Keep: `src/flask_apcore/schemas/_constants.py`
- Rewrite: `src/flask_apcore/schemas/pydantic_backend.py`
- Rewrite: `src/flask_apcore/schemas/marshmallow_backend.py`
- Rewrite: `src/flask_apcore/schemas/typehints_backend.py`
- Create: `tests/test_schema_dispatcher.py`
- Create: `tests/test_schema_pydantic.py`
- Create: `tests/test_schema_marshmallow.py`
- Create: `tests/test_schema_typehints.py`

**Step 1: Write failing tests for dispatcher**

Test SchemaDispatcher priority chain:
- Pydantic param → PydanticBackend
- marshmallow context → MarshmallowBackend
- Type hints → TypeHintsBackend
- No annotations → empty schema

**Step 2: Write failing tests for each backend**

PydanticBackend:
- can_handle_input with BaseModel parameter
- infer_input produces JSON Schema with URL params merged
- infer_output for Model, Optional[Model], list[Model]

MarshmallowBackend:
- can_handle_input/output with context keys
- Schema field type mapping (String, Integer, Float, etc.)
- Nested schema handling

TypeHintsBackend:
- Basic types (str, int, float, bool)
- datetime, uuid
- Optional[T], list[T]
- Return type inference

**Step 3: Implement all schema files**

Rewrite each backend. Same logic as current but:
- Remove references to yaml_backend
- Import FLASK_TYPE_MAP from _constants

**Step 4: Run all schema tests — expect PASS**

```bash
pytest tests/test_schema_*.py -v
```

**Step 5: Commit**

```bash
git commit -m "feat: rewrite schema inference system (3 backends)"
```

---

### Task 10: Scanner init + NativeFlaskScanner

**Files:**
- Rewrite: `src/flask_apcore/scanners/__init__.py`
- Rewrite: `src/flask_apcore/scanners/native.py`
- Create: `tests/test_scanner_native.py`

**Step 1: Write failing tests for NativeFlaskScanner**

Test annotation inference:
```python
def test_get_route_readonly(self, app):
    @app.route("/items", methods=["GET"])
    def get_items():
        """List all items."""
        return {}

    scanner = NativeFlaskScanner()
    modules = scanner.scan(app)
    m = modules[0]
    assert m.annotations is not None
    assert m.annotations.readonly is True

def test_delete_route_destructive(self, app):
    @app.route("/items/<int:id>", methods=["DELETE"])
    def delete_item(id: int):
        """Delete an item."""
        return {}

    scanner = NativeFlaskScanner()
    modules = scanner.scan(app)
    m = modules[0]
    assert m.annotations.destructive is True

def test_put_route_idempotent(self, app):
    @app.route("/items/<int:id>", methods=["PUT"])
    def update_item(id: int):
        """Update an item."""
        return {}

    scanner = NativeFlaskScanner()
    modules = scanner.scan(app)
    m = modules[0]
    assert m.annotations.idempotent is True
```

Test documentation extraction:
```python
def test_documentation_full_docstring(self, app):
    @app.route("/items")
    def get_items():
        """List all items.

        Returns paginated list of items with filtering support.
        """
        return {}

    scanner = NativeFlaskScanner()
    modules = scanner.scan(app)
    m = modules[0]
    assert m.description == "List all items."
    assert "paginated" in m.documentation
```

Test metadata:
```python
def test_metadata_has_source(self, app):
    @app.route("/items")
    def get_items():
        return {}

    scanner = NativeFlaskScanner()
    modules = scanner.scan(app)
    assert modules[0].metadata["source"] == "native"
```

Also test: URL param extraction, module_id generation, Blueprint handling, deduplication, static route skipping, HEAD/OPTIONS filtering.

**Step 2: Implement scanners/__init__.py and native.py**

In native.py, add annotation inference based on HTTP method:

```python
from apcore import ModuleAnnotations

def _infer_annotations(self, method: str) -> ModuleAnnotations:
    if method == "GET":
        return ModuleAnnotations(readonly=True)
    elif method == "DELETE":
        return ModuleAnnotations(destructive=True)
    elif method == "PUT":
        return ModuleAnnotations(idempotent=True)
    return ModuleAnnotations()
```

Extract full docstring as `documentation`, first line as `description`.
Add `metadata={"source": "native"}`.

**Step 3: Run tests — expect PASS**

```bash
pytest tests/test_scanner_native.py -v
```

**Step 4: Commit**

```bash
git commit -m "feat: rewrite NativeFlaskScanner with annotation inference"
```

---

## Phase 5: Output

### Task 11: RegistryWriter (output/registry_writer.py)

**Files:**
- Create: `src/flask_apcore/output/registry_writer.py`
- Create: `tests/test_registry_writer.py`

**Step 1: Write failing tests**

```python
def test_register_scanned_modules(self):
    """RegistryWriter registers ScannedModules into apcore Registry."""
    from apcore import Registry, ModuleAnnotations
    from flask_apcore.output.registry_writer import RegistryWriter
    from flask_apcore.scanners.base import ScannedModule

    registry = Registry()
    modules = [
        ScannedModule(
            module_id="users.list",
            description="List users",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            tags=["users"],
            target="myapp.views:list_users",
            http_method="GET",
            url_rule="/users",
            annotations=ModuleAnnotations(readonly=True),
        ),
    ]

    writer = RegistryWriter()
    writer.write(modules, registry)
    assert registry.get("users.list") is not None

def test_dry_run_does_not_register(self):
    registry = Registry()
    modules = [...]  # same as above
    writer = RegistryWriter()
    writer.write(modules, registry, dry_run=True)
    assert registry.get("users.list") is None
```

**Step 2: Implement registry_writer.py**

```python
# src/flask_apcore/output/registry_writer.py
"""Direct registration of scanned modules into apcore Registry."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask_apcore.scanners.base import ScannedModule

logger = logging.getLogger("flask_apcore")


class RegistryWriter:
    """Registers ScannedModules directly into an apcore Registry."""

    def write(
        self,
        modules: list[ScannedModule],
        registry: Any,
        *,
        dry_run: bool = False,
    ) -> list[str]:
        """Register scanned modules into the registry.

        Returns list of registered module IDs.
        """
        registered: list[str] = []
        for mod in modules:
            if dry_run:
                logger.info("[dry-run] Would register: %s", mod.module_id)
                continue

            fm = self._to_function_module(mod)
            registry.register(mod.module_id, fm)
            registered.append(mod.module_id)
            logger.debug("Registered: %s", mod.module_id)

        return registered

    def _to_function_module(self, mod: ScannedModule) -> Any:
        """Convert ScannedModule to apcore FunctionModule."""
        from apcore import FunctionModule
        from flask_apcore.output._resolve_target import resolve_target

        func = resolve_target(mod.target)
        annotations_dict = None
        if mod.annotations is not None:
            from dataclasses import asdict
            annotations_dict = asdict(mod.annotations)

        return FunctionModule(
            func=func,
            module_id=mod.module_id,
            description=mod.description,
            documentation=mod.documentation,
            tags=mod.tags,
            version=mod.version,
            annotations=annotations_dict,
            metadata=mod.metadata,
        )
```

Note: We need a helper `_resolve_target()` to import the function from "module:qualname" format. Create `src/flask_apcore/output/_resolve_target.py`:

```python
"""Resolve 'module:qualname' target strings to callable objects."""
from __future__ import annotations

import importlib
from typing import Callable


def resolve_target(target: str) -> Callable:
    """Resolve 'module.path:function_name' to callable."""
    module_path, _, qualname = target.partition(":")
    if not qualname:
        raise ValueError(f"Invalid target format: {target!r}. Expected 'module:name'.")
    mod = importlib.import_module(module_path)
    obj = getattr(mod, qualname)
    if not callable(obj):
        raise ValueError(f"Target {target!r} is not callable.")
    return obj
```

**Step 3: Run tests — expect PASS**

**Step 4: Commit**

```bash
git commit -m "feat: add RegistryWriter for direct module registration"
```

---

### Task 12: YAMLWriter upgrade

**Files:**
- Rewrite: `src/flask_apcore/output/yaml_writer.py`
- Rewrite: `src/flask_apcore/output/__init__.py`
- Create: `tests/test_yaml_writer.py`

**Step 1: Write failing tests**

Test YAML writer:
- Generates .binding.yaml files
- Includes annotations in YAML output
- Includes documentation field
- Includes metadata field
- Dry run doesn't write files
- Filename sanitization
- get_writer("yaml") returns YAMLWriter
- get_writer(None) returns RegistryWriter

**Step 2: Implement yaml_writer.py and output/__init__.py**

Upgrade yaml_writer.py _build_binding() to include annotations, documentation, metadata.

Update output/__init__.py:
```python
def get_writer(output_format: str | None = None):
    if output_format is None:
        from flask_apcore.output.registry_writer import RegistryWriter
        return RegistryWriter()
    elif output_format == "yaml":
        from flask_apcore.output.yaml_writer import YAMLWriter
        return YAMLWriter()
    else:
        raise ValueError(f"Unknown output format: {output_format!r}. Expected 'yaml' or None.")
```

**Step 3: Run tests — expect PASS**

**Step 4: Commit**

```bash
git commit -m "feat: upgrade YAMLWriter with annotations/documentation/metadata"
```

---

## Phase 6: CLI

### Task 13: CLI scan command

**Files:**
- Rewrite: `src/flask_apcore/cli.py` (scan portion)
- Create: `tests/test_cli_scan.py`

**Step 1: Write failing tests**

```python
def test_scan_default_registers_to_registry(self, initialized_app):
    """Default scan (no --output) registers directly to Registry."""
    # Add a route to scan
    @initialized_app.route("/hello")
    def hello():
        """Say hello."""
        return {"message": "hello"}

    runner = initialized_app.test_cli_runner()
    result = runner.invoke(args=["apcore", "scan"])
    assert result.exit_code == 0
    assert "Registered" in result.output or "registered" in result.output

def test_scan_output_yaml(self, initialized_app, tmp_path):
    """--output yaml generates .binding.yaml files."""
    @initialized_app.route("/hello")
    def hello():
        return {}

    runner = initialized_app.test_cli_runner()
    result = runner.invoke(args=["apcore", "scan", "--output", "yaml", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    yaml_files = list(tmp_path.glob("*.binding.yaml"))
    assert len(yaml_files) > 0

def test_scan_dry_run(self, initialized_app):
    @initialized_app.route("/hello")
    def hello():
        return {}

    runner = initialized_app.test_cli_runner()
    result = runner.invoke(args=["apcore", "scan", "--dry-run"])
    assert result.exit_code == 0
    assert "dry run" in result.output.lower() or "Dry run" in result.output
```

**Step 2: Implement scan command in cli.py**

Key changes from current:
- `--output` is now optional (not required). Choices: `yaml` only.
- No `--output` → use RegistryWriter (pass `registry` from ext_data)
- `--output yaml` → use YAMLWriter (same as before)
- Remove `python` from choices

**Step 3: Run tests — expect PASS**

**Step 4: Commit**

```bash
git commit -m "feat: rewrite CLI scan with default registry registration"
```

---

### Task 14: CLI serve command

**Files:**
- Continue: `src/flask_apcore/cli.py` (serve portion)
- Create: `tests/test_cli_serve.py`

**Step 1: Write failing tests**

```python
from unittest.mock import patch, MagicMock

def test_serve_passes_validate_inputs(self, initialized_app):
    """--validate-inputs flag is passed to apcore_mcp.serve()."""
    # Register at least one module
    registry = initialized_app.extensions["apcore"]["registry"]
    _register_dummy_module(registry)

    runner = initialized_app.test_cli_runner()
    with patch("flask_apcore.cli._do_serve") as mock_serve:
        result = runner.invoke(args=["apcore", "serve", "--validate-inputs"])
        assert result.exit_code == 0
        call_kwargs = mock_serve.call_args
        assert call_kwargs[1]["validate_inputs"] is True  # or positional

def test_serve_passes_log_level(self, initialized_app):
    registry = initialized_app.extensions["apcore"]["registry"]
    _register_dummy_module(registry)

    runner = initialized_app.test_cli_runner()
    with patch("flask_apcore.cli._do_serve") as mock_serve:
        result = runner.invoke(args=["apcore", "serve", "--log-level", "DEBUG"])
        assert result.exit_code == 0
        call_kwargs = mock_serve.call_args
        assert call_kwargs[1]["log_level"] == "DEBUG"

def test_serve_passes_metrics_collector(self, app, tmp_path):
    """When metrics enabled, metrics_collector passed to serve."""
    app.config["APCORE_MODULE_DIR"] = str(tmp_path)
    app.config["APCORE_AUTO_DISCOVER"] = False
    app.config["APCORE_METRICS_ENABLED"] = True
    from flask_apcore import Apcore
    Apcore(app)
    registry = app.extensions["apcore"]["registry"]
    _register_dummy_module(registry)

    runner = app.test_cli_runner()
    with patch("flask_apcore.cli._do_serve") as mock_serve:
        result = runner.invoke(args=["apcore", "serve"])
        assert result.exit_code == 0
        assert mock_serve.call_args[1]["metrics_collector"] is not None
```

**Step 2: Implement serve command**

Update _do_serve() signature to accept all new params:

```python
def _do_serve(
    registry_or_executor,
    transport, host, port, name,
    *,
    validate_inputs=False,
    log_level=None,
    metrics_collector=None,
):
    from apcore_mcp import serve
    serve(
        registry_or_executor,
        transport=transport,
        host=host,
        port=port,
        name=name,
        validate_inputs=validate_inputs,
        log_level=log_level,
        metrics_collector=metrics_collector,
    )
```

Add CLI options:
```python
@click.option("--validate-inputs", is_flag=True, default=False)
@click.option("--log-level", type=click.Choice(["DEBUG","INFO","WARNING","ERROR"]), default=None)
```

In serve_command, get metrics_collector from ext_data:
```python
metrics_collector = app.extensions["apcore"].get("metrics_collector")
```

**Step 3: Run tests — expect PASS**

**Step 4: Commit**

```bash
git commit -m "feat: rewrite CLI serve with full apcore-mcp parameter passthrough"
```

---

## Phase 7: Public API + Integration

### Task 15: Public API (__init__.py)

**Files:**
- Rewrite: `src/flask_apcore/__init__.py`

**Step 1: Write test**

```python
# tests/test_public_api.py
def test_public_exports():
    import flask_apcore
    assert hasattr(flask_apcore, "Apcore")
    assert hasattr(flask_apcore, "module")
    assert hasattr(flask_apcore, "__version__")
    assert flask_apcore.__version__ == "0.1.0"

def test_reexported_apcore_types():
    from flask_apcore import (
        Registry, Executor, Context, Identity,
        ModuleAnnotations, ModuleDescriptor,
        Middleware, ACL, Config,
    )
    # Just verify they're importable
    assert Registry is not None
```

**Step 2: Implement __init__.py**

```python
"""flask-apcore: Flask Extension for apcore AI-Perceivable Core integration."""

__version__ = "0.1.0"

from flask_apcore.extension import Apcore

from apcore import module

from apcore import (
    ACL,
    Config,
    Context,
    Executor,
    Identity,
    Middleware,
    ModuleAnnotations,
    ModuleDescriptor,
    Registry,
)

__all__ = [
    "Apcore",
    "__version__",
    "module",
    "ACL",
    "Config",
    "Context",
    "Executor",
    "Identity",
    "Middleware",
    "ModuleAnnotations",
    "ModuleDescriptor",
    "Registry",
]
```

**Step 3: Run test — expect PASS**

**Step 4: Commit**

```bash
git commit -m "feat: rewrite public API with apcore type re-exports"
```

---

### Task 16: Integration tests

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write E2E tests**

```python
# tests/test_integration.py
"""End-to-end integration tests."""
from __future__ import annotations

import pytest
from flask import Flask


class TestScanAndRegister:
    """Scan Flask routes → register to Registry → verify."""

    def test_scan_register_and_verify(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False

        @app.route("/users", methods=["GET"])
        def list_users():
            """List all users."""
            return {"users": []}

        @app.route("/users/<int:user_id>", methods=["DELETE"])
        def delete_user(user_id: int):
            """Delete a user by ID."""
            return {}

        from flask_apcore import Apcore
        Apcore(app)

        with app.app_context():
            runner = app.test_cli_runner()
            result = runner.invoke(args=["apcore", "scan"])
            assert result.exit_code == 0

            registry = app.extensions["apcore"]["registry"]
            all_modules = registry.all()
            assert len(all_modules) >= 2


class TestScanToYAML:
    """Scan Flask routes → generate .binding.yaml files."""

    def test_generates_binding_files(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False

        @app.route("/items", methods=["GET"])
        def list_items():
            """List items."""
            return []

        from flask_apcore import Apcore
        Apcore(app)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with app.app_context():
            runner = app.test_cli_runner()
            result = runner.invoke(
                args=["apcore", "scan", "--output", "yaml", "--dir", str(output_dir)]
            )
            assert result.exit_code == 0
            yaml_files = list(output_dir.glob("*.binding.yaml"))
            assert len(yaml_files) >= 1


class TestObservabilityIntegration:
    """Observability middlewares injected into Executor."""

    def test_tracing_middleware_in_executor(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False
        app.config["APCORE_TRACING_ENABLED"] = True
        app.config["APCORE_TRACING_EXPORTER"] = "memory"

        from flask_apcore import Apcore
        Apcore(app)

        with app.app_context():
            from flask_apcore.registry import get_executor
            executor = get_executor(app)
            middleware_types = [type(m).__name__ for m in executor.middlewares]
            assert "TracingMiddleware" in middleware_types


class TestContextIntegration:
    """FlaskContextFactory creates Context with TraceContext."""

    def test_traceparent_propagated(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False

        from flask_apcore import Apcore
        Apcore(app)

        with app.test_request_context(
            headers={"traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"}
        ):
            from flask_apcore.context import FlaskContextFactory
            from flask import request
            factory = FlaskContextFactory()
            ctx = factory.create_context(request)
            assert ctx.trace_id == "0af7651916cd43dd8448eb211c80319c"
```

**Step 2: Run all tests**

```bash
pytest tests/ -v
```

**Step 3: Commit**

```bash
git commit -m "test: add end-to-end integration tests"
```

---

### Task 17: Final cleanup and full test run

**Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

**Step 2: Run ruff lint**

```bash
ruff check src/ tests/
```

**Step 3: Fix any issues**

**Step 4: Final commit**

```bash
git commit -m "chore: final cleanup for flask-apcore v0.1.0 redesign"
```

---

## Task Dependency Graph

```
Task 1 (foundation)
  ├─→ Task 2 (config) ─→ Task 3 (conftest)
  │     │
  │     ├─→ Task 4 (observability)
  │     ├─→ Task 5 (registry) ←── Task 4
  │     └─→ Task 6 (context)
  │           │
  │           └─→ Task 7 (extension) ←── Task 4, 5
  │
  ├─→ Task 8 (scanner base)
  ├─→ Task 9 (schema system)
  │     │
  │     └─→ Task 10 (native scanner) ←── Task 8
  │
  ├─→ Task 11 (registry writer) ←── Task 8
  ├─→ Task 12 (yaml writer) ←── Task 8, 11
  │
  ├─→ Task 13 (CLI scan) ←── Task 7, 10, 11, 12
  ├─→ Task 14 (CLI serve) ←── Task 7
  │
  ├─→ Task 15 (public API) ←── Task 7
  └─→ Task 16 (integration) ←── all above
       └─→ Task 17 (cleanup)
```
