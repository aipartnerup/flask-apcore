"""Shared constants for schema backends."""

from __future__ import annotations

from typing import Any

# Flask URL converter type to JSON Schema mapping.
# Used by all schema backends to convert URL path parameter types.
FLASK_TYPE_MAP: dict[str, dict[str, Any]] = {
    "int": {"type": "integer"},
    "float": {"type": "number"},
    "string": {"type": "string"},
    "uuid": {"type": "string", "format": "uuid"},
    "path": {"type": "string"},
}
