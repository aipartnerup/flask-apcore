# Explorer Simplification & Try-it Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove `--output json`, `--output openapi`, `/apcore/openapi.json`; add `POST /modules/<id>/call` execute endpoint with "Try it" UI in Explorer.

**Architecture:** Delete json_writer, openapi_writer, _openapi.py and their tests. Add execute endpoint using Executor.call() behind `APCORE_EXPLORER_ALLOW_EXECUTE` config. Upgrade Explorer HTML with input form + execute button.

**Tech Stack:** Flask, apcore Executor, Click CLI, inline JS/CSS

---

### Task 1: Delete json_writer and openapi_writer

**Files:**
- Delete: `src/flask_apcore/output/json_writer.py`
- Delete: `src/flask_apcore/output/openapi_writer.py`
- Delete: `tests/test_json_writer.py`
- Delete: `tests/test_openapi_writer.py`
- Modify: `src/flask_apcore/output/__init__.py`

**Step 1: Delete the writer files and their tests**

```bash
rm src/flask_apcore/output/json_writer.py
rm src/flask_apcore/output/openapi_writer.py
rm tests/test_json_writer.py
rm tests/test_openapi_writer.py
```

**Step 2: Update `output/__init__.py` — remove json/openapi branches**

Replace the entire file with:

```python
"""Output writer subpackage for flask-apcore.

Provides get_writer() factory for selecting output format.

Default writer is RegistryWriter (direct registration).
YAML writer is available via output_format="yaml".
"""

from __future__ import annotations


def get_writer(output_format: str | None = None):
    """Return a writer instance for the given format.

    Args:
        output_format: None for direct registry, "yaml" for YAML files.

    Returns:
        A RegistryWriter (default) or YAMLWriter instance.

    Raises:
        ValueError: If format is unknown.
    """
    if output_format is None:
        from flask_apcore.output.registry_writer import RegistryWriter

        return RegistryWriter()
    elif output_format == "yaml":
        from flask_apcore.output.yaml_writer import YAMLWriter

        return YAMLWriter()
    else:
        raise ValueError(f"Unknown output format: {output_format!r}")
```

**Step 3: Run tests to verify nothing breaks**

Run: `pytest tests/ -x -q`
Expected: Tests pass (minus deleted test files). Some tests in test_cli_scan.py will fail because `TestScanJSONOutput` and `TestScanOpenAPIOutput` still reference deleted code — those are fixed in Task 2.

**Step 4: Commit**

```bash
git add -A
git commit -m "refactor: remove json_writer and openapi_writer"
```

---

### Task 2: Clean up CLI and remaining tests

**Files:**
- Modify: `src/flask_apcore/cli.py:36` — revert `--output` Choice to `["yaml"]`
- Modify: `tests/test_cli_scan.py:274-323` — delete `TestScanJSONOutput` and `TestScanOpenAPIOutput`

**Step 1: Update CLI `--output` option**

In `src/flask_apcore/cli.py`, change line 36:

```python
# Old:
    type=click.Choice(["yaml", "json", "openapi"]),
# New:
    type=click.Choice(["yaml"]),
```

**Step 2: Delete test classes from test_cli_scan.py**

Remove the entire `TestScanJSONOutput` class (lines 274-296) and `TestScanOpenAPIOutput` class (lines 299-323).

**Step 3: Run tests**

Run: `pytest tests/test_cli_scan.py -v`
Expected: All remaining tests PASS.

**Step 4: Commit**

```bash
git add src/flask_apcore/cli.py tests/test_cli_scan.py
git commit -m "refactor: revert --output to yaml-only"
```

---

### Task 3: Delete _openapi.py and clean up serializers

**Files:**
- Delete: `src/flask_apcore/web/_openapi.py`
- Modify: `src/flask_apcore/web/api.py:53-65` — remove `openapi_spec` route
- Modify: `src/flask_apcore/serializers.py` — remove `modules_to_openapi`, `_build_operation`, `_schema_to_parameters`, `_BODY_METHODS`
- Modify: `tests/test_web.py:109-116` — delete `TestOpenAPIEndpoint`
- Modify: `tests/test_serializers.py:88-158` — delete `TestModulesToOpenapi`
- Modify: `tests/test_integration.py:542-546` — remove openapi assertion block

**Step 1: Delete _openapi.py**

```bash
rm src/flask_apcore/web/_openapi.py
```

**Step 2: Remove openapi_spec route from api.py**

Delete lines 53-65 (the `@bp.route("/openapi.json")` function and its body).

**Step 3: Clean up serializers.py**

Remove:
- `_BODY_METHODS` constant (line 16)
- `modules_to_openapi` function (lines 63-108)
- `_build_operation` function (lines 111-161)
- `_schema_to_parameters` function (lines 164-185)

Keep:
- `annotations_to_dict`
- `module_to_dict`
- `modules_to_dicts`
- All imports they need (`dataclasses`, `Any`, `ScannedModule`)

**Step 4: Remove test classes**

- `tests/test_web.py`: Delete `TestOpenAPIEndpoint` class (lines 109-116)
- `tests/test_serializers.py`: Delete `TestModulesToOpenapi` class (lines 88-158)
- `tests/test_integration.py`: Remove lines 542-546 (the openapi.json check in `test_scan_then_explore`)

**Step 5: Run tests**

Run: `pytest tests/ -x -q`
Expected: All tests PASS.

**Step 6: Commit**

```bash
git add -A
git commit -m "refactor: remove openapi endpoint and serializers"
```

---

### Task 4: Add `APCORE_EXPLORER_ALLOW_EXECUTE` config

**Files:**
- Modify: `src/flask_apcore/config.py`
- Modify: `tests/test_config.py`

**Step 1: Write the failing tests**

Add to `tests/test_config.py`:

```python
class TestExplorerAllowExecute:
    def test_default_false(self) -> None:
        s = _load()
        assert s.explorer_allow_execute is False

    def test_true(self) -> None:
        s = _load(APCORE_EXPLORER_ALLOW_EXECUTE=True)
        assert s.explorer_allow_execute is True

    def test_none_falls_back(self) -> None:
        s = _load(APCORE_EXPLORER_ALLOW_EXECUTE=None)
        assert s.explorer_allow_execute is False

    def test_non_bool_raises(self) -> None:
        with pytest.raises(ValueError, match="APCORE_EXPLORER_ALLOW_EXECUTE"):
            _load(APCORE_EXPLORER_ALLOW_EXECUTE="yes")
```

Also update the field count test:
```python
# Old: assert len(fields) == 28
# New: assert len(fields) == 29
```

And update the `test_all_defaults` to include:
```python
assert settings.explorer_allow_execute is False
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py::TestExplorerAllowExecute -v`
Expected: FAIL — `ApcoreSettings` doesn't have `explorer_allow_execute` yet.

**Step 3: Implement the config**

In `src/flask_apcore/config.py`:

Add default:
```python
DEFAULT_EXPLORER_ALLOW_EXECUTE = False
```

Add field to `ApcoreSettings`:
```python
    explorer_allow_execute: bool
```

Add validation block in `load_settings()` (after explorer_url_prefix):
```python
    # --- explorer_allow_execute ---
    explorer_allow_execute = app.config.get(
        "APCORE_EXPLORER_ALLOW_EXECUTE", DEFAULT_EXPLORER_ALLOW_EXECUTE
    )
    if explorer_allow_execute is None:
        explorer_allow_execute = DEFAULT_EXPLORER_ALLOW_EXECUTE
    if not isinstance(explorer_allow_execute, bool):
        actual = type(explorer_allow_execute).__name__
        raise ValueError(
            f"APCORE_EXPLORER_ALLOW_EXECUTE must be a boolean. Got: {actual}"
        )
```

Add to the `ApcoreSettings(...)` constructor call:
```python
        explorer_allow_execute=explorer_allow_execute,
```

**Step 4: Run tests**

Run: `pytest tests/test_config.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git add src/flask_apcore/config.py tests/test_config.py
git commit -m "feat: add APCORE_EXPLORER_ALLOW_EXECUTE config setting"
```

---

### Task 5: Add `POST /modules/<id>/call` endpoint

**Files:**
- Modify: `src/flask_apcore/web/api.py`
- Modify: `tests/test_web.py`

**Step 1: Write failing tests**

Add to `tests/test_web.py`:

```python
@pytest.fixture()
def execute_app(tmp_path):
    """Flask app with explorer + execute enabled."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["APCORE_MODULE_DIR"] = str(tmp_path / "modules")
    app.config["APCORE_AUTO_DISCOVER"] = False
    app.config["APCORE_EXPLORER_ENABLED"] = True
    app.config["APCORE_EXPLORER_ALLOW_EXECUTE"] = True

    app.add_url_rule("/items", "list_items", list_items, methods=["GET"])
    app.add_url_rule("/items", "create_item", create_item, methods=["POST"])

    Apcore(app)

    with app.app_context():
        from flask_apcore.scanners import auto_detect_scanner
        from flask_apcore.output.registry_writer import RegistryWriter

        scanner = auto_detect_scanner(app)
        modules = scanner.scan(app, exclude=r"^apcore_explorer\.")
        writer = RegistryWriter()
        writer.write(modules, app.extensions["apcore"]["registry"])

    return app


@pytest.fixture()
def execute_client(execute_app):
    return execute_app.test_client()


class TestCallEndpoint:
    def test_call_returns_output(self, execute_client):
        listing = execute_client.get("/apcore/modules").get_json()
        # Find list_items module (GET, no required inputs)
        mid = next(m["module_id"] for m in listing if "list_items" in m["module_id"])

        resp = execute_client.post(
            f"/apcore/modules/{mid}/call",
            json={},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "output" in data

    def test_call_not_found_returns_404(self, execute_client):
        resp = execute_client.post(
            "/apcore/modules/nonexistent.module/call",
            json={},
        )
        assert resp.status_code == 404

    def test_call_disabled_returns_403(self, client):
        """When APCORE_EXPLORER_ALLOW_EXECUTE is False (default), returns 403."""
        listing = client.get("/apcore/modules").get_json()
        mid = listing[0]["module_id"]

        resp = client.post(
            f"/apcore/modules/{mid}/call",
            json={},
        )
        assert resp.status_code == 403


class TestCallEndpointDisabledExplorer:
    def test_call_404_when_explorer_disabled(self, disabled_app):
        """When explorer is disabled entirely, call endpoint doesn't exist."""
        c = disabled_app.test_client()
        resp = c.post("/apcore/modules/foo/call", json={})
        assert resp.status_code == 404
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_web.py::TestCallEndpoint -v`
Expected: FAIL — route doesn't exist yet.

**Step 3: Implement the call endpoint**

Add to `src/flask_apcore/web/api.py`, inside `register_api_routes(bp)`:

```python
    @bp.route("/modules/<path:module_id>/call", methods=["POST"])
    def call_module(module_id: str):
        settings = current_app.extensions["apcore"]["settings"]
        if not settings.explorer_allow_execute:
            return jsonify({"error": "Module execution is disabled. "
                           "Set APCORE_EXPLORER_ALLOW_EXECUTE=True to enable."}), 403

        from flask import request
        from flask_apcore.registry import get_executor, get_context_factory
        from apcore.errors import ModuleNotFoundError as ApcoreNotFound
        from apcore.errors import SchemaValidationError

        inputs = request.get_json(silent=True) or {}

        executor = get_executor()
        context = get_context_factory().create_context(request)

        try:
            output = executor.call(module_id, inputs, context)
        except ApcoreNotFound:
            return jsonify({"error": f"Module '{module_id}' not found"}), 404
        except SchemaValidationError as e:
            return jsonify({"error": f"Input validation failed: {e}"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        return jsonify({"output": output})
```

**Step 4: Run tests**

Run: `pytest tests/test_web.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git add src/flask_apcore/web/api.py tests/test_web.py
git commit -m "feat: add POST /modules/<id>/call execute endpoint"
```

---

### Task 6: Upgrade Explorer HTML with "Try it" UI

**Files:**
- Modify: `src/flask_apcore/web/views.py`

**Step 1: Write failing test**

Add to `tests/test_web.py`:

```python
class TestExplorerHTMLTryIt:
    def test_html_contains_try_it_elements(self, client):
        resp = client.get("/apcore/")
        html = resp.data.decode()
        assert "Try it" in html
        assert "execute-btn" in html or "Execute" in html
        assert "input-editor" in html or "textarea" in html

    def test_html_contains_result_area(self, client):
        resp = client.get("/apcore/")
        html = resp.data.decode()
        assert "result" in html.lower()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_web.py::TestExplorerHTMLTryIt -v`
Expected: FAIL — current HTML has no "Try it" elements.

**Step 3: Update the HTML in views.py**

Replace the `_EXPLORER_HTML` string in `src/flask_apcore/web/views.py` with:

```python
_EXPLORER_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>apcore Explorer</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
         background: #f5f5f5; color: #333; padding: 24px; }
  h1 { font-size: 1.4rem; margin-bottom: 16px; }
  .module-list { list-style: none; }
  .module-item { background: #fff; border: 1px solid #ddd; border-radius: 6px;
                 padding: 12px 16px; margin-bottom: 8px; cursor: pointer; }
  .module-item:hover { border-color: #888; }
  .module-id { font-weight: 600; }
  .module-method { display: inline-block; font-size: 0.75rem; font-weight: 700;
                   padding: 2px 6px; border-radius: 3px; margin-right: 8px; color: #fff; }
  .method-get { background: #61affe; }
  .method-post { background: #49cc90; }
  .method-put { background: #fca130; }
  .method-delete { background: #f93e3e; }
  .method-patch { background: #50e3c2; }
  .module-desc { color: #666; font-size: 0.9rem; margin-top: 4px; }
  .detail { background: #fff; border: 1px solid #ddd; border-radius: 6px;
            padding: 16px; margin-top: 16px; display: none; }
  .detail.active { display: block; }
  .detail h2 { font-size: 1.1rem; margin-bottom: 12px; }
  .schema-label { font-weight: 600; margin-top: 12px; display: block; }
  pre { background: #282c34; color: #abb2bf; padding: 12px; border-radius: 4px;
        overflow-x: auto; font-size: 0.85rem; margin-top: 4px; }
  .tag { display: inline-block; background: #e8e8e8; padding: 2px 8px;
         border-radius: 3px; font-size: 0.75rem; margin-right: 4px; }
  #loading { color: #888; }
  .try-it { margin-top: 16px; border-top: 1px solid #eee; padding-top: 16px; }
  .try-it h3 { font-size: 0.95rem; margin-bottom: 8px; }
  .input-editor { width: 100%; min-height: 120px; font-family: monospace;
                  font-size: 0.85rem; padding: 10px; border: 1px solid #ddd;
                  border-radius: 4px; resize: vertical; background: #fafafa; }
  .execute-btn { margin-top: 8px; padding: 8px 20px; background: #4CAF50; color: #fff;
                 border: none; border-radius: 4px; cursor: pointer; font-size: 0.9rem;
                 font-weight: 600; }
  .execute-btn:hover { background: #45a049; }
  .execute-btn:disabled { background: #ccc; cursor: not-allowed; }
  .result-area { margin-top: 12px; }
  .result-area pre { background: #1a2332; }
  .result-error { color: #f93e3e; }
  .result-success { color: #49cc90; }
  .exec-disabled { color: #888; font-size: 0.85rem; font-style: italic; margin-top: 16px; }
</style>
</head>
<body>
<h1>apcore Explorer</h1>
<div id="loading">Loading modules...</div>
<ul class="module-list" id="modules"></ul>
<div class="detail" id="detail"></div>
<script>
(function() {
  var base = window.location.pathname.replace(/\\/$/, '');
  var modulesEl = document.getElementById('modules');
  var detailEl = document.getElementById('detail');
  var loadingEl = document.getElementById('loading');
  var executeEnabled = null;

  function esc(s) {
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(s));
    return d.innerHTML;
  }

  function defaultFromSchema(schema) {
    if (!schema || !schema.properties) return {};
    var result = {};
    var props = schema.properties;
    for (var key in props) {
      if (!props.hasOwnProperty(key)) continue;
      var t = props[key].type;
      if (props[key]['default'] !== undefined) {
        result[key] = props[key]['default'];
      } else if (t === 'string') {
        result[key] = '';
      } else if (t === 'number' || t === 'integer') {
        result[key] = 0;
      } else if (t === 'boolean') {
        result[key] = false;
      } else if (t === 'array') {
        result[key] = [];
      } else if (t === 'object') {
        result[key] = {};
      } else {
        result[key] = null;
      }
    }
    return result;
  }

  fetch(base + '/modules')
    .then(function(r) { return r.json(); })
    .then(function(modules) {
      loadingEl.style.display = 'none';
      modules.forEach(function(m) {
        var li = document.createElement('li');
        li.className = 'module-item';
        var method = (m.http_method || 'GET').toUpperCase();
        li.innerHTML =
          '<span class="module-method method-' + esc(method.toLowerCase()) + '">' + esc(method) + '</span>' +
          '<span class="module-id">' + esc(m.module_id) + '</span> ' +
          '<span style="color:#888;font-size:0.85rem">' + esc(m.url_rule || '') + '</span>' +
          '<div class="module-desc">' + esc(m.description || '') + '</div>' +
          '<div>' + (m.tags || []).map(function(t) { return '<span class="tag">' + esc(t) + '</span>'; }).join('') + '</div>';
        li.onclick = function() { loadDetail(m.module_id); };
        modulesEl.appendChild(li);
      });
    })
    .catch(function(e) { loadingEl.textContent = 'Error: ' + e; });

  function loadDetail(id) {
    fetch(base + '/modules/' + id)
      .then(function(r) { return r.json(); })
      .then(function(d) {
        detailEl.className = 'detail active';
        var html =
          '<h2>' + esc(d.module_id) + '</h2>' +
          '<p>' + esc(d.documentation || d.description || '') + '</p>' +
          '<span class="schema-label">Input Schema</span>' +
          '<pre>' + esc(JSON.stringify(d.input_schema, null, 2)) + '</pre>' +
          '<span class="schema-label">Output Schema</span>' +
          '<pre>' + esc(JSON.stringify(d.output_schema, null, 2)) + '</pre>' +
          (d.annotations ? '<span class="schema-label">Annotations</span><pre>' + esc(JSON.stringify(d.annotations, null, 2)) + '</pre>' : '') +
          (d.metadata ? '<span class="schema-label">Metadata</span><pre>' + esc(JSON.stringify(d.metadata, null, 2)) + '</pre>' : '');

        html += '<div class="try-it" id="try-it-section">' +
          '<h3>Try it</h3>' +
          '<textarea class="input-editor" id="input-editor">' +
          esc(JSON.stringify(defaultFromSchema(d.input_schema), null, 2)) +
          '</textarea>' +
          '<button class="execute-btn" id="execute-btn" onclick="window._execModule(\\'' + esc(d.module_id.replace(/'/g, "\\\\'")) + '\\')">Execute</button>' +
          '<div class="result-area" id="result-area"></div>' +
          '</div>';

        detailEl.innerHTML = html;

        if (executeEnabled === false) {
          var section = document.getElementById('try-it-section');
          if (section) section.innerHTML = '<p class="exec-disabled">Module execution is disabled. Set APCORE_EXPLORER_ALLOW_EXECUTE=True to enable.</p>';
        }
      });
  }

  window._execModule = function(moduleId) {
    var btn = document.getElementById('execute-btn');
    var editor = document.getElementById('input-editor');
    var resultArea = document.getElementById('result-area');

    var inputText = editor.value.trim();
    var inputs;
    try {
      inputs = inputText ? JSON.parse(inputText) : {};
    } catch (e) {
      resultArea.innerHTML = '<p class="result-error">Invalid JSON: ' + esc(e.message) + '</p>';
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Executing...';
    resultArea.innerHTML = '';

    fetch(base + '/modules/' + moduleId + '/call', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(inputs)
    })
    .then(function(r) {
      if (r.status === 403) {
        executeEnabled = false;
        var section = document.getElementById('try-it-section');
        if (section) section.innerHTML = '<p class="exec-disabled">Module execution is disabled. Set APCORE_EXPLORER_ALLOW_EXECUTE=True to enable.</p>';
        return null;
      }
      return r.json().then(function(data) { return {status: r.status, data: data}; });
    })
    .then(function(result) {
      if (!result) return;
      btn.disabled = false;
      btn.textContent = 'Execute';
      if (result.status >= 400) {
        resultArea.innerHTML = '<span class="schema-label result-error">Error (' + result.status + ')</span>' +
          '<pre>' + esc(JSON.stringify(result.data, null, 2)) + '</pre>';
      } else {
        resultArea.innerHTML = '<span class="schema-label result-success">Result</span>' +
          '<pre>' + esc(JSON.stringify(result.data, null, 2)) + '</pre>';
      }
    })
    .catch(function(e) {
      btn.disabled = false;
      btn.textContent = 'Execute';
      resultArea.innerHTML = '<p class="result-error">Request failed: ' + esc(e.message) + '</p>';
    });
  };
})();
</script>
</body>
</html>
"""
```

**Step 4: Run tests**

Run: `pytest tests/test_web.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git add src/flask_apcore/web/views.py tests/test_web.py
git commit -m "feat: add Try-it UI to Explorer HTML page"
```

---

### Task 7: Update integration test

**Files:**
- Modify: `tests/test_integration.py`

**Step 1: Update `test_scan_then_explore`**

In `tests/test_integration.py`, replace the openapi check (lines 542-546) with a call endpoint test:

```python
        # Call endpoint (disabled by default)
        resp = client.post(
            f"/apcore/modules/{mid}/call",
            json={},
            content_type="application/json",
        )
        assert resp.status_code == 403
```

**Step 2: Run the integration test**

Run: `pytest tests/test_integration.py::TestExplorerIntegration -v`
Expected: PASS.

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: update integration test for explorer simplification"
```

---

### Task 8: Final verification

**Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass.

**Step 2: Run linter**

Run: `ruff check src/ tests/`
Expected: All checks passed.

**Step 3: Verify no orphan imports**

Run: `grep -r "json_writer\|openapi_writer\|_openapi\|modules_to_openapi\|OpenAPIWriter\|JSONWriter" src/ tests/`
Expected: No matches (all references cleaned up).

**Step 4: Commit any final fixes if needed**

```bash
git add -A
git commit -m "chore: final cleanup for explorer simplification"
```
