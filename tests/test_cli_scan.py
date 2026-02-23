"""Tests for CLI scan command."""

from __future__ import annotations

import pytest
from flask import Flask

from flask_apcore import Apcore


# ---------------------------------------------------------------------------
# Module-level view functions (resolvable by RegistryWriter._resolve_target)
# ---------------------------------------------------------------------------


def list_items() -> dict:
    """List all items."""
    return {"items": []}


def create_item() -> dict:
    """Create a new item."""
    return {}


def delete_item(item_id: int) -> dict:
    """Delete an item."""
    return {}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def scan_app(tmp_path):
    """Flask app with routes for scan testing."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
    app.config["APCORE_AUTO_DISCOVER"] = False

    app.add_url_rule("/items", "list_items", list_items, methods=["GET"])
    app.add_url_rule("/items", "create_item", create_item, methods=["POST"])
    app.add_url_rule("/items/<int:item_id>", "delete_item", delete_item, methods=["DELETE"])

    Apcore(app)
    return app


@pytest.fixture()
def empty_app(tmp_path):
    """Flask app with NO API routes (only static)."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
    app.config["APCORE_AUTO_DISCOVER"] = False
    Apcore(app)
    return app


# ---------------------------------------------------------------------------
# Default scan (no --output) -> direct registry registration
# ---------------------------------------------------------------------------


class TestScanDefaultRegistration:
    """Default scan registers modules directly into the Registry."""

    def test_default_scan_registers_to_registry(self, scan_app):
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan"])

        assert result.exit_code == 0, result.output
        assert "Registered" in result.output

        with scan_app.app_context():
            registry = scan_app.extensions["apcore"]["registry"]
            assert registry.count >= 3

    def test_default_scan_output_message(self, scan_app):
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan"])

        assert result.exit_code == 0, result.output
        assert "Scanning" in result.output
        assert "Found" in result.output
        assert "Registered" in result.output


# ---------------------------------------------------------------------------
# --output yaml -> generates .binding.yaml files
# ---------------------------------------------------------------------------


class TestScanYAMLOutput:
    """--output yaml generates .binding.yaml files."""

    def test_yaml_output_creates_files(self, scan_app, tmp_path):
        out_dir = str(tmp_path / "yaml_out")
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan", "--output", "yaml", "--dir", out_dir])

        assert result.exit_code == 0, result.output
        assert "Generated" in result.output
        assert "Written to" in result.output

        from pathlib import Path

        yaml_files = list(Path(out_dir).glob("*.binding.yaml"))
        assert len(yaml_files) >= 3

    def test_yaml_output_does_not_register(self, scan_app, tmp_path):
        out_dir = str(tmp_path / "yaml_out2")
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan", "--output", "yaml", "--dir", out_dir])

        assert result.exit_code == 0, result.output
        with scan_app.app_context():
            registry = scan_app.extensions["apcore"]["registry"]
            # Should NOT register; YAML mode only writes files
            assert registry.count == 0


# ---------------------------------------------------------------------------
# --dry-run
# ---------------------------------------------------------------------------


class TestScanDryRun:
    """--dry-run doesn't register or write files."""

    def test_dry_run_no_registration(self, scan_app):
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan", "--dry-run"])

        assert result.exit_code == 0, result.output
        assert "Dry run" in result.output
        assert "no modules registered" in result.output

        with scan_app.app_context():
            registry = scan_app.extensions["apcore"]["registry"]
            assert registry.count == 0

    def test_dry_run_yaml_no_files(self, scan_app, tmp_path):
        out_dir = str(tmp_path / "dry_yaml")
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan", "--output", "yaml", "--dir", out_dir, "--dry-run"])

        assert result.exit_code == 0, result.output
        assert "Dry run" in result.output
        assert "no files written" in result.output

        from pathlib import Path

        out_path = Path(out_dir)
        if out_path.exists():
            assert len(list(out_path.glob("*.binding.yaml"))) == 0


# ---------------------------------------------------------------------------
# --include / --exclude filters
# ---------------------------------------------------------------------------


class TestScanFilters:
    """--include and --exclude filter modules."""

    def test_include_filter(self, scan_app):
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan", "--include", r"list_items"])

        assert result.exit_code == 0, result.output
        assert "Registered 1 modules" in result.output

    def test_exclude_filter(self, scan_app):
        runner = scan_app.test_cli_runner()
        # Exclude delete_item, should leave list_items and create_item
        result = runner.invoke(args=["apcore", "scan", "--exclude", r"delete_item"])

        assert result.exit_code == 0, result.output
        assert "Registered 2 modules" in result.output

    def test_include_and_exclude_combined(self, scan_app):
        runner = scan_app.test_cli_runner()
        # Include items-related, exclude delete
        result = runner.invoke(
            args=[
                "apcore",
                "scan",
                "--include",
                r"item",
                "--exclude",
                r"delete",
            ]
        )

        assert result.exit_code == 0, result.output
        assert "Registered 2 modules" in result.output


# ---------------------------------------------------------------------------
# No routes -> exit code 1
# ---------------------------------------------------------------------------


class TestScanNoRoutes:
    """No routes found -> exit code 1."""

    def test_no_routes_exits_1(self, scan_app):
        runner = scan_app.test_cli_runner()
        # Include pattern that matches nothing
        result = runner.invoke(args=["apcore", "scan", "--include", r"^zzz_nonexistent$"])

        assert result.exit_code == 1
        assert "No routes found" in result.output

    def test_empty_app_exits_1(self, empty_app):
        runner = empty_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan"])

        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Invalid regex -> ClickException
# ---------------------------------------------------------------------------


class TestScanInvalidRegex:
    """Invalid regex patterns raise ClickException."""

    def test_invalid_include_regex(self, scan_app):
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan", "--include", "[invalid("])

        assert result.exit_code != 0
        assert "Invalid --include pattern" in result.output

    def test_invalid_exclude_regex(self, scan_app):
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan", "--exclude", "[invalid("])

        assert result.exit_code != 0
        assert "Invalid --exclude pattern" in result.output


# ---------------------------------------------------------------------------
# Scanner source selection
# ---------------------------------------------------------------------------


class TestScanSourceSelection:
    """--source selects the scanner."""

    def test_auto_source(self, scan_app):
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan", "--source", "auto"])
        assert result.exit_code == 0, result.output

    def test_native_source(self, scan_app):
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan", "--source", "native"])
        assert result.exit_code == 0, result.output

    def test_invalid_source_rejected(self, scan_app):
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan", "--source", "invalid"])
        # click.Choice rejects invalid values
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# --output json -> generates apcore-modules.json file
# ---------------------------------------------------------------------------


class TestScanJSONOutput:
    """--output json generates apcore-modules.json file."""

    def test_json_output_creates_file(self, scan_app, tmp_path):
        out_dir = str(tmp_path / "json_out")
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan", "--output", "json", "--dir", out_dir])

        assert result.exit_code == 0, result.output
        assert "Generated" in result.output

        from pathlib import Path
        import json

        json_file = Path(out_dir) / "apcore-modules.json"
        assert json_file.exists()
        data = json.loads(json_file.read_text())
        assert len(data) >= 3


# ---------------------------------------------------------------------------
# --output openapi -> generates openapi.json file
# ---------------------------------------------------------------------------


class TestScanOpenAPIOutput:
    """--output openapi generates openapi.json file."""

    def test_openapi_output_creates_file(self, scan_app, tmp_path):
        out_dir = str(tmp_path / "openapi_out")
        runner = scan_app.test_cli_runner()
        result = runner.invoke(args=["apcore", "scan", "--output", "openapi", "--dir", out_dir])

        assert result.exit_code == 0, result.output
        assert "Generated" in result.output

        from pathlib import Path
        import json

        spec_file = Path(out_dir) / "openapi.json"
        assert spec_file.exists()
        spec = json.loads(spec_file.read_text())
        assert spec["openapi"] == "3.1.0"
        assert len(spec["paths"]) >= 2
