"""Native Flask route scanner.

Scans native Flask routes via app.url_map and app.view_functions.
This scanner provides baseline schema inference using the SchemaDispatcher
(multi-backend: Pydantic, marshmallow, type hints).

From tech design section 7.5.2:
- Iterates app.url_map.iter_rules()
- Skips static routes and HEAD/OPTIONS-only rules
- Extracts URL path parameters with Flask converter type mapping
- Generates module_id from Blueprint name + function name + method
- Infers schemas via SchemaDispatcher
- Extracts description from docstring (first line)
- Annotation inference from HTTP method (GET -> readonly, DELETE -> destructive, etc.)
- Full docstring extracted as documentation field
- metadata["source"] = "native" for provenance tracking
"""

from __future__ import annotations

import inspect
import logging
import re
from typing import TYPE_CHECKING, Callable

from apcore import ModuleAnnotations

from flask_apcore.scanners.base import BaseScanner, ScannedModule
from flask_apcore.schemas import SchemaDispatcher

if TYPE_CHECKING:
    from flask import Flask
    from werkzeug.routing import Rule

logger = logging.getLogger("flask_apcore")

# Flask URL converter class name to url_params shorthand type mapping.
# The shorthand types ("int", "float", etc.) are resolved to JSON Schema
# by the schema backends via their _FLASK_TYPE_MAP.
_CONVERTER_TYPE_MAP: dict[str, str] = {
    "IntegerConverter": "int",
    "FloatConverter": "float",
    "UUIDConverter": "uuid",
    "PathConverter": "path",
}


class NativeFlaskScanner(BaseScanner):
    """Scans native Flask routes via app.url_map and app.view_functions.

    This scanner provides baseline schema inference using Python type hints
    and function signatures. It does not require any Flask API framework.
    """

    def __init__(self) -> None:
        self._schema_dispatcher = SchemaDispatcher()

    def scan(
        self,
        app: Flask,
        include: str | None = None,
        exclude: str | None = None,
    ) -> list[ScannedModule]:
        """Scan all Flask routes and generate module definitions.

        For each route:
        1. Skip static file routes and template-rendering routes
        2. Extract URL path parameters with types from converters
        3. Infer input_schema via SchemaDispatcher
        4. Infer output_schema from return type annotation
        5. Extract description and documentation from docstring
        6. Infer annotations from HTTP method
        7. Generate module_id from Blueprint + function + method

        Args:
            app: Flask application with active application context.
            include: Regex pattern for module_id inclusion.
            exclude: Regex pattern for module_id exclusion.

        Returns:
            List of ScannedModule instances.
        """
        modules: list[ScannedModule] = []

        for rule in app.url_map.iter_rules():
            if rule.endpoint == "static":
                continue

            view_func = app.view_functions.get(rule.endpoint)
            if view_func is None:
                continue

            if not self._is_api_route(rule, view_func):
                continue

            # Filter methods: skip HEAD, OPTIONS
            methods = rule.methods - {"HEAD", "OPTIONS"}
            if not methods:
                continue

            # Extract URL path parameters
            url_params = self._extract_url_params(rule)

            for method in sorted(methods):
                module_id = self._generate_module_id(rule, view_func, method)
                description = self._extract_description(view_func, rule, method)
                documentation = self._extract_documentation(view_func)
                annotations = self._infer_annotations(method)
                target = self._generate_target(view_func)
                tags = self._extract_tags(rule)

                input_schema = self._schema_dispatcher.infer_input_schema(view_func, url_params=url_params)
                output_schema = self._schema_dispatcher.infer_output_schema(view_func)

                warnings: list[str] = []
                if not input_schema.get("properties"):
                    warnings.append(f"Route '{method} {rule.rule}' has no type hints " f"(input_schema is empty)")

                modules.append(
                    ScannedModule(
                        module_id=module_id,
                        description=description,
                        input_schema=input_schema,
                        output_schema=output_schema,
                        tags=tags,
                        target=target,
                        http_method=method,
                        url_rule=rule.rule,
                        annotations=annotations,
                        documentation=documentation,
                        metadata={"source": "native"},
                        warnings=warnings,
                    )
                )

        modules = self._deduplicate_ids(modules)
        return self.filter_modules(modules, include, exclude)

    def get_source_name(self) -> str:
        """Return human-readable scanner name."""
        return "native-flask"

    def _infer_annotations(self, method: str) -> ModuleAnnotations:
        """Infer behavioral annotations from HTTP method.

        Mapping:
            GET    -> readonly=True
            DELETE -> destructive=True
            PUT    -> idempotent=True
            Others -> default (all False)

        Args:
            method: HTTP method string (uppercase).

        Returns:
            ModuleAnnotations instance with inferred flags.
        """
        if method == "GET":
            return ModuleAnnotations(readonly=True)
        elif method == "DELETE":
            return ModuleAnnotations(destructive=True)
        elif method == "PUT":
            return ModuleAnnotations(idempotent=True)
        return ModuleAnnotations()

    def _extract_url_params(self, rule: Rule) -> dict[str, str]:
        """Extract URL path parameters with their Flask converter types.

        Maps werkzeug converter class names to shorthand type strings
        that the schema backends understand (e.g., "int", "float", "uuid").

        Args:
            rule: The werkzeug routing Rule to extract parameters from.

        Returns:
            Dict mapping parameter names to type shorthand strings.
        """
        params: dict[str, str] = {}
        for argument in rule.arguments:
            converter = rule._converters.get(argument)
            if converter is not None:
                converter_type = type(converter).__name__
                params[argument] = _CONVERTER_TYPE_MAP.get(converter_type, "string")
            else:
                params[argument] = "string"
        return params

    def _generate_module_id(self, rule: Rule, view_func: Callable, method: str) -> str:
        """Generate module_id from Blueprint name + function name + method.

        Rules (from tech design section 7.5.2):
        - Blueprint route: {blueprint}.{function}.{method}
        - Non-Blueprint route: {function}.{method}
        - Special characters replaced with _

        Args:
            rule: The werkzeug routing Rule.
            view_func: The view function callable.
            method: The HTTP method string (e.g., "GET").

        Returns:
            Module ID string.
        """
        endpoint = rule.endpoint
        parts = endpoint.split(".")
        func_name = parts[-1]
        blueprint_name = parts[0] if len(parts) > 1 else None

        if blueprint_name:
            module_id = f"{blueprint_name}.{func_name}.{method.lower()}"
        else:
            module_id = f"{func_name}.{method.lower()}"

        # Replace non-alphanumeric (except .) with _
        module_id = re.sub(r"[^a-zA-Z0-9.]", "_", module_id)
        return module_id

    def _extract_description(self, view_func: Callable, rule: Rule, method: str) -> str:
        """Extract description from docstring (first line) or auto-generate.

        Args:
            view_func: The view function callable.
            rule: The werkzeug routing Rule (used for auto-generation).
            method: The HTTP method (used for auto-generation).

        Returns:
            Description string.
        """
        doc = inspect.getdoc(view_func)
        if doc:
            return doc.split("\n")[0].strip()
        return f"{method} {rule.rule}"

    def _extract_documentation(self, view_func: Callable) -> str | None:
        """Extract full docstring as documentation.

        Args:
            view_func: The view function callable.

        Returns:
            Full cleaned docstring, or None if no docstring.
        """
        doc = inspect.getdoc(view_func)
        if doc:
            return doc.strip()
        return None

    def _generate_target(self, view_func: Callable) -> str:
        """Generate target in 'module.path:callable' format.

        Args:
            view_func: The view function callable.

        Returns:
            Target string in 'module:qualname' format.
        """
        module = getattr(view_func, "__module__", "__main__")
        name = getattr(view_func, "__qualname__", view_func.__name__)
        return f"{module}:{name}"

    def _extract_tags(self, rule: Rule) -> list[str]:
        """Extract tags from Blueprint name.

        Args:
            rule: The werkzeug routing Rule.

        Returns:
            List of tag strings (Blueprint name if applicable).
        """
        parts = rule.endpoint.split(".")
        if len(parts) > 1:
            return [parts[0]]
        return []
