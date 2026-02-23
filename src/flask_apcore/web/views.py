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

  fetch(base + '/modules')
    .then(function(r) { return r.json(); })
    .then(function(modules) {
      loadingEl.style.display = 'none';
      modules.forEach(function(m) {
        var li = document.createElement('li');
        li.className = 'module-item';
        var method = (m.http_method || 'GET').toUpperCase();
        li.innerHTML =
          '<span class="module-method method-' + method.toLowerCase() + '">' + method + '</span>' +
          '<span class="module-id">' + m.module_id + '</span> ' +
          '<span style="color:#888;font-size:0.85rem">' + (m.url_rule || '') + '</span>' +
          '<div class="module-desc">' + (m.description || '') + '</div>' +
          '<div>' + (m.tags || []).map(function(t) { return '<span class="tag">' + t + '</span>'; }).join('') + '</div>';
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
        detailEl.innerHTML =
          '<h2>' + d.module_id + '</h2>' +
          '<p>' + (d.documentation || d.description || '') + '</p>' +
          '<span class="schema-label">Input Schema</span>' +
          '<pre>' + JSON.stringify(d.input_schema, null, 2) + '</pre>' +
          '<span class="schema-label">Output Schema</span>' +
          '<pre>' + JSON.stringify(d.output_schema, null, 2) + '</pre>' +
          (d.annotations ? '<span class="schema-label">Annotations</span><pre>' + JSON.stringify(d.annotations, null, 2) + '</pre>' : '') +
          (d.metadata ? '<span class="schema-label">Metadata</span><pre>' + JSON.stringify(d.metadata, null, 2) + '</pre>' : '');
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
