# flask-apcore v0.1.0 Demo

A Docker-based demo of the full flask-apcore pipeline: Flask routes → Scanner → Registry → MCP Server, with observability.

## Quick Start

```bash
cd examples/demo
docker compose up --build
```

This will:

1. Build a container with flask-apcore installed from local source
2. Scan 5 Flask CRUD routes (`GET`, `POST`, `GET/:id`, `PUT/:id`, `DELETE/:id`)
3. Infer annotations (readonly, destructive, idempotent) from HTTP methods
4. Register a standalone `@module` function (`task_stats.v1`)
5. Start an MCP server on `http://localhost:9100` with streamable-http transport

## What's Inside

| File | Purpose |
|---|---|
| `app.py` | Task Manager API with Pydantic models and `@module` example |
| `Dockerfile` | Installs flask-apcore[mcp] from local source |
| `docker-compose.yml` | One-click launch |
| `entrypoint.sh` | Scans routes then starts the MCP server |

## Features Demonstrated

- **Route scanning** — `flask apcore scan` discovers all 5 API routes
- **Annotation inference** — GET→readonly, DELETE→destructive, PUT→idempotent
- **Pydantic schemas** — Input validation from `TaskCreate` and `TaskUpdate` models
- **@module decorator** — `task_stats.v1` registered alongside scanned routes
- **MCP server** — HTTP transport on port 9100
- **Observability** — Tracing (stdout), metrics, and structured JSON logging
- **Input validation** — `--validate-inputs` checks tool inputs against schemas

## Verification

After `docker compose up`:

```bash
# Check the MCP endpoint is responding
curl http://localhost:9100/health
```

Connect from any MCP client (e.g., Claude Desktop) using:

```
http://localhost:9100
```

## Cleanup

```bash
docker compose down
```
