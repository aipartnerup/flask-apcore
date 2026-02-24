# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-02-24

### Added
- Web Explorer Blueprint with JSON API and built-in HTML UI for browsing registered modules.
- Explorer config settings: `APCORE_EXPLORER_ENABLED`, `APCORE_EXPLORER_URL_PREFIX`.
- `APCORE_EXPLORER_ALLOW_EXECUTE` config setting for controlling module execution.
- `POST /modules/<id>/call` execute endpoint for calling registered modules via Explorer.
- Try-it UI integrated into the Explorer HTML page for interactive module testing.
- Shared serializers module for ScannedModule data transformation.
- End-to-end integration test covering scan → register → explore via HTTP.
- Explorer and Try-it documentation in README.

### Fixed
- Preserve `http_method` and `url_rule` in RegistryWriter metadata.
- Change call endpoint to `POST /call/<id>` to avoid path converter routing conflict.
- Serialize Pydantic models correctly in call endpoint output.

### Changed
- Remove JSON / OpenAPI output writers and endpoint (superseded by Explorer Blueprint).

### Security
- Add security warnings for Explorer config and `.env.example`.

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
