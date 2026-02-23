"""Tests for flask_apcore.web -- Explorer Blueprint (API + HTML)."""

from __future__ import annotations

import json

import pytest
from flask import Flask

from flask_apcore import Apcore


def list_items() -> dict:
    """List all items."""
    return {"items": []}


def create_item(title: str) -> dict:
    """Create a new item."""
    return {"title": title}


@pytest.fixture()
def explorer_app(tmp_path):
    """Flask app with explorer enabled and routes registered."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
    app.config["APCORE_AUTO_DISCOVER"] = False
    app.config["APCORE_EXPLORER_ENABLED"] = True

    app.add_url_rule("/items", "list_items", list_items, methods=["GET"])
    app.add_url_rule("/items", "create_item", create_item, methods=["POST"])

    Apcore(app)

    # Register modules via scan (exclude explorer blueprint routes)
    with app.app_context():
        from flask_apcore.scanners import auto_detect_scanner
        from flask_apcore.output.registry_writer import RegistryWriter

        scanner = auto_detect_scanner(app)
        modules = scanner.scan(app, exclude=r"^apcore_explorer\.")
        writer = RegistryWriter()
        writer.write(modules, app.extensions["apcore"]["registry"])

    return app


@pytest.fixture()
def client(explorer_app):
    return explorer_app.test_client()


@pytest.fixture()
def disabled_app(tmp_path):
    """Flask app with explorer disabled (default)."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
    app.config["APCORE_AUTO_DISCOVER"] = False
    Apcore(app)
    return app


class TestExplorerDisabled:
    def test_no_explorer_routes_when_disabled(self, disabled_app):
        client = disabled_app.test_client()
        resp = client.get("/apcore/modules")
        assert resp.status_code == 404


class TestModulesListAPI:
    def test_returns_json_list(self, client):
        resp = client.get("/apcore/modules")
        assert resp.status_code == 200
        assert resp.content_type == "application/json"
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_module_has_summary_fields(self, client):
        resp = client.get("/apcore/modules")
        data = resp.get_json()
        entry = data[0]
        assert "module_id" in entry
        assert "description" in entry
        assert "tags" in entry
        assert "http_method" in entry
        assert "url_rule" in entry


class TestModuleDetailAPI:
    def test_returns_single_module(self, client):
        listing = client.get("/apcore/modules").get_json()
        mid = listing[0]["module_id"]

        resp = client.get(f"/apcore/modules/{mid}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["module_id"] == mid
        assert "input_schema" in data
        assert "output_schema" in data

    def test_not_found_returns_404(self, client):
        resp = client.get("/apcore/modules/nonexistent.module")
        assert resp.status_code == 404


class TestOpenAPIEndpoint:
    def test_returns_openapi_spec(self, client):
        resp = client.get("/apcore/openapi.json")
        assert resp.status_code == 200
        spec = resp.get_json()
        assert spec["openapi"] == "3.1.0"
        assert "paths" in spec
        assert len(spec["paths"]) >= 1


class TestExplorerHTML:
    def test_returns_html(self, client):
        resp = client.get("/apcore/")
        assert resp.status_code == 200
        assert "text/html" in resp.content_type
        assert b"<html" in resp.data

    def test_html_contains_fetch_script(self, client):
        resp = client.get("/apcore/")
        assert b"fetch" in resp.data


class TestCustomUrlPrefix:
    def test_custom_prefix(self, tmp_path):
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
        app.config["APCORE_AUTO_DISCOVER"] = False
        app.config["APCORE_EXPLORER_ENABLED"] = True
        app.config["APCORE_EXPLORER_URL_PREFIX"] = "/my-explorer"
        Apcore(app)

        client = app.test_client()
        resp = client.get("/apcore/modules")
        assert resp.status_code == 404

        resp = client.get("/my-explorer/modules")
        assert resp.status_code == 200
