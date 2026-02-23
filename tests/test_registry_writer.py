"""Tests for output/registry_writer.py — RegistryWriter."""

from __future__ import annotations


import pytest
from apcore import ModuleAnnotations, Registry

from flask_apcore.output.registry_writer import RegistryWriter, _resolve_target
from flask_apcore.scanners.base import ScannedModule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_module(
    module_id: str = "test.get",
    target: str = "tests._test_target_module:sample_handler",
    **kwargs,
) -> ScannedModule:
    defaults = dict(
        module_id=module_id,
        description="Test endpoint",
        input_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        output_schema={"type": "object", "properties": {}},
        tags=["test"],
        target=target,
        http_method="GET",
        url_rule="/test",
        version="1.0.0",
        annotations=ModuleAnnotations(readonly=True),
        documentation="Full docs for test endpoint.",
        metadata={"source": "native"},
        warnings=[],
    )
    defaults.update(kwargs)
    return ScannedModule(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestResolveTarget:
    """Test _resolve_target helper."""

    def test_resolves_function(self):
        func = _resolve_target("tests._test_target_module:sample_handler")
        assert callable(func)
        assert func.__name__ == "sample_handler"

    def test_missing_module_raises(self):
        with pytest.raises(ImportError):
            _resolve_target("nonexistent_module:func")

    def test_missing_attr_raises(self):
        with pytest.raises(AttributeError):
            _resolve_target("tests._test_target_module:nonexistent_func")


class TestRegistryWriter:
    """Test RegistryWriter.write()."""

    def test_registers_modules(self):
        writer = RegistryWriter()
        registry = Registry()
        modules = [_make_module(module_id="test.get")]

        registered = writer.write(modules, registry)

        assert registered == ["test.get"]
        fm = registry.get("test.get")
        assert fm is not None
        assert fm.module_id == "test.get"

    def test_module_accessible_via_registry_get(self):
        writer = RegistryWriter()
        registry = Registry()
        modules = [_make_module(module_id="users.list.get")]

        writer.write(modules, registry)

        fm = registry.get("users.list.get")
        assert fm.description == "Test endpoint"
        assert fm.version == "1.0.0"

    def test_multiple_modules(self):
        writer = RegistryWriter()
        registry = Registry()
        modules = [
            _make_module(module_id="a.get"),
            _make_module(module_id="b.post"),
        ]

        registered = writer.write(modules, registry)

        assert len(registered) == 2
        assert registry.get("a.get") is not None
        assert registry.get("b.post") is not None

    def test_dry_run_does_not_register(self):
        writer = RegistryWriter()
        registry = Registry()
        modules = [_make_module(module_id="test.get")]

        registered = writer.write(modules, registry, dry_run=True)

        assert registered == []
        assert registry.get("test.get") is None

    def test_annotations_passed_to_function_module(self):
        writer = RegistryWriter()
        registry = Registry()
        modules = [
            _make_module(
                module_id="test.get",
                annotations=ModuleAnnotations(readonly=True, destructive=False),
            )
        ]

        writer.write(modules, registry)

        fm = registry.get("test.get")
        assert fm.annotations is not None
        assert fm.annotations["readonly"] is True

    def test_documentation_passed_to_function_module(self):
        writer = RegistryWriter()
        registry = Registry()
        modules = [_make_module(module_id="test.get", documentation="Full docs.")]

        writer.write(modules, registry)

        fm = registry.get("test.get")
        assert fm.documentation == "Full docs."

    def test_metadata_passed_to_function_module(self):
        writer = RegistryWriter()
        registry = Registry()
        modules = [_make_module(module_id="test.get", metadata={"source": "native"})]

        writer.write(modules, registry)

        fm = registry.get("test.get")
        assert fm.metadata is not None
        assert fm.metadata["source"] == "native"

    def test_tags_passed_to_function_module(self):
        writer = RegistryWriter()
        registry = Registry()
        modules = [_make_module(module_id="test.get", tags=["api", "users"])]

        writer.write(modules, registry)

        fm = registry.get("test.get")
        assert fm.tags == ["api", "users"]

    def test_empty_modules_list(self):
        writer = RegistryWriter()
        registry = Registry()

        registered = writer.write([], registry)

        assert registered == []
