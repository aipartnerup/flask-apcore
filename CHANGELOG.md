# Changelog

All notable changes to this project will be documented in this file.

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
