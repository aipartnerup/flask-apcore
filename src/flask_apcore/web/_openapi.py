"""OpenAPI spec generation from Registry for the web endpoint."""

from __future__ import annotations

import dataclasses
from typing import Any


def _annotations_to_dict(annotations: Any) -> dict[str, Any] | None:
    """Convert annotations to a dict, handling both dataclass and dict forms."""
    if annotations is None:
        return None
    if isinstance(annotations, dict):
        return annotations
    if dataclasses.is_dataclass(annotations) and not isinstance(annotations, type):
        return dataclasses.asdict(annotations)
    return None


def registry_to_openapi(registry: Any, *, title: str, version: str) -> dict[str, Any]:
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
                        "application/json": {"schema": descriptor.output_schema}
                    },
                }
            },
        }

        if descriptor.documentation:
            operation["description"] = descriptor.documentation

        ann_dict = _annotations_to_dict(descriptor.annotations)
        if ann_dict is not None:
            operation["x-apcore-annotations"] = ann_dict

        if http_method in ("post", "put", "patch"):
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {"schema": descriptor.input_schema}
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
