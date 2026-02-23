"""Python type hints to JSON Schema conversion backend.

This is the fallback backend for native Flask routes that have type
annotations but no Pydantic or marshmallow schemas.

Type mapping table (from tech design section 9.3.3):
    str         -> {"type": "string"}
    int         -> {"type": "integer"}
    float       -> {"type": "number"}
    bool        -> {"type": "boolean"}
    list        -> {"type": "array"}
    list[T]     -> {"type": "array", "items": {T schema}}
    dict        -> {"type": "object"}
    Optional[T] -> schema for T, not required
    T | None    -> same as Optional[T]
    datetime    -> {"type": "string", "format": "date-time"}
    uuid.UUID   -> {"type": "string", "format": "uuid"}
    unannotated -> skipped with warning
"""

from __future__ import annotations

import datetime
import inspect
import logging
import types
import typing
import uuid
from typing import Any, Callable, Union

from flask_apcore.schemas._constants import FLASK_TYPE_MAP

logger = logging.getLogger("flask_apcore")


class TypeHintsBackend:
    """Python type hints to JSON Schema conversion.

    Priority: lowest (fallback). Used when neither Pydantic nor
    marshmallow backends can handle the function.
    """

    _TYPE_MAP: dict[type, dict[str, Any]] = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
        datetime.datetime: {"type": "string", "format": "date-time"},
        datetime.date: {"type": "string", "format": "date"},
        uuid.UUID: {"type": "string", "format": "uuid"},
    }

    def can_handle_input(self, func: Callable, context: dict | None = None) -> bool:
        """Return True if function has any typed parameters (excluding return, self, cls)."""
        hints = typing.get_type_hints(func, include_extras=True)
        return any(name not in ("return", "self", "cls") for name in hints)

    def infer_input(
        self,
        func: Callable,
        url_params: dict[str, str] | None = None,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Convert function parameter type hints to JSON Schema.

        Args:
            func: The view function to analyze.
            url_params: URL path parameters with their Flask converter types.
            context: Additional context (unused by this backend).

        Returns:
            JSON Schema dict for the function's input.
        """
        hints = typing.get_type_hints(func, include_extras=True)
        sig = inspect.signature(func)

        schema: dict[str, Any] = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        for name, hint in hints.items():
            if name in ("return", "self", "cls"):
                continue

            is_optional = False
            resolved_hint = hint

            # Check for Optional[T] or T | None
            origin = typing.get_origin(hint)
            if origin is Union or isinstance(hint, types.UnionType):
                args = typing.get_args(hint)
                non_none = [a for a in args if a is not type(None)]
                if len(non_none) == 1 and type(None) in args:
                    is_optional = True
                    resolved_hint = non_none[0]

            prop_schema = self._type_to_schema(resolved_hint)
            schema["properties"][name] = prop_schema

            # Determine if required (no default value and not Optional)
            param = sig.parameters.get(name)
            has_default = param is not None and param.default is not inspect.Parameter.empty
            if not is_optional and not has_default:
                schema["required"].append(name)

        # Merge URL params
        if url_params:
            for param_name, param_type in url_params.items():
                schema["properties"][param_name] = FLASK_TYPE_MAP.get(param_type, {"type": "string"})
                if param_name not in schema["required"]:
                    schema["required"].append(param_name)

        return schema

    def can_handle_output(self, func: Callable, context: dict | None = None) -> bool:
        """Return True if function has a return type annotation."""
        hints = typing.get_type_hints(func, include_extras=True)
        return "return" in hints

    def infer_output(self, func: Callable, context: dict | None = None) -> dict[str, Any]:
        """Convert function return type hint to JSON Schema."""
        hints = typing.get_type_hints(func, include_extras=True)
        return_type = hints.get("return")
        if return_type is None:
            return {"type": "object", "properties": {}}
        return self._type_to_schema(return_type)

    def _type_to_schema(self, hint: Any) -> dict[str, Any]:
        """Convert a single Python type to a JSON Schema dict."""
        # Direct type match
        if hint in self._TYPE_MAP:
            return dict(self._TYPE_MAP[hint])

        # Parameterized generics: list[str], dict[str, int], etc.
        origin = typing.get_origin(hint)
        args = typing.get_args(hint)

        if origin is list:
            schema: dict[str, Any] = {"type": "array"}
            if args:
                schema["items"] = self._type_to_schema(args[0])
            return schema

        if origin is dict:
            return {"type": "object"}

        # Fallback
        logger.warning("Unrecognized type hint: %s, defaulting to string", hint)
        return {"type": "string"}
