"""Tests for flask_apcore.extension – Apcore class with layered init_app."""

from __future__ import annotations

from flask import Flask


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path, **overrides) -> Flask:
    """Create a minimal Flask app with APCORE_* config overrides."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
    app.config["APCORE_AUTO_DISCOVER"] = False
    for k, v in overrides.items():
        app.config[k] = v
    return app


# ===========================================================================
# Direct init: Apcore(app)
# ===========================================================================


class TestDirectInit:
    """When Apcore is initialized directly with Apcore(app)."""

    def test_apcore_extension_registered(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(tmp_path)
        Apcore(app)
        assert "apcore" in app.extensions

    def test_ext_data_has_expected_keys(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(tmp_path)
        Apcore(app)
        ext_data = app.extensions["apcore"]

        assert "registry" in ext_data
        assert "executor" in ext_data
        assert "settings" in ext_data
        assert "extension_manager" in ext_data
        assert "observability_middlewares" in ext_data
        assert "metrics_collector" in ext_data

    def test_executor_is_none_initially(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(tmp_path)
        Apcore(app)
        assert app.extensions["apcore"]["executor"] is None


# ===========================================================================
# Factory pattern: init_app()
# ===========================================================================


class TestFactoryPattern:
    """When using the factory pattern with init_app()."""

    def test_init_app(self, tmp_path) -> None:
        from flask_apcore import Apcore

        apcore = Apcore()
        app = _make_app(tmp_path)
        apcore.init_app(app)
        assert "apcore" in app.extensions

    def test_multiple_apps(self, tmp_path) -> None:
        from flask_apcore import Apcore

        apcore = Apcore()
        app1 = _make_app(tmp_path)
        app2 = _make_app(tmp_path)
        apcore.init_app(app1)
        apcore.init_app(app2)
        assert "apcore" in app1.extensions
        assert "apcore" in app2.extensions
        # Each app should have its own registry
        assert app1.extensions["apcore"]["registry"] is not app2.extensions["apcore"]["registry"]


# ===========================================================================
# Registry creation
# ===========================================================================


class TestRegistryCreation:
    """Registry is created during init_app and accessible."""

    def test_registry_created(self, tmp_path) -> None:
        from flask_apcore import Apcore
        from apcore import Registry

        app = _make_app(tmp_path)
        Apcore(app)
        reg = app.extensions["apcore"]["registry"]
        assert isinstance(reg, Registry)

    def test_get_registry_convenience(self, tmp_path) -> None:
        from flask_apcore import Apcore
        from flask_apcore.registry import get_registry

        app = _make_app(tmp_path)
        Apcore(app)
        with app.app_context():
            reg = get_registry()
        assert reg is app.extensions["apcore"]["registry"]


# ===========================================================================
# ExtensionManager creation
# ===========================================================================


class TestExtensionManager:
    """ExtensionManager is created during init_app."""

    def test_extension_manager_created(self, tmp_path) -> None:
        from flask_apcore import Apcore
        from apcore import ExtensionManager

        app = _make_app(tmp_path)
        Apcore(app)
        ext_mgr = app.extensions["apcore"]["extension_manager"]
        assert isinstance(ext_mgr, ExtensionManager)


# ===========================================================================
# CLI commands registered
# ===========================================================================


class TestCLIRegistered:
    """CLI commands are registered during init_app."""

    def test_apcore_command_group_registered(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(tmp_path)
        Apcore(app)
        # Flask's CLI uses click groups; check "apcore" is a registered command
        runner = app.test_cli_runner()
        result = runner.invoke(args=["apcore", "--help"])
        assert result.exit_code == 0
        assert "apcore" in result.output.lower()


# ===========================================================================
# Auto-discover disabled
# ===========================================================================


class TestAutoDiscoverDisabled:
    """When APCORE_AUTO_DISCOVER is False, no modules should be loaded."""

    def test_no_modules_registered(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(tmp_path)
        Apcore(app)
        reg = app.extensions["apcore"]["registry"]
        assert reg.count == 0


# ===========================================================================
# Observability setup
# ===========================================================================


class TestObservabilitySetup:
    """Observability is set up during init_app."""

    def test_observability_middlewares_empty_by_default(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(tmp_path)
        Apcore(app)
        assert app.extensions["apcore"]["observability_middlewares"] == []

    def test_observability_middlewares_populated_when_enabled(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(
            tmp_path,
            APCORE_TRACING_ENABLED=True,
            APCORE_METRICS_ENABLED=True,
            APCORE_LOGGING_ENABLED=True,
        )
        Apcore(app)
        mws = app.extensions["apcore"]["observability_middlewares"]
        assert len(mws) == 3

    def test_metrics_collector_populated_when_enabled(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(tmp_path, APCORE_METRICS_ENABLED=True)
        Apcore(app)
        from apcore.observability.metrics import MetricsCollector

        assert isinstance(app.extensions["apcore"]["metrics_collector"], MetricsCollector)


# ===========================================================================
# Convenience methods
# ===========================================================================


class TestConvenienceMethods:
    """Test Apcore.get_registry() and Apcore.get_executor()."""

    def test_get_registry(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(tmp_path)
        apcore_ext = Apcore(app)
        with app.app_context():
            reg = apcore_ext.get_registry()
        assert reg is app.extensions["apcore"]["registry"]

    def test_get_executor(self, tmp_path) -> None:
        from flask_apcore import Apcore
        from apcore import Executor

        app = _make_app(tmp_path)
        apcore_ext = Apcore(app)
        with app.app_context():
            executor = apcore_ext.get_executor()
        assert isinstance(executor, Executor)

    def test_get_executor_includes_obs_middlewares(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(
            tmp_path,
            APCORE_TRACING_ENABLED=True,
            APCORE_METRICS_ENABLED=True,
        )
        apcore_ext = Apcore(app)
        with app.app_context():
            executor = apcore_ext.get_executor()
        # Should include tracing + metrics middlewares
        assert len(executor.middlewares) >= 2


# ===========================================================================
# Explorer Blueprint registration
# ===========================================================================


class TestExplorerBlueprint:
    """Explorer Blueprint is registered when APCORE_EXPLORER_ENABLED=True."""

    def test_explorer_registered_when_enabled(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(tmp_path, APCORE_EXPLORER_ENABLED=True)
        Apcore(app)
        assert "apcore_explorer" in app.blueprints

    def test_explorer_not_registered_when_disabled(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(tmp_path, APCORE_EXPLORER_ENABLED=False)
        Apcore(app)
        assert "apcore_explorer" not in app.blueprints

    def test_explorer_not_registered_by_default(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(tmp_path)
        Apcore(app)
        assert "apcore_explorer" not in app.blueprints

    def test_custom_url_prefix(self, tmp_path) -> None:
        from flask_apcore import Apcore

        app = _make_app(
            tmp_path,
            APCORE_EXPLORER_ENABLED=True,
            APCORE_EXPLORER_URL_PREFIX="/my-api",
        )
        Apcore(app)
        assert "apcore_explorer" in app.blueprints
