"""Flask Context/Identity adapter for apcore.

Provides FlaskContextFactory that creates apcore Context objects from
Flask request context, mapping Flask identity patterns to apcore Identity.

Adapted from django-apcore's context.py (DjangoContextFactory):
- Django's request.user -> Flask's g.user / request.authorization / flask-login
- Django's user.groups -> Flask roles (from g.user or flask-login)
- W3C TraceContext propagation via TraceContext.extract()
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from flask import Flask, Request

logger = logging.getLogger("flask_apcore")

# Detect flask-login availability at import time
FLASK_LOGIN_AVAILABLE = False
try:
    from flask_login import current_user  # noqa: F401

    FLASK_LOGIN_AVAILABLE = True
except ImportError:
    current_user = None  # type: ignore[assignment]


class FlaskContextFactory:
    """Creates apcore Context from Flask request context.

    Implements the apcore ContextFactory protocol:
        create_context(request) -> Context

    Identity extraction priority:
    1. flask_login current_user (if flask-login installed)
    2. g.user (common Flask pattern)
    3. request.authorization (HTTP Basic/Bearer)
    4. Falls back to anonymous identity

    W3C TraceContext propagation:
    When a ``traceparent`` header is present in the request, the trace_id
    from the header is used instead of generating a new one.
    """

    def create_context(self, request: Request | None = None) -> Any:
        """Create an apcore Context from Flask request context.

        If request is None (MCP serve mode), creates an anonymous Context.

        Args:
            request: Flask Request object, or None for MCP-originated calls.

        Returns:
            apcore Context with Identity derived from request if available,
            and trace_parent from W3C traceparent header if present.
        """
        from apcore import Context
        from apcore.trace_context import TraceContext

        if request is None:
            identity = self._anonymous_identity()
            return Context.create(identity=identity)

        identity = self._extract_identity(request)

        # Extract W3C TraceContext from request headers.
        # Flask normalizes header keys to title-case (e.g. "Traceparent"),
        # but TraceContext.extract() expects lowercase "traceparent".
        trace_parent = None
        headers = {k.lower(): v for k, v in request.headers}
        trace_parent = TraceContext.extract(headers)

        return Context.create(identity=identity, trace_parent=trace_parent)

    def _extract_identity(self, request: Request) -> Any:
        """Extract an apcore Identity from a Flask request.

        Checks (in order):
        1. flask_login current_user (if flask-login installed and authenticated)
        2. g.user (common Flask pattern)
        3. request.authorization (HTTP Basic/Bearer)
        4. Falls back to anonymous identity

        Args:
            request: Flask Request object.

        Returns:
            apcore Identity with user info, or anonymous identity.
        """
        from apcore import Identity

        # 1. Check flask-login
        if FLASK_LOGIN_AVAILABLE:
            try:
                if hasattr(current_user, "is_authenticated") and current_user.is_authenticated:
                    return Identity(
                        id=str(current_user.id),
                        type="user",
                    )
            except Exception:
                logger.debug("flask-login current_user check failed", exc_info=True)

        # 2. Check g.user
        try:
            from flask import g

            user = getattr(g, "user", None)
            if user is not None and getattr(user, "is_authenticated", True):
                return Identity(
                    id=str(user.id),
                    type="user",
                )
        except RuntimeError:
            # Outside of application context
            pass

        # 3. Check request.authorization (HTTP Basic/Bearer)
        if request.authorization is not None:
            auth = request.authorization
            if auth.username:
                return Identity(id=auth.username, type="api_key")
            return Identity(id="bearer", type="api_key")

        # 4. Fallback: anonymous
        return self._anonymous_identity()

    def _anonymous_identity(self) -> Any:
        """Create an anonymous apcore Identity."""
        from apcore import Identity

        return Identity(id="anonymous", type="anonymous")


def push_app_context_for_module(app: Flask) -> Callable:
    """Create a wrapper that pushes Flask app context before module execution.

    Used by the WSGI/async bridge to ensure module functions can access
    current_app, g, and database connections when called from the MCP
    server's asyncio event loop via asyncio.to_thread().

    Args:
        app: Flask application instance.

    Returns:
        An async callable that wraps module execution with app_context.
    """

    async def execute_with_context(
        module_func: Callable,
        inputs: dict[str, Any],
        context: Any,
    ) -> dict[str, Any]:
        """Execute a module function in a thread with Flask app context.

        Args:
            module_func: The synchronous module function to execute.
            inputs: Input arguments dict.
            context: apcore Context with identity and trace info.

        Returns:
            Module output dict.
        """

        def _run_in_context() -> dict[str, Any]:
            with app.app_context():
                return module_func(inputs, context)

        return await asyncio.to_thread(_run_in_context)

    return execute_with_context
