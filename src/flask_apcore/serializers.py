"""Shared serialization functions for ScannedModule data.

Pure functions with no Flask dependency. Used by CLI writers (JSONWriter,
OpenAPIWriter) and the web Blueprint to convert ScannedModule instances
into dicts and OpenAPI 3.1 specs.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from flask_apcore.scanners.base import ScannedModule

# HTTP methods whose input_schema maps to a requestBody (not query parameters).
_BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})


def module_to_dict(module: ScannedModule) -> dict[str, Any]:
    """Convert a ScannedModule to a flat dict with all fields.

    The ``annotations`` field is converted to a plain dict via
    ``dataclasses.asdict`` when present, or kept as ``None``.

    Args:
        module: A ScannedModule instance.

    Returns:
        Dictionary representation of the module.
    """
    return {
        "module_id": module.module_id,
        "description": module.description,
        "documentation": module.documentation,
        "http_method": module.http_method,
        "url_rule": module.url_rule,
        "tags": module.tags,
        "version": module.version,
        "target": module.target,
        "annotations": (
            dataclasses.asdict(module.annotations)
            if module.annotations is not None
            else None
        ),
        "metadata": module.metadata,
        "input_schema": module.input_schema,
        "output_schema": module.output_schema,
    }


def modules_to_dicts(modules: list[ScannedModule]) -> list[dict[str, Any]]:
    """Batch-convert a list of ScannedModules to dicts.

    Args:
        modules: List of ScannedModule instances.

    Returns:
        List of dictionary representations.
    """
    return [module_to_dict(m) for m in modules]


def modules_to_openapi(
    modules: list[ScannedModule],
    *,
    title: str,
    version: str,
) -> dict[str, Any]:
    """Convert a list of ScannedModules to an OpenAPI 3.1 specification.

    Mapping rules:
    - Each module maps to a path entry keyed by ``url_rule`` and ``http_method``.
    - For POST/PUT/PATCH methods, ``input_schema`` is placed in ``requestBody``.
    - For GET/DELETE (and others), ``input_schema`` properties become query
      ``parameters``.
    - ``output_schema`` maps to ``responses.200.content.application/json.schema``.
    - ``annotations`` (when present) are added as the ``x-apcore-annotations``
      extension field on the operation.
    - ``tags`` are mapped directly to the operation's ``tags`` field.
    - Multiple methods on the same path are grouped under one path entry.

    Args:
        modules: List of ScannedModule instances.
        title: API title for the info object.
        version: API version for the info object.

    Returns:
        OpenAPI 3.1.0 specification as a nested dict.
    """
    paths: dict[str, dict[str, Any]] = {}

    for module in modules:
        method_lower = module.http_method.lower()
        operation = _build_operation(module)

        if module.url_rule not in paths:
            paths[module.url_rule] = {}

        paths[module.url_rule][method_lower] = operation

    return {
        "openapi": "3.1.0",
        "info": {
            "title": title,
            "version": version,
        },
        "paths": paths,
    }


def _build_operation(module: ScannedModule) -> dict[str, Any]:
    """Build a single OpenAPI operation object from a ScannedModule.

    Args:
        module: A ScannedModule instance.

    Returns:
        OpenAPI operation dict.
    """
    operation: dict[str, Any] = {
        "operationId": module.module_id,
        "summary": module.description,
        "tags": list(module.tags),
    }

    if module.documentation:
        operation["description"] = module.documentation

    # Input schema handling
    if module.http_method.upper() in _BODY_METHODS:
        operation["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": module.input_schema,
                },
            },
        }
    else:
        # GET, DELETE, etc. -- map input_schema properties to query parameters
        parameters = _schema_to_parameters(module.input_schema)
        if parameters:
            operation["parameters"] = parameters

    # Output schema -> 200 response
    operation["responses"] = {
        "200": {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": module.output_schema,
                },
            },
        },
    }

    # Annotations extension
    if module.annotations is not None:
        operation["x-apcore-annotations"] = dataclasses.asdict(module.annotations)

    return operation


def _schema_to_parameters(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a JSON Schema's properties to OpenAPI query parameters.

    Args:
        schema: A JSON Schema dict (expected to have a ``properties`` key).

    Returns:
        List of OpenAPI parameter objects for the ``query`` location.
    """
    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))
    parameters: list[dict[str, Any]] = []

    for name, prop_schema in properties.items():
        parameters.append({
            "name": name,
            "in": "query",
            "required": name in required_fields,
            "schema": prop_schema,
        })

    return parameters
