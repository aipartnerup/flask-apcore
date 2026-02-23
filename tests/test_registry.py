"""Tests for flask_apcore.registry – get_registry, get_executor, get_context_factory."""

from __future__ import annotations

import pytest
from flask import Flask

from flask_apcore.config import load_settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(**overrides) -> Flask:
    """Create a minimal Flask app with APCORE_* config overrides."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["APCORE_AUTO_DISCOVER"] = False
    for k, v in overrides.items():
        app.config[k] = v
    return app


def _init_ext_data(app: Flask, **extra) -> dict:
    """Manually set up app.extensions['apcore'] for unit testing registry functions."""
    from apcore import Registry

    settings = load_settings(app)
    registry = Registry()
    ext_data = {
        "registry": registry,
        "executor": None,
        "settings": settings,
        "extension_manager": None,
        "observability_middlewares": [],
        "metrics_collector": None,
    }
    ext_data.update(extra)
    app.extensions["apcore"] = ext_data
    return ext_data


# ===========================================================================
# get_registry()
# ===========================================================================


class TestGetRegistry:
    """Tests for get_registry()."""

    def test_returns_registry(self) -> None:
        from flask_apcore.registry import get_registry

        app = _make_app()
        ext_data = _init_ext_data(app)
        with app.app_context():
            reg = get_registry()
        assert reg is ext_data["registry"]

    def test_with_explicit_app(self) -> None:
        from flask_apcore.registry import get_registry

        app = _make_app()
        ext_data = _init_ext_data(app)
        reg = get_registry(app)
        assert reg is ext_data["registry"]

    def test_raises_when_not_initialized(self) -> None:
        from flask_apcore.registry import get_registry

        app = _make_app()
        with app.app_context():
            with pytest.raises(RuntimeError, match="flask-apcore not initialized"):
                get_registry()


# ===========================================================================
# get_executor()
# ===========================================================================


class TestGetExecutor:
    """Tests for get_executor()."""

    def test_creates_executor_lazily(self) -> None:
        from flask_apcore.registry import get_executor

        app = _make_app()
        _init_ext_data(app)
        with app.app_context():
            executor = get_executor()
        from apcore import Executor

        assert isinstance(executor, Executor)

    def test_caches_on_second_call(self) -> None:
        from flask_apcore.registry import get_executor

        app = _make_app()
        _init_ext_data(app)
        with app.app_context():
            executor1 = get_executor()
            executor2 = get_executor()
        assert executor1 is executor2

    def test_combines_user_and_obs_middlewares(self) -> None:
        """Executor should include both user middlewares and observability middlewares."""
        from flask_apcore.registry import get_executor

        app = _make_app(
            APCORE_TRACING_ENABLED=True,
            APCORE_METRICS_ENABLED=True,
        )
        settings = load_settings(app)

        # Create observability middlewares
        from flask_apcore.observability import setup_observability

        ext_data_partial: dict = {}
        setup_observability(settings, ext_data_partial)

        from apcore import Registry

        registry = Registry()
        ext_data = {
            "registry": registry,
            "executor": None,
            "settings": settings,
            "extension_manager": None,
            **ext_data_partial,
        }
        app.extensions["apcore"] = ext_data

        with app.app_context():
            executor = get_executor()
            # Should have at least the obs middlewares
            assert len(executor.middlewares) >= 2

    def test_raises_when_not_initialized(self) -> None:
        from flask_apcore.registry import get_executor

        app = _make_app()
        with app.app_context():
            with pytest.raises(RuntimeError, match="flask-apcore not initialized"):
                get_executor()


# ===========================================================================
# get_context_factory()
# ===========================================================================


class TestGetContextFactory:
    """Tests for get_context_factory()."""

    def test_returns_flask_context_factory_by_default(self) -> None:
        from flask_apcore.registry import get_context_factory
        from flask_apcore.context import FlaskContextFactory

        app = _make_app()
        _init_ext_data(app)
        with app.app_context():
            factory = get_context_factory()
        assert isinstance(factory, FlaskContextFactory)

    def test_resolves_custom_dotted_path(self) -> None:
        from flask_apcore.registry import get_context_factory

        app = _make_app(
            APCORE_CONTEXT_FACTORY="flask_apcore.context.FlaskContextFactory",
        )
        _init_ext_data(app)
        with app.app_context():
            factory = get_context_factory()
        from flask_apcore.context import FlaskContextFactory

        assert isinstance(factory, FlaskContextFactory)

    def test_raises_when_not_initialized(self) -> None:
        from flask_apcore.registry import get_context_factory

        app = _make_app()
        with app.app_context():
            with pytest.raises(RuntimeError, match="flask-apcore not initialized"):
                get_context_factory()
