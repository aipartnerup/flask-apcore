# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-02-25

### Added
- MCP Serve Explorer passthrough: `--explorer`, `--explorer-prefix`, `--allow-execute` CLI flags and corresponding `APCORE_SERVE_EXPLORER`, `APCORE_SERVE_EXPLORER_PREFIX`, `APCORE_SERVE_ALLOW_EXECUTE` config settings, forwarded to `apcore_mcp.serve()`.

### Fixed
- Preserve `http_method` and `url_rule` in RegistryWriter metadata.
- Serialize Pydantic models correctly in call endpoint output.

### Changed
- Remove Flask Blueprint Explorer (`/apcore/` routes, `flask_apcore.web` module, `APCORE_EXPLORER_*` config settings) in favour of the apcore-mcp Tool Explorer available via `flask apcore serve --explorer`.
- Remove JSON / OpenAPI output writers (superseded by apcore-mcp explorer).
- Bump `apcore-mcp` optional dependency from `>=0.4.0` to `>=0.5.1`.

## [0.1.0] - 2026-02-23

### Added
- Initial release of `flask-apcore`.
- Flask extension for apcore AI-Perceivable Core integration.
- App-scoped Registry, Executor, and ContextFactory wrappers following Flask multi-app best practices.
- Direct registration of scanned modules into the apcore Registry via `RegistryWriter`.
- Support for user and observability middlewares, ACL, and executor config.
- Schema backends for Marshmallow, Pydantic, and type hints.
- Comprehensive test suite including async test support.
- Developer tooling: pytest, pytest-flask, pytest-asyncio, ruff, mypy, pre-commit, coverage.
