"""Tests for output/openapi_writer.py and get_writer('openapi')."""

from __future__ import annotations

import json

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
