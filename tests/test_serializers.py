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
