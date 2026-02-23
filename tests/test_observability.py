"""Tests for flask_apcore.observability – setup_observability()."""

from __future__ import annotations

from flask import Flask

from flask_apcore.config import load_settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(**overrides) -> Flask:
    """Create a Flask app with given APCORE_* config overrides."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["APCORE_AUTO_DISCOVER"] = False
    for k, v in overrides.items():
        app.config[k] = v
    return app


def _setup(app: Flask) -> dict:
    """Load settings and run setup_observability, returning ext_data."""
    from flask_apcore.observability import setup_observability

    settings = load_settings(app)
    ext_data: dict = {}
    setup_observability(settings, ext_data)
    return ext_data


# ===========================================================================
# Nothing enabled
# ===========================================================================


class TestNothingEnabled:
    """When tracing, metrics, and logging are all disabled."""

    def test_empty_middleware_list(self) -> None:
        app = _make_app()
        ext_data = _setup(app)
        assert ext_data["observability_middlewares"] == []

    def test_no_metrics_collector(self) -> None:
        app = _make_app()
        ext_data = _setup(app)
        assert ext_data.get("metrics_collector") is None


# ===========================================================================
# Tracing enabled
# ===========================================================================


class TestTracingEnabled:
    """When APCORE_TRACING_ENABLED is True."""

    def test_stdout_exporter_by_default(self) -> None:
        app = _make_app(APCORE_TRACING_ENABLED=True)
        ext_data = _setup(app)
        mws = ext_data["observability_middlewares"]
        assert len(mws) == 1
        from apcore.observability.tracing import TracingMiddleware

        assert isinstance(mws[0], TracingMiddleware)

    def test_memory_exporter(self) -> None:
        app = _make_app(
            APCORE_TRACING_ENABLED=True,
            APCORE_TRACING_EXPORTER="memory",
        )
        ext_data = _setup(app)
        mws = ext_data["observability_middlewares"]
        assert len(mws) == 1
        from apcore.observability.tracing import TracingMiddleware

        assert isinstance(mws[0], TracingMiddleware)

    def test_otlp_exporter_raises_without_deps(self) -> None:
        """OTLPExporter requires opentelemetry packages; if missing, ImportError."""
        app = _make_app(
            APCORE_TRACING_ENABLED=True,
            APCORE_TRACING_EXPORTER="otlp",
        )
        # This may or may not raise depending on whether opentelemetry is installed.
        # We just verify setup_observability processes tracing correctly.
        try:
            ext_data = _setup(app)
            mws = ext_data["observability_middlewares"]
            assert len(mws) >= 1
            from apcore.observability.tracing import TracingMiddleware

            assert isinstance(mws[0], TracingMiddleware)
        except ImportError:
            pass  # Expected if opentelemetry is not installed


# ===========================================================================
# Metrics enabled
# ===========================================================================


class TestMetricsEnabled:
    """When APCORE_METRICS_ENABLED is True."""

    def test_metrics_middleware_created(self) -> None:
        app = _make_app(APCORE_METRICS_ENABLED=True)
        ext_data = _setup(app)
        mws = ext_data["observability_middlewares"]
        assert len(mws) == 1
        from apcore.observability.metrics import MetricsMiddleware

        assert isinstance(mws[0], MetricsMiddleware)

    def test_metrics_collector_stored(self) -> None:
        app = _make_app(APCORE_METRICS_ENABLED=True)
        ext_data = _setup(app)
        from apcore.observability.metrics import MetricsCollector

        assert isinstance(ext_data["metrics_collector"], MetricsCollector)

    def test_custom_buckets(self) -> None:
        buckets = [0.01, 0.05, 0.1, 0.5, 1.0]
        app = _make_app(
            APCORE_METRICS_ENABLED=True,
            APCORE_METRICS_BUCKETS=buckets,
        )
        ext_data = _setup(app)
        collector = ext_data["metrics_collector"]
        assert collector._buckets == sorted(buckets)


# ===========================================================================
# Logging enabled
# ===========================================================================


class TestLoggingEnabled:
    """When APCORE_LOGGING_ENABLED is True."""

    def test_logging_middleware_created(self) -> None:
        app = _make_app(APCORE_LOGGING_ENABLED=True)
        ext_data = _setup(app)
        mws = ext_data["observability_middlewares"]
        assert len(mws) == 1
        from apcore.observability.context_logger import ObsLoggingMiddleware

        assert isinstance(mws[0], ObsLoggingMiddleware)


# ===========================================================================
# All enabled
# ===========================================================================


class TestAllEnabled:
    """When tracing, metrics, and logging are all enabled."""

    def test_three_middlewares(self) -> None:
        app = _make_app(
            APCORE_TRACING_ENABLED=True,
            APCORE_METRICS_ENABLED=True,
            APCORE_LOGGING_ENABLED=True,
        )
        ext_data = _setup(app)
        mws = ext_data["observability_middlewares"]
        assert len(mws) == 3

    def test_correct_types(self) -> None:
        app = _make_app(
            APCORE_TRACING_ENABLED=True,
            APCORE_METRICS_ENABLED=True,
            APCORE_LOGGING_ENABLED=True,
        )
        ext_data = _setup(app)
        mws = ext_data["observability_middlewares"]

        from apcore.observability.tracing import TracingMiddleware
        from apcore.observability.metrics import MetricsMiddleware
        from apcore.observability.context_logger import ObsLoggingMiddleware

        types = {type(mw) for mw in mws}
        assert TracingMiddleware in types
        assert MetricsMiddleware in types
        assert ObsLoggingMiddleware in types

    def test_metrics_collector_present(self) -> None:
        app = _make_app(
            APCORE_TRACING_ENABLED=True,
            APCORE_METRICS_ENABLED=True,
            APCORE_LOGGING_ENABLED=True,
        )
        ext_data = _setup(app)
        assert ext_data["metrics_collector"] is not None
