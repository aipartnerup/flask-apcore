"""Tests for output/yaml_writer.py and output/__init__.py."""

from __future__ import annotations

from typing import Any

import pytest
import yaml
from apcore import ModuleAnnotations

from flask_apcore.output import get_writer
from flask_apcore.output.registry_writer import RegistryWriter
from flask_apcore.output.yaml_writer import YAMLWriter
from flask_apcore.scanners.base import ScannedModule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_module(
    module_id: str = "test.get",
    annotations: ModuleAnnotations | None = None,
    documentation: str | None = None,
    metadata: dict[str, Any] | None = None,
    **kwargs,
) -> ScannedModule:
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
        annotations=annotations,
        documentation=documentation,
        metadata=metadata or {},
        warnings=[],
    )
    defaults.update(kwargs)
    return ScannedModule(**defaults)


# ---------------------------------------------------------------------------
# YAMLWriter tests
# ---------------------------------------------------------------------------


class TestYAMLWriter:
    """Test YAMLWriter generates correct .binding.yaml files."""

    def test_generates_yaml_file(self, tmp_path):
        writer = YAMLWriter()
        modules = [_make_module()]

        results = writer.write(modules, str(tmp_path))

        assert len(results) == 1
        files = list(tmp_path.glob("*.binding.yaml"))
        assert len(files) == 1

    def test_yaml_content_structure(self, tmp_path):
        writer = YAMLWriter()
        modules = [_make_module()]

        results = writer.write(modules, str(tmp_path))

        binding = results[0]
        assert "bindings" in binding
        assert len(binding["bindings"]) == 1
        entry = binding["bindings"][0]
        assert entry["module_id"] == "test.get"
        assert entry["target"] == "myapp.views:get_items"
        assert entry["description"] == "Test endpoint"

    def test_yaml_includes_annotations(self, tmp_path):
        writer = YAMLWriter()
        ann = ModuleAnnotations(readonly=True, destructive=False)
        modules = [_make_module(annotations=ann)]

        results = writer.write(modules, str(tmp_path))

        entry = results[0]["bindings"][0]
        assert "annotations" in entry
        assert entry["annotations"]["readonly"] is True
        assert entry["annotations"]["destructive"] is False

    def test_yaml_annotations_none(self, tmp_path):
        writer = YAMLWriter()
        modules = [_make_module(annotations=None)]

        results = writer.write(modules, str(tmp_path))

        entry = results[0]["bindings"][0]
        # When annotations is None, it should not be in the output
        # or should be None
        assert entry.get("annotations") is None

    def test_yaml_includes_documentation(self, tmp_path):
        writer = YAMLWriter()
        modules = [_make_module(documentation="Full documentation text.")]

        results = writer.write(modules, str(tmp_path))

        entry = results[0]["bindings"][0]
        assert entry["documentation"] == "Full documentation text."

    def test_yaml_documentation_none(self, tmp_path):
        writer = YAMLWriter()
        modules = [_make_module(documentation=None)]

        results = writer.write(modules, str(tmp_path))

        entry = results[0]["bindings"][0]
        assert entry.get("documentation") is None

    def test_yaml_includes_metadata(self, tmp_path):
        writer = YAMLWriter()
        modules = [_make_module(metadata={"source": "native", "extra": "data"})]

        results = writer.write(modules, str(tmp_path))

        entry = results[0]["bindings"][0]
        assert entry["metadata"]["source"] == "native"
        assert entry["metadata"]["extra"] == "data"

    def test_yaml_metadata_empty(self, tmp_path):
        writer = YAMLWriter()
        modules = [_make_module(metadata={})]

        results = writer.write(modules, str(tmp_path))

        entry = results[0]["bindings"][0]
        assert entry["metadata"] == {}

    def test_dry_run_does_not_write(self, tmp_path):
        writer = YAMLWriter()
        modules = [_make_module()]

        results = writer.write(modules, str(tmp_path), dry_run=True)

        assert len(results) == 1
        files = list(tmp_path.glob("*.binding.yaml"))
        assert len(files) == 0

    def test_empty_modules_returns_empty(self, tmp_path):
        writer = YAMLWriter()
        results = writer.write([], str(tmp_path))
        assert results == []

    def test_written_yaml_is_parseable(self, tmp_path):
        writer = YAMLWriter()
        ann = ModuleAnnotations(readonly=True)
        modules = [
            _make_module(
                annotations=ann,
                documentation="Docs here.",
                metadata={"source": "native"},
            )
        ]

        writer.write(modules, str(tmp_path))

        files = list(tmp_path.glob("*.binding.yaml"))
        content = files[0].read_text()
        parsed = yaml.safe_load(content)
        assert parsed["bindings"][0]["annotations"]["readonly"] is True
        assert parsed["bindings"][0]["documentation"] == "Docs here."
        assert parsed["bindings"][0]["metadata"]["source"] == "native"

    def test_multiple_modules_create_multiple_files(self, tmp_path):
        writer = YAMLWriter()
        modules = [
            _make_module(module_id="a.get"),
            _make_module(module_id="b.post"),
        ]

        results = writer.write(modules, str(tmp_path))

        assert len(results) == 2
        files = list(tmp_path.glob("*.binding.yaml"))
        assert len(files) == 2


# ---------------------------------------------------------------------------
# get_writer factory tests
# ---------------------------------------------------------------------------


class TestGetWriter:
    """Test output/__init__.py get_writer() factory."""

    def test_none_returns_registry_writer(self):
        writer = get_writer(None)
        assert isinstance(writer, RegistryWriter)

    def test_yaml_returns_yaml_writer(self):
        writer = get_writer("yaml")
        assert isinstance(writer, YAMLWriter)

    def test_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown output format"):
            get_writer("python")
