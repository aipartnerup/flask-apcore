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
