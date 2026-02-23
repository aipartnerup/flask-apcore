# flask-apcore: Idea Validation Summary

**Status:** Validated - Ready for PRD
**Date:** 2026-02-20

## Core Idea

Build `flask-apcore` — the official Flask integration for the apcore (AI-Perceivable Core) framework, providing dual-mode integration: a lightweight 3-line MCP server mode AND full apcore module governance.

## Market Opportunity

### The Gap

| Framework | MCP Integration | Stars | Downloads |
|-----------|----------------|-------|-----------|
| FastAPI | fastapi-mcp: 11.6k stars, 6.68M downloads | Dominated | N/A |
| Django | django-mcp-server: 274 stars, 1M downloads | Covered | N/A |
| **Flask** | **Best project: 5 stars, 26k downloads** | **Wide Open** | **~9M monthly** |

Flask has ~68k GitHub stars and ~9M monthly PyPI downloads, yet its AI/MCP integration space is virtually empty. The strongest existing project (mcp-utils) has only 5 stars and is a utility library, not a framework.

### Existing Flask MCP Projects (All Weak)

- `flask-mcp-server` — 2 stars, 2,038 total downloads, manual registration
- `flaskmcp` — Repo deleted, 4,474 downloads, stale since 2025.04
- `mcp-utils` — 5 stars, 26,096 downloads, sync utility library

**None provide auto-discovery of Flask routes or zero-config integration.**

### Success Benchmark: fastapi-mcp

fastapi-mcp succeeded by offering: zero-config 3-line integration, automatic endpoint-to-tool conversion, schema preservation (Pydantic), auth reuse (Depends()), and ASGI native transport.

## Validated Decisions

### 1. Product Positioning: Dual Mode

- **Lite Mode:** 3-line Flask MCP server (compete with fastapi-mcp mindshare)
- **Full Mode:** Complete apcore integration (ACL, middleware, observability, module governance)
- Users choose depth; Lite mode is the onramp to Full mode.

### 2. Schema Strategy: Multi-Backend

Auto-detect and support:
- marshmallow schemas (Flask ecosystem standard)
- Pydantic models (apcore internal + FastAPI migration users)
- Native Python type hints (fallback)
- YAML external schemas (apcore unique — zero-code binding)

### 3. Transport: STDIO + HTTP Dual Mode

- **STDIO:** For Claude Code and local MCP clients (simplest, works first)
- **HTTP (Streamable HTTP):** For network deployment (POST JSON-RPC + GET SSE)
- STDIO ships first; HTTP follows.

### 4. Differentiation from fastapi-mcp

| Capability | fastapi-mcp | flask-apcore |
|-----------|-------------|--------------|
| Auto route discovery | Yes | Yes (Blueprint scanner) |
| Schema driven | Pydantic only | JSON Schema 2020-12 (cross-language) |
| ACL | No | Yes (module-to-module permissions) |
| Middleware pipeline | No (uses FastAPI's) | Yes (onion model, independent) |
| Distributed tracing | No | Yes (OpenTelemetry) |
| Inter-module calls | No | Yes |
| Multi-protocol output | MCP only | MCP + HTTP + CLI + code |
| Zero-code YAML binding | No | Yes |

## Technical Feasibility

### Confirmed Viable

- Flask `Response(stream_with_context())` supports SSE for Streamable HTTP
- Blueprint name + endpoint maps cleanly to apcore module IDs
- django-apcore provides a proven reference architecture (AppConfig → Flask Extension init_app)
- MCP Python SDK (409M downloads) provides solid foundation

### Key Challenges (Mitigated)

1. **WSGI vs ASGI:** Streamable HTTP works with WSGI; mcp-utils proves sync Flask MCP is viable
2. **Sparse type info:** Multi-backend schema strategy compensates for Flask's weaker typing
3. **Blueprint mapping:** `blueprint.name.endpoint` → apcore module ID is natural

## Competitive Window

- **Duration:** 6-12 months
- **Risk:** Someone builds a simple "flask-mcp" that captures mindshare before flask-apcore ships
- **Mitigation:** Ship Lite Mode (MCP) fast, differentiate on Full Mode (apcore governance)

## "What If We Don't Build This?"

- Flask's MCP gap will be filled by someone else (likely a pure MCP library without apcore depth)
- apcore loses the Flask ecosystem (~50% of Python web developers)
- The "apcore covers all major Python frameworks" narrative breaks
- fastapi-mcp's success model becomes unreplicable for apcore

## Next Step

**Proceed to PRD generation (`/prd`)** — define formal product requirements.
