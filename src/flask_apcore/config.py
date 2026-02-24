"""APCORE_* settings resolution and validation.

Reads all APCORE_* settings from Flask's app.config, applies defaults,
validates types and values, and exposes a frozen dataclass for internal use.

Adapted from django-apcore's settings.py, replacing django.conf.settings
with app.config and ImproperlyConfigured with ValueError.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask import Flask

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_MODULE_DIR = "apcore_modules/"
DEFAULT_AUTO_DISCOVER = True
DEFAULT_SERVE_TRANSPORT = "stdio"
DEFAULT_SERVE_HOST = "127.0.0.1"
DEFAULT_SERVE_PORT = 9100
DEFAULT_SERVER_NAME = "apcore-mcp"
DEFAULT_BINDING_PATTERN = "*.binding.yaml"
DEFAULT_SCANNER_SOURCE = "auto"

# New MCP Serve defaults
DEFAULT_SERVE_VALIDATE_INPUTS = False

# New Observability defaults
DEFAULT_TRACING_ENABLED = False
DEFAULT_TRACING_EXPORTER = "stdout"
DEFAULT_TRACING_SERVICE_NAME = "flask-apcore"
DEFAULT_METRICS_ENABLED = False
DEFAULT_LOGGING_ENABLED = False
DEFAULT_LOGGING_FORMAT = "json"
DEFAULT_LOGGING_LEVEL = "INFO"

# Explorer defaults
DEFAULT_EXPLORER_ENABLED = False
DEFAULT_EXPLORER_URL_PREFIX = "/apcore"
DEFAULT_EXPLORER_ALLOW_EXECUTE = False

# ---------------------------------------------------------------------------
# Valid choices
# ---------------------------------------------------------------------------
VALID_TRANSPORTS = ("stdio", "streamable-http", "sse")
VALID_SCANNER_SOURCES = ("auto", "native", "smorest", "restx")
VALID_SERVE_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
VALID_TRACING_EXPORTERS = ("stdout", "memory", "otlp")
VALID_LOGGING_FORMATS = ("json", "text")
VALID_LOGGING_LEVELS = ("trace", "debug", "info", "warn", "error", "fatal")


@dataclass(frozen=True)
class ApcoreSettings:
    """Validated APCORE_* settings.

    All fields are immutable after validation. Created by load_settings().
    """

    # Existing
    module_dir: str
    auto_discover: bool
    serve_transport: str
    serve_host: str
    serve_port: int
    server_name: str
    binding_pattern: str
    scanner_source: str
    module_packages: list[str]
    middlewares: list[str]
    acl_path: str | None
    context_factory: str | None
    server_version: str | None
    executor_config: dict[str, Any] | None

    # New MCP Serve
    serve_validate_inputs: bool
    serve_log_level: str | None

    # New Observability
    tracing_enabled: bool
    tracing_exporter: str
    tracing_otlp_endpoint: str | None
    tracing_service_name: str
    metrics_enabled: bool
    metrics_buckets: list[float] | None
    logging_enabled: bool
    logging_format: str
    logging_level: str

    # New Extensions
    extensions: list[str]

    # Explorer
    explorer_enabled: bool
    explorer_url_prefix: str
    explorer_allow_execute: bool


def load_settings(app: Flask) -> ApcoreSettings:
    """Read and validate APCORE_* settings from app.config.

    Each Flask config key is ``APCORE_`` + uppercase field name
    (e.g. ``APCORE_MODULE_DIR``).  ``None`` values fall back to defaults.

    Args:
        app: Flask application instance.

    Returns:
        Validated, frozen ApcoreSettings dataclass.

    Raises:
        ValueError: If any setting is invalid.
    """
    # === Existing fields ===

    # --- module_dir ---
    module_dir = app.config.get("APCORE_MODULE_DIR", DEFAULT_MODULE_DIR)
    if module_dir is None:
        module_dir = DEFAULT_MODULE_DIR
    if not isinstance(module_dir, (str, Path)):
        actual = type(module_dir).__name__
        raise ValueError(f"APCORE_MODULE_DIR must be a string path. Got: {actual}")
    module_dir = str(module_dir)

    # --- auto_discover ---
    auto_discover = app.config.get("APCORE_AUTO_DISCOVER", DEFAULT_AUTO_DISCOVER)
    if auto_discover is None:
        auto_discover = DEFAULT_AUTO_DISCOVER
    if not isinstance(auto_discover, bool):
        actual = type(auto_discover).__name__
        raise ValueError(f"APCORE_AUTO_DISCOVER must be a boolean. Got: {actual}")

    # --- serve_transport ---
    serve_transport = app.config.get("APCORE_SERVE_TRANSPORT", DEFAULT_SERVE_TRANSPORT)
    if serve_transport is None:
        serve_transport = DEFAULT_SERVE_TRANSPORT
    if serve_transport not in VALID_TRANSPORTS:
        choices = ", ".join(VALID_TRANSPORTS)
        raise ValueError(f"APCORE_SERVE_TRANSPORT must be one of: {choices}." f" Got: '{serve_transport}'")

    # --- serve_host ---
    serve_host = app.config.get("APCORE_SERVE_HOST", DEFAULT_SERVE_HOST)
    if serve_host is None:
        serve_host = DEFAULT_SERVE_HOST
    if not isinstance(serve_host, str):
        actual = type(serve_host).__name__
        raise ValueError(f"APCORE_SERVE_HOST must be a string. Got: {actual}")

    # --- serve_port ---
    serve_port = app.config.get("APCORE_SERVE_PORT", DEFAULT_SERVE_PORT)
    if serve_port is None:
        serve_port = DEFAULT_SERVE_PORT
    if not isinstance(serve_port, int) or isinstance(serve_port, bool):
        actual = type(serve_port).__name__
        raise ValueError(f"APCORE_SERVE_PORT must be an integer between 1 and 65535." f" Got: {actual}")
    if not (1 <= serve_port <= 65535):
        raise ValueError(f"APCORE_SERVE_PORT must be an integer between 1 and 65535." f" Got: {serve_port}")

    # --- server_name ---
    server_name = app.config.get("APCORE_SERVER_NAME", DEFAULT_SERVER_NAME)
    if server_name is None:
        server_name = DEFAULT_SERVER_NAME
    if not isinstance(server_name, str) or len(server_name) == 0 or len(server_name) > 100:
        raise ValueError("APCORE_SERVER_NAME must be a non-empty string up to 100 characters.")

    # --- binding_pattern ---
    binding_pattern = app.config.get("APCORE_BINDING_PATTERN", DEFAULT_BINDING_PATTERN)
    if binding_pattern is None:
        binding_pattern = DEFAULT_BINDING_PATTERN
    if not isinstance(binding_pattern, str):
        raise ValueError("APCORE_BINDING_PATTERN must be a valid glob pattern string.")

    # --- scanner_source ---
    scanner_source = app.config.get("APCORE_SCANNER_SOURCE", DEFAULT_SCANNER_SOURCE)
    if scanner_source is None:
        scanner_source = DEFAULT_SCANNER_SOURCE
    if scanner_source not in VALID_SCANNER_SOURCES:
        choices = ", ".join(VALID_SCANNER_SOURCES)
        raise ValueError(f"APCORE_SCANNER_SOURCE must be one of: {choices}." f" Got: '{scanner_source}'")

    # --- module_packages ---
    module_packages = app.config.get("APCORE_MODULE_PACKAGES", [])
    if module_packages is None:
        module_packages = []
    if not isinstance(module_packages, list) or not all(isinstance(p, str) for p in module_packages):
        raise ValueError("APCORE_MODULE_PACKAGES must be a list of dotted path strings.")

    # --- middlewares ---
    middlewares = app.config.get("APCORE_MIDDLEWARES", [])
    if middlewares is None:
        middlewares = []
    if not isinstance(middlewares, list) or not all(isinstance(m, str) for m in middlewares):
        raise ValueError("APCORE_MIDDLEWARES must be a list of dotted path strings.")

    # --- acl_path ---
    acl_path = app.config.get("APCORE_ACL_PATH", None)
    if acl_path is not None and not isinstance(acl_path, str):
        actual = type(acl_path).__name__
        raise ValueError(f"APCORE_ACL_PATH must be a string path. Got: {actual}")

    # --- context_factory ---
    context_factory = app.config.get("APCORE_CONTEXT_FACTORY", None)
    if context_factory is not None and not isinstance(context_factory, str):
        actual = type(context_factory).__name__
        raise ValueError(f"APCORE_CONTEXT_FACTORY must be a dotted path string. Got: {actual}")

    # --- server_version ---
    server_version = app.config.get("APCORE_SERVER_VERSION", None)
    if server_version is not None and (not isinstance(server_version, str) or len(server_version) == 0):
        raise ValueError("APCORE_SERVER_VERSION must be a non-empty string if set.")

    # --- executor_config ---
    executor_config = app.config.get("APCORE_EXECUTOR_CONFIG", None)
    if executor_config is not None and not isinstance(executor_config, dict):
        actual = type(executor_config).__name__
        raise ValueError(f"APCORE_EXECUTOR_CONFIG must be a dict. Got: {actual}")

    # === New MCP Serve fields ===

    # --- serve_validate_inputs ---
    serve_validate_inputs = app.config.get("APCORE_SERVE_VALIDATE_INPUTS", DEFAULT_SERVE_VALIDATE_INPUTS)
    if serve_validate_inputs is None:
        serve_validate_inputs = DEFAULT_SERVE_VALIDATE_INPUTS
    if not isinstance(serve_validate_inputs, bool):
        actual = type(serve_validate_inputs).__name__
        raise ValueError(f"APCORE_SERVE_VALIDATE_INPUTS must be a boolean. Got: {actual}")

    # --- serve_log_level ---
    serve_log_level = app.config.get("APCORE_SERVE_LOG_LEVEL", None)
    if serve_log_level is not None:
        if not isinstance(serve_log_level, str):
            actual = type(serve_log_level).__name__
            raise ValueError(f"APCORE_SERVE_LOG_LEVEL must be a string. Got: {actual}")
        if serve_log_level not in VALID_SERVE_LOG_LEVELS:
            choices = ", ".join(VALID_SERVE_LOG_LEVELS)
            raise ValueError(f"APCORE_SERVE_LOG_LEVEL must be one of: {choices}." f" Got: '{serve_log_level}'")

    # === New Observability fields ===

    # --- tracing_enabled ---
    tracing_enabled = app.config.get("APCORE_TRACING_ENABLED", DEFAULT_TRACING_ENABLED)
    if tracing_enabled is None:
        tracing_enabled = DEFAULT_TRACING_ENABLED
    if not isinstance(tracing_enabled, bool):
        actual = type(tracing_enabled).__name__
        raise ValueError(f"APCORE_TRACING_ENABLED must be a boolean. Got: {actual}")

    # --- tracing_exporter ---
    tracing_exporter = app.config.get("APCORE_TRACING_EXPORTER", DEFAULT_TRACING_EXPORTER)
    if tracing_exporter is None:
        tracing_exporter = DEFAULT_TRACING_EXPORTER
    if tracing_exporter not in VALID_TRACING_EXPORTERS:
        choices = ", ".join(VALID_TRACING_EXPORTERS)
        raise ValueError(f"APCORE_TRACING_EXPORTER must be one of: {choices}." f" Got: '{tracing_exporter}'")

    # --- tracing_otlp_endpoint ---
    tracing_otlp_endpoint = app.config.get("APCORE_TRACING_OTLP_ENDPOINT", None)
    if tracing_otlp_endpoint is not None and not isinstance(tracing_otlp_endpoint, str):
        actual = type(tracing_otlp_endpoint).__name__
        raise ValueError(f"APCORE_TRACING_OTLP_ENDPOINT must be a string. Got: {actual}")

    # --- tracing_service_name ---
    tracing_service_name = app.config.get("APCORE_TRACING_SERVICE_NAME", DEFAULT_TRACING_SERVICE_NAME)
    if tracing_service_name is None:
        tracing_service_name = DEFAULT_TRACING_SERVICE_NAME
    if not isinstance(tracing_service_name, str) or len(tracing_service_name) == 0:
        raise ValueError("APCORE_TRACING_SERVICE_NAME must be a non-empty string.")

    # --- metrics_enabled ---
    metrics_enabled = app.config.get("APCORE_METRICS_ENABLED", DEFAULT_METRICS_ENABLED)
    if metrics_enabled is None:
        metrics_enabled = DEFAULT_METRICS_ENABLED
    if not isinstance(metrics_enabled, bool):
        actual = type(metrics_enabled).__name__
        raise ValueError(f"APCORE_METRICS_ENABLED must be a boolean. Got: {actual}")

    # --- metrics_buckets ---
    metrics_buckets = app.config.get("APCORE_METRICS_BUCKETS", None)
    if metrics_buckets is not None:
        if not isinstance(metrics_buckets, list) or not all(
            isinstance(b, (int, float)) and not isinstance(b, bool) for b in metrics_buckets
        ):
            raise ValueError("APCORE_METRICS_BUCKETS must be a list of numeric values.")

    # --- logging_enabled ---
    logging_enabled = app.config.get("APCORE_LOGGING_ENABLED", DEFAULT_LOGGING_ENABLED)
    if logging_enabled is None:
        logging_enabled = DEFAULT_LOGGING_ENABLED
    if not isinstance(logging_enabled, bool):
        actual = type(logging_enabled).__name__
        raise ValueError(f"APCORE_LOGGING_ENABLED must be a boolean. Got: {actual}")

    # --- logging_format ---
    logging_format = app.config.get("APCORE_LOGGING_FORMAT", DEFAULT_LOGGING_FORMAT)
    if logging_format is None:
        logging_format = DEFAULT_LOGGING_FORMAT
    if logging_format not in VALID_LOGGING_FORMATS:
        choices = ", ".join(VALID_LOGGING_FORMATS)
        raise ValueError(f"APCORE_LOGGING_FORMAT must be one of: {choices}." f" Got: '{logging_format}'")

    # --- logging_level ---
    logging_level = app.config.get("APCORE_LOGGING_LEVEL", DEFAULT_LOGGING_LEVEL)
    if logging_level is None:
        logging_level = DEFAULT_LOGGING_LEVEL
    if not isinstance(logging_level, str):
        actual = type(logging_level).__name__
        raise ValueError(f"APCORE_LOGGING_LEVEL must be a string. Got: {actual}")
    if logging_level.lower() not in VALID_LOGGING_LEVELS:
        choices = ", ".join(VALID_LOGGING_LEVELS)
        raise ValueError(f"APCORE_LOGGING_LEVEL must be one of: {choices}." f" Got: '{logging_level}'")

    # === New Extensions ===

    # --- extensions ---
    extensions = app.config.get("APCORE_EXTENSIONS", [])
    if extensions is None:
        extensions = []
    if not isinstance(extensions, list) or not all(isinstance(e, str) for e in extensions):
        raise ValueError("APCORE_EXTENSIONS must be a list of dotted path strings.")

    # === Explorer settings ===

    # --- explorer_enabled ---
    explorer_enabled = app.config.get("APCORE_EXPLORER_ENABLED", DEFAULT_EXPLORER_ENABLED)
    if explorer_enabled is None:
        explorer_enabled = DEFAULT_EXPLORER_ENABLED
    if not isinstance(explorer_enabled, bool):
        actual = type(explorer_enabled).__name__
        raise ValueError(f"APCORE_EXPLORER_ENABLED must be a boolean. Got: {actual}")

    # --- explorer_url_prefix ---
    explorer_url_prefix = app.config.get("APCORE_EXPLORER_URL_PREFIX", DEFAULT_EXPLORER_URL_PREFIX)
    if explorer_url_prefix is None:
        explorer_url_prefix = DEFAULT_EXPLORER_URL_PREFIX
    if not isinstance(explorer_url_prefix, str) or len(explorer_url_prefix) == 0:
        raise ValueError("APCORE_EXPLORER_URL_PREFIX must be a non-empty string.")

    # --- explorer_allow_execute ---
    explorer_allow_execute = app.config.get(
        "APCORE_EXPLORER_ALLOW_EXECUTE", DEFAULT_EXPLORER_ALLOW_EXECUTE
    )
    if explorer_allow_execute is None:
        explorer_allow_execute = DEFAULT_EXPLORER_ALLOW_EXECUTE
    if not isinstance(explorer_allow_execute, bool):
        actual = type(explorer_allow_execute).__name__
        raise ValueError(
            f"APCORE_EXPLORER_ALLOW_EXECUTE must be a boolean. Got: {actual}"
        )

    return ApcoreSettings(
        module_dir=module_dir,
        auto_discover=auto_discover,
        serve_transport=serve_transport,
        serve_host=serve_host,
        serve_port=serve_port,
        server_name=server_name,
        binding_pattern=binding_pattern,
        scanner_source=scanner_source,
        module_packages=module_packages,
        middlewares=middlewares,
        acl_path=acl_path,
        context_factory=context_factory,
        server_version=server_version,
        executor_config=executor_config,
        serve_validate_inputs=serve_validate_inputs,
        serve_log_level=serve_log_level,
        tracing_enabled=tracing_enabled,
        tracing_exporter=tracing_exporter,
        tracing_otlp_endpoint=tracing_otlp_endpoint,
        tracing_service_name=tracing_service_name,
        metrics_enabled=metrics_enabled,
        metrics_buckets=metrics_buckets,
        logging_enabled=logging_enabled,
        logging_format=logging_format,
        logging_level=logging_level,
        extensions=extensions,
        explorer_enabled=explorer_enabled,
        explorer_url_prefix=explorer_url_prefix,
        explorer_allow_execute=explorer_allow_execute,
    )
