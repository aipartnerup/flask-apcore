"""Tests for public API (__init__.py) exports."""

from __future__ import annotations

import pytest

import flask_apcore


# ---------------------------------------------------------------------------
# All exports exist
# ---------------------------------------------------------------------------


class TestExportsExist:
    """All declared exports exist in flask_apcore."""

    EXPECTED_EXPORTS = [
        "Apcore",
        "__version__",
        "module",
        "ACL",
        "Config",
        "Context",
        "Executor",
        "Identity",
        "Middleware",
        "ModuleAnnotations",
        "ModuleDescriptor",
        "Registry",
    ]

    @pytest.mark.parametrize("name", EXPECTED_EXPORTS)
    def test_export_exists(self, name):
        assert hasattr(flask_apcore, name), f"Missing export: {name}"

    def test_all_list_complete(self):
        for name in self.EXPECTED_EXPORTS:
            assert name in flask_apcore.__all__, f"{name} not in __all__"

    def test_no_extra_public_exports(self):
        """__all__ should only contain the expected exports."""
        for name in flask_apcore.__all__:
            assert name in self.EXPECTED_EXPORTS, f"Unexpected export: {name}"


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


class TestVersion:
    """__version__ matches expected value."""

    def test_version_is_0_1_1(self):
        assert flask_apcore.__version__ == "0.1.1"

    def test_version_is_string(self):
        assert isinstance(flask_apcore.__version__, str)


# ---------------------------------------------------------------------------
# Re-exported types are the actual apcore classes
# ---------------------------------------------------------------------------


class TestReExportedTypes:
    """Re-exported types are identical to apcore originals."""

    def test_apcore_class(self):
        from flask_apcore.extension import Apcore as ExtApcore

        assert flask_apcore.Apcore is ExtApcore

    def test_module_decorator(self):
        import apcore

        assert flask_apcore.module is apcore.module

    def test_registry(self):
        import apcore

        assert flask_apcore.Registry is apcore.Registry

    def test_executor(self):
        import apcore

        assert flask_apcore.Executor is apcore.Executor

    def test_context(self):
        import apcore

        assert flask_apcore.Context is apcore.Context

    def test_identity(self):
        import apcore

        assert flask_apcore.Identity is apcore.Identity

    def test_acl(self):
        import apcore

        assert flask_apcore.ACL is apcore.ACL

    def test_config(self):
        import apcore

        assert flask_apcore.Config is apcore.Config

    def test_middleware(self):
        import apcore

        assert flask_apcore.Middleware is apcore.Middleware

    def test_module_annotations(self):
        import apcore

        assert flask_apcore.ModuleAnnotations is apcore.ModuleAnnotations

    def test_module_descriptor(self):
        import apcore

        assert flask_apcore.ModuleDescriptor is apcore.ModuleDescriptor
