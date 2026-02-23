"""Pydantic BaseModel to JSON Schema conversion backend.

This is the highest-priority backend in the schema dispatcher.
Uses Pydantic's model_json_schema() for conversion.

From tech design section 9.3.1:
- Detection: Checks if function parameters have Pydantic BaseModel type hints
- Conversion: Uses hint.model_json_schema() for each Pydantic-typed param
- If single Pydantic param, its schema IS the input_schema
- If multiple Pydantic params, schemas are merged
- URL parameters are added as additional required properties
"""

from __future__ import annotations

import logging
import types
import typing
from typing import Any, Callable, Union, get_args, get_origin

from pydantic import BaseModel

from flask_apcore.schemas._constants import FLASK_TYPE_MAP

logger = logging.getLogger("flask_apcore")

# Sentinel names to skip when inspecting function parameters
_SKIP_NAMES = frozenset({"self", "cls", "return"})


def _extract_pydantic_model(hint: Any) -> type[BaseModel] | None:
    """Extract a Pydantic BaseModel class from a type hint.

    Handles plain BaseModel subclasses, Optional[Model], and list[Model].

    Returns:
        The BaseModel subclass if found, otherwise None.
    """
    # Direct BaseModel subclass
    if isinstance(hint, type) and issubclass(hint, BaseModel):
        return hint

    origin = get_origin(hint)
    args = get_args(hint)

    # Handle Optional[Model] / Model | None (Union[Model, None] or types.UnionType)
    if origin is Union or isinstance(hint, types.UnionType):
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, BaseModel):
                return arg

    # Handle list[Model]
    if origin is list:
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, BaseModel):
                return arg

    return None


class PydanticBackend:
    """Converts Pydantic BaseModel to JSON Schema.

    Detection: Checks if function parameters have Pydantic BaseModel type hints
    or if the return type is a Pydantic BaseModel subclass.

    Priority: highest in the schema dispatcher chain.
    """

    def can_handle_input(self, func: Callable, context: dict | None = None) -> bool:
        """Return True if any parameter type is a Pydantic BaseModel subclass.

        Handles direct BaseModel annotations as well as Optional[Model]
        and list[Model] wrapper types. Ignores ``self``, ``cls``, and
        ``return`` entries in the type hints.
        """
        hints = typing.get_type_hints(func, include_extras=True)
        return any(_extract_pydantic_model(hint) is not None for name, hint in hints.items() if name not in _SKIP_NAMES)

    def infer_input(
        self,
        func: Callable,
        url_params: dict[str, str] | None = None,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Extract JSON Schema from Pydantic-typed parameters.

        If a single Pydantic model parameter exists, its schema IS the
        input_schema.  If multiple exist, they are merged into a single
        schema.  URL parameters are added as additional required properties.

        Args:
            func: The view function to analyze.
            url_params: URL path parameters with their Flask converter types.
            context: Additional context (unused by this backend).

        Returns:
            JSON Schema dict for the function's input.
        """
        hints = typing.get_type_hints(func, include_extras=True)
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        for name, hint in hints.items():
            if name in _SKIP_NAMES:
                continue

            model_cls = _extract_pydantic_model(hint)
            if model_cls is not None:
                model_schema = model_cls.model_json_schema()
                schema["properties"].update(model_schema.get("properties", {}))
                schema["required"].extend(model_schema.get("required", []))

        # Add URL parameters
        if url_params:
            for param_name, param_type in url_params.items():
                schema["properties"][param_name] = FLASK_TYPE_MAP.get(param_type, {"type": "string"})
                if param_name not in schema["required"]:
                    schema["required"].append(param_name)

        return schema

    def can_handle_output(self, func: Callable, context: dict | None = None) -> bool:
        """Return True if return type is a Pydantic BaseModel subclass.

        Also handles Optional[Model] and list[Model] return types.
        """
        hints = typing.get_type_hints(func, include_extras=True)
        return_type = hints.get("return")
        if return_type is None:
            return False
        return _extract_pydantic_model(return_type) is not None or (
            get_origin(return_type) is list
            and any(isinstance(arg, type) and issubclass(arg, BaseModel) for arg in get_args(return_type))
        )

    def infer_output(self, func: Callable, context: dict | None = None) -> dict[str, Any]:
        """Extract JSON Schema from Pydantic return type.

        For direct Model or Optional[Model], returns the model's
        ``model_json_schema()``.  For ``list[Model]``, returns an
        array schema wrapping the model schema.
        """
        hints = typing.get_type_hints(func, include_extras=True)
        return_type = hints["return"]

        # Direct BaseModel subclass
        if isinstance(return_type, type) and issubclass(return_type, BaseModel):
            return return_type.model_json_schema()

        origin = get_origin(return_type)
        args = get_args(return_type)

        # list[Model] -> array schema
        if origin is list:
            for arg in args:
                if isinstance(arg, type) and issubclass(arg, BaseModel):
                    return {
                        "type": "array",
                        "items": arg.model_json_schema(),
                    }

        # Optional[Model] / Model | None -> model schema
        if origin is Union or isinstance(return_type, types.UnionType):
            for arg in args:
                if isinstance(arg, type) and issubclass(arg, BaseModel):
                    return arg.model_json_schema()

        msg = f"Cannot infer output schema for return type: {return_type}"
        raise TypeError(msg)
