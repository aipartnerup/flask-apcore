"""Tests for flask_apcore.serializers -- shared serialization functions."""

from __future__ import annotations

from typing import Any

from apcore import ModuleAnnotations

from flask_apcore.scanners.base import ScannedModule


_UNSET = object()


def _make_module(
    module_id: str = "items.get",
    http_method: str = "GET",
    url_rule: str = "/items",
    annotations: ModuleAnnotations | None = _UNSET,  # type: ignore[assignment]
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
        annotations=(
            ModuleAnnotations(readonly=True) if annotations is _UNSET else annotations
        ),
        documentation=documentation,
        metadata=metadata or {"source": "native"},
        warnings=[],
    )
    defaults.update(kwargs)
    return ScannedModule(**defaults)


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
