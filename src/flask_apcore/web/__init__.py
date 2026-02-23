"""Explorer Blueprint for flask-apcore."""

from __future__ import annotations

from flask import Blueprint


def create_explorer_blueprint(url_prefix: str = "/apcore") -> Blueprint:
    bp = Blueprint("apcore_explorer", __name__, url_prefix=url_prefix)

    from flask_apcore.web.api import register_api_routes
    from flask_apcore.web.views import register_view_routes

    register_api_routes(bp)
    register_view_routes(bp)

    return bp
