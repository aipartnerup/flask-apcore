"""App-scoped Registry, Executor, and ContextFactory wrappers.

Unlike django-apcore's module-level singletons with threading.Lock,
flask-apcore stores state per-app in app.extensions["apcore"].
This follows Flask's multi-app pattern and enables:
- Multiple Flask apps with separate registries (testing, multi-tenant)
- Clean teardown between test cases
- No global mutable state

Adapted from django-apcore's registry.py:
- get_registry() reads from app.extensions instead of a global _registry
- get_executor() lazily creates Executor per-app instead of a global _executor
- get_context_factory() resolves per-app instead of a global _context_factory

get_executor() merges user middlewares with observability middlewares
from setup_observability().
"""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING, Any

from flask import current_app

if TYPE_CHECKING:
    from flask import Flask

logger = logging.getLogger("flask_apcore")


def get_registry(app: Flask | None = None) -> Any:
    """Return the apcore Registry for the current Flask app.

    The registry is stored in app.extensions["apcore"]["registry"].
    If no app is provided, uses flask.current_app.

    Args:
        app: Flask app instance, or None to use current_app.

    Returns:
        The apcore Registry scoped to this app.

    Raises:
        RuntimeError: If flask-apcore not initialized or outside app context.
    """
    if app is None:
        app = current_app._get_current_object()
    ext_data = app.extensions.get("apcore")
    if ext_data is None:
        raise RuntimeError("flask-apcore not initialized. " "Call Apcore(app) or apcore.init_app(app) first.")
    return ext_data["registry"]


def get_executor(app: Flask | None = None) -> Any:
    """Return the apcore Executor for the current Flask app.

    Lazily created on first call. Configured from APCORE_MIDDLEWARES,
    APCORE_ACL_PATH, APCORE_EXECUTOR_CONFIG, and observability settings.

    User middlewares (from APCORE_MIDDLEWARES) are applied first, followed
    by observability middlewares (tracing, metrics, logging).

    Args:
        app: Flask app instance, or None to use current_app.

    Returns:
        The apcore Executor scoped to this app.

    Raises:
        RuntimeError: If flask-apcore not initialized or outside app context.
    """
    if app is None:
        app = current_app._get_current_object()
    ext_data = app.extensions.get("apcore")
    if ext_data is None:
        raise RuntimeError("flask-apcore not initialized. " "Call Apcore(app) or apcore.init_app(app) first.")

    if ext_data["executor"] is None:
        registry = ext_data["registry"]
        settings = ext_data["settings"]

        user_middlewares = _resolve_middlewares(settings.middlewares)
        obs_middlewares = ext_data.get("observability_middlewares", [])
        all_middlewares = user_middlewares + obs_middlewares

        acl = _resolve_acl(settings.acl_path)
        config = _resolve_config(settings.executor_config)

        from apcore import Executor

        ext_data["executor"] = Executor(
            registry,
            middlewares=all_middlewares,
            acl=acl,
            config=config,
        )
        logger.debug(
            "Created apcore.Executor with %d middlewares " "(%d user + %d observability)",
            len(all_middlewares),
            len(user_middlewares),
            len(obs_middlewares),
        )

    return ext_data["executor"]


def get_context_factory(app: Flask | None = None) -> Any:
    """Return the ContextFactory for the current Flask app.

    Resolves from APCORE_CONTEXT_FACTORY setting if configured,
    otherwise returns the built-in FlaskContextFactory.

    Args:
        app: Flask app instance, or None to use current_app.

    Returns:
        A ContextFactory instance.

    Raises:
        RuntimeError: If flask-apcore not initialized or outside app context.
    """
    if app is None:
        app = current_app._get_current_object()
    ext_data = app.extensions.get("apcore")
    if ext_data is None:
        raise RuntimeError("flask-apcore not initialized. " "Call Apcore(app) or apcore.init_app(app) first.")

    settings = ext_data["settings"]
    if settings.context_factory is not None:
        module_path, class_name = settings.context_factory.rsplit(".", 1)
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        return cls()

    from flask_apcore.context import FlaskContextFactory

    return FlaskContextFactory()


# --- Private helpers (adapted from django-apcore registry.py) ---


def _resolve_middlewares(paths: list[str]) -> list[Any]:
    """Import and instantiate middleware classes from dotted paths.

    Args:
        paths: List of dotted path strings
            (e.g., 'myapp.middleware.LoggingMiddleware').

    Returns:
        List of instantiated middleware objects.
    """
    middlewares = []
    for path in paths:
        module_path, class_name = path.rsplit(".", 1)
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        middlewares.append(cls())
    return middlewares


def _resolve_acl(path: str | None) -> Any:
    """Load ACL from a YAML file path.

    Args:
        path: File path to ACL YAML, or None.

    Returns:
        ACL instance or None.
    """
    if path is None:
        return None
    from apcore import ACL

    return ACL.load(path)


def _resolve_config(data: dict[str, Any] | None) -> Any:
    """Create an Executor Config from a dict.

    Args:
        data: Config dict, or None.

    Returns:
        Config instance or None.
    """
    if data is None:
        return None
    from apcore import Config

    return Config(data=data)
