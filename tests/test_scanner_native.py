"""Tests for scanners/native.py — NativeFlaskScanner."""

from __future__ import annotations

import pytest
from flask import Blueprint, Flask

from flask_apcore.scanners import auto_detect_scanner, get_scanner
from flask_apcore.scanners.native import NativeFlaskScanner


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app():
    """Minimal Flask app with a few routes for scanner testing."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/items", methods=["GET"])
    def list_items():
        """List all items in the store.

        Returns a paginated list of items with optional filtering.
        """
        return []

    @app.route("/items", methods=["POST"])
    def create_item():
        """Create a new item."""
        return {}

    @app.route("/items/<int:item_id>", methods=["GET"])
    def get_item(item_id: int):
        """Get a single item by ID."""
        return {}

    @app.route("/items/<int:item_id>", methods=["PUT"])
    def update_item(item_id: int):
        """Update an existing item."""
        return {}

    @app.route("/items/<int:item_id>", methods=["DELETE"])
    def delete_item(item_id: int):
        """Delete an item permanently.

        This action cannot be undone.
        """
        return {}

    @app.route("/no-doc")
    def no_doc_view():
        return ""

    return app


@pytest.fixture()
def bp_app():
    """Flask app with Blueprint routes."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    bp = Blueprint("users", __name__, url_prefix="/users")

    @bp.route("/", methods=["GET"])
    def list_users():
        """List all users."""
        return []

    @bp.route("/<int:user_id>", methods=["GET"])
    def get_user(user_id: int):
        """Get user by ID."""
        return {}

    app.register_blueprint(bp)
    return app


@pytest.fixture()
def scanner():
    return NativeFlaskScanner()


# ---------------------------------------------------------------------------
# Annotation inference
# ---------------------------------------------------------------------------


class TestAnnotationInference:
    """Test HTTP method to ModuleAnnotations mapping."""

    def test_get_readonly(self, app, scanner):
        with app.app_context():
            modules = scanner.scan(app, include=r"list_items\.get$")
        assert len(modules) == 1
        ann = modules[0].annotations
        assert ann is not None
        assert ann.readonly is True
        assert ann.destructive is False

    def test_delete_destructive(self, app, scanner):
        with app.app_context():
            modules = scanner.scan(app, include=r"delete_item\.delete$")
        assert len(modules) == 1
        ann = modules[0].annotations
        assert ann is not None
        assert ann.destructive is True
        assert ann.readonly is False

    def test_put_idempotent(self, app, scanner):
        with app.app_context():
            modules = scanner.scan(app, include=r"update_item\.put$")
        assert len(modules) == 1
        ann = modules[0].annotations
        assert ann is not None
        assert ann.idempotent is True

    def test_post_default_annotations(self, app, scanner):
        with app.app_context():
            modules = scanner.scan(app, include=r"create_item\.post$")
        assert len(modules) == 1
        ann = modules[0].annotations
        assert ann is not None
        assert ann.readonly is False
        assert ann.destructive is False
        assert ann.idempotent is False


# ---------------------------------------------------------------------------
# Documentation extraction
# ---------------------------------------------------------------------------


class TestDocumentation:
    """Test docstring extraction into documentation and description."""

    def test_full_docstring_in_documentation(self, app, scanner):
        with app.app_context():
            modules = scanner.scan(app, include=r"list_items\.get$")
        m = modules[0]
        assert m.documentation is not None
        assert "paginated list" in m.documentation

    def test_first_line_in_description(self, app, scanner):
        with app.app_context():
            modules = scanner.scan(app, include=r"list_items\.get$")
        m = modules[0]
        assert m.description == "List all items in the store."

    def test_single_line_docstring(self, app, scanner):
        with app.app_context():
            modules = scanner.scan(app, include=r"create_item\.post$")
        m = modules[0]
        assert m.description == "Create a new item."
        assert m.documentation == "Create a new item."

    def test_no_docstring_auto_generates(self, app, scanner):
        with app.app_context():
            modules = scanner.scan(app, include=r"no_doc_view\.get$")
        m = modules[0]
        assert "GET" in m.description or "/no-doc" in m.description
        assert m.documentation is None


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestMetadata:
    """Test metadata field population."""

    def test_metadata_source_native(self, app, scanner):
        with app.app_context():
            modules = scanner.scan(app)
        for m in modules:
            assert m.metadata.get("source") == "native"


# ---------------------------------------------------------------------------
# URL parameter extraction and typing
# ---------------------------------------------------------------------------


class TestUrlParams:
    """Test URL parameter extraction and type mapping."""

    def test_int_param(self, app, scanner):
        with app.app_context():
            modules = scanner.scan(app, include=r"get_item\.get$")
        m = modules[0]
        assert "item_id" in m.input_schema.get("properties", {})
        # Should be mapped to integer type
        prop = m.input_schema["properties"]["item_id"]
        assert prop.get("type") == "integer"


# ---------------------------------------------------------------------------
# Blueprint handling
# ---------------------------------------------------------------------------


class TestBlueprintHandling:
    """Test Blueprint route scanning."""

    def test_blueprint_tags(self, bp_app, scanner):
        with bp_app.app_context():
            modules = scanner.scan(bp_app, include=r"^users\.")
        assert len(modules) >= 1
        for m in modules:
            assert "users" in m.tags

    def test_blueprint_module_id_prefix(self, bp_app, scanner):
        with bp_app.app_context():
            modules = scanner.scan(bp_app, include=r"^users\.")
        for m in modules:
            assert m.module_id.startswith("users.")


# ---------------------------------------------------------------------------
# Module ID generation
# ---------------------------------------------------------------------------


class TestModuleIdGeneration:
    """Test module ID format."""

    def test_format_without_blueprint(self, app, scanner):
        with app.app_context():
            modules = scanner.scan(app, include=r"list_items\.get$")
        m = modules[0]
        assert m.module_id == "list_items.get"

    def test_format_with_blueprint(self, bp_app, scanner):
        with bp_app.app_context():
            modules = scanner.scan(bp_app, include=r"list_users\.get$")
        m = modules[0]
        assert m.module_id == "users.list_users.get"


# ---------------------------------------------------------------------------
# Static route skipping
# ---------------------------------------------------------------------------


class TestStaticRouteSkipping:
    """Test that static and non-API routes are skipped."""

    def test_no_static_routes(self, app, scanner):
        with app.app_context():
            modules = scanner.scan(app)
        ids = [m.module_id for m in modules]
        assert not any("static" in mid for mid in ids)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    """Test that duplicate module IDs get suffixed."""

    def test_dedup_applied(self):
        """Create an app with routes that would produce duplicate IDs."""
        app = Flask(__name__)

        @app.route("/a", methods=["GET"], endpoint="dup_a")
        def dup_a():
            return ""

        @app.route("/b", methods=["GET"], endpoint="dup_a_2")
        def dup_a_2():
            return ""

        scanner = NativeFlaskScanner()
        with app.app_context():
            modules = scanner.scan(app)

        # Verify no module IDs collide
        ids = [m.module_id for m in modules]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Scanner registry / factory
# ---------------------------------------------------------------------------


class TestScannerRegistry:
    """Test get_scanner and auto_detect_scanner."""

    def test_get_native_scanner(self):
        scanner = get_scanner("native")
        assert isinstance(scanner, NativeFlaskScanner)

    def test_get_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown scanner source"):
            get_scanner("nonexistent")

    def test_auto_detect_returns_native(self):
        app = Flask(__name__)
        scanner = auto_detect_scanner(app)
        assert isinstance(scanner, NativeFlaskScanner)
