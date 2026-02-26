"""Flask Extension for apcore AI-Perceivable Core integration.

Provides the Apcore class following Flask's Extension pattern.
Adapted from django-apcore's ApcoreAppConfig (apps.py):
- Django's AppConfig.ready() -> Flask's init_app()
- Django's settings module -> Flask's app.config
- Django's INSTALLED_APPS scanning -> Flask's APCORE_MODULE_PACKAGES config

init_app flow:
1. load_settings(app)
2. Create Registry
3. Create ExtensionManager, register event listeners
4. Call setup_observability(settings, ext_data)
5. Register CLI commands
6. Auto-discover if enabled (load bindings + scan packages)
7. Store everything in app.extensions["apcore"]
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask import Flask

from flask_apcore.config import load_settings
from flask_apcore.observability import setup_observability
from flask_apcore.registry import get_executor, get_registry

logger = logging.getLogger("flask_apcore")


class Apcore:
    """Flask Extension for apcore AI-Perceivable Core integration.

    Usage (direct):
        app = Flask(__name__)
        apcore = Apcore(app)

    Usage (factory pattern):
        apcore = Apcore()

        def create_app():
            app = Flask(__name__)
            apcore.init_app(app)
            return app
    """

    def __init__(self, app: Flask | None = None) -> None:
        """Initialize the extension.

        Args:
            app: Flask application instance. If provided, init_app()
                 is called immediately.
        """
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Initialize the extension with a Flask application.

        This method:
        1. Validates APCORE_* configuration in app.config
        2. Creates the app-scoped Registry singleton
        3. Creates ExtensionManager and registers event listeners
        4. Sets up observability (tracing, metrics, logging)
        5. Registers the Click CLI command group
        6. If APCORE_AUTO_DISCOVER is True:
           a. Loads YAML binding files from APCORE_MODULE_DIR
           b. Scans for @module-decorated functions in configured packages
        7. Stores everything in app.extensions["apcore"]

        Args:
            app: Flask application instance.

        Raises:
            ValueError: If any APCORE_* config value is invalid.
        """
        # 1. Load and validate config
        settings = load_settings(app)

        # 2. Create Registry
        from apcore import Registry

        registry = Registry()

        # 3. Create ExtensionManager
        from apcore import ExtensionManager

        ext_mgr = ExtensionManager()

        # 4. Set up observability — populates ext_data with middlewares
        ext_data: dict[str, Any] = {
            "registry": registry,
            "executor": None,  # Lazily created by get_executor()
            "settings": settings,
            "extension_manager": ext_mgr,
        }
        setup_observability(settings, ext_data)

        # Store in app.extensions
        app.extensions["apcore"] = ext_data

        # 5. Register CLI commands
        from flask_apcore.cli import apcore_cli

        app.cli.add_command(apcore_cli)

        logger.debug("flask-apcore initialized for app %s", app.name)

        # 6. Auto-discover if enabled
        if settings.auto_discover:
            self._register_event_listeners(registry)

            # 6a. Load YAML binding files
            module_dir = Path(settings.module_dir)
            if module_dir.exists() and module_dir.is_dir():
                self._load_bindings(registry, str(module_dir), settings.binding_pattern)
            else:
                logger.warning(
                    "Module directory not found: %s. " "Skipping auto-discovery of binding files.",
                    module_dir,
                )

            # 6b. Scan packages for @module-decorated functions
            if settings.module_packages:
                self._scan_packages_for_modules(registry, settings.module_packages)

            # 6c. Flatten Pydantic model params for all registered modules
            self._flatten_registered_modules(registry)

            logger.info(
                "flask-apcore: auto-discovery complete: %d total modules",
                registry.count,
            )
        else:
            logger.debug("Auto-discovery disabled (APCORE_AUTO_DISCOVER=False)")

    def _register_event_listeners(self, registry: Any) -> None:
        """Register event listeners on the registry for debug logging.

        Adapted from django-apcore's ApcoreAppConfig._register_event_listeners().
        Gracefully handles registries that don't support events.
        """
        try:
            registry.on(
                "register",
                lambda module_id, module: logger.debug("Registry event: registered module '%s'", module_id),
            )
            logger.debug("Registered event listeners on registry")
        except (AttributeError, TypeError):
            logger.debug("Registry does not support events; " "skipping event listener registration")

    def _flatten_registered_modules(self, registry: Any) -> None:
        """Re-register modules whose functions have Pydantic model parameters.

        YAML-loaded and @module-decorated functions may accept Pydantic
        BaseModel params (e.g. ``body: TaskCreate``).  MCP tools should
        expose flat scalar fields instead.  This method iterates the
        registry and replaces any such modules with versions whose
        functions are wrapped by ``_flatten_pydantic_params``.
        """
        from flask_apcore.output.registry_writer import _flatten_pydantic_params

        for module_id in list(registry.module_ids):
            module = registry.get(module_id)
            func = getattr(module, "_func", None)
            if func is None:
                continue
            wrapped = _flatten_pydantic_params(func)
            if wrapped is func:
                continue  # no Pydantic params, skip

            from apcore import FunctionModule

            new_module = FunctionModule(
                func=wrapped,
                module_id=module.module_id,
                description=module.description,
                documentation=getattr(module, "documentation", None),
                tags=getattr(module, "tags", None),
                version=getattr(module, "version", "1.0.0"),
                annotations=getattr(module, "annotations", None),
                metadata=getattr(module, "metadata", None),
            )
            registry.unregister(module_id)
            registry.register(module_id, new_module)
            logger.debug("Flattened Pydantic params for module: %s", module_id)

    def _load_bindings(self, registry: Any, module_dir: str, pattern: str) -> None:
        """Load YAML binding files from the module directory.

        Adapted from django-apcore's ApcoreAppConfig._load_bindings().
        Uses apcore.BindingLoader to load .binding.yaml files into the registry.

        Args:
            registry: The apcore Registry to load bindings into.
            module_dir: Path to the directory containing binding files.
            pattern: Glob pattern for binding files (e.g., '*.binding.yaml').
        """
        try:
            from apcore import BindingLoader

            loader = BindingLoader()
            modules = loader.load_binding_dir(str(module_dir), registry, pattern=pattern)
            count = len(modules) if modules else 0
            logger.info("Loaded %d binding modules from %s", count, module_dir)
        except ImportError:
            logger.warning("apcore.BindingLoader not available; " "skipping binding file loading")
        except Exception:
            logger.exception("Error loading binding files from %s", module_dir)

    def _scan_packages_for_modules(self, registry: Any, packages: list[str]) -> None:
        """Scan Python packages for @module-decorated functions.

        Adapted from django-apcore's ApcoreAppConfig._scan_apps_for_modules():
        - Django scans INSTALLED_APPS for {app}.apcore_modules submodules
        - Flask scans APCORE_MODULE_PACKAGES config entries directly

        Args:
            registry: The apcore Registry to register modules into.
            packages: List of dotted Python package paths to scan.
        """
        for package_name in packages:
            try:
                mod = importlib.import_module(package_name)
                for attr_name in dir(mod):
                    obj = getattr(mod, attr_name)
                    if callable(obj) and hasattr(obj, "apcore_module"):
                        try:
                            fm = obj.apcore_module
                            registry.register(fm.module_id, fm)
                            logger.debug(
                                "Registered @module function: %s.%s",
                                package_name,
                                attr_name,
                            )
                        except Exception:
                            logger.warning(
                                "Failed to register module from %s.%s",
                                package_name,
                                attr_name,
                                exc_info=True,
                            )
            except ImportError:
                logger.debug(
                    "Package %s not found; skipping module scan",
                    package_name,
                )
            except Exception:
                logger.warning(
                    "Error scanning %s for apcore modules",
                    package_name,
                    exc_info=True,
                )

    def get_registry(self, app: Flask | None = None) -> Any:
        """Return the apcore Registry for the given app.

        Args:
            app: Flask app instance. If None, uses current_app.

        Returns:
            The apcore Registry scoped to this app.
        """
        return get_registry(app)

    def get_executor(self, app: Flask | None = None) -> Any:
        """Return the apcore Executor for the given app.

        Args:
            app: Flask app instance. If None, uses current_app.

        Returns:
            The apcore Executor scoped to this app.
        """
        return get_executor(app)
