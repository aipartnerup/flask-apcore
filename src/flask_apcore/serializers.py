"""Shared serialization functions for ScannedModule data.

Pure functions with no Flask dependency. Used by CLI writers and the web
Blueprint to convert ScannedModule instances into dicts.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from flask_apcore.scanners.base import ScannedModule


def annotations_to_dict(annotations: Any) -> dict[str, Any] | None:
    """Convert annotations to a plain dict, handling both dataclass and dict forms.

    This is useful for annotations retrieved from the Registry, where
    RegistryWriter may have already converted them to a dict, or they may
    still be a dataclass instance.

    Args:
        annotations: An annotations object (dict, dataclass instance, or None).

    Returns:
        A plain dict, or None if annotations is None or unrecognised.
    """
    if annotations is None:
        return None
    if isinstance(annotations, dict):
        return annotations
    if dataclasses.is_dataclass(annotations) and not isinstance(annotations, type):
        return dataclasses.asdict(annotations)
    return None


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
        "annotations": (dataclasses.asdict(module.annotations) if module.annotations is not None else None),
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
