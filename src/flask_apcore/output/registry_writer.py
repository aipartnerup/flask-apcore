"""Registry writer for direct module registration.

Converts ScannedModule instances into apcore FunctionModule instances
and registers them directly into an apcore Registry. This is the default
output mode (no file I/O needed).

Replaces YAML-only output with direct registration as default.
"""

from __future__ import annotations

import functools
import importlib
import inspect
import logging
import typing
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Callable

    from apcore import Registry

    from flask_apcore.scanners.base import ScannedModule

logger = logging.getLogger("flask_apcore")


def _resolve_target(target: str) -> Any:
    """Resolve a 'module.path:qualname' target string to a callable.

    Args:
        target: Target string in 'module:qualname' format.

    Returns:
        The resolved callable.

    Raises:
        ImportError: If the module cannot be imported.
        AttributeError: If the qualified name cannot be resolved.
    """
    module_path, _, qualname = target.partition(":")
    mod = importlib.import_module(module_path)
    return getattr(mod, qualname)


def _flatten_pydantic_params(func: Callable) -> Callable:
    """Wrap a function so Pydantic model params are flattened to scalar kwargs.

    Flask view functions like ``create_task(body: TaskCreate)`` expect a
    Pydantic model instance.  MCP tools should expose flat fields instead
    (``title``, ``description``, …).  This wrapper bridges the gap:

    1. Inspects the function signature for Pydantic BaseModel parameters.
    2. Creates a wrapper accepting the model's fields as flat kwargs.
    3. Reconstructs the Pydantic model(s) internally before calling
       the original function.

    If the function has no Pydantic model parameters, it is returned as-is.
    """
    try:
        hints = typing.get_type_hints(func, include_extras=True)
    except Exception:
        return func

    sig = inspect.signature(func)

    pydantic_params: dict[str, type[BaseModel]] = {}
    simple_params: list[tuple[str, inspect.Parameter]] = []

    for name, param in sig.parameters.items():
        hint = hints.get(name)
        if hint is not None and isinstance(hint, type) and issubclass(hint, BaseModel):
            pydantic_params[name] = hint
        else:
            simple_params.append((name, param))

    if not pydantic_params:
        return func

    # Build flat signature and annotations for generate_input_model()
    flat_params: list[inspect.Parameter] = []
    flat_annotations: dict[str, Any] = {}

    for name, param in simple_params:
        flat_params.append(param)
        if name in hints:
            flat_annotations[name] = hints[name]

    for model_cls in pydantic_params.values():
        for field_name, field_info in model_cls.model_fields.items():
            default = field_info.default if not field_info.is_required() else inspect.Parameter.empty
            flat_params.append(
                inspect.Parameter(
                    field_name,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=field_info.annotation,
                )
            )
            flat_annotations[field_name] = field_info.annotation

    if "return" in hints:
        flat_annotations["return"] = hints["return"]

    simple_param_names = {name for name, _ in simple_params}

    @functools.wraps(func)
    def wrapper(**kwargs: Any) -> Any:
        call_kwargs: dict[str, Any] = {}
        remaining = dict(kwargs)

        for name in list(remaining):
            if name in simple_param_names:
                call_kwargs[name] = remaining.pop(name)

        for param_name, model_cls in pydantic_params.items():
            model_field_names = set(model_cls.model_fields.keys())
            model_data = {k: remaining.pop(k) for k in list(remaining) if k in model_field_names}
            call_kwargs[param_name] = model_cls(**model_data)

        return func(**call_kwargs)

    wrapper.__signature__ = inspect.Signature(flat_params)  # type: ignore[attr-defined]
    wrapper.__annotations__ = flat_annotations
    return wrapper


class RegistryWriter:
    """Converts ScannedModule to FunctionModule and registers into Registry.

    This is the default writer used when no output_format is specified.
    Instead of writing YAML binding files, it registers modules directly
    into the apcore Registry for immediate use.
    """

    def write(
        self,
        modules: list[ScannedModule],
        registry: Registry,
        *,
        dry_run: bool = False,
    ) -> list[str]:
        """Register scanned modules into the registry.

        Args:
            modules: List of ScannedModule instances to register.
            registry: The apcore Registry to register modules into.
            dry_run: If True, skip registration and return empty list.

        Returns:
            List of registered module IDs.
        """
        registered: list[str] = []
        for mod in modules:
            if dry_run:
                continue
            fm = self._to_function_module(mod)
            registry.register(mod.module_id, fm)
            registered.append(mod.module_id)
            logger.debug("Registered module: %s", mod.module_id)
        return registered

    def _to_function_module(self, mod: ScannedModule) -> Any:
        """Convert a ScannedModule to an apcore FunctionModule.

        Args:
            mod: The ScannedModule to convert.

        Returns:
            A FunctionModule instance ready for registry insertion.
        """
        from apcore import FunctionModule

        func = _flatten_pydantic_params(_resolve_target(mod.target))

        annotations_dict: dict[str, Any] | None = None
        if mod.annotations is not None:
            from dataclasses import asdict

            annotations_dict = asdict(mod.annotations)

        metadata = {
            **(mod.metadata or {}),
            "http_method": mod.http_method,
            "url_rule": mod.url_rule,
        }

        return FunctionModule(
            func=func,
            module_id=mod.module_id,
            description=mod.description,
            documentation=mod.documentation,
            tags=mod.tags,
            version=mod.version,
            annotations=annotations_dict,
            metadata=metadata,
        )
