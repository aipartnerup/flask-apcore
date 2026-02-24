# Explorer Simplification & Try-it Feature Design

Date: 2026-02-24

## Goal

1. Remove low-value features: `--output json`, `--output openapi`, `/apcore/openapi.json`
2. Add module execution endpoint (`POST /apcore/modules/<id>/call`) via Executor
3. Upgrade Explorer HTML with "Try it" UI (Swagger-style)

## Deletions

| Item | Files |
|------|-------|
| `--output json` CLI | `output/json_writer.py`, `output/__init__.py`, `cli.py` |
| `--output openapi` CLI | `output/openapi_writer.py`, `output/__init__.py`, `cli.py` |
| `/apcore/openapi.json` endpoint | `web/api.py`, `web/_openapi.py` |
| OpenAPI serializer | `serializers.py` (`modules_to_openapi`, `_build_operation`, `_schema_to_parameters`) |
| Related tests | `test_json_writer.py`, `test_openapi_writer.py`, openapi tests in `test_web.py`, `test_cli_scan.py`, `test_serializers.py` |

CLI `--output` reverts to `yaml` only.

## New: Execute Endpoint

**Route**: `POST /apcore/modules/<module_id>/call`

```
Request:  {"title": "hello", "done": false}
Response: {"output": {"id": 3, "title": "hello", ...}}
```

Execution path:
1. `request.get_json()` -> inputs
2. `get_executor()` -> Executor (with middlewares, ACL, observability)
3. `get_context_factory().create_context(request)` -> Context
4. `executor.call(module_id, inputs, context)` -> output
5. Error mapping: `ModuleNotFoundError` -> 404, `SchemaValidationError` -> 400

Guard: `APCORE_EXPLORER_ALLOW_EXECUTE` (default False). Returns 403 when disabled.

## New: Explorer HTML "Try it"

Module detail area gains:
- JSON textarea pre-filled with skeleton from `input_schema.properties`
- Execute button -> `POST /modules/<id>/call`
- Result area showing response JSON or error
- Hidden when execute is disabled (detected via 403 on first attempt, or probed via config)

Default value generation from schema:
- `string` -> `""`
- `number`/`integer` -> `0`
- `boolean` -> `false`
- `object` -> `{}`
- `array` -> `[]`

## Config Changes

| Key | Default | Description |
|-----|---------|-------------|
| `APCORE_EXPLORER_ENABLED` | `False` | Existing, controls Blueprint registration |
| `APCORE_EXPLORER_URL_PREFIX` | `"/apcore"` | Existing |
| `APCORE_EXPLORER_ALLOW_EXECUTE` | `False` | **New**, controls call endpoint |

## File Changes

| Action | File |
|--------|------|
| Delete | `src/flask_apcore/output/json_writer.py` |
| Delete | `src/flask_apcore/output/openapi_writer.py` |
| Delete | `src/flask_apcore/web/_openapi.py` |
| Delete | `tests/test_json_writer.py` |
| Delete | `tests/test_openapi_writer.py` |
| Modify | `src/flask_apcore/output/__init__.py` |
| Modify | `src/flask_apcore/cli.py` |
| Modify | `src/flask_apcore/serializers.py` |
| Modify | `src/flask_apcore/web/api.py` |
| Modify | `src/flask_apcore/web/views.py` |
| Modify | `src/flask_apcore/config.py` |
| Modify | `tests/test_web.py` |
| Modify | `tests/test_config.py` |
| Modify | `tests/test_cli_scan.py` |
| Modify | `tests/test_serializers.py` |
