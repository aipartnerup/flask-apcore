"""Registry writer for direct module registration.

Converts ScannedModule instances into apcore FunctionModule instances
and registers them directly into an apcore Registry. This is the default
output mode (no file I/O needed).

Replaces YAML-only output with direct registration as default.
"""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
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

        func = _resolve_target(mod.target)

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
