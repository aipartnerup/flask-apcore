"""marshmallow Schema to JSON Schema conversion backend.

Used primarily with flask-smorest, where marshmallow schemas are attached
to view functions via @blp.arguments() and @blp.response() decorators.

Field type mapping (from tech design section 9.3.2):
    fields.String    -> {"type": "string"}
    fields.Integer   -> {"type": "integer"}
    fields.Float     -> {"type": "number"}
    fields.Boolean   -> {"type": "boolean"}
    fields.List      -> {"type": "array", "items": {...}}
    fields.Nested    -> recursive schema
    fields.DateTime  -> {"type": "string", "format": "date-time"}
    fields.Date      -> {"type": "string", "format": "date"}
    fields.UUID      -> {"type": "string", "format": "uuid"}
    fields.Email     -> {"type": "string", "format": "email"}
    fields.Enum      -> {"type": "string", "enum": [...]}
    Other/Unknown    -> {"type": "string"} (fallback with warning)

marshmallow is an optional dependency; import errors are handled gracefully.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from flask_apcore.schemas._constants import FLASK_TYPE_MAP

logger = logging.getLogger("flask_apcore")


class MarshmallowBackend:
    """Converts marshmallow Schema to JSON Schema.

    Detection: Relies on context dict containing 'marshmallow_input'
    or 'marshmallow_output' keys (populated by SmorestScanner or
    manually by the SchemaDispatcher).

    Priority: second (after Pydantic) in the dispatcher chain.
    """

    def can_handle_input(self, func: Callable[..., Any], context: dict[str, Any] | None = None) -> bool:
        """Return True if context contains a marshmallow input schema."""
        return context is not None and "marshmallow_input" in context

    def infer_input(
        self,
        func: Callable[..., Any],
        url_params: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Convert marshmallow Schema instance to JSON Schema.

        Args:
            func: The view function (unused; schema from context).
            url_params: URL path parameters with their Flask converter types.
            context: Must contain 'marshmallow_input' key.

        Returns:
            JSON Schema dict.
        """
        schema_instance = context["marshmallow_input"]  # type: ignore[index]
        result = self._schema_to_json_schema(schema_instance)

        # Merge URL params
        if url_params:
            for param_name, param_type in url_params.items():
                result["properties"][param_name] = FLASK_TYPE_MAP.get(param_type, {"type": "string"})
                if param_name not in result.get("required", []):
                    result.setdefault("required", []).append(param_name)

        return result

    def can_handle_output(self, func: Callable[..., Any], context: dict[str, Any] | None = None) -> bool:
        """Return True if context contains a marshmallow output schema."""
        return context is not None and "marshmallow_output" in context

    def infer_output(
        self,
        func: Callable[..., Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Convert marshmallow output Schema to JSON Schema."""
        schema_instance = context["marshmallow_output"]  # type: ignore[index]
        return self._schema_to_json_schema(schema_instance)

    def _schema_to_json_schema(self, schema_instance: Any) -> dict[str, Any]:
        """Convert a marshmallow Schema instance to JSON Schema dict.

        Handles both Schema classes and Schema instances. If a class is
        provided, it is instantiated first.
        """
        from marshmallow import Schema

        if isinstance(schema_instance, type) and issubclass(schema_instance, Schema):
            schema_instance = schema_instance()

        result: dict[str, Any] = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        for field_name, field_obj in schema_instance.fields.items():
            result["properties"][field_name] = self._marshmallow_field_to_json_schema(field_obj)
            if field_obj.required:
                result["required"].append(field_name)

        return result

    def _marshmallow_field_to_json_schema(self, field_obj: Any) -> dict[str, Any]:
        """Convert a single marshmallow field to a JSON Schema property.

        Handles: Email, String, Integer, Float, Boolean, List, Nested,
                 DateTime, Date, UUID, Enum.

        Note: isinstance checks are ordered so that subclasses are tested
        before their parents (e.g., Email before String, since Email
        inherits from String).
        """
        from marshmallow import fields

        schema: dict[str, Any] = {}

        # Email must come before String (Email is a subclass of String)
        if isinstance(field_obj, fields.Email):
            schema = {"type": "string", "format": "email"}
        elif isinstance(field_obj, fields.UUID):
            schema = {"type": "string", "format": "uuid"}
        elif isinstance(field_obj, fields.DateTime):
            schema = {"type": "string", "format": "date-time"}
        elif isinstance(field_obj, fields.Date):
            schema = {"type": "string", "format": "date"}
        elif isinstance(field_obj, fields.String):
            schema = {"type": "string"}
        elif isinstance(field_obj, fields.Integer):
            schema = {"type": "integer"}
        elif isinstance(field_obj, fields.Float):
            schema = {"type": "number"}
        elif isinstance(field_obj, fields.Boolean):
            schema = {"type": "boolean"}
        elif isinstance(field_obj, fields.List):
            inner = self._marshmallow_field_to_json_schema(field_obj.inner)
            schema = {"type": "array", "items": inner}
        elif isinstance(field_obj, fields.Nested):
            nested_schema = field_obj.nested
            schema = self._schema_to_json_schema(nested_schema)
        elif hasattr(fields, "Enum") and isinstance(field_obj, fields.Enum):
            enum_values = [e.value for e in field_obj.enum]
            schema = {"type": "string", "enum": enum_values}
        else:
            logger.warning(
                "Unknown marshmallow field type: %s, defaulting to string",
                type(field_obj),
            )
            schema = {"type": "string"}

        # Extract validation constraints
        self._apply_validators(field_obj, schema)

        return schema

    def _apply_validators(self, field_obj: Any, schema: dict[str, Any]) -> None:
        """Extract marshmallow validators and add to JSON Schema.

        Supported validators:
        - validate.Length -> minLength / maxLength
        - validate.Range -> minimum / maximum
        """
        from marshmallow import validate

        for validator in field_obj.validators:
            if isinstance(validator, validate.Length):
                if validator.min is not None:
                    schema["minLength"] = validator.min
                if validator.max is not None:
                    schema["maxLength"] = validator.max
            elif isinstance(validator, validate.Range):
                if validator.min is not None:
                    schema["minimum"] = validator.min
                if validator.max is not None:
                    schema["maximum"] = validator.max
