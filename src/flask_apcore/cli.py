"""Click CLI commands for flask-apcore.

Provides the 'flask apcore' command group with 'scan' and 'serve' subcommands.
Adapted from django-apcore's management/commands/apcore_scan.py and apcore_serve.py.

Features:
- scan: --output is optional; omit for direct registry registration
- serve: supports --validate-inputs, --log-level, metrics_collector passthrough
"""

from __future__ import annotations

import re
from typing import Any

import click
from flask import current_app
from flask.cli import AppGroup, with_appcontext

from flask_apcore.registry import get_executor

apcore_cli = AppGroup("apcore", help="apcore AI-Perceivable Core commands.")


@apcore_cli.command("scan")
@click.option(
    "--source",
    "-s",
    type=click.Choice(["auto", "native", "smorest", "restx"]),
    default="auto",
    help="Scanner source. 'auto' detects the best scanner.",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["yaml"]),
    default=None,
    help="Output format. Omit to register directly.",
)
@click.option(
    "--dir",
    "-d",
    "output_dir",
    type=click.Path(),
    default=None,
    help="Output directory. Defaults to APCORE_MODULE_DIR config.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview output without writing files or registering modules.",
)
@click.option(
    "--include",
    type=str,
    default=None,
    help="Regex pattern: only include matching module IDs.",
)
@click.option(
    "--exclude",
    type=str,
    default=None,
    help="Regex pattern: exclude matching module IDs.",
)
@with_appcontext
def scan_command(source, output, output_dir, dry_run, include, exclude):
    """Scan Flask routes and generate apcore module definitions."""
    app = current_app._get_current_object()
    settings = app.extensions["apcore"]["settings"]
    registry = app.extensions["apcore"]["registry"]

    # Resolve output directory
    if output_dir is None:
        output_dir = settings.module_dir

    # Validate regex patterns
    if include:
        try:
            re.compile(include)
        except re.error as e:
            raise click.ClickException(f"Invalid --include pattern: '{include}'. " f"Must be valid regex. Error: {e}")

    if exclude:
        try:
            re.compile(exclude)
        except re.error as e:
            raise click.ClickException(f"Invalid --exclude pattern: '{exclude}'. " f"Must be valid regex. Error: {e}")

    # Get scanner
    from flask_apcore.scanners import get_scanner, auto_detect_scanner

    try:
        if source == "auto":
            scanner = auto_detect_scanner(app)
        else:
            scanner = get_scanner(source)
    except (ImportError, ValueError) as e:
        raise click.ClickException(str(e))

    source_name = scanner.get_source_name()
    click.echo(f"[flask-apcore] Scanning {source_name} routes...")

    # Run scan
    try:
        modules = scanner.scan(app, include=include, exclude=exclude)
    except re.error as e:
        raise click.ClickException(f"Invalid regex pattern. Error: {e}")

    click.echo(f"[flask-apcore] Found {len(modules)} API routes.")

    if not modules:
        click.echo(f"[flask-apcore] No routes found for source '{source_name}'. " f"Ensure your API is configured.")
        raise SystemExit(1)

    # Report warnings
    all_warnings = []
    for module in modules:
        all_warnings.extend(module.warnings)
    if all_warnings:
        click.echo(f"[flask-apcore] Warnings: {len(all_warnings)}")
        for warning in all_warnings:
            click.echo(f"[flask-apcore]   - {warning}")

    # Get writer and write output
    from flask_apcore.output import get_writer

    writer = get_writer(output)

    if output is None:
        # Direct registration mode
        if dry_run:
            click.echo("[flask-apcore] Dry run -- no modules registered.")
            writer.write(modules, registry, dry_run=True)
        else:
            result = writer.write(modules, registry)
            click.echo(f"[flask-apcore] Registered {len(result)} modules.")
    else:
        # File output mode (YAML / JSON)
        if dry_run:
            click.echo("[flask-apcore] Dry run -- no files written.")
            writer.write(modules, output_dir, dry_run=True)
        else:
            writer.write(modules, output_dir)
            click.echo(f"[flask-apcore] Generated {len(modules)} module definitions.")
            click.echo(f"[flask-apcore] Written to {output_dir}/")


@apcore_cli.command("serve")
@click.option(
    "--stdio",
    "transport",
    flag_value="stdio",
    default=True,
    help="Use stdio transport (default).",
)
@click.option(
    "--http",
    "transport",
    flag_value="streamable-http",
    help="Use HTTP Streamable transport.",
)
@click.option(
    "--host",
    type=str,
    default=None,
    help="Host for HTTP transport. Default: APCORE_SERVE_HOST config.",
)
@click.option(
    "--port",
    "-p",
    type=int,
    default=None,
    help="Port for HTTP transport. Default: APCORE_SERVE_PORT config.",
)
@click.option(
    "--name",
    type=str,
    default=None,
    help="MCP server name. Default: APCORE_SERVER_NAME config.",
)
@click.option(
    "--validate-inputs",
    is_flag=True,
    default=False,
    help="Validate tool inputs against schemas before execution.",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default=None,
    help="Set the log level for the apcore-mcp logger.",
)
@click.option(
    "--explorer",
    is_flag=True,
    default=False,
    help="Enable the MCP Tool Explorer UI (HTTP transports only).",
)
@click.option(
    "--explorer-prefix",
    type=str,
    default=None,
    help="URL prefix for the MCP Tool Explorer. Default: /explorer.",
)
@click.option(
    "--allow-execute",
    is_flag=True,
    default=False,
    help="Allow tool execution from the MCP Tool Explorer UI.",
)
@click.option(
    "--jwt-secret",
    type=str,
    default=None,
    help="JWT secret key for authenticating MCP requests (HTTP transports only).",
)
@click.option(
    "--jwt-algorithm",
    type=click.Choice(["HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]),
    default=None,
    help="JWT signing algorithm. Default: APCORE_SERVE_JWT_ALGORITHM config.",
)
@click.option(
    "--jwt-audience",
    type=str,
    default=None,
    help="Expected JWT audience claim.",
)
@click.option(
    "--jwt-issuer",
    type=str,
    default=None,
    help="Expected JWT issuer claim.",
)
@with_appcontext
def serve_command(
    transport: str,
    host: str | None,
    port: int | None,
    name: str | None,
    validate_inputs: bool,
    log_level: str | None,
    explorer: bool,
    explorer_prefix: str | None,
    allow_execute: bool,
    jwt_secret: str | None,
    jwt_algorithm: str | None,
    jwt_audience: str | None,
    jwt_issuer: str | None,
) -> None:
    """Start an MCP server exposing registered apcore modules as tools."""
    app = current_app._get_current_object()
    settings = app.extensions["apcore"]["settings"]
    registry = app.extensions["apcore"]["registry"]
    metrics_collector = app.extensions["apcore"].get("metrics_collector")

    # Resolve with config fallbacks
    transport = transport or settings.serve_transport
    host = host or settings.serve_host
    port = port if port is not None else settings.serve_port
    name = name or settings.server_name

    # Use config fallbacks for validate_inputs, log_level, and explorer
    if not validate_inputs:
        validate_inputs = settings.serve_validate_inputs
    if log_level is None:
        log_level = settings.serve_log_level
    if not explorer:
        explorer = settings.serve_explorer
    if explorer_prefix is None:
        explorer_prefix = settings.serve_explorer_prefix
    if not allow_execute:
        allow_execute = settings.serve_allow_execute

    # JWT authentication config fallbacks
    if jwt_secret is None:
        jwt_secret = settings.serve_jwt_secret
    if jwt_algorithm is None:
        jwt_algorithm = settings.serve_jwt_algorithm
    if jwt_audience is None:
        jwt_audience = settings.serve_jwt_audience
    if jwt_issuer is None:
        jwt_issuer = settings.serve_jwt_issuer

    # Build authenticator if JWT secret is provided
    authenticator = None
    if jwt_secret is not None:
        try:
            from apcore_mcp import JWTAuthenticator
        except ImportError:
            raise click.ClickException(
                "apcore-mcp>=0.7.0 is required for JWT authentication. " "Install with: pip install flask-apcore[mcp]"
            )
        authenticator = JWTAuthenticator(
            jwt_secret,
            algorithms=[jwt_algorithm],
            audience=jwt_audience,
            issuer=jwt_issuer,
        )

    # Check module count
    if registry.count == 0:
        raise click.ClickException(
            "No apcore modules registered. "
            "Run 'flask apcore scan' first or define modules "
            "with @module decorator."
        )

    # Validate port
    if not (1 <= port <= 65535):
        raise click.ClickException(f"--port must be between 1 and 65535. Got: {port}.")

    # Security warning for 0.0.0.0
    if transport in ("streamable-http", "sse") and host == "0.0.0.0":
        click.echo(
            "[flask-apcore] WARNING: Binding to 0.0.0.0 exposes the MCP "
            "server to all network interfaces. Ensure the server is "
            "behind a firewall.",
            err=True,
        )

    # Detect if executor is needed
    use_executor = bool(settings.middlewares or settings.acl_path or settings.executor_config)

    if use_executor:
        registry_or_executor = get_executor(app)
    else:
        registry_or_executor = registry

    click.echo(f"[flask-apcore] Starting MCP server '{name}' via {transport}...")
    click.echo(f"[flask-apcore] {registry.count} modules registered.")

    _do_serve(
        registry_or_executor,
        transport=transport,
        host=host,
        port=port,
        name=name,
        validate_inputs=validate_inputs,
        log_level=log_level,
        metrics_collector=metrics_collector,
        explorer=explorer,
        explorer_prefix=explorer_prefix,
        allow_execute=allow_execute,
        authenticator=authenticator,
    )


def _do_serve(
    registry_or_executor: Any,
    *,
    transport: str,
    host: str,
    port: int,
    name: str,
    validate_inputs: bool = False,
    log_level: str | None = None,
    metrics_collector: Any | None = None,
    explorer: bool = False,
    explorer_prefix: str = "/explorer",
    allow_execute: bool = False,
    authenticator: Any | None = None,
) -> None:
    """Delegate to apcore_mcp.serve().

    Separated for testability (can be mocked in tests).

    Adapted from django-apcore's management/commands/apcore_serve.py serve()
    function.
    """
    try:
        from apcore_mcp import serve
    except ImportError:
        raise click.ClickException(
            "apcore-mcp is required for 'flask apcore serve'. " "Install with: pip install flask-apcore[mcp]"
        )

    kwargs: dict[str, Any] = dict(
        transport=transport,
        host=host,
        port=port,
        name=name,
        validate_inputs=validate_inputs,
        log_level=log_level,
        metrics_collector=metrics_collector,
    )
    if explorer:
        kwargs["explorer"] = explorer
        kwargs["explorer_prefix"] = explorer_prefix
        kwargs["allow_execute"] = allow_execute
    if authenticator is not None:
        kwargs["authenticator"] = authenticator

    serve(registry_or_executor, **kwargs)
