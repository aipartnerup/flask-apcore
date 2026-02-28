"""Tests for CLI serve command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from flask_apcore import Apcore


# ---------------------------------------------------------------------------
# Module-level view function (resolvable target)
# ---------------------------------------------------------------------------


def dummy_handler() -> dict:
    """Dummy handler for registration."""
    return {}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def serve_app(tmp_path):
    """Flask app with at least one module registered for serve tests."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
    app.config["APCORE_AUTO_DISCOVER"] = False

    app.add_url_rule("/health", "health_check", dummy_handler, methods=["GET"])

    Apcore(app)

    # Register a module so registry.count > 0
    with app.app_context():
        runner = app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan"])
        assert result.exit_code == 0, result.output

    return app


@pytest.fixture()
def empty_serve_app(tmp_path):
    """Flask app with no modules registered."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
    app.config["APCORE_AUTO_DISCOVER"] = False
    Apcore(app)
    return app


# ---------------------------------------------------------------------------
# Basic serve invocation
# ---------------------------------------------------------------------------


class TestServeBasic:
    """Basic serve command behavior."""

    @patch("flask_apcore.cli._do_serve")
    def test_serve_invokes_do_serve(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code == 0, result.output
        mock_serve.assert_called_once()

    @patch("flask_apcore.cli._do_serve")
    def test_serve_output_message(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code == 0, result.output
        assert "Starting MCP server" in result.output
        assert "modules registered" in result.output


# ---------------------------------------------------------------------------
# validate_inputs passthrough
# ---------------------------------------------------------------------------


class TestServeValidateInputs:
    """--validate-inputs flag is passed through to _do_serve."""

    @patch("flask_apcore.cli._do_serve")
    def test_validate_inputs_flag(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve", "--validate-inputs"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["validate_inputs"] is True

    @patch("flask_apcore.cli._do_serve")
    def test_validate_inputs_default_false(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["validate_inputs"] is False

    @patch("flask_apcore.cli._do_serve")
    def test_validate_inputs_config_fallback(self, mock_serve, tmp_path):
        """If --validate-inputs not passed, uses config fallback."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
        app.config["APCORE_AUTO_DISCOVER"] = False
        app.config["APCORE_SERVE_VALIDATE_INPUTS"] = True

        app.add_url_rule("/x", "x_handler", dummy_handler, methods=["GET"])
        Apcore(app)

        with app.app_context():
            r = app.test_cli_runner()
            r.invoke(args=["apcore", "scan"])

        runner = app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["validate_inputs"] is True


# ---------------------------------------------------------------------------
# log_level passthrough
# ---------------------------------------------------------------------------


class TestServeLogLevel:
    """--log-level is passed through to _do_serve."""

    @patch("flask_apcore.cli._do_serve")
    def test_log_level_flag(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve", "--log-level", "DEBUG"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["log_level"] == "DEBUG"

    @patch("flask_apcore.cli._do_serve")
    def test_log_level_default_none(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["log_level"] is None

    @patch("flask_apcore.cli._do_serve")
    def test_log_level_config_fallback(self, mock_serve, tmp_path):
        """If --log-level not passed, uses config fallback."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
        app.config["APCORE_AUTO_DISCOVER"] = False
        app.config["APCORE_SERVE_LOG_LEVEL"] = "WARNING"

        app.add_url_rule("/y", "y_handler", dummy_handler, methods=["GET"])
        Apcore(app)

        with app.app_context():
            r = app.test_cli_runner()
            r.invoke(args=["apcore", "scan"])

        runner = app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["log_level"] == "WARNING"

    def test_invalid_log_level_rejected(self, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve", "--log-level", "INVALID"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# metrics_collector passthrough
# ---------------------------------------------------------------------------


class TestServeMetricsCollector:
    """metrics_collector from ext_data is passed through."""

    @patch("flask_apcore.cli._do_serve")
    def test_metrics_collector_none_by_default(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["metrics_collector"] is None

    @patch("flask_apcore.cli._do_serve")
    def test_metrics_collector_passed_when_enabled(self, mock_serve, tmp_path):
        """When metrics enabled, collector is passed to _do_serve."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
        app.config["APCORE_AUTO_DISCOVER"] = False
        app.config["APCORE_METRICS_ENABLED"] = True

        app.add_url_rule("/z", "z_handler", dummy_handler, methods=["GET"])
        Apcore(app)

        with app.app_context():
            r = app.test_cli_runner()
            r.invoke(args=["apcore", "scan"])

        runner = app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["metrics_collector"] is not None


# ---------------------------------------------------------------------------
# No modules registered -> ClickException
# ---------------------------------------------------------------------------


class TestServeNoModules:
    """serve raises ClickException when no modules registered."""

    def test_no_modules_raises_error(self, empty_serve_app):
        runner = empty_serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code != 0
        assert "No apcore modules registered" in result.output


# ---------------------------------------------------------------------------
# Port validation
# ---------------------------------------------------------------------------


class TestServePortValidation:
    """Port validation in serve command."""

    @patch("flask_apcore.cli._do_serve")
    def test_custom_port(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve", "--http", "--port", "8080"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["port"] == 8080

    def test_invalid_port_zero(self, tmp_path):
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
        app.config["APCORE_AUTO_DISCOVER"] = False
        app.config["APCORE_SERVE_PORT"] = 9100  # valid config port

        app.add_url_rule("/w", "w_handler", dummy_handler, methods=["GET"])
        Apcore(app)

        with app.app_context():
            r = app.test_cli_runner()
            r.invoke(args=["apcore", "scan"])

        runner = app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve", "--port", "0"])
        assert result.exit_code != 0
        assert "--port must be between 1 and 65535" in result.output


# ---------------------------------------------------------------------------
# Security warning for 0.0.0.0
# ---------------------------------------------------------------------------


class TestServeSecurityWarning:
    """Security warning when binding to 0.0.0.0."""

    @patch("flask_apcore.cli._do_serve")
    def test_wildcard_host_warning(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve", "--http", "--host", "0.0.0.0"])

        assert result.exit_code == 0, result.output
        # Warning goes to stderr
        assert "0.0.0.0" in (result.output or "")

    @patch("flask_apcore.cli._do_serve")
    def test_localhost_no_warning(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve", "--http", "--host", "127.0.0.1"])

        assert result.exit_code == 0, result.output
        # No warning for localhost
        assert "0.0.0.0" not in (result.output or "")


# ---------------------------------------------------------------------------
# Transport selection
# ---------------------------------------------------------------------------


class TestServeTransport:
    """Transport selection in serve command."""

    @patch("flask_apcore.cli._do_serve")
    def test_default_stdio(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["transport"] == "stdio"

    @patch("flask_apcore.cli._do_serve")
    def test_http_transport(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve", "--http"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["transport"] == "streamable-http"


# ---------------------------------------------------------------------------
# Explorer passthrough
# ---------------------------------------------------------------------------


class TestServeExplorer:
    """--explorer, --explorer-prefix, --allow-execute flags are passed through."""

    @patch("flask_apcore.cli._do_serve")
    def test_explorer_flag(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve", "--explorer"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["explorer"] is True

    @patch("flask_apcore.cli._do_serve")
    def test_explorer_default_false(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["explorer"] is False

    @patch("flask_apcore.cli._do_serve")
    def test_explorer_prefix_flag(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve", "--explorer-prefix", "/tools"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["explorer_prefix"] == "/tools"

    @patch("flask_apcore.cli._do_serve")
    def test_explorer_prefix_default(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["explorer_prefix"] == "/explorer"

    @patch("flask_apcore.cli._do_serve")
    def test_allow_execute_flag(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve", "--allow-execute"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["allow_execute"] is True

    @patch("flask_apcore.cli._do_serve")
    def test_allow_execute_default_false(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["allow_execute"] is False

    @patch("flask_apcore.cli._do_serve")
    def test_explorer_config_fallback(self, mock_serve, tmp_path):
        """If --explorer not passed, uses config fallback."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
        app.config["APCORE_AUTO_DISCOVER"] = False
        app.config["APCORE_SERVE_EXPLORER"] = True
        app.config["APCORE_SERVE_EXPLORER_PREFIX"] = "/tools"
        app.config["APCORE_SERVE_ALLOW_EXECUTE"] = True

        app.add_url_rule("/e", "e_handler", dummy_handler, methods=["GET"])
        Apcore(app)

        with app.app_context():
            r = app.test_cli_runner()
            r.invoke(args=["apcore", "scan"])

        runner = app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["explorer"] is True
        assert call_kwargs.kwargs["explorer_prefix"] == "/tools"
        assert call_kwargs.kwargs["allow_execute"] is True


# ---------------------------------------------------------------------------
# JWT authentication passthrough
# ---------------------------------------------------------------------------


class TestServeJwtAuth:
    """--jwt-secret, --jwt-algorithm, --jwt-audience, --jwt-issuer flags."""

    @patch("flask_apcore.cli._do_serve")
    def test_jwt_secret_flag(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve", "--jwt-secret", "my-secret"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["authenticator"] is not None

    @patch("flask_apcore.cli._do_serve")
    def test_jwt_no_secret_no_authenticator(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["authenticator"] is None

    @patch("flask_apcore.cli._do_serve")
    def test_jwt_algorithm_flag(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve", "--jwt-secret", "s", "--jwt-algorithm", "HS512"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["authenticator"] is not None

    @patch("flask_apcore.cli._do_serve")
    def test_jwt_audience_flag(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve", "--jwt-secret", "s", "--jwt-audience", "my-api"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["authenticator"] is not None

    @patch("flask_apcore.cli._do_serve")
    def test_jwt_issuer_flag(self, mock_serve, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(
            args=["apcore", "serve", "--jwt-secret", "s", "--jwt-issuer", "https://auth.example.com"]
        )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["authenticator"] is not None

    @patch("flask_apcore.cli._do_serve")
    def test_jwt_config_fallback(self, mock_serve, tmp_path):
        """If --jwt-secret not passed, uses config fallback."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
        app.config["APCORE_AUTO_DISCOVER"] = False
        app.config["APCORE_SERVE_JWT_SECRET"] = "config-secret-long-enough"

        app.add_url_rule("/j", "j_handler", dummy_handler, methods=["GET"])
        Apcore(app)

        with app.app_context():
            r = app.test_cli_runner()
            r.invoke(args=["apcore", "scan"])

        runner = app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["authenticator"] is not None

    def test_invalid_jwt_algorithm_rejected(self, serve_app):
        runner = serve_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "serve", "--jwt-secret", "s", "--jwt-algorithm", "NONE"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# _do_serve authenticator forwarding
# ---------------------------------------------------------------------------


class TestDoServeForwardsAuthenticator:
    """_do_serve passes authenticator through to apcore_mcp.serve()."""

    @patch("apcore_mcp.serve")
    def test_authenticator_forwarded(self, mock_serve):
        from flask_apcore.cli import _do_serve

        sentinel = MagicMock()
        _do_serve(
            MagicMock(),
            transport="stdio",
            host="127.0.0.1",
            port=9100,
            name="test",
            authenticator=sentinel,
        )

        mock_serve.assert_called_once()
        assert mock_serve.call_args.kwargs["authenticator"] is sentinel

    @patch("apcore_mcp.serve")
    def test_no_authenticator_not_in_kwargs(self, mock_serve):
        from flask_apcore.cli import _do_serve

        _do_serve(
            MagicMock(),
            transport="stdio",
            host="127.0.0.1",
            port=9100,
            name="test",
        )

        mock_serve.assert_called_once()
        assert "authenticator" not in mock_serve.call_args.kwargs


# ---------------------------------------------------------------------------
# JWTAuthenticator import error
# ---------------------------------------------------------------------------


class TestJwtAuthenticatorImportError:
    """serve raises ClickException when apcore-mcp < 0.7.0 (no JWTAuthenticator)."""

    def test_jwt_authenticator_import_error(self, serve_app):
        import types

        # Create a fake apcore_mcp module without JWTAuthenticator
        fake_module = types.ModuleType("apcore_mcp")
        fake_module.serve = MagicMock()

        with patch.dict("sys.modules", {"apcore_mcp": fake_module}):
            runner = serve_app.test_cli_runner()
            result = runner.invoke(args=["apcore", "serve", "--jwt-secret", "a-long-enough-secret"])

            assert result.exit_code != 0
            assert "apcore-mcp>=0.7.0" in result.output


# ---------------------------------------------------------------------------
# _do_serve import error
# ---------------------------------------------------------------------------


class TestDoServeImportError:
    """_do_serve raises ClickException when apcore-mcp not installed."""

    def test_import_error_message(self):
        from flask_apcore.cli import _do_serve
        import click

        mock_registry = MagicMock()
        mock_registry.count = 1

        with patch.dict("sys.modules", {"apcore_mcp": None}):
            with pytest.raises(click.ClickException, match="apcore-mcp is required"):
                _do_serve(
                    mock_registry,
                    transport="stdio",
                    host="127.0.0.1",
                    port=9100,
                    name="test",
                )
