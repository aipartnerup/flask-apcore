"""Tests for schemas/typehints_backend.py — TypeHintsBackend."""

from __future__ import annotations

import datetime
import uuid


from flask_apcore.schemas.typehints_backend import TypeHintsBackend


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------


def basic_func(name: str, count: int, active: bool) -> str:
    return ""


def float_func(price: float) -> float:
    return 0.0


def dict_func(data: dict) -> dict:
    return {}


def list_func(items: list) -> list:
    return []


def typed_list_func(items: list[str]) -> list[int]:
    return []


def optional_func(name: str, nickname: str | None = None) -> str:
    return ""


def datetime_func(ts: datetime.datetime) -> datetime.datetime:
    return datetime.datetime.now()


def date_func(d: datetime.date) -> datetime.date:
    return datetime.date.today()


def uuid_func(uid: uuid.UUID) -> uuid.UUID:
    return uuid.uuid4()


def no_hints_func():
    pass


def return_only() -> str:
    return ""


def default_param(x: int = 42) -> int:
    return x


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCanHandleInput:
    def setup_method(self):
        self.backend = TypeHintsBackend()

    def test_with_typed_params(self):
        assert self.backend.can_handle_input(basic_func) is True

    def test_no_hints(self):
        assert self.backend.can_handle_input(no_hints_func) is False


class TestInferInput:
    def setup_method(self):
        self.backend = TypeHintsBackend()

    def test_basic_types(self):
        schema = self.backend.infer_input(basic_func)
        props = schema["properties"]
        assert props["name"]["type"] == "string"
        assert props["count"]["type"] == "integer"
        assert props["active"]["type"] == "boolean"
        assert "name" in schema["required"]

    def test_float(self):
        schema = self.backend.infer_input(float_func)
        assert schema["properties"]["price"]["type"] == "number"

    def test_dict(self):
        schema = self.backend.infer_input(dict_func)
        assert schema["properties"]["data"]["type"] == "object"

    def test_list_bare(self):
        schema = self.backend.infer_input(list_func)
        assert schema["properties"]["items"]["type"] == "array"

    def test_list_typed(self):
        schema = self.backend.infer_input(typed_list_func)
        items_prop = schema["properties"]["items"]
        assert items_prop["type"] == "array"
        assert items_prop["items"]["type"] == "string"

    def test_optional_not_required(self):
        schema = self.backend.infer_input(optional_func)
        assert "name" in schema["required"]
        assert "nickname" not in schema["required"]

    def test_datetime(self):
        schema = self.backend.infer_input(datetime_func)
        assert schema["properties"]["ts"]["type"] == "string"
        assert schema["properties"]["ts"]["format"] == "date-time"

    def test_date(self):
        schema = self.backend.infer_input(date_func)
        assert schema["properties"]["d"]["type"] == "string"
        assert schema["properties"]["d"]["format"] == "date"

    def test_uuid(self):
        schema = self.backend.infer_input(uuid_func)
        assert schema["properties"]["uid"]["type"] == "string"
        assert schema["properties"]["uid"]["format"] == "uuid"

    def test_default_param_not_required(self):
        schema = self.backend.infer_input(default_param)
        assert "x" not in schema["required"]

    def test_url_params_merged(self):
        schema = self.backend.infer_input(basic_func, url_params={"item_id": "int"})
        assert "item_id" in schema["properties"]
        assert schema["properties"]["item_id"]["type"] == "integer"
        assert "item_id" in schema["required"]


class TestCanHandleOutput:
    def setup_method(self):
        self.backend = TypeHintsBackend()

    def test_with_return_hint(self):
        assert self.backend.can_handle_output(basic_func) is True

    def test_no_return_hint(self):
        assert self.backend.can_handle_output(no_hints_func) is False


class TestInferOutput:
    def setup_method(self):
        self.backend = TypeHintsBackend()

    def test_string_return(self):
        schema = self.backend.infer_output(basic_func)
        assert schema["type"] == "string"

    def test_dict_return(self):
        schema = self.backend.infer_output(dict_func)
        assert schema["type"] == "object"

    def test_list_return(self):
        schema = self.backend.infer_output(list_func)
        assert schema["type"] == "array"

    def test_typed_list_return(self):
        schema = self.backend.infer_output(typed_list_func)
        assert schema["type"] == "array"
        assert schema["items"]["type"] == "integer"

    def test_datetime_return(self):
        schema = self.backend.infer_output(datetime_func)
        assert schema["format"] == "date-time"

    def test_no_return_type(self):
        schema = self.backend.infer_output(no_hints_func)
        assert schema == {"type": "object", "properties": {}}
