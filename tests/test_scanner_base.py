"""Tests for scanners/base.py — ScannedModule and BaseScanner."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from apcore import ModuleAnnotations

from flask_apcore.scanners.base import BaseScanner, ScannedModule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_module(
    module_id: str = "test.get",
    description: str = "Test endpoint",
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    target: str = "myapp.views:get_items",
    http_method: str = "GET",
    url_rule: str = "/items",
    version: str = "1.0.0",
    annotations: ModuleAnnotations | None = None,
    documentation: str | None = None,
    metadata: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> ScannedModule:
    return ScannedModule(
        module_id=module_id,
        description=description,
        input_schema=input_schema or {"type": "object", "properties": {}},
        output_schema=output_schema or {"type": "object", "properties": {}},
        tags=tags or [],
        target=target,
        http_method=http_method,
        url_rule=url_rule,
        version=version,
        annotations=annotations,
        documentation=documentation,
        metadata=metadata or {},
        warnings=warnings or [],
    )


class _DummyScanner(BaseScanner):
    """Concrete scanner for testing base class methods."""

    def scan(self, app, include=None, exclude=None):
        return []

    def get_source_name(self):
        return "dummy"


# ---------------------------------------------------------------------------
# ScannedModule creation
# ---------------------------------------------------------------------------


class TestScannedModuleCreation:
    """Test ScannedModule dataclass with all fields."""

    def test_basic_fields(self):
        m = _make_module()
        assert m.module_id == "test.get"
        assert m.description == "Test endpoint"
        assert m.http_method == "GET"
        assert m.url_rule == "/items"
        assert m.target == "myapp.views:get_items"
        assert m.version == "1.0.0"

    def test_annotations_field(self):
        ann = ModuleAnnotations(readonly=True)
        m = _make_module(annotations=ann)
        assert m.annotations is not None
        assert m.annotations.readonly is True
        assert m.annotations.destructive is False

    def test_annotations_none_by_default(self):
        m = _make_module()
        assert m.annotations is None

    def test_documentation_field(self):
        m = _make_module(documentation="Full docstring\nwith multiple lines.")
        assert m.documentation == "Full docstring\nwith multiple lines."

    def test_documentation_none_by_default(self):
        m = _make_module()
        assert m.documentation is None

    def test_metadata_field(self):
        m = _make_module(metadata={"source": "native", "custom": 42})
        assert m.metadata == {"source": "native", "custom": 42}

    def test_metadata_empty_by_default(self):
        m = _make_module()
        assert m.metadata == {}

    def test_warnings_field(self):
        m = _make_module(warnings=["no type hints"])
        assert m.warnings == ["no type hints"]

    def test_all_new_fields_together(self):
        ann = ModuleAnnotations(destructive=True, requires_approval=True)
        m = _make_module(
            annotations=ann,
            documentation="Delete a user permanently.",
            metadata={"source": "native", "risk": "high"},
        )
        assert m.annotations.destructive is True
        assert m.annotations.requires_approval is True
        assert m.documentation == "Delete a user permanently."
        assert m.metadata["risk"] == "high"


# ---------------------------------------------------------------------------
# filter_modules
# ---------------------------------------------------------------------------


class TestFilterModules:
    """Test BaseScanner.filter_modules() with regex patterns."""

    def setup_method(self):
        self.scanner = _DummyScanner()
        self.modules = [
            _make_module(module_id="users.list.get"),
            _make_module(module_id="users.create.post"),
            _make_module(module_id="items.list.get"),
            _make_module(module_id="items.detail.get"),
            _make_module(module_id="admin.dashboard.get"),
        ]

    def test_no_filters(self):
        result = self.scanner.filter_modules(self.modules)
        assert len(result) == 5

    def test_include_pattern(self):
        result = self.scanner.filter_modules(self.modules, include=r"^users\.")
        assert len(result) == 2
        assert all(m.module_id.startswith("users.") for m in result)

    def test_exclude_pattern(self):
        result = self.scanner.filter_modules(self.modules, exclude=r"^admin\.")
        assert len(result) == 4
        assert all(not m.module_id.startswith("admin.") for m in result)

    def test_include_and_exclude(self):
        result = self.scanner.filter_modules(self.modules, include=r"\.get$", exclude=r"^admin\.")
        assert len(result) == 3
        ids = {m.module_id for m in result}
        assert ids == {"users.list.get", "items.list.get", "items.detail.get"}

    def test_include_matches_none(self):
        result = self.scanner.filter_modules(self.modules, include=r"^nonexistent\.")
        assert result == []

    def test_exclude_matches_all(self):
        result = self.scanner.filter_modules(self.modules, exclude=r".*")
        assert result == []


# ---------------------------------------------------------------------------
# _deduplicate_ids
# ---------------------------------------------------------------------------


class TestDeduplicateIds:
    """Test BaseScanner._deduplicate_ids()."""

    def setup_method(self):
        self.scanner = _DummyScanner()

    def test_no_duplicates(self):
        modules = [
            _make_module(module_id="a.get"),
            _make_module(module_id="b.get"),
        ]
        result = self.scanner._deduplicate_ids(modules)
        assert [m.module_id for m in result] == ["a.get", "b.get"]

    def test_two_duplicates(self):
        modules = [
            _make_module(module_id="a.get"),
            _make_module(module_id="a.get"),
        ]
        result = self.scanner._deduplicate_ids(modules)
        assert [m.module_id for m in result] == ["a.get", "a.get_2"]

    def test_three_duplicates(self):
        modules = [
            _make_module(module_id="x.post"),
            _make_module(module_id="x.post"),
            _make_module(module_id="x.post"),
        ]
        result = self.scanner._deduplicate_ids(modules)
        assert [m.module_id for m in result] == ["x.post", "x.post_2", "x.post_3"]

    def test_preserves_other_fields(self):
        modules = [
            _make_module(module_id="a.get", description="first"),
            _make_module(module_id="a.get", description="second"),
        ]
        result = self.scanner._deduplicate_ids(modules)
        assert result[0].description == "first"
        assert result[1].description == "second"
        assert result[1].module_id == "a.get_2"


# ---------------------------------------------------------------------------
# _is_api_route
# ---------------------------------------------------------------------------


class TestIsApiRoute:
    """Test BaseScanner._is_api_route()."""

    def setup_method(self):
        self.scanner = _DummyScanner()

    def _make_rule(self, endpoint: str) -> MagicMock:
        rule = MagicMock()
        rule.endpoint = endpoint
        return rule

    def test_static_route_skipped(self):
        rule = self._make_rule("static")
        assert self.scanner._is_api_route(rule, lambda: None) is False

    def test_blueprint_static_skipped(self):
        rule = self._make_rule("admin.static")
        assert self.scanner._is_api_route(rule, lambda: None) is False

    def test_api_route_passes(self):
        rule = self._make_rule("users.list_users")
        assert self.scanner._is_api_route(rule, lambda: None) is True

    def test_simple_endpoint_passes(self):
        rule = self._make_rule("index")
        assert self.scanner._is_api_route(rule, lambda: None) is True
