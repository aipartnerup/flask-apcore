"""Shared test fixtures for flask-apcore."""

from __future__ import annotations

import pytest
from flask import Flask


@pytest.fixture()
def app(tmp_path):
    """Minimal Flask app with APCORE_MODULE_DIR pointed to tmp_path."""
    a = Flask(__name__)
    a.config["TESTING"] = True
    a.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
    a.config["APCORE_AUTO_DISCOVER"] = False
    return a


@pytest.fixture()
def app_ctx(app):
    """Push an application context."""
    with app.app_context() as ctx:
        yield ctx


@pytest.fixture()
def initialized_app(app):
    """Flask app with Apcore initialized (auto-discover off)."""
    from flask_apcore import Apcore

    Apcore(app)
    return app
