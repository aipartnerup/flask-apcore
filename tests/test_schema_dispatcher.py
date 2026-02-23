"""Tests for schemas/__init__.py — SchemaDispatcher."""

from __future__ import annotations


from pydantic import BaseModel

from flask_apcore.schemas import SchemaBackend, SchemaDispatcher


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _plain_func(x: int, y: str) -> dict:
    """A plain function with type hints."""
    return {}


class _UserModel(BaseModel):
    name: str
    age: int


def _pydantic_func(body: _UserModel) -> _UserModel:
    """A function with Pydantic model params."""
    return body


def _no_hints_func():
    """No type hints at all."""
    pass


# ---------------------------------------------------------------------------
# SchemaDispatcher
# ---------------------------------------------------------------------------


class TestSchemaDispatcher:
    """Test SchemaDispatcher with priority chain."""

    def setup_method(self):
        self.dispatcher = SchemaDispatcher()

    def test_backends_registered(self):
        """At least Pydantic and TypeHints backends are registered."""
        assert len(self.dispatcher._backends) >= 2

    def test_pydantic_is_first_priority(self):
        """Pydantic backend should be first."""
        from flask_apcore.schemas.pydantic_backend import PydanticBackend

        assert isinstance(self.dispatcher._backends[0], PydanticBackend)

    def test_typehints_is_last(self):
        """TypeHints backend should be last."""
        from flask_apcore.schemas.typehints_backend import TypeHintsBackend

        assert isinstance(self.dispatcher._backends[-1], TypeHintsBackend)

    def test_infer_input_pydantic_selected(self):
        """Pydantic backend selected for Pydantic-typed params."""
        schema = self.dispatcher.infer_input_schema(_pydantic_func)
        assert "name" in schema.get("properties", {})
        assert "age" in schema.get("properties", {})

    def test_infer_input_typehints_fallback(self):
        """TypeHints backend selected for plain typed params."""
        schema = self.dispatcher.infer_input_schema(_plain_func)
        assert "x" in schema.get("properties", {})
        assert "y" in schema.get("properties", {})

    def test_infer_input_fallback_empty(self):
        """Empty schema for function with no type hints."""
        schema = self.dispatcher.infer_input_schema(_no_hints_func)
        assert schema == {"type": "object", "properties": {}}

    def test_infer_output_pydantic(self):
        """Pydantic output schema for Pydantic return type."""
        schema = self.dispatcher.infer_output_schema(_pydantic_func)
        assert "name" in schema.get("properties", {})

    def test_infer_output_typehints(self):
        """TypeHints output for plain return type."""
        schema = self.dispatcher.infer_output_schema(_plain_func)
        assert schema.get("type") == "object"

    def test_infer_output_fallback_empty(self):
        """Empty schema for function with no return type."""
        schema = self.dispatcher.infer_output_schema(_no_hints_func)
        assert schema == {"type": "object", "properties": {}}

    def test_url_params_passed_to_backend(self):
        """URL params are forwarded to the selected backend."""
        schema = self.dispatcher.infer_input_schema(_plain_func, url_params={"item_id": "int"})
        assert "item_id" in schema.get("properties", {})
        assert schema["properties"]["item_id"]["type"] == "integer"


class TestSchemaBackendProtocol:
    """Test SchemaBackend as a runtime checkable Protocol."""

    def test_protocol_check(self):
        """A class with the right methods satisfies the Protocol."""

        class _MockBackend:
            def can_handle_input(self, func, context=None):
                return True

            def infer_input(self, func, url_params=None, context=None):
                return {}

            def can_handle_output(self, func, context=None):
                return True

            def infer_output(self, func, context=None):
                return {}

        assert isinstance(_MockBackend(), SchemaBackend)
