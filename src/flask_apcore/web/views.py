"""HTML explorer page for the explorer Blueprint."""

from __future__ import annotations

from flask import Blueprint, Response


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
  .input-editor { width: 100%%; min-height: 120px; font-family: monospace;
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
          '<button class="execute-btn" id="execute-btn">Execute</button>' +
          '<div class="result-area" id="result-area"></div>' +
          '</div>';

        detailEl.innerHTML = html;

        document.getElementById('execute-btn').onclick = function() {
          execModule(d.module_id);
        };

        if (executeEnabled === false) {
          var section = document.getElementById('try-it-section');
          if (section) section.innerHTML = '<p class="exec-disabled">Module execution is disabled. Set APCORE_EXPLORER_ALLOW_EXECUTE=True to enable.</p>';
        }
      });
  }

  function execModule(moduleId) {
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
  }
})();
</script>
</body>
</html>
"""


def register_view_routes(bp: Blueprint) -> None:
    @bp.route("/")
    def explorer_page():
        return Response(_EXPLORER_HTML, content_type="text/html")
