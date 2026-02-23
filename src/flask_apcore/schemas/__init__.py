"""Schema inference subpackage for flask-apcore.

Provides the SchemaDispatcher that routes schema inference to the best
available backend using the priority chain:
    Pydantic (highest) > marshmallow > type hints (fallback)

From tech design sections 9.1--9.4:
- SchemaDispatcher.infer_input_schema(func, url_params, extra_context)
- SchemaDispatcher.infer_output_schema(func, extra_context)
- Backends implement can_handle_input/output and infer_input/output
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Protocol, runtime_checkable

logger = logging.getLogger("flask_apcore")


@runtime_checkable
class SchemaBackend(Protocol):
    """Protocol for schema inference backends.

    Each backend implements detection (can_handle) and conversion (infer)
    for both input and output schemas.
    """

    def can_handle_input(self, func: Callable, context: dict | None = None) -> bool: ...

    def infer_input(
        self, func: Callable, url_params: dict[str, str] | None = None, context: dict | None = None
    ) -> dict[str, Any]: ...

    def can_handle_output(self, func: Callable, context: dict | None = None) -> bool: ...

    def infer_output(self, func: Callable, context: dict | None = None) -> dict[str, Any]: ...


class SchemaDispatcher:
    """Routes schema inference to the best available backend.

    Detection precedence for input_schema:
    1. Pydantic: function has Pydantic BaseModel-typed parameters
    2. Marshmallow: function has marshmallow Schema associated (via context)
    3. Type hints: function has standard Python type annotations
    4. Fallback: empty schema

    Detection precedence for output_schema follows the same order.
    """

    def __init__(self) -> None:
        self._backends: list[SchemaBackend] = []
        self._register_available_backends()

    def _register_available_backends(self) -> None:
        """Register backends based on available imports.

        Order matters: Pydantic first, marshmallow second (optional),
        type hints last (always available).
        """
        from flask_apcore.schemas.pydantic_backend import PydanticBackend
        from flask_apcore.schemas.typehints_backend import TypeHintsBackend

        self._backends.append(PydanticBackend())

        # Optional: marshmallow (inserted between pydantic and typehints)
        try:
            import marshmallow  # noqa: F401
            from flask_apcore.schemas.marshmallow_backend import MarshmallowBackend

            self._backends.append(MarshmallowBackend())
        except ImportError:
            logger.debug("marshmallow not installed; MarshmallowBackend not available")

        self._backends.append(TypeHintsBackend())

    def infer_input_schema(
        self,
        func: Callable,
        url_params: dict[str, str] | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Infer JSON Schema for a function's input.

        Iterates through registered backends in priority order.
        The first backend whose can_handle_input() returns True is used.

        Args:
            func: The view function to analyze.
            url_params: URL path parameters with their Flask converter types.
            extra_context: Additional context (e.g., marshmallow schema from smorest).

        Returns:
            JSON Schema dict for the function's input.
        """
        for backend in self._backends:
            if backend.can_handle_input(func, context=extra_context):
                backend_name = type(backend).__name__
                logger.debug(
                    "Schema input inference: selected %s for %s",
                    backend_name,
                    getattr(func, "__name__", repr(func)),
                )
                return backend.infer_input(func, url_params=url_params, context=extra_context)

        # Fallback: empty schema
        logger.debug(
            "Schema input inference: no backend matched for %s, using fallback empty schema",
            getattr(func, "__name__", repr(func)),
        )
        return {"type": "object", "properties": {}}

    def infer_output_schema(
        self,
        func: Callable,
        extra_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Infer JSON Schema for a function's output.

        Args:
            func: The view function to analyze.
            extra_context: Additional context (e.g., marshmallow response schema).

        Returns:
            JSON Schema dict for the function's output.
        """
        for backend in self._backends:
            if backend.can_handle_output(func, context=extra_context):
                backend_name = type(backend).__name__
                logger.debug(
                    "Schema output inference: selected %s for %s",
                    backend_name,
                    getattr(func, "__name__", repr(func)),
                )
                return backend.infer_output(func, context=extra_context)

        # Fallback: permissive schema
        logger.debug(
            "Schema output inference: no backend matched for %s, using fallback empty schema",
            getattr(func, "__name__", repr(func)),
        )
        return {"type": "object", "properties": {}}
