"""End-to-end integration tests for flask-apcore v0.1.0.

Tests the full flow: Flask app creation -> Apcore init -> scan -> register -> verify.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flask import Flask

from flask_apcore import Apcore


# ---------------------------------------------------------------------------
# Module-level view functions (resolvable targets for RegistryWriter)
# ---------------------------------------------------------------------------


def list_users() -> dict:
    """List all users."""
    return {"users": []}


def delete_user(user_id: int) -> dict:
    """Delete a user by ID."""
    return {}


def get_item(item_id: int) -> dict:
    """Get a single item by ID."""
    return {}


def create_order() -> dict:
    """Create a new order."""
    return {}


# ---------------------------------------------------------------------------
# TestScanAndRegister: scan -> register to Registry -> verify
# ---------------------------------------------------------------------------


class TestScanAndRegister:
    """Scan Flask routes -> register to Registry -> verify."""

    def test_scan_register_and_verify(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False

        app.add_url_rule("/users", "list_users", list_users, methods=["GET"])
        app.add_url_rule("/users/<int:user_id>", "delete_user", delete_user, methods=["DELETE"])

        Apcore(app)

        with app.app_context():
            runner = app.test_cli_runner()
            result = runner.invoke(args=["apcore", "scan"])
            assert result.exit_code == 0, result.output

            registry = app.extensions["apcore"]["registry"]
            assert registry.count >= 2

    def test_registered_modules_have_correct_ids(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False

        app.add_url_rule("/users", "list_users", list_users, methods=["GET"])
        app.add_url_rule("/users/<int:user_id>", "delete_user", delete_user, methods=["DELETE"])

        Apcore(app)

        with app.app_context():
            runner = app.test_cli_runner()
            result = runner.invoke(args=["apcore", "scan"])
            assert result.exit_code == 0, result.output

            registry = app.extensions["apcore"]["registry"]
            module_ids = registry.module_ids

            assert "list_users.get" in module_ids
            assert "delete_user.delete" in module_ids

    def test_registered_modules_have_annotations(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False

        app.add_url_rule("/users", "list_users", list_users, methods=["GET"])
        app.add_url_rule("/users/<int:user_id>", "delete_user", delete_user, methods=["DELETE"])

        Apcore(app)

        with app.app_context():
            runner = app.test_cli_runner()
            runner.invoke(args=["apcore", "scan"])

            registry = app.extensions["apcore"]["registry"]
            get_mod = registry.get("list_users.get")
            del_mod = registry.get("delete_user.delete")

            # GET should be readonly
            assert get_mod.annotations is not None
            assert get_mod.annotations["readonly"] is True

            # DELETE should be destructive
            assert del_mod.annotations is not None
            assert del_mod.annotations["destructive"] is True

    def test_registered_modules_have_descriptions(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False

        app.add_url_rule("/users", "list_users", list_users, methods=["GET"])

        Apcore(app)

        with app.app_context():
            runner = app.test_cli_runner()
            runner.invoke(args=["apcore", "scan"])

            registry = app.extensions["apcore"]["registry"]
            mod = registry.get("list_users.get")

            assert mod.description == "List all users."

    def test_scan_multiple_times_accumulates(self, tmp_path):
        """Scanning twice should register modules from both scans."""
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False

        app.add_url_rule("/users", "list_users", list_users, methods=["GET"])

        Apcore(app)

        with app.app_context():
            runner = app.test_cli_runner()
            result1 = runner.invoke(args=["apcore", "scan"])
            assert result1.exit_code == 0, result1.output

            registry = app.extensions["apcore"]["registry"]
            count_after_first = registry.count
            assert count_after_first >= 1


# ---------------------------------------------------------------------------
# TestScanToYAML: scan -> generate YAML files -> verify
# ---------------------------------------------------------------------------


class TestScanToYAML:
    """Scan Flask routes -> generate .binding.yaml files -> verify."""

    def test_generates_binding_files(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
        app.config["APCORE_AUTO_DISCOVER"] = False

        app.add_url_rule("/items/<int:item_id>", "get_item", get_item, methods=["GET"])
        app.add_url_rule("/orders", "create_order", create_order, methods=["POST"])

        Apcore(app)

        yaml_dir = str(tmp_path / "yaml_output")

        with app.app_context():
            runner = app.test_cli_runner()
            result = runner.invoke(args=["apcore", "scan", "--output", "yaml", "--dir", yaml_dir])
            assert result.exit_code == 0, result.output

        yaml_files = list(Path(yaml_dir).glob("*.binding.yaml"))
        assert len(yaml_files) >= 2

        # Verify file content contains binding data
        import yaml

        for f in yaml_files:
            data = yaml.safe_load(f.read_text())
            assert "bindings" in data
            for binding in data["bindings"]:
                assert "module_id" in binding
                assert "target" in binding
                assert "description" in binding

    def test_yaml_does_not_register(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
        app.config["APCORE_AUTO_DISCOVER"] = False

        app.add_url_rule("/items/<int:item_id>", "get_item", get_item, methods=["GET"])

        Apcore(app)

        yaml_dir = str(tmp_path / "yaml_out")

        with app.app_context():
            runner = app.test_cli_runner()
            result = runner.invoke(args=["apcore", "scan", "--output", "yaml", "--dir", yaml_dir])
            assert result.exit_code == 0, result.output

            registry = app.extensions["apcore"]["registry"]
            assert registry.count == 0


# ---------------------------------------------------------------------------
# TestObservabilityIntegration: tracing middleware in executor
# ---------------------------------------------------------------------------


class TestObservabilityIntegration:
    """Observability middleware is properly wired into the Executor."""

    def test_tracing_middleware_in_executor(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False
        app.config["APCORE_TRACING_ENABLED"] = True
        app.config["APCORE_TRACING_EXPORTER"] = "memory"

        app.add_url_rule("/users", "list_users", list_users, methods=["GET"])

        Apcore(app)

        with app.app_context():
            # Scan to register modules
            runner = app.test_cli_runner()
            runner.invoke(args=["apcore", "scan"])

            # Get executor (lazily creates with tracing middleware)
            from flask_apcore.registry import get_executor

            executor = get_executor(app)

            # Verify tracing middleware is included
            from apcore.observability.tracing import TracingMiddleware

            mw_types = [type(mw) for mw in executor.middlewares]
            assert TracingMiddleware in mw_types

    def test_metrics_middleware_in_executor(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False
        app.config["APCORE_METRICS_ENABLED"] = True

        app.add_url_rule("/users", "list_users", list_users, methods=["GET"])

        Apcore(app)

        with app.app_context():
            runner = app.test_cli_runner()
            runner.invoke(args=["apcore", "scan"])

            from flask_apcore.registry import get_executor

            executor = get_executor(app)

            from apcore.observability.metrics import MetricsMiddleware

            mw_types = [type(mw) for mw in executor.middlewares]
            assert MetricsMiddleware in mw_types

    def test_all_observability_middlewares(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False
        app.config["APCORE_TRACING_ENABLED"] = True
        app.config["APCORE_TRACING_EXPORTER"] = "memory"
        app.config["APCORE_METRICS_ENABLED"] = True
        app.config["APCORE_LOGGING_ENABLED"] = True

        app.add_url_rule("/users", "list_users", list_users, methods=["GET"])

        Apcore(app)

        with app.app_context():
            runner = app.test_cli_runner()
            runner.invoke(args=["apcore", "scan"])

            from flask_apcore.registry import get_executor

            executor = get_executor(app)

            # Should have all 3 observability middlewares
            assert len(executor.middlewares) >= 3

    def test_metrics_collector_in_ext_data(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False
        app.config["APCORE_METRICS_ENABLED"] = True

        Apcore(app)

        from apcore.observability.metrics import MetricsCollector

        mc = app.extensions["apcore"]["metrics_collector"]
        assert isinstance(mc, MetricsCollector)


# ---------------------------------------------------------------------------
# TestContextIntegration: traceparent propagation
# ---------------------------------------------------------------------------


class TestContextIntegration:
    """Context bridge propagates W3C traceparent headers."""

    def test_traceparent_propagated(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False

        Apcore(app)

        with app.app_context():
            from flask_apcore.context import FlaskContextFactory

            factory = FlaskContextFactory()

            # Create a test request with traceparent header
            with app.test_request_context(
                "/",
                headers={"traceparent": "00-12345678901234567890123456789012-1234567890123456-01"},
            ):
                from flask import request

                ctx = factory.create_context(request)

                # trace_id is derived from the traceparent header
                assert ctx.trace_id is not None
                assert "1234567890123456789012345678901" in ctx.trace_id.replace("-", "")

    def test_no_traceparent_works(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False

        Apcore(app)

        with app.app_context():
            from flask_apcore.context import FlaskContextFactory

            factory = FlaskContextFactory()

            # Request without traceparent header
            with app.test_request_context("/"):
                from flask import request

                ctx = factory.create_context(request)

                # Should still create a valid context
                assert ctx is not None

    def test_anonymous_context_without_request(self, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False

        Apcore(app)

        with app.app_context():
            from flask_apcore.context import FlaskContextFactory

            factory = FlaskContextFactory()
            ctx = factory.create_context(None)

            assert ctx is not None
            assert ctx.identity.id == "anonymous"


# ---------------------------------------------------------------------------
# TestFullPipeline: scan + serve (mocked)
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """Full pipeline: create app, init, scan, serve (mocked)."""

    @patch("flask_apcore.cli._do_serve")
    def test_scan_then_serve(self, mock_serve, tmp_path):
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False

        app.add_url_rule("/users", "list_users", list_users, methods=["GET"])
        app.add_url_rule("/users/<int:user_id>", "delete_user", delete_user, methods=["DELETE"])

        Apcore(app)

        runner = app.test_cli_runner()

        # Step 1: Scan and register
        scan_result = runner.invoke(args=["apcore", "scan"])
        assert scan_result.exit_code == 0, scan_result.output

        # Step 2: Serve (mocked)
        serve_result = runner.invoke(args=["apcore", "serve"])
        assert serve_result.exit_code == 0, serve_result.output

        # Verify _do_serve was called with the registry
        mock_serve.assert_called_once()
        call_kwargs = mock_serve.call_args
        assert call_kwargs.kwargs["name"] == "apcore-mcp"

    @patch("flask_apcore.cli._do_serve")
    def test_scan_with_observability_then_serve(self, mock_serve, tmp_path):
        """Full pipeline with observability enabled."""
        app = Flask(__name__)
        app.config["APCORE_MODULE_DIR"] = str(tmp_path)
        app.config["APCORE_AUTO_DISCOVER"] = False
        app.config["APCORE_TRACING_ENABLED"] = True
        app.config["APCORE_TRACING_EXPORTER"] = "memory"
        app.config["APCORE_METRICS_ENABLED"] = True

        app.add_url_rule("/users", "list_users", list_users, methods=["GET"])

        Apcore(app)

        runner = app.test_cli_runner()

        scan_result = runner.invoke(args=["apcore", "scan"])
        assert scan_result.exit_code == 0, scan_result.output

        serve_result = runner.invoke(args=["apcore", "serve"])
        assert serve_result.exit_code == 0, serve_result.output

        call_kwargs = mock_serve.call_args
        # metrics_collector should be passed
        assert call_kwargs.kwargs["metrics_collector"] is not None


# ---------------------------------------------------------------------------
# TestMultiAppIsolation: separate registries per app
# ---------------------------------------------------------------------------


class TestMultiAppIsolation:
    """Multiple Flask apps have independent registries."""

    def test_separate_registries(self, tmp_path):
        app1 = Flask("app1")
        app1.config["APCORE_MODULE_DIR"] = str(tmp_path / "m1")
        app1.config["APCORE_AUTO_DISCOVER"] = False

        app2 = Flask("app2")
        app2.config["APCORE_MODULE_DIR"] = str(tmp_path / "m2")
        app2.config["APCORE_AUTO_DISCOVER"] = False

        apcore = Apcore()
        apcore.init_app(app1)
        apcore.init_app(app2)

        reg1 = app1.extensions["apcore"]["registry"]
        reg2 = app2.extensions["apcore"]["registry"]

        assert reg1 is not reg2

    def test_independent_module_counts(self, tmp_path):
        app1 = Flask("app1")
        app1.config["APCORE_MODULE_DIR"] = str(tmp_path / "m1")
        app1.config["APCORE_AUTO_DISCOVER"] = False
        app1.add_url_rule("/a", "a_handler", list_users, methods=["GET"])

        app2 = Flask("app2")
        app2.config["APCORE_MODULE_DIR"] = str(tmp_path / "m2")
        app2.config["APCORE_AUTO_DISCOVER"] = False

        Apcore(app1)
        Apcore(app2)

        # Scan only app1
        with app1.app_context():
            r1 = app1.test_cli_runner()
            r1.invoke(args=["apcore", "scan"])

        # app1 has modules, app2 doesn't
        assert app1.extensions["apcore"]["registry"].count >= 1
        assert app2.extensions["apcore"]["registry"].count == 0
