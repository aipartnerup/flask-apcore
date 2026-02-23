# Schema Explorer & Output Formats Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Schema HTTP API, HTML explorer page, OpenAPI export, and `--output json` to flask-apcore.

**Architecture:** Shared serialization layer (`serializers.py`) consumed by both CLI writers (`json_writer.py`, `openapi_writer.py`) and a Flask Blueprint (`web/`). Explorer Blueprint is opt-in via `APCORE_EXPLORER_ENABLED`. RegistryWriter enriched to preserve `http_method`/`url_rule` in metadata.

**Tech Stack:** Flask Blueprint, JSON, OpenAPI 3.1, inline HTML/CSS/JS (no external deps)

---

### Task 1: RegistryWriter Metadata Enrichment

**Files:**
- Modify: `src/flask_apcore/output/registry_writer.py:77-105`
- Test: `tests/test_registry_writer.py`

**Step 1: Write the failing test**

Add to `tests/test_registry_writer.py` class `TestRegistryWriter`:

```python
def test_http_method_and_url_rule_in_metadata(self):
    """http_method and url_rule must be preserved in FunctionModule metadata."""
    writer = RegistryWriter()
    registry = Registry()
    modules = [_make_module(
        module_id="items.get",
        http_method="GET",
        url_rule="/items",
        metadata={"source": "native"},
    )]

    writer.write(modules, registry)

    fm = registry.get("items.get")
    assert fm.metadata["http_method"] == "GET"
    assert fm.metadata["url_rule"] == "/items"
    assert fm.metadata["source"] == "native"  # original metadata preserved
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_registry_writer.py::TestRegistryWriter::test_http_method_and_url_rule_in_metadata -v`
Expected: FAIL with `KeyError: 'http_method'`

**Step 3: Write minimal implementation**

In `src/flask_apcore/output/registry_writer.py`, modify `_to_function_module()`:

```python
def _to_function_module(self, mod: ScannedModule) -> Any:
    from apcore import FunctionModule

    func = _resolve_target(mod.target)

    annotations_dict: dict[str, Any] | None = None
    if mod.annotations is not None:
        from dataclasses import asdict

        annotations_dict = asdict(mod.annotations)

    metadata = {
        **(mod.metadata or {}),
        "http_method": mod.http_method,
        "url_rule": mod.url_rule,
    }

    return FunctionModule(
        func=func,
        module_id=mod.module_id,
        description=mod.description,
        documentation=mod.documentation,
        tags=mod.tags,
        version=mod.version,
        annotations=annotations_dict,
        metadata=metadata,
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_registry_writer.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/flask_apcore/output/registry_writer.py tests/test_registry_writer.py
git commit -m "fix: preserve http_method and url_rule in RegistryWriter metadata"
```

---

### Task 2: Shared Serializers

**Files:**
- Create: `src/flask_apcore/serializers.py`
- Create: `tests/test_serializers.py`

**Step 1: Write the failing tests**

Create `tests/test_serializers.py`:

```python
"""Tests for flask_apcore.serializers — shared serialization functions."""

from __future__ import annotations

from typing import Any

import pytest
from apcore import ModuleAnnotations

from flask_apcore.scanners.base import ScannedModule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_module(
    module_id: str = "items.get",
    http_method: str = "GET",
    url_rule: str = "/items",
    annotations: ModuleAnnotations | None = None,
    documentation: str | None = "List all items.",
    metadata: dict[str, Any] | None = None,
    **kwargs,
) -> ScannedModule:
    defaults = dict(
        module_id=module_id,
        description="List items",
        input_schema={"type": "object", "properties": {"q": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"items": {"type": "array"}}},
        tags=["items"],
        target="myapp:list_items",
        http_method=http_method,
        url_rule=url_rule,
        version="1.0.0",
        annotations=annotations or ModuleAnnotations(readonly=True),
        documentation=documentation,
        metadata=metadata or {"source": "native"},
        warnings=[],
    )
    defaults.update(kwargs)
    return ScannedModule(**defaults)


# ---------------------------------------------------------------------------
# module_to_dict
# ---------------------------------------------------------------------------


class TestModuleToDict:
    def test_contains_all_fields(self):
        from flask_apcore.serializers import module_to_dict

        mod = _make_module()
        d = module_to_dict(mod)

        assert d["module_id"] == "items.get"
        assert d["description"] == "List items"
        assert d["http_method"] == "GET"
        assert d["url_rule"] == "/items"
        assert d["tags"] == ["items"]
        assert d["version"] == "1.0.0"
        assert "input_schema" in d
        assert "output_schema" in d
        assert "annotations" in d
        assert d["documentation"] == "List all items."
        assert d["metadata"] == {"source": "native"}

    def test_annotations_none(self):
        from flask_apcore.serializers import module_to_dict

        mod = _make_module(annotations=None)
        d = module_to_dict(mod)
        assert d["annotations"] is None


class TestModulesToDicts:
    def test_batch_conversion(self):
        from flask_apcore.serializers import modules_to_dicts

        mods = [_make_module(module_id="a.get"), _make_module(module_id="b.post")]
        result = modules_to_dicts(mods)
        assert len(result) == 2
        assert result[0]["module_id"] == "a.get"
        assert result[1]["module_id"] == "b.post"

    def test_empty_list(self):
        from flask_apcore.serializers import modules_to_dicts

        assert modules_to_dicts([]) == []


# ---------------------------------------------------------------------------
# modules_to_openapi
# ---------------------------------------------------------------------------


class TestModulesToOpenapi:
    def test_openapi_structure(self):
        from flask_apcore.serializers import modules_to_openapi

        mods = [_make_module()]
        spec = modules_to_openapi(mods, title="Test API", version="1.0.0")

        assert spec["openapi"] == "3.1.0"
        assert spec["info"]["title"] == "Test API"
        assert spec["info"]["version"] == "1.0.0"
        assert "/items" in spec["paths"]

    def test_get_method_uses_parameters(self):
        from flask_apcore.serializers import modules_to_openapi

        mods = [_make_module(http_method="GET", url_rule="/items")]
        spec = modules_to_openapi(mods, title="T", version="1")
        op = spec["paths"]["/items"]["get"]

        assert "parameters" in op or "requestBody" not in op

    def test_post_method_uses_request_body(self):
        from flask_apcore.serializers import modules_to_openapi

        mods = [_make_module(
            module_id="items.post",
            http_method="POST",
            url_rule="/items",
        )]
        spec = modules_to_openapi(mods, title="T", version="1")
        op = spec["paths"]["/items"]["post"]

        assert "requestBody" in op

    def test_annotations_in_extension(self):
        from flask_apcore.serializers import modules_to_openapi

        ann = ModuleAnnotations(readonly=True, destructive=False)
        mods = [_make_module(annotations=ann)]
        spec = modules_to_openapi(mods, title="T", version="1")
        op = spec["paths"]["/items"]["get"]

        assert "x-apcore-annotations" in op

    def test_tags_mapped(self):
        from flask_apcore.serializers import modules_to_openapi

        mods = [_make_module(tags=["items"])]
        spec = modules_to_openapi(mods, title="T", version="1")
        op = spec["paths"]["/items"]["get"]

        assert op["tags"] == ["items"]

    def test_empty_modules(self):
        from flask_apcore.serializers import modules_to_openapi

        spec = modules_to_openapi([], title="T", version="1")
        assert spec["paths"] == {}

    def test_multiple_methods_same_path(self):
        from flask_apcore.serializers import modules_to_openapi

        mods = [
            _make_module(module_id="items.get", http_method="GET", url_rule="/items"),
            _make_module(module_id="items.post", http_method="POST", url_rule="/items"),
        ]
        spec = modules_to_openapi(mods, title="T", version="1")

        assert "get" in spec["paths"]["/items"]
        assert "post" in spec["paths"]["/items"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_serializers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'flask_apcore.serializers'`

**Step 3: Write minimal implementation**

Create `src/flask_apcore/serializers.py`:

```python
"""Shared serialization functions for flask-apcore.

Pure functions with no Flask dependency. Used by CLI writers and web endpoints.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask_apcore.scanners.base import ScannedModule


def module_to_dict(module: ScannedModule) -> dict[str, Any]:
    """Convert a ScannedModule to a flat dict."""
    annotations_dict: dict[str, Any] | None = None
    if module.annotations is not None:
        annotations_dict = asdict(module.annotations)

    return {
        "module_id": module.module_id,
        "description": module.description,
        "documentation": module.documentation,
        "http_method": module.http_method,
        "url_rule": module.url_rule,
        "tags": module.tags,
        "version": module.version,
        "target": module.target,
        "annotations": annotations_dict,
        "metadata": module.metadata,
        "input_schema": module.input_schema,
        "output_schema": module.output_schema,
    }


def modules_to_dicts(modules: list[ScannedModule]) -> list[dict[str, Any]]:
    """Batch convert ScannedModules to dicts."""
    return [module_to_dict(m) for m in modules]


def modules_to_openapi(
    modules: list[ScannedModule],
    *,
    title: str,
    version: str,
) -> dict[str, Any]:
    """Convert ScannedModule list to OpenAPI 3.1 spec dict."""
    paths: dict[str, Any] = {}

    for mod in modules:
        method = mod.http_method.lower()
        path = mod.url_rule

        if path not in paths:
            paths[path] = {}

        operation: dict[str, Any] = {
            "operationId": mod.module_id,
            "summary": mod.description,
            "tags": mod.tags,
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": mod.output_schema,
                        }
                    },
                }
            },
        }

        if mod.documentation:
            operation["description"] = mod.documentation

        # Annotations as extension
        if mod.annotations is not None:
            operation["x-apcore-annotations"] = asdict(mod.annotations)

        # Input schema handling
        if method in ("post", "put", "patch"):
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": mod.input_schema,
                    }
                },
            }
        else:
            # GET/DELETE: convert input_schema properties to query parameters
            props = mod.input_schema.get("properties", {})
            required = mod.input_schema.get("required", [])
            if props:
                parameters = []
                for name, schema in props.items():
                    parameters.append({
                        "name": name,
                        "in": "query",
                        "required": name in required,
                        "schema": schema,
                    })
                operation["parameters"] = parameters

        paths[path][method] = operation

    return {
        "openapi": "3.1.0",
        "info": {
            "title": title,
            "version": version,
        },
        "paths": paths,
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_serializers.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/flask_apcore/serializers.py tests/test_serializers.py
git commit -m "feat: add shared serializers for module-to-dict and OpenAPI conversion"
```

---

### Task 3: JSON Writer + CLI Integration

**Files:**
- Create: `src/flask_apcore/output/json_writer.py`
- Modify: `src/flask_apcore/output/__init__.py:12-33`
- Modify: `src/flask_apcore/cli.py:36`
- Test: `tests/test_json_writer.py`

**Step 1: Write the failing tests**

Create `tests/test_json_writer.py`:

```python
"""Tests for output/json_writer.py and get_writer('json')."""

from __future__ import annotations

import json
from typing import Any

import pytest
from apcore import ModuleAnnotations

from flask_apcore.scanners.base import ScannedModule


def _make_module(module_id: str = "test.get", **kwargs) -> ScannedModule:
    defaults = dict(
        module_id=module_id,
        description="Test endpoint",
        input_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        output_schema={"type": "object", "properties": {}},
        tags=["test"],
        target="myapp.views:get_items",
        http_method="GET",
        url_rule="/items",
        version="1.0.0",
        annotations=ModuleAnnotations(readonly=True),
        documentation="Full docs.",
        metadata={"source": "native"},
        warnings=[],
    )
    defaults.update(kwargs)
    return ScannedModule(**defaults)


class TestJSONWriter:
    def test_writes_single_json_file(self, tmp_path):
        from flask_apcore.output.json_writer import JSONWriter

        writer = JSONWriter()
        modules = [_make_module()]
        writer.write(modules, str(tmp_path))

        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        assert files[0].name == "apcore-modules.json"

    def test_json_content_is_list(self, tmp_path):
        from flask_apcore.output.json_writer import JSONWriter

        writer = JSONWriter()
        modules = [_make_module(), _make_module(module_id="b.post")]
        writer.write(modules, str(tmp_path))

        data = json.loads((tmp_path / "apcore-modules.json").read_text())
        assert isinstance(data, list)
        assert len(data) == 2

    def test_module_fields_present(self, tmp_path):
        from flask_apcore.output.json_writer import JSONWriter

        writer = JSONWriter()
        modules = [_make_module()]
        writer.write(modules, str(tmp_path))

        data = json.loads((tmp_path / "apcore-modules.json").read_text())
        entry = data[0]
        assert entry["module_id"] == "test.get"
        assert entry["http_method"] == "GET"
        assert entry["url_rule"] == "/items"

    def test_dry_run_does_not_write(self, tmp_path):
        from flask_apcore.output.json_writer import JSONWriter

        writer = JSONWriter()
        modules = [_make_module()]
        result = writer.write(modules, str(tmp_path), dry_run=True)

        assert len(result) == 1
        assert not list(tmp_path.glob("*.json"))

    def test_empty_modules(self, tmp_path):
        from flask_apcore.output.json_writer import JSONWriter

        writer = JSONWriter()
        result = writer.write([], str(tmp_path))
        assert result == []


class TestGetWriterJSON:
    def test_json_returns_json_writer(self):
        from flask_apcore.output import get_writer
        from flask_apcore.output.json_writer import JSONWriter

        writer = get_writer("json")
        assert isinstance(writer, JSONWriter)
```

Also add CLI test to `tests/test_cli_scan.py`:

```python
class TestScanJSONOutput:
    """--output json generates apcore-modules.json file."""

    def test_json_output_creates_file(self, scan_app, tmp_path):
        out_dir = str(tmp_path / "json_out")
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan", "--output", "json", "--dir", out_dir])

        assert result.exit_code == 0, result.output
        assert "Generated" in result.output

        from pathlib import Path
        import json

        json_file = Path(out_dir) / "apcore-modules.json"
        assert json_file.exists()
        data = json.loads(json_file.read_text())
        assert len(data) >= 3
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_json_writer.py tests/test_cli_scan.py::TestScanJSONOutput -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `src/flask_apcore/output/json_writer.py`:

```python
"""JSON output writer for flask-apcore.

Writes all ScannedModules as a single apcore-modules.json file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask_apcore.scanners.base import ScannedModule

logger = logging.getLogger("flask_apcore")


class JSONWriter:
    """Generates a single apcore-modules.json from ScannedModule instances."""

    def write(
        self,
        modules: list[ScannedModule],
        output_dir: str,
        dry_run: bool = False,
    ) -> list[dict[str, Any]]:
        """Write all modules to a single JSON file.

        Args:
            modules: List of ScannedModule instances.
            output_dir: Directory to write the JSON file to.
            dry_run: If True, return data without writing to disk.

        Returns:
            List of dicts representing the serialized modules.
        """
        if not modules:
            return []

        from flask_apcore.serializers import modules_to_dicts

        results = modules_to_dicts(modules)

        if not dry_run:
            output_path = Path(output_dir).resolve()
            output_path.mkdir(parents=True, exist_ok=True)
            file_path = output_path / "apcore-modules.json"
            file_path.write_text(
                json.dumps(results, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Written: %s", file_path)

        return results
```

Modify `src/flask_apcore/output/__init__.py` — add `"json"` branch:

```python
def get_writer(output_format: str | None = None):
    if output_format is None:
        from flask_apcore.output.registry_writer import RegistryWriter
        return RegistryWriter()
    elif output_format == "yaml":
        from flask_apcore.output.yaml_writer import YAMLWriter
        return YAMLWriter()
    elif output_format == "json":
        from flask_apcore.output.json_writer import JSONWriter
        return JSONWriter()
    else:
        raise ValueError(f"Unknown output format: {output_format!r}")
```

Modify `src/flask_apcore/cli.py` line 36 — add `"json"` to Choice:

```python
type=click.Choice(["yaml", "json", "openapi"]),
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_json_writer.py tests/test_cli_scan.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/flask_apcore/output/json_writer.py src/flask_apcore/output/__init__.py src/flask_apcore/cli.py tests/test_json_writer.py tests/test_cli_scan.py
git commit -m "feat: add --output json CLI support with JSONWriter"
```

---

### Task 4: OpenAPI Writer + CLI Integration

**Files:**
- Create: `src/flask_apcore/output/openapi_writer.py`
- Modify: `src/flask_apcore/output/__init__.py`
- Test: `tests/test_openapi_writer.py`

**Step 1: Write the failing tests**

Create `tests/test_openapi_writer.py`:

```python
"""Tests for output/openapi_writer.py and get_writer('openapi')."""

from __future__ import annotations

import json
from typing import Any

import pytest
from apcore import ModuleAnnotations

from flask_apcore.scanners.base import ScannedModule


def _make_module(module_id: str = "test.get", **kwargs) -> ScannedModule:
    defaults = dict(
        module_id=module_id,
        description="Test endpoint",
        input_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        output_schema={"type": "object", "properties": {}},
        tags=["test"],
        target="myapp.views:get_items",
        http_method="GET",
        url_rule="/items",
        version="1.0.0",
        annotations=ModuleAnnotations(readonly=True),
        documentation="Full docs.",
        metadata={"source": "native"},
        warnings=[],
    )
    defaults.update(kwargs)
    return ScannedModule(**defaults)


class TestOpenAPIWriter:
    def test_writes_openapi_json_file(self, tmp_path):
        from flask_apcore.output.openapi_writer import OpenAPIWriter

        writer = OpenAPIWriter()
        modules = [_make_module()]
        writer.write(modules, str(tmp_path))

        files = list(tmp_path.glob("openapi.json"))
        assert len(files) == 1

    def test_openapi_spec_structure(self, tmp_path):
        from flask_apcore.output.openapi_writer import OpenAPIWriter

        writer = OpenAPIWriter()
        modules = [_make_module()]
        writer.write(modules, str(tmp_path))

        spec = json.loads((tmp_path / "openapi.json").read_text())
        assert spec["openapi"] == "3.1.0"
        assert "info" in spec
        assert "paths" in spec

    def test_dry_run_does_not_write(self, tmp_path):
        from flask_apcore.output.openapi_writer import OpenAPIWriter

        writer = OpenAPIWriter()
        modules = [_make_module()]
        result = writer.write(modules, str(tmp_path), dry_run=True)

        assert "openapi" in result
        assert not list(tmp_path.glob("openapi.json"))

    def test_empty_modules(self, tmp_path):
        from flask_apcore.output.openapi_writer import OpenAPIWriter

        writer = OpenAPIWriter()
        result = writer.write([], str(tmp_path))
        assert result["paths"] == {}


class TestGetWriterOpenAPI:
    def test_openapi_returns_openapi_writer(self):
        from flask_apcore.output import get_writer
        from flask_apcore.output.openapi_writer import OpenAPIWriter

        writer = get_writer("openapi")
        assert isinstance(writer, OpenAPIWriter)
```

Also add CLI test to `tests/test_cli_scan.py`:

```python
class TestScanOpenAPIOutput:
    """--output openapi generates openapi.json file."""

    def test_openapi_output_creates_file(self, scan_app, tmp_path):
        out_dir = str(tmp_path / "openapi_out")
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan", "--output", "openapi", "--dir", out_dir])

        assert result.exit_code == 0, result.output
        assert "Generated" in result.output

        from pathlib import Path
        import json

        spec_file = Path(out_dir) / "openapi.json"
        assert spec_file.exists()
        spec = json.loads(spec_file.read_text())
        assert spec["openapi"] == "3.1.0"
        assert len(spec["paths"]) >= 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_openapi_writer.py tests/test_cli_scan.py::TestScanOpenAPIOutput -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `src/flask_apcore/output/openapi_writer.py`:

```python
"""OpenAPI 3.1 output writer for flask-apcore.

Writes all ScannedModules as a single openapi.json file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask_apcore.scanners.base import ScannedModule

logger = logging.getLogger("flask_apcore")

# Default values used when no app context is available (CLI mode)
_DEFAULT_TITLE = "flask-apcore API"
_DEFAULT_VERSION = "1.0.0"


class OpenAPIWriter:
    """Generates openapi.json from ScannedModule instances."""

    def write(
        self,
        modules: list[ScannedModule],
        output_dir: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Write OpenAPI 3.1 spec to a single JSON file.

        Args:
            modules: List of ScannedModule instances.
            output_dir: Directory to write the spec file to.
            dry_run: If True, return spec without writing to disk.

        Returns:
            OpenAPI spec dict.
        """
        from flask_apcore.serializers import modules_to_openapi

        spec = modules_to_openapi(
            modules, title=_DEFAULT_TITLE, version=_DEFAULT_VERSION
        )

        if not dry_run and modules:
            output_path = Path(output_dir).resolve()
            output_path.mkdir(parents=True, exist_ok=True)
            file_path = output_path / "openapi.json"
            file_path.write_text(
                json.dumps(spec, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Written: %s", file_path)

        return spec
```

Modify `src/flask_apcore/output/__init__.py` — add `"openapi"` branch:

```python
elif output_format == "openapi":
    from flask_apcore.output.openapi_writer import OpenAPIWriter
    return OpenAPIWriter()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_openapi_writer.py tests/test_cli_scan.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/flask_apcore/output/openapi_writer.py src/flask_apcore/output/__init__.py tests/test_openapi_writer.py tests/test_cli_scan.py
git commit -m "feat: add --output openapi CLI support with OpenAPIWriter"
```

---

### Task 5: Explorer Config Settings

**Files:**
- Modify: `src/flask_apcore/config.py`
- Modify: `tests/test_config.py`

**Step 1: Write the failing tests**

Add to `tests/test_config.py`:

```python
# ===========================================================================
# 9. Explorer settings
# ===========================================================================


class TestExplorerEnabled:
    def test_default_false(self) -> None:
        s = _load()
        assert s.explorer_enabled is False

    def test_true(self) -> None:
        s = _load(APCORE_EXPLORER_ENABLED=True)
        assert s.explorer_enabled is True

    def test_none_falls_back(self) -> None:
        s = _load(APCORE_EXPLORER_ENABLED=None)
        assert s.explorer_enabled is False

    def test_non_bool_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_EXPLORER_ENABLED"):
            _load(APCORE_EXPLORER_ENABLED="yes")


class TestExplorerUrlPrefix:
    def test_default(self) -> None:
        s = _load()
        assert s.explorer_url_prefix == "/apcore"

    def test_custom(self) -> None:
        s = _load(APCORE_EXPLORER_URL_PREFIX="/api-explorer")
        assert s.explorer_url_prefix == "/api-explorer"

    def test_none_falls_back(self) -> None:
        s = _load(APCORE_EXPLORER_URL_PREFIX=None)
        assert s.explorer_url_prefix == "/apcore"

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_EXPLORER_URL_PREFIX"):
            _load(APCORE_EXPLORER_URL_PREFIX=123)

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_EXPLORER_URL_PREFIX"):
            _load(APCORE_EXPLORER_URL_PREFIX="")
```

Also update `TestAllDefaults.test_defaults` to add:
```python
assert settings.explorer_enabled is False
assert settings.explorer_url_prefix == "/apcore"
```

Update `TestNoneFallback.test_none_falls_back_to_default` parametrize to add:
```python
("APCORE_EXPLORER_ENABLED", "explorer_enabled", False),
("APCORE_EXPLORER_URL_PREFIX", "explorer_url_prefix", "/apcore"),
```

Update `TestCombinedSettings.test_dataclass_fields_count`:
```python
# 26 existing + 2 explorer = 28
assert len(fields) == 28
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py::TestExplorerEnabled tests/test_config.py::TestExplorerUrlPrefix -v`
Expected: FAIL with `AttributeError`

**Step 3: Write minimal implementation**

In `src/flask_apcore/config.py`:

Add defaults after line 41:
```python
# Explorer defaults
DEFAULT_EXPLORER_ENABLED = False
DEFAULT_EXPLORER_URL_PREFIX = "/apcore"
```

Add fields to `ApcoreSettings` dataclass:
```python
# Explorer
explorer_enabled: bool
explorer_url_prefix: str
```

Add validation in `load_settings()` before the final `return ApcoreSettings(...)`:
```python
# === Explorer settings ===

# --- explorer_enabled ---
explorer_enabled = app.config.get("APCORE_EXPLORER_ENABLED", DEFAULT_EXPLORER_ENABLED)
if explorer_enabled is None:
    explorer_enabled = DEFAULT_EXPLORER_ENABLED
if not isinstance(explorer_enabled, bool):
    actual = type(explorer_enabled).__name__
    raise ValueError(f"APCORE_EXPLORER_ENABLED must be a boolean. Got: {actual}")

# --- explorer_url_prefix ---
explorer_url_prefix = app.config.get("APCORE_EXPLORER_URL_PREFIX", DEFAULT_EXPLORER_URL_PREFIX)
if explorer_url_prefix is None:
    explorer_url_prefix = DEFAULT_EXPLORER_URL_PREFIX
if not isinstance(explorer_url_prefix, str) or len(explorer_url_prefix) == 0:
    raise ValueError("APCORE_EXPLORER_URL_PREFIX must be a non-empty string.")
```

Add to `return ApcoreSettings(...)`:
```python
explorer_enabled=explorer_enabled,
explorer_url_prefix=explorer_url_prefix,
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/flask_apcore/config.py tests/test_config.py
git commit -m "feat: add APCORE_EXPLORER_ENABLED and APCORE_EXPLORER_URL_PREFIX config"
```

---

### Task 6: Web Blueprint — JSON API + HTML Explorer

**Files:**
- Create: `src/flask_apcore/web/__init__.py`
- Create: `src/flask_apcore/web/api.py`
- Create: `src/flask_apcore/web/views.py`
- Create: `tests/test_web.py`

**Step 1: Write the failing tests**

Create `tests/test_web.py`:

```python
"""Tests for flask_apcore.web — Explorer Blueprint (API + HTML)."""

from __future__ import annotations

import json

import pytest
from flask import Flask

from flask_apcore import Apcore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def list_items() -> dict:
    """List all items."""
    return {"items": []}


def create_item(title: str) -> dict:
    """Create a new item."""
    return {"title": title}


@pytest.fixture()
def explorer_app(tmp_path):
    """Flask app with explorer enabled and routes registered."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
    app.config["APCORE_AUTO_DISCOVER"] = False
    app.config["APCORE_EXPLORER_ENABLED"] = True

    app.add_url_rule("/items", "list_items", list_items, methods=["GET"])
    app.add_url_rule("/items", "create_item", create_item, methods=["POST"])

    Apcore(app)

    # Register modules via scan
    with app.app_context():
        from flask_apcore.scanners import auto_detect_scanner

        scanner = auto_detect_scanner(app)
        modules = scanner.scan(app)

        from flask_apcore.output.registry_writer import RegistryWriter

        writer = RegistryWriter()
        writer.write(modules, app.extensions["apcore"]["registry"])

    return app


@pytest.fixture()
def client(explorer_app):
    return explorer_app.test_client()


@pytest.fixture()
def disabled_app(tmp_path):
    """Flask app with explorer disabled (default)."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
    app.config["APCORE_AUTO_DISCOVER"] = False
    Apcore(app)
    return app


# ---------------------------------------------------------------------------
# Explorer disabled by default
# ---------------------------------------------------------------------------


class TestExplorerDisabled:
    def test_no_explorer_routes_when_disabled(self, disabled_app):
        client = disabled_app.test_client()
        resp = client.get("/apcore/modules")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# JSON API: GET /apcore/modules
# ---------------------------------------------------------------------------


class TestModulesListAPI:
    def test_returns_json_list(self, client):
        resp = client.get("/apcore/modules")
        assert resp.status_code == 200
        assert resp.content_type == "application/json"
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_module_has_summary_fields(self, client):
        resp = client.get("/apcore/modules")
        data = resp.get_json()
        entry = data[0]
        assert "module_id" in entry
        assert "description" in entry
        assert "tags" in entry
        assert "http_method" in entry
        assert "url_rule" in entry


# ---------------------------------------------------------------------------
# JSON API: GET /apcore/modules/<module_id>
# ---------------------------------------------------------------------------


class TestModuleDetailAPI:
    def test_returns_single_module(self, client):
        # First get list to find a valid module_id
        listing = client.get("/apcore/modules").get_json()
        mid = listing[0]["module_id"]

        resp = client.get(f"/apcore/modules/{mid}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["module_id"] == mid
        assert "input_schema" in data
        assert "output_schema" in data

    def test_not_found_returns_404(self, client):
        resp = client.get("/apcore/modules/nonexistent.module")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# JSON API: GET /apcore/openapi.json
# ---------------------------------------------------------------------------


class TestOpenAPIEndpoint:
    def test_returns_openapi_spec(self, client):
        resp = client.get("/apcore/openapi.json")
        assert resp.status_code == 200
        spec = resp.get_json()
        assert spec["openapi"] == "3.1.0"
        assert "paths" in spec
        assert len(spec["paths"]) >= 1


# ---------------------------------------------------------------------------
# HTML: GET /apcore/
# ---------------------------------------------------------------------------


class TestExplorerHTML:
    def test_returns_html(self, client):
        resp = client.get("/apcore/")
        assert resp.status_code == 200
        assert "text/html" in resp.content_type
        assert b"<html" in resp.data

    def test_html_contains_fetch_script(self, client):
        resp = client.get("/apcore/")
        # Should have JS that fetches /apcore/modules
        assert b"fetch" in resp.data


# ---------------------------------------------------------------------------
# Custom URL prefix
# ---------------------------------------------------------------------------


class TestCustomUrlPrefix:
    def test_custom_prefix(self, tmp_path):
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
        app.config["APCORE_AUTO_DISCOVER"] = False
        app.config["APCORE_EXPLORER_ENABLED"] = True
        app.config["APCORE_EXPLORER_URL_PREFIX"] = "/my-explorer"
        Apcore(app)

        client = app.test_client()
        # Default prefix should not work
        resp = client.get("/apcore/modules")
        assert resp.status_code == 404

        # Custom prefix should work
        resp = client.get("/my-explorer/modules")
        assert resp.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `src/flask_apcore/web/__init__.py`:

```python
"""Explorer Blueprint for flask-apcore.

Provides HTTP API endpoints and an HTML viewer for registered modules.
Activated by APCORE_EXPLORER_ENABLED=True.
"""

from __future__ import annotations

from flask import Blueprint


def create_explorer_blueprint(url_prefix: str = "/apcore") -> Blueprint:
    """Create and return the explorer Blueprint.

    Args:
        url_prefix: URL prefix for all explorer routes.

    Returns:
        Configured Flask Blueprint.
    """
    bp = Blueprint("apcore_explorer", __name__, url_prefix=url_prefix)

    from flask_apcore.web.api import register_api_routes
    from flask_apcore.web.views import register_view_routes

    register_api_routes(bp)
    register_view_routes(bp)

    return bp
```

Create `src/flask_apcore/web/api.py`:

```python
"""JSON API endpoints for the explorer Blueprint."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from flask import Blueprint, current_app, jsonify


def register_api_routes(bp: Blueprint) -> None:
    """Register API routes on the given Blueprint."""

    @bp.route("/modules")
    def list_modules():
        """Return summary list of all registered modules."""
        registry = current_app.extensions["apcore"]["registry"]
        modules = []
        for module_id, module in registry.iter():
            metadata = getattr(module, "metadata", None) or {}
            entry = {
                "module_id": module_id,
                "description": getattr(module, "description", ""),
                "tags": list(getattr(module, "tags", None) or []),
                "http_method": metadata.get("http_method", ""),
                "url_rule": metadata.get("url_rule", ""),
                "version": getattr(module, "version", "1.0.0"),
            }
            modules.append(entry)
        return jsonify(modules)

    @bp.route("/modules/<path:module_id>")
    def get_module(module_id: str):
        """Return full detail for a single module."""
        registry = current_app.extensions["apcore"]["registry"]
        descriptor = registry.get_definition(module_id)
        if descriptor is None:
            return jsonify({"error": f"Module '{module_id}' not found"}), 404

        annotations_dict: dict[str, Any] | None = None
        if descriptor.annotations is not None:
            annotations_dict = asdict(descriptor.annotations)

        result = {
            "module_id": descriptor.module_id,
            "description": descriptor.description,
            "documentation": descriptor.documentation,
            "tags": descriptor.tags,
            "version": descriptor.version,
            "annotations": annotations_dict,
            "metadata": descriptor.metadata,
            "http_method": descriptor.metadata.get("http_method", ""),
            "url_rule": descriptor.metadata.get("url_rule", ""),
            "input_schema": descriptor.input_schema,
            "output_schema": descriptor.output_schema,
        }
        return jsonify(result)

    @bp.route("/openapi.json")
    def openapi_spec():
        """Return live-generated OpenAPI 3.1 spec."""
        registry = current_app.extensions["apcore"]["registry"]
        settings = current_app.extensions["apcore"]["settings"]

        from flask_apcore.web._openapi import registry_to_openapi

        spec = registry_to_openapi(
            registry,
            title=settings.server_name,
            version=getattr(settings, "server_version", None) or "1.0.0",
        )
        return jsonify(spec)
```

Create `src/flask_apcore/web/_openapi.py`:

```python
"""OpenAPI spec generation from Registry for the web endpoint."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any


def registry_to_openapi(
    registry: Any,
    *,
    title: str,
    version: str,
) -> dict[str, Any]:
    """Generate OpenAPI 3.1 spec from a Registry's registered modules."""
    paths: dict[str, Any] = {}

    for module_id, module in registry.iter():
        metadata = getattr(module, "metadata", None) or {}
        http_method = metadata.get("http_method", "get").lower()
        url_rule = metadata.get("url_rule", f"/{module_id}")

        descriptor = registry.get_definition(module_id)
        if descriptor is None:
            continue

        if url_rule not in paths:
            paths[url_rule] = {}

        operation: dict[str, Any] = {
            "operationId": module_id,
            "summary": descriptor.description,
            "tags": descriptor.tags,
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": descriptor.output_schema,
                        }
                    },
                }
            },
        }

        if descriptor.documentation:
            operation["description"] = descriptor.documentation

        if descriptor.annotations is not None:
            operation["x-apcore-annotations"] = asdict(descriptor.annotations)

        if http_method in ("post", "put", "patch"):
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": descriptor.input_schema,
                    }
                },
            }
        else:
            props = descriptor.input_schema.get("properties", {})
            required = descriptor.input_schema.get("required", [])
            if props:
                parameters = []
                for name, schema in props.items():
                    parameters.append({
                        "name": name,
                        "in": "query",
                        "required": name in required,
                        "schema": schema,
                    })
                operation["parameters"] = parameters

        paths[url_rule][http_method] = operation

    return {
        "openapi": "3.1.0",
        "info": {"title": title, "version": version},
        "paths": paths,
    }
```

Create `src/flask_apcore/web/views.py`:

```python
"""HTML explorer page for the explorer Blueprint."""

from __future__ import annotations

from flask import Blueprint, Response


_EXPLORER_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>apcore Explorer</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
         background: #f5f5f5; color: #333; padding: 24px; }
  h1 { font-size: 1.4rem; margin-bottom: 16px; }
  .module-list { list-style: none; }
  .module-item { background: #fff; border: 1px solid #ddd; border-radius: 6px;
                 padding: 12px 16px; margin-bottom: 8px; cursor: pointer; }
  .module-item:hover { border-color: #888; }
  .module-id { font-weight: 600; }
  .module-method { display: inline-block; font-size: 0.75rem; font-weight: 700;
                   padding: 2px 6px; border-radius: 3px; margin-right: 8px;
                   color: #fff; }
  .method-get { background: #61affe; }
  .method-post { background: #49cc90; }
  .method-put { background: #fca130; }
  .method-delete { background: #f93e3e; }
  .method-patch { background: #50e3c2; }
  .module-desc { color: #666; font-size: 0.9rem; margin-top: 4px; }
  .detail { background: #fff; border: 1px solid #ddd; border-radius: 6px;
            padding: 16px; margin-top: 16px; display: none; }
  .detail.active { display: block; }
  .detail h2 { font-size: 1.1rem; margin-bottom: 12px; }
  .schema-label { font-weight: 600; margin-top: 12px; display: block; }
  pre { background: #282c34; color: #abb2bf; padding: 12px; border-radius: 4px;
        overflow-x: auto; font-size: 0.85rem; margin-top: 4px; }
  .tag { display: inline-block; background: #e8e8e8; padding: 2px 8px;
         border-radius: 3px; font-size: 0.75rem; margin-right: 4px; }
  #loading { color: #888; }
</style>
</head>
<body>
<h1>apcore Explorer</h1>
<div id="loading">Loading modules...</div>
<ul class="module-list" id="modules"></ul>
<div class="detail" id="detail"></div>
<script>
const BASE = document.currentScript ? '' : '';
(function() {
  const base = window.location.pathname.replace(/\\/$/, '');
  const modulesEl = document.getElementById('modules');
  const detailEl = document.getElementById('detail');
  const loadingEl = document.getElementById('loading');

  fetch(base + '/modules')
    .then(r => r.json())
    .then(modules => {
      loadingEl.style.display = 'none';
      modules.forEach(m => {
        const li = document.createElement('li');
        li.className = 'module-item';
        const method = (m.http_method || 'GET').toUpperCase();
        li.innerHTML = `
          <span class="module-method method-${method.toLowerCase()}">${method}</span>
          <span class="module-id">${m.module_id}</span>
          <span style="color:#888;font-size:0.85rem">${m.url_rule || ''}</span>
          <div class="module-desc">${m.description || ''}</div>
          <div>${(m.tags||[]).map(t => '<span class="tag">'+t+'</span>').join('')}</div>
        `;
        li.onclick = () => loadDetail(m.module_id);
        modulesEl.appendChild(li);
      });
    })
    .catch(e => { loadingEl.textContent = 'Error loading modules: ' + e; });

  function loadDetail(id) {
    fetch(base + '/modules/' + id)
      .then(r => r.json())
      .then(d => {
        detailEl.className = 'detail active';
        detailEl.innerHTML = `
          <h2>${d.module_id}</h2>
          <p>${d.documentation || d.description || ''}</p>
          <span class="schema-label">Input Schema</span>
          <pre>${JSON.stringify(d.input_schema, null, 2)}</pre>
          <span class="schema-label">Output Schema</span>
          <pre>${JSON.stringify(d.output_schema, null, 2)}</pre>
          ${d.annotations ? '<span class="schema-label">Annotations</span><pre>' + JSON.stringify(d.annotations, null, 2) + '</pre>' : ''}
          ${d.metadata ? '<span class="schema-label">Metadata</span><pre>' + JSON.stringify(d.metadata, null, 2) + '</pre>' : ''}
        `;
      });
  }
})();
</script>
</body>
</html>
"""


def register_view_routes(bp: Blueprint) -> None:
    """Register HTML view routes on the given Blueprint."""

    @bp.route("/")
    def explorer_page():
        """Serve the explorer HTML page."""
        return Response(_EXPLORER_HTML, content_type="text/html")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_web.py -v`
Expected: FAIL — Blueprint not registered yet (Task 7)

This is expected. The Blueprint creation code is ready, but `extension.py` doesn't register it yet. Proceed to Task 7.

**Step 5: (deferred to Task 7)**

---

### Task 7: Extension — Register Explorer Blueprint

**Files:**
- Modify: `src/flask_apcore/extension.py:104-112`
- Modify: `tests/test_extension.py`

**Step 1: Write the failing test**

Add to `tests/test_extension.py`:

```python
# ===========================================================================
# Explorer Blueprint registration
# ===========================================================================


class TestExplorerBlueprint:
    """Explorer Blueprint is registered when APCORE_EXPLORER_ENABLED=True."""

    def test_explorer_registered_when_enabled(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(tmp_path, APCORE_EXPLORER_ENABLED=True)
        Apcore(app)

        # Check that apcore_explorer blueprint is registered
        assert "apcore_explorer" in app.blueprints

    def test_explorer_not_registered_when_disabled(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(tmp_path, APCORE_EXPLORER_ENABLED=False)
        Apcore(app)

        assert "apcore_explorer" not in app.blueprints

    def test_explorer_not_registered_by_default(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(tmp_path)
        Apcore(app)

        assert "apcore_explorer" not in app.blueprints

    def test_custom_url_prefix(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(
            tmp_path,
            APCORE_EXPLORER_ENABLED=True,
            APCORE_EXPLORER_URL_PREFIX="/my-api",
        )
        Apcore(app)

        assert "apcore_explorer" in app.blueprints
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_extension.py::TestExplorerBlueprint -v`
Expected: FAIL

**Step 3: Write minimal implementation**

In `src/flask_apcore/extension.py`, after the CLI registration block (after line 110 `app.cli.add_command(apcore_cli)`), add:

```python
# 5b. Register explorer Blueprint if enabled
if settings.explorer_enabled:
    from flask_apcore.web import create_explorer_blueprint

    bp = create_explorer_blueprint(settings.explorer_url_prefix)
    app.register_blueprint(bp)
```

**Step 4: Run tests to verify everything passes**

Run: `pytest tests/test_extension.py tests/test_web.py -v`
Expected: ALL PASS

**Step 5: Commit everything from Task 6 + Task 7**

```bash
git add src/flask_apcore/web/__init__.py src/flask_apcore/web/api.py src/flask_apcore/web/_openapi.py src/flask_apcore/web/views.py src/flask_apcore/extension.py tests/test_web.py tests/test_extension.py
git commit -m "feat: add explorer Blueprint with JSON API, OpenAPI endpoint, and HTML viewer"
```

---

### Task 8: Full Integration Test

**Files:**
- Test: `tests/test_integration.py` (add to existing)

**Step 1: Write integration test**

Read existing `tests/test_integration.py` first, then add:

```python
class TestExplorerIntegration:
    """End-to-end: scan -> register -> explore via HTTP."""

    def test_scan_then_explore(self, tmp_path):
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
        app.config["APCORE_AUTO_DISCOVER"] = False
        app.config["APCORE_EXPLORER_ENABLED"] = True

        @app.route("/tasks", methods=["GET"])
        def list_tasks():
            """List all tasks."""
            return {"tasks": []}

        @app.route("/tasks", methods=["POST"])
        def create_task():
            """Create a task."""
            return {"id": 1}

        Apcore(app)

        # Scan and register
        runner = app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan"])
        assert result.exit_code == 0

        # Explore via HTTP
        client = app.test_client()

        # List modules
        resp = client.get("/apcore/modules")
        assert resp.status_code == 200
        modules = resp.get_json()
        assert len(modules) >= 2

        # Get detail
        mid = modules[0]["module_id"]
        resp = client.get(f"/apcore/modules/{mid}")
        assert resp.status_code == 200
        detail = resp.get_json()
        assert "input_schema" in detail

        # OpenAPI spec
        resp = client.get("/apcore/openapi.json")
        assert resp.status_code == 200
        spec = resp.get_json()
        assert spec["openapi"] == "3.1.0"

        # HTML page
        resp = client.get("/apcore/")
        assert resp.status_code == 200
        assert b"apcore Explorer" in resp.data
```

**Step 2: Run test**

Run: `pytest tests/test_integration.py::TestExplorerIntegration -v`
Expected: PASS

**Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add explorer end-to-end integration test"
```

---

### Task 9: Final Verification

**Step 1: Run full test suite with coverage**

```bash
pytest tests/ -v --tb=short
```

**Step 2: Run ruff linter**

```bash
ruff check src/flask_apcore/ tests/
```

**Step 3: Run mypy**

```bash
mypy src/flask_apcore/
```

**Step 4: Fix any issues found, then commit**

```bash
git add -A
git commit -m "chore: fix lint and type issues"
```
