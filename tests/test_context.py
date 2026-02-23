"""Tests for flask_apcore.context – FlaskContextFactory with W3C TraceContext."""

from __future__ import annotations

import pytest
from flask import Flask
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app() -> Flask:
    """Create a minimal Flask app."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


# ===========================================================================
# Anonymous context (request is None)
# ===========================================================================


class TestAnonymousContext:
    """When request is None, create anonymous context."""

    def test_anonymous_identity(self) -> None:
        from flask_apcore.context import FlaskContextFactory

        factory = FlaskContextFactory()
        ctx = factory.create_context(request=None)
        assert ctx.identity is not None
        assert ctx.identity.id == "anonymous"
        assert ctx.identity.type == "anonymous"

    def test_trace_id_generated(self) -> None:
        from flask_apcore.context import FlaskContextFactory

        factory = FlaskContextFactory()
        ctx = factory.create_context(request=None)
        # Should have a UUID-format trace_id
        assert len(ctx.trace_id) == 36  # UUID with dashes


# ===========================================================================
# flask-login user extraction
# ===========================================================================


class TestFlaskLoginUser:
    """When flask-login current_user is available and authenticated."""

    def test_extracts_flask_login_user(self) -> None:
        from flask_apcore.context import FlaskContextFactory

        app = _make_app()

        # Create a mock current_user
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = 42

        factory = FlaskContextFactory()

        with app.test_request_context("/"):
            with patch("flask_apcore.context.FLASK_LOGIN_AVAILABLE", True):
                with patch("flask_apcore.context.current_user", mock_user):
                    from flask import request

                    ctx = factory.create_context(request=request)

        assert ctx.identity.id == "42"
        assert ctx.identity.type == "user"


# ===========================================================================
# g.user extraction
# ===========================================================================


class TestGUser:
    """When g.user is set (common Flask pattern)."""

    def test_extracts_g_user(self) -> None:
        from flask_apcore.context import FlaskContextFactory

        app = _make_app()
        factory = FlaskContextFactory()

        with app.test_request_context("/"):
            from flask import g, request

            mock_user = MagicMock()
            mock_user.id = 99
            mock_user.is_authenticated = True
            g.user = mock_user

            # Disable flask-login to force g.user path
            with patch("flask_apcore.context.FLASK_LOGIN_AVAILABLE", False):
                ctx = factory.create_context(request=request)

        assert ctx.identity.id == "99"
        assert ctx.identity.type == "user"


# ===========================================================================
# request.authorization extraction
# ===========================================================================


class TestRequestAuthorization:
    """When request.authorization is present (HTTP Basic/Bearer)."""

    def test_basic_auth_extracts_username(self) -> None:
        from flask_apcore.context import FlaskContextFactory

        app = _make_app()
        factory = FlaskContextFactory()

        with app.test_request_context(
            "/",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},  # user:pass
        ):
            from flask import request

            with patch("flask_apcore.context.FLASK_LOGIN_AVAILABLE", False):
                ctx = factory.create_context(request=request)

        assert ctx.identity.id == "user"
        assert ctx.identity.type == "api_key"


# ===========================================================================
# Traceparent header extraction
# ===========================================================================


class TestTraceparentExtraction:
    """When the traceparent header is present."""

    def test_traceparent_propagated(self) -> None:
        from flask_apcore.context import FlaskContextFactory

        app = _make_app()
        factory = FlaskContextFactory()

        traceparent = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"

        with app.test_request_context(
            "/",
            headers={"traceparent": traceparent},
        ):
            from flask import request

            with patch("flask_apcore.context.FLASK_LOGIN_AVAILABLE", False):
                ctx = factory.create_context(request=request)

        # The trace_id should be derived from the traceparent header
        # TraceContext.extract returns TraceParent with trace_id = "0af7651916cd43dd8448eb211c80319c"
        # Context.create converts it to UUID format: "0af76519-16cd-43dd-8448-eb211c80319c"
        assert ctx.trace_id == "0af76519-16cd-43dd-8448-eb211c80319c"

    def test_missing_traceparent_generates_uuid(self) -> None:
        from flask_apcore.context import FlaskContextFactory

        app = _make_app()
        factory = FlaskContextFactory()

        with app.test_request_context("/"):
            from flask import request

            with patch("flask_apcore.context.FLASK_LOGIN_AVAILABLE", False):
                ctx = factory.create_context(request=request)

        # Should be a generated UUID (36 chars)
        assert len(ctx.trace_id) == 36
        # Should NOT be from a traceparent
        assert "-" in ctx.trace_id

    def test_malformed_traceparent_ignored(self) -> None:
        from flask_apcore.context import FlaskContextFactory

        app = _make_app()
        factory = FlaskContextFactory()

        with app.test_request_context(
            "/",
            headers={"traceparent": "not-valid"},
        ):
            from flask import request

            with patch("flask_apcore.context.FLASK_LOGIN_AVAILABLE", False):
                ctx = factory.create_context(request=request)

        # Should fall back to generated UUID
        assert len(ctx.trace_id) == 36


# ===========================================================================
# push_app_context_for_module
# ===========================================================================


class TestPushAppContextForModule:
    """Tests for push_app_context_for_module()."""

    def test_returns_callable(self) -> None:
        from flask_apcore.context import push_app_context_for_module

        app = _make_app()
        result = push_app_context_for_module(app)
        assert callable(result)

    @pytest.mark.asyncio
    async def test_executes_with_app_context(self) -> None:
        from flask_apcore.context import push_app_context_for_module

        app = _make_app()
        wrapper = push_app_context_for_module(app)

        def my_module(inputs, context):
            from flask import current_app

            return {"app_name": current_app.name}

        result = await wrapper(my_module, {}, None)
        assert "app_name" in result
