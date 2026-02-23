"""Tests for schemas/pydantic_backend.py — PydanticBackend."""

from __future__ import annotations


from pydantic import BaseModel

from flask_apcore.schemas.pydantic_backend import PydanticBackend


# ---------------------------------------------------------------------------
# Test models
# ---------------------------------------------------------------------------


class UserModel(BaseModel):
    name: str
    age: int
    email: str | None = None


class ItemModel(BaseModel):
    title: str
    price: float


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------


def pydantic_input(body: UserModel) -> dict:
    return {}


def pydantic_optional_input(body: UserModel | None = None) -> dict:
    return {}


def pydantic_list_input(items: list[ItemModel]) -> dict:
    return {}


def pydantic_multi_input(user: UserModel, item: ItemModel) -> dict:
    return {}


def pydantic_return() -> UserModel:
    return UserModel(name="test", age=1)


def pydantic_optional_return() -> UserModel | None:
    return None


def pydantic_list_return() -> list[UserModel]:
    return []


def plain_func(x: int, y: str) -> dict:
    return {}


def no_return_hint(x: int):
    pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCanHandleInput:
    def setup_method(self):
        self.backend = PydanticBackend()

    def test_pydantic_param_detected(self):
        assert self.backend.can_handle_input(pydantic_input) is True

    def test_optional_pydantic_param_detected(self):
        assert self.backend.can_handle_input(pydantic_optional_input) is True

    def test_list_pydantic_param_detected(self):
        assert self.backend.can_handle_input(pydantic_list_input) is True

    def test_plain_types_not_detected(self):
        assert self.backend.can_handle_input(plain_func) is False


class TestInferInput:
    def setup_method(self):
        self.backend = PydanticBackend()

    def test_single_model_schema(self):
        schema = self.backend.infer_input(pydantic_input)
        props = schema["properties"]
        assert "name" in props
        assert "age" in props
        assert "email" in props

    def test_multi_model_merged(self):
        schema = self.backend.infer_input(pydantic_multi_input)
        props = schema["properties"]
        assert "name" in props
        assert "title" in props
        assert "price" in props

    def test_url_params_merged(self):
        schema = self.backend.infer_input(pydantic_input, url_params={"user_id": "int"})
        props = schema["properties"]
        assert "user_id" in props
        assert props["user_id"]["type"] == "integer"
        assert "user_id" in schema["required"]

    def test_url_params_not_duplicated_in_required(self):
        schema = self.backend.infer_input(pydantic_input, url_params={"name": "string"})
        assert schema["required"].count("name") == 1


class TestCanHandleOutput:
    def setup_method(self):
        self.backend = PydanticBackend()

    def test_pydantic_return_detected(self):
        assert self.backend.can_handle_output(pydantic_return) is True

    def test_optional_pydantic_return_detected(self):
        assert self.backend.can_handle_output(pydantic_optional_return) is True

    def test_list_pydantic_return_detected(self):
        assert self.backend.can_handle_output(pydantic_list_return) is True

    def test_dict_return_not_detected(self):
        assert self.backend.can_handle_output(plain_func) is False

    def test_no_return_hint_not_detected(self):
        assert self.backend.can_handle_output(no_return_hint) is False


class TestInferOutput:
    def setup_method(self):
        self.backend = PydanticBackend()

    def test_direct_model(self):
        schema = self.backend.infer_output(pydantic_return)
        assert "name" in schema.get("properties", {})
        assert "age" in schema.get("properties", {})

    def test_optional_model(self):
        schema = self.backend.infer_output(pydantic_optional_return)
        assert "name" in schema.get("properties", {})

    def test_list_model(self):
        schema = self.backend.infer_output(pydantic_list_return)
        assert schema["type"] == "array"
        assert "name" in schema["items"].get("properties", {})
