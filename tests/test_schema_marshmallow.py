"""Tests for schemas/marshmallow_backend.py — MarshmallowBackend.

marshmallow is an optional dependency; tests are skipped if not installed.
"""

from __future__ import annotations

import pytest

try:
    import marshmallow  # noqa: F401
    from marshmallow import Schema, fields, validate

    HAS_MARSHMALLOW = True
except ImportError:
    HAS_MARSHMALLOW = False

pytestmark = pytest.mark.skipif(not HAS_MARSHMALLOW, reason="marshmallow not installed")


# ---------------------------------------------------------------------------
# Test schemas (only defined if marshmallow is available)
# ---------------------------------------------------------------------------

if HAS_MARSHMALLOW:
    import enum

    class Color(enum.Enum):
        RED = "red"
        GREEN = "green"
        BLUE = "blue"

    class UserSchema(Schema):
        name = fields.String(required=True)
        age = fields.Integer(required=True)
        email = fields.Email()

    class AddressSchema(Schema):
        street = fields.String(required=True)
        city = fields.String(required=True)
        zip_code = fields.String()

    class UserWithAddressSchema(Schema):
        name = fields.String(required=True)
        address = fields.Nested(AddressSchema, required=True)

    class ItemListSchema(Schema):
        items = fields.List(fields.String(), required=True)

    class DateTimeSchema(Schema):
        created_at = fields.DateTime(required=True)
        updated_at = fields.Date()
        uuid = fields.UUID()

    class ValidatedSchema(Schema):
        name = fields.String(
            required=True,
            validate=validate.Length(min=1, max=100),
        )
        score = fields.Integer(
            validate=validate.Range(min=0, max=100),
        )

    class BooleanSchema(Schema):
        active = fields.Boolean(required=True)

    class FloatSchema(Schema):
        price = fields.Float(required=True)

    class EnumSchema(Schema):
        color = fields.Enum(Color, required=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dummy_func():
    pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCanHandleInput:
    def setup_method(self):
        from flask_apcore.schemas.marshmallow_backend import MarshmallowBackend

        self.backend = MarshmallowBackend()

    def test_with_marshmallow_context(self):
        ctx = {"marshmallow_input": UserSchema()}
        assert self.backend.can_handle_input(_dummy_func, context=ctx) is True

    def test_without_context(self):
        assert self.backend.can_handle_input(_dummy_func) is False

    def test_with_empty_context(self):
        assert self.backend.can_handle_input(_dummy_func, context={}) is False


class TestCanHandleOutput:
    def setup_method(self):
        from flask_apcore.schemas.marshmallow_backend import MarshmallowBackend

        self.backend = MarshmallowBackend()

    def test_with_marshmallow_context(self):
        ctx = {"marshmallow_output": UserSchema()}
        assert self.backend.can_handle_output(_dummy_func, context=ctx) is True

    def test_without_context(self):
        assert self.backend.can_handle_output(_dummy_func) is False


class TestInferInput:
    def setup_method(self):
        from flask_apcore.schemas.marshmallow_backend import MarshmallowBackend

        self.backend = MarshmallowBackend()

    def test_basic_schema(self):
        ctx = {"marshmallow_input": UserSchema()}
        schema = self.backend.infer_input(_dummy_func, context=ctx)
        props = schema["properties"]
        assert props["name"]["type"] == "string"
        assert props["age"]["type"] == "integer"
        assert props["email"]["type"] == "string"
        assert props["email"]["format"] == "email"
        assert "name" in schema["required"]
        assert "age" in schema["required"]
        assert "email" not in schema["required"]

    def test_url_params_merged(self):
        ctx = {"marshmallow_input": UserSchema()}
        schema = self.backend.infer_input(_dummy_func, url_params={"user_id": "int"}, context=ctx)
        assert "user_id" in schema["properties"]
        assert schema["properties"]["user_id"]["type"] == "integer"
        assert "user_id" in schema["required"]

    def test_schema_class_auto_instantiated(self):
        """Passing a Schema class (not instance) should work."""
        ctx = {"marshmallow_input": UserSchema}
        schema = self.backend.infer_input(_dummy_func, context=ctx)
        assert "name" in schema["properties"]


class TestInferOutput:
    def setup_method(self):
        from flask_apcore.schemas.marshmallow_backend import MarshmallowBackend

        self.backend = MarshmallowBackend()

    def test_basic_output(self):
        ctx = {"marshmallow_output": UserSchema()}
        schema = self.backend.infer_output(_dummy_func, context=ctx)
        assert "name" in schema["properties"]


class TestFieldTypes:
    """Test field type mapping for all supported marshmallow field types."""

    def setup_method(self):
        from flask_apcore.schemas.marshmallow_backend import MarshmallowBackend

        self.backend = MarshmallowBackend()

    def test_string(self):
        ctx = {"marshmallow_input": UserSchema()}
        schema = self.backend.infer_input(_dummy_func, context=ctx)
        assert schema["properties"]["name"]["type"] == "string"

    def test_integer(self):
        ctx = {"marshmallow_input": UserSchema()}
        schema = self.backend.infer_input(_dummy_func, context=ctx)
        assert schema["properties"]["age"]["type"] == "integer"

    def test_float(self):
        ctx = {"marshmallow_input": FloatSchema()}
        schema = self.backend.infer_input(_dummy_func, context=ctx)
        assert schema["properties"]["price"]["type"] == "number"

    def test_boolean(self):
        ctx = {"marshmallow_input": BooleanSchema()}
        schema = self.backend.infer_input(_dummy_func, context=ctx)
        assert schema["properties"]["active"]["type"] == "boolean"

    def test_email(self):
        ctx = {"marshmallow_input": UserSchema()}
        schema = self.backend.infer_input(_dummy_func, context=ctx)
        assert schema["properties"]["email"]["format"] == "email"

    def test_datetime(self):
        ctx = {"marshmallow_input": DateTimeSchema()}
        schema = self.backend.infer_input(_dummy_func, context=ctx)
        assert schema["properties"]["created_at"]["format"] == "date-time"

    def test_date(self):
        ctx = {"marshmallow_input": DateTimeSchema()}
        schema = self.backend.infer_input(_dummy_func, context=ctx)
        assert schema["properties"]["updated_at"]["format"] == "date"

    def test_uuid(self):
        ctx = {"marshmallow_input": DateTimeSchema()}
        schema = self.backend.infer_input(_dummy_func, context=ctx)
        assert schema["properties"]["uuid"]["format"] == "uuid"

    def test_list(self):
        ctx = {"marshmallow_input": ItemListSchema()}
        schema = self.backend.infer_input(_dummy_func, context=ctx)
        items_prop = schema["properties"]["items"]
        assert items_prop["type"] == "array"
        assert items_prop["items"]["type"] == "string"

    def test_nested(self):
        ctx = {"marshmallow_input": UserWithAddressSchema()}
        schema = self.backend.infer_input(_dummy_func, context=ctx)
        addr_prop = schema["properties"]["address"]
        assert addr_prop["type"] == "object"
        assert "street" in addr_prop["properties"]

    def test_validators_length(self):
        ctx = {"marshmallow_input": ValidatedSchema()}
        schema = self.backend.infer_input(_dummy_func, context=ctx)
        assert schema["properties"]["name"]["minLength"] == 1
        assert schema["properties"]["name"]["maxLength"] == 100

    def test_validators_range(self):
        ctx = {"marshmallow_input": ValidatedSchema()}
        schema = self.backend.infer_input(_dummy_func, context=ctx)
        assert schema["properties"]["score"]["minimum"] == 0
        assert schema["properties"]["score"]["maximum"] == 100

    def test_enum(self):
        ctx = {"marshmallow_input": EnumSchema()}
        schema = self.backend.infer_input(_dummy_func, context=ctx)
        color_prop = schema["properties"]["color"]
        assert color_prop["type"] == "string"
        assert set(color_prop["enum"]) == {"red", "green", "blue"}
