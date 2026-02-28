"""Comprehensive tests for flask_apcore.config – ApcoreSettings & load_settings().

Covers:
- All default values are correct
- Each setting accepts valid values
- Each setting rejects invalid values with ValueError
- Frozen immutability of ApcoreSettings
- None fallback to default for every field with a default
"""

from __future__ import annotations

import dataclasses

import pytest
from flask import Flask

from flask_apcore.config import ApcoreSettings, load_settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(**overrides: object) -> Flask:
    """Create a minimal Flask app with APCORE_* config overrides."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    for key, value in overrides.items():
        app.config[key] = value
    return app


def _load(**overrides: object) -> ApcoreSettings:
    """Shortcut: build app + load_settings in one call."""
    return load_settings(_make_app(**overrides))


# ===========================================================================
# 1. All defaults are correct
# ===========================================================================


class TestAllDefaults:
    """When no APCORE_* keys are set, every field gets its default."""

    def test_defaults(self) -> None:
        settings = _load()

        # Existing fields
        assert settings.module_dir == "apcore_modules/"
        assert settings.auto_discover is True
        assert settings.serve_transport == "stdio"
        assert settings.serve_host == "127.0.0.1"
        assert settings.serve_port == 9100
        assert settings.server_name == "apcore-mcp"
        assert settings.binding_pattern == "*.binding.yaml"
        assert settings.scanner_source == "auto"
        assert settings.module_packages == []
        assert settings.middlewares == []
        assert settings.acl_path is None
        assert settings.context_factory is None
        assert settings.server_version is None
        assert settings.executor_config is None

        # New MCP Serve
        assert settings.serve_validate_inputs is False
        assert settings.serve_log_level is None

        # New Observability
        assert settings.tracing_enabled is False
        assert settings.tracing_exporter == "stdout"
        assert settings.tracing_otlp_endpoint is None
        assert settings.tracing_service_name == "flask-apcore"
        assert settings.metrics_enabled is False
        assert settings.metrics_buckets is None
        assert settings.logging_enabled is False
        assert settings.logging_format == "json"
        assert settings.logging_level == "INFO"

        # New Extensions
        assert settings.extensions == []

        # MCP Serve Explorer
        assert settings.serve_explorer is False
        assert settings.serve_explorer_prefix == "/explorer"
        assert settings.serve_allow_execute is False

        # JWT Authentication
        assert settings.serve_jwt_secret is None
        assert settings.serve_jwt_algorithm == "HS256"
        assert settings.serve_jwt_audience is None
        assert settings.serve_jwt_issuer is None


# ===========================================================================
# 2. None fallback to default
# ===========================================================================


class TestNoneFallback:
    """Setting a key to None should fall back to the default value."""

    @pytest.mark.parametrize(
        "config_key, expected_attr, expected_default",
        [
            ("APCORE_MODULE_DIR", "module_dir", "apcore_modules/"),
            ("APCORE_AUTO_DISCOVER", "auto_discover", True),
            ("APCORE_SERVE_TRANSPORT", "serve_transport", "stdio"),
            ("APCORE_SERVE_HOST", "serve_host", "127.0.0.1"),
            ("APCORE_SERVE_PORT", "serve_port", 9100),
            ("APCORE_SERVER_NAME", "server_name", "apcore-mcp"),
            ("APCORE_BINDING_PATTERN", "binding_pattern", "*.binding.yaml"),
            ("APCORE_SCANNER_SOURCE", "scanner_source", "auto"),
            ("APCORE_MODULE_PACKAGES", "module_packages", []),
            ("APCORE_MIDDLEWARES", "middlewares", []),
            ("APCORE_SERVE_VALIDATE_INPUTS", "serve_validate_inputs", False),
            ("APCORE_TRACING_ENABLED", "tracing_enabled", False),
            ("APCORE_TRACING_EXPORTER", "tracing_exporter", "stdout"),
            ("APCORE_TRACING_SERVICE_NAME", "tracing_service_name", "flask-apcore"),
            ("APCORE_METRICS_ENABLED", "metrics_enabled", False),
            ("APCORE_LOGGING_ENABLED", "logging_enabled", False),
            ("APCORE_LOGGING_FORMAT", "logging_format", "json"),
            ("APCORE_LOGGING_LEVEL", "logging_level", "INFO"),
            ("APCORE_EXTENSIONS", "extensions", []),
            ("APCORE_SERVE_EXPLORER", "serve_explorer", False),
            ("APCORE_SERVE_EXPLORER_PREFIX", "serve_explorer_prefix", "/explorer"),
            ("APCORE_SERVE_ALLOW_EXECUTE", "serve_allow_execute", False),
            ("APCORE_SERVE_JWT_ALGORITHM", "serve_jwt_algorithm", "HS256"),
        ],
    )
    def test_none_falls_back_to_default(self, config_key: str, expected_attr: str, expected_default: object) -> None:
        settings = _load(**{config_key: None})
        assert getattr(settings, expected_attr) == expected_default

    @pytest.mark.parametrize(
        "config_key, expected_attr",
        [
            ("APCORE_ACL_PATH", "acl_path"),
            ("APCORE_CONTEXT_FACTORY", "context_factory"),
            ("APCORE_SERVER_VERSION", "server_version"),
            ("APCORE_EXECUTOR_CONFIG", "executor_config"),
            ("APCORE_SERVE_LOG_LEVEL", "serve_log_level"),
            ("APCORE_TRACING_OTLP_ENDPOINT", "tracing_otlp_endpoint"),
            ("APCORE_METRICS_BUCKETS", "metrics_buckets"),
            ("APCORE_SERVE_JWT_SECRET", "serve_jwt_secret"),
            ("APCORE_SERVE_JWT_AUDIENCE", "serve_jwt_audience"),
            ("APCORE_SERVE_JWT_ISSUER", "serve_jwt_issuer"),
        ],
    )
    def test_none_stays_none_for_optional_fields(self, config_key: str, expected_attr: str) -> None:
        """Fields whose default is None should stay None when explicitly set to None."""
        settings = _load(**{config_key: None})
        assert getattr(settings, expected_attr) is None


# ===========================================================================
# 3. Frozen immutability
# ===========================================================================


class TestFrozenImmutability:
    """ApcoreSettings is a frozen dataclass; attribute assignment must fail."""

    def test_cannot_set_attribute(self) -> None:
        settings = _load()
        with pytest.raises(dataclasses.FrozenInstanceError):
            settings.module_dir = "other/"  # type: ignore[misc]

    def test_cannot_delete_attribute(self) -> None:
        settings = _load()
        with pytest.raises(dataclasses.FrozenInstanceError):
            del settings.auto_discover  # type: ignore[misc]


# ===========================================================================
# 4. Existing fields – valid values
# ===========================================================================


class TestModuleDir:
    def test_custom_string(self) -> None:
        s = _load(APCORE_MODULE_DIR="my_modules/")
        assert s.module_dir == "my_modules/"

    def test_path_object_accepted(self) -> None:
        from pathlib import Path

        s = _load(APCORE_MODULE_DIR=Path("my_modules"))
        assert s.module_dir == "my_modules"

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_MODULE_DIR"):
            _load(APCORE_MODULE_DIR=123)


class TestAutoDiscover:
    def test_false(self) -> None:
        s = _load(APCORE_AUTO_DISCOVER=False)
        assert s.auto_discover is False

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_AUTO_DISCOVER"):
            _load(APCORE_AUTO_DISCOVER="yes")


class TestServeTransport:
    @pytest.mark.parametrize("val", ["stdio", "streamable-http", "sse"])
    def test_valid_choices(self, val: str) -> None:
        s = _load(APCORE_SERVE_TRANSPORT=val)
        assert s.serve_transport == val

    def test_invalid_choice_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_TRANSPORT"):
            _load(APCORE_SERVE_TRANSPORT="grpc")


class TestServeHost:
    def test_custom_host(self) -> None:
        s = _load(APCORE_SERVE_HOST="0.0.0.0")
        assert s.serve_host == "0.0.0.0"

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_HOST"):
            _load(APCORE_SERVE_HOST=9100)


class TestServePort:
    def test_custom_port(self) -> None:
        s = _load(APCORE_SERVE_PORT=8080)
        assert s.serve_port == 8080

    def test_min_boundary(self) -> None:
        s = _load(APCORE_SERVE_PORT=1)
        assert s.serve_port == 1

    def test_max_boundary(self) -> None:
        s = _load(APCORE_SERVE_PORT=65535)
        assert s.serve_port == 65535

    def test_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_PORT"):
            _load(APCORE_SERVE_PORT=0)

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_PORT"):
            _load(APCORE_SERVE_PORT=-1)

    def test_too_high_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_PORT"):
            _load(APCORE_SERVE_PORT=65536)

    def test_bool_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_PORT"):
            _load(APCORE_SERVE_PORT=True)

    def test_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_PORT"):
            _load(APCORE_SERVE_PORT="8080")


class TestServerName:
    def test_custom_name(self) -> None:
        s = _load(APCORE_SERVER_NAME="my-server")
        assert s.server_name == "my-server"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVER_NAME"):
            _load(APCORE_SERVER_NAME="")

    def test_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVER_NAME"):
            _load(APCORE_SERVER_NAME="x" * 101)

    def test_exactly_100_chars(self) -> None:
        s = _load(APCORE_SERVER_NAME="x" * 100)
        assert len(s.server_name) == 100

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVER_NAME"):
            _load(APCORE_SERVER_NAME=42)


class TestBindingPattern:
    def test_custom_pattern(self) -> None:
        s = _load(APCORE_BINDING_PATTERN="*.yaml")
        assert s.binding_pattern == "*.yaml"

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_BINDING_PATTERN"):
            _load(APCORE_BINDING_PATTERN=123)


class TestScannerSource:
    @pytest.mark.parametrize("val", ["auto", "native", "smorest", "restx"])
    def test_valid_choices(self, val: str) -> None:
        s = _load(APCORE_SCANNER_SOURCE=val)
        assert s.scanner_source == val

    def test_invalid_choice_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SCANNER_SOURCE"):
            _load(APCORE_SCANNER_SOURCE="graphql")


class TestModulePackages:
    def test_custom_list(self) -> None:
        s = _load(APCORE_MODULE_PACKAGES=["my.pkg", "other.pkg"])
        assert s.module_packages == ["my.pkg", "other.pkg"]

    def test_non_list_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_MODULE_PACKAGES"):
            _load(APCORE_MODULE_PACKAGES="my.pkg")

    def test_list_with_non_strings_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_MODULE_PACKAGES"):
            _load(APCORE_MODULE_PACKAGES=["good", 123])


class TestMiddlewares:
    def test_custom_list(self) -> None:
        s = _load(APCORE_MIDDLEWARES=["my.middleware"])
        assert s.middlewares == ["my.middleware"]

    def test_non_list_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_MIDDLEWARES"):
            _load(APCORE_MIDDLEWARES="bad")

    def test_list_with_non_strings_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_MIDDLEWARES"):
            _load(APCORE_MIDDLEWARES=[42])


class TestAclPath:
    def test_valid_string(self) -> None:
        s = _load(APCORE_ACL_PATH="/etc/acl.yaml")
        assert s.acl_path == "/etc/acl.yaml"

    def test_none_default(self) -> None:
        s = _load()
        assert s.acl_path is None

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_ACL_PATH"):
            _load(APCORE_ACL_PATH=123)


class TestContextFactory:
    def test_valid_string(self) -> None:
        s = _load(APCORE_CONTEXT_FACTORY="myapp.ctx.factory")
        assert s.context_factory == "myapp.ctx.factory"

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_CONTEXT_FACTORY"):
            _load(APCORE_CONTEXT_FACTORY=True)


class TestServerVersion:
    def test_valid_string(self) -> None:
        s = _load(APCORE_SERVER_VERSION="1.2.3")
        assert s.server_version == "1.2.3"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVER_VERSION"):
            _load(APCORE_SERVER_VERSION="")

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVER_VERSION"):
            _load(APCORE_SERVER_VERSION=123)


class TestExecutorConfig:
    def test_valid_dict(self) -> None:
        s = _load(APCORE_EXECUTOR_CONFIG={"max_workers": 4})
        assert s.executor_config == {"max_workers": 4}

    def test_non_dict_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_EXECUTOR_CONFIG"):
            _load(APCORE_EXECUTOR_CONFIG="bad")


# ===========================================================================
# 5. New MCP Serve fields
# ===========================================================================


class TestServeValidateInputs:
    def test_true(self) -> None:
        s = _load(APCORE_SERVE_VALIDATE_INPUTS=True)
        assert s.serve_validate_inputs is True

    def test_false(self) -> None:
        s = _load(APCORE_SERVE_VALIDATE_INPUTS=False)
        assert s.serve_validate_inputs is False

    def test_non_bool_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_VALIDATE_INPUTS"):
            _load(APCORE_SERVE_VALIDATE_INPUTS="yes")

    def test_int_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_VALIDATE_INPUTS"):
            _load(APCORE_SERVE_VALIDATE_INPUTS=1)


class TestServeLogLevel:
    @pytest.mark.parametrize("val", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    def test_valid_levels(self, val: str) -> None:
        s = _load(APCORE_SERVE_LOG_LEVEL=val)
        assert s.serve_log_level == val

    def test_none_default(self) -> None:
        s = _load()
        assert s.serve_log_level is None

    def test_invalid_level_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_LOG_LEVEL"):
            _load(APCORE_SERVE_LOG_LEVEL="TRACE")

    def test_lowercase_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_LOG_LEVEL"):
            _load(APCORE_SERVE_LOG_LEVEL="debug")

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_LOG_LEVEL"):
            _load(APCORE_SERVE_LOG_LEVEL=10)


# ===========================================================================
# 6. New Observability fields
# ===========================================================================


class TestTracingEnabled:
    def test_true(self) -> None:
        s = _load(APCORE_TRACING_ENABLED=True)
        assert s.tracing_enabled is True

    def test_non_bool_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_TRACING_ENABLED"):
            _load(APCORE_TRACING_ENABLED="yes")


class TestTracingExporter:
    @pytest.mark.parametrize("val", ["stdout", "memory", "otlp"])
    def test_valid_exporters(self, val: str) -> None:
        s = _load(APCORE_TRACING_EXPORTER=val)
        assert s.tracing_exporter == val

    def test_invalid_exporter_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_TRACING_EXPORTER"):
            _load(APCORE_TRACING_EXPORTER="jaeger")


class TestTracingOtlpEndpoint:
    def test_valid_url(self) -> None:
        s = _load(APCORE_TRACING_OTLP_ENDPOINT="http://localhost:4317")
        assert s.tracing_otlp_endpoint == "http://localhost:4317"

    def test_none_default(self) -> None:
        s = _load()
        assert s.tracing_otlp_endpoint is None

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_TRACING_OTLP_ENDPOINT"):
            _load(APCORE_TRACING_OTLP_ENDPOINT=4317)


class TestTracingServiceName:
    def test_custom_name(self) -> None:
        s = _load(APCORE_TRACING_SERVICE_NAME="my-service")
        assert s.tracing_service_name == "my-service"

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_TRACING_SERVICE_NAME"):
            _load(APCORE_TRACING_SERVICE_NAME=42)

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_TRACING_SERVICE_NAME"):
            _load(APCORE_TRACING_SERVICE_NAME="")


class TestMetricsEnabled:
    def test_true(self) -> None:
        s = _load(APCORE_METRICS_ENABLED=True)
        assert s.metrics_enabled is True

    def test_non_bool_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_METRICS_ENABLED"):
            _load(APCORE_METRICS_ENABLED=1)


class TestMetricsBuckets:
    def test_valid_list(self) -> None:
        buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
        s = _load(APCORE_METRICS_BUCKETS=buckets)
        assert s.metrics_buckets == buckets

    def test_none_default(self) -> None:
        s = _load()
        assert s.metrics_buckets is None

    def test_non_list_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_METRICS_BUCKETS"):
            _load(APCORE_METRICS_BUCKETS="0.1,0.5")

    def test_list_with_non_numeric_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_METRICS_BUCKETS"):
            _load(APCORE_METRICS_BUCKETS=[0.1, "bad", 0.5])


class TestLoggingEnabled:
    def test_true(self) -> None:
        s = _load(APCORE_LOGGING_ENABLED=True)
        assert s.logging_enabled is True

    def test_non_bool_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_LOGGING_ENABLED"):
            _load(APCORE_LOGGING_ENABLED="true")


class TestLoggingFormat:
    @pytest.mark.parametrize("val", ["json", "text"])
    def test_valid_formats(self, val: str) -> None:
        s = _load(APCORE_LOGGING_FORMAT=val)
        assert s.logging_format == val

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_LOGGING_FORMAT"):
            _load(APCORE_LOGGING_FORMAT="xml")


class TestLoggingLevel:
    @pytest.mark.parametrize(
        "val", ["trace", "debug", "info", "warn", "error", "fatal", "TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"]
    )
    def test_valid_levels_case_insensitive(self, val: str) -> None:
        s = _load(APCORE_LOGGING_LEVEL=val)
        assert s.logging_level == val

    def test_default_is_info(self) -> None:
        s = _load()
        assert s.logging_level == "INFO"

    def test_invalid_level_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_LOGGING_LEVEL"):
            _load(APCORE_LOGGING_LEVEL="verbose")

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_LOGGING_LEVEL"):
            _load(APCORE_LOGGING_LEVEL=10)


# ===========================================================================
# 7. New Extensions field
# ===========================================================================


class TestExtensions:
    def test_custom_list(self) -> None:
        s = _load(APCORE_EXTENSIONS=["my.ext.Auth", "my.ext.Cache"])
        assert s.extensions == ["my.ext.Auth", "my.ext.Cache"]

    def test_non_list_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_EXTENSIONS"):
            _load(APCORE_EXTENSIONS="bad")

    def test_list_with_non_strings_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_EXTENSIONS"):
            _load(APCORE_EXTENSIONS=[42])


# ===========================================================================
# 8. Combined / integration scenarios
# ===========================================================================


class TestCombinedSettings:
    """Verify that multiple settings can be set simultaneously."""

    def test_several_overrides(self) -> None:
        s = _load(
            APCORE_MODULE_DIR="custom/",
            APCORE_AUTO_DISCOVER=False,
            APCORE_SERVE_PORT=8080,
            APCORE_TRACING_ENABLED=True,
            APCORE_TRACING_EXPORTER="otlp",
            APCORE_TRACING_OTLP_ENDPOINT="http://otel:4317",
            APCORE_LOGGING_ENABLED=True,
            APCORE_LOGGING_FORMAT="text",
            APCORE_EXTENSIONS=["my.ext"],
        )
        assert s.module_dir == "custom/"
        assert s.auto_discover is False
        assert s.serve_port == 8080
        assert s.tracing_enabled is True
        assert s.tracing_exporter == "otlp"
        assert s.tracing_otlp_endpoint == "http://otel:4317"
        assert s.logging_enabled is True
        assert s.logging_format == "text"
        assert s.extensions == ["my.ext"]

    def test_dataclass_fields_count(self) -> None:
        """Ensure ApcoreSettings has exactly the expected number of fields."""
        fields = dataclasses.fields(ApcoreSettings)
        # 26 existing + 3 serve explorer + 4 JWT auth = 33
        assert len(fields) == 33


# ===========================================================================
# 9. MCP Serve Explorer settings
# ===========================================================================


class TestServeExplorer:
    def test_default_false(self) -> None:
        s = _load()
        assert s.serve_explorer is False

    def test_true(self) -> None:
        s = _load(APCORE_SERVE_EXPLORER=True)
        assert s.serve_explorer is True

    def test_none_falls_back(self) -> None:
        s = _load(APCORE_SERVE_EXPLORER=None)
        assert s.serve_explorer is False

    def test_non_bool_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_EXPLORER"):
            _load(APCORE_SERVE_EXPLORER="yes")


class TestServeExplorerPrefix:
    def test_default(self) -> None:
        s = _load()
        assert s.serve_explorer_prefix == "/explorer"

    def test_custom(self) -> None:
        s = _load(APCORE_SERVE_EXPLORER_PREFIX="/tools")
        assert s.serve_explorer_prefix == "/tools"

    def test_none_falls_back(self) -> None:
        s = _load(APCORE_SERVE_EXPLORER_PREFIX=None)
        assert s.serve_explorer_prefix == "/explorer"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_EXPLORER_PREFIX"):
            _load(APCORE_SERVE_EXPLORER_PREFIX="")

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_EXPLORER_PREFIX"):
            _load(APCORE_SERVE_EXPLORER_PREFIX=123)


class TestServeAllowExecute:
    def test_default_false(self) -> None:
        s = _load()
        assert s.serve_allow_execute is False

    def test_true(self) -> None:
        s = _load(APCORE_SERVE_ALLOW_EXECUTE=True)
        assert s.serve_allow_execute is True

    def test_none_falls_back(self) -> None:
        s = _load(APCORE_SERVE_ALLOW_EXECUTE=None)
        assert s.serve_allow_execute is False

    def test_non_bool_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_ALLOW_EXECUTE"):
            _load(APCORE_SERVE_ALLOW_EXECUTE="yes")


# ===========================================================================
# 10. JWT Authentication settings
# ===========================================================================


class TestServeJwtSecret:
    def test_none_default(self) -> None:
        s = _load()
        assert s.serve_jwt_secret is None

    def test_valid_string(self) -> None:
        s = _load(APCORE_SERVE_JWT_SECRET="my-secret-key-long-enough")
        assert s.serve_jwt_secret == "my-secret-key-long-enough"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_JWT_SECRET"):
            _load(APCORE_SERVE_JWT_SECRET="")

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_JWT_SECRET"):
            _load(APCORE_SERVE_JWT_SECRET=12345)

    def test_short_hmac_secret_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 16 characters"):
            _load(APCORE_SERVE_JWT_SECRET="short")

    def test_short_secret_ok_for_rsa(self) -> None:
        s = _load(APCORE_SERVE_JWT_SECRET="short", APCORE_SERVE_JWT_ALGORITHM="RS256")
        assert s.serve_jwt_secret == "short"

    def test_exactly_16_chars_ok(self) -> None:
        s = _load(APCORE_SERVE_JWT_SECRET="a" * 16)
        assert s.serve_jwt_secret == "a" * 16


class TestServeJwtAlgorithm:
    @pytest.mark.parametrize("val", ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"])
    def test_valid_algorithms(self, val: str) -> None:
        s = _load(APCORE_SERVE_JWT_ALGORITHM=val)
        assert s.serve_jwt_algorithm == val

    def test_default_hs256(self) -> None:
        s = _load()
        assert s.serve_jwt_algorithm == "HS256"

    def test_none_falls_back(self) -> None:
        s = _load(APCORE_SERVE_JWT_ALGORITHM=None)
        assert s.serve_jwt_algorithm == "HS256"

    def test_invalid_algorithm_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_JWT_ALGORITHM"):
            _load(APCORE_SERVE_JWT_ALGORITHM="NONE")


class TestServeJwtAudience:
    def test_none_default(self) -> None:
        s = _load()
        assert s.serve_jwt_audience is None

    def test_valid_string(self) -> None:
        s = _load(APCORE_SERVE_JWT_AUDIENCE="my-api")
        assert s.serve_jwt_audience == "my-api"

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_JWT_AUDIENCE"):
            _load(APCORE_SERVE_JWT_AUDIENCE=123)


class TestServeJwtIssuer:
    def test_none_default(self) -> None:
        s = _load()
        assert s.serve_jwt_issuer is None

    def test_valid_string(self) -> None:
        s = _load(APCORE_SERVE_JWT_ISSUER="https://auth.example.com")
        assert s.serve_jwt_issuer == "https://auth.example.com"

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_SERVE_JWT_ISSUER"):
            _load(APCORE_SERVE_JWT_ISSUER=True)
