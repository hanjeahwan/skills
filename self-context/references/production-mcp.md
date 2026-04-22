# Production MCP Operation

Use this reference when deploying `scripts/fastify_mcp_server.mjs` outside a private local desktop session.

## Runtime Boundary

Keep the private ledger outside the skill package. Mount or configure it through:

```bash
SELF_CONTEXT_HOME="<ledger-path>"
```

Production or non-loopback hosts require authentication:

```bash
NODE_ENV=production
MCP_AUTH_TOKEN="<strong-random-token>"
MCP_REQUIRE_AUTH=true
```

When binding beyond localhost, explicitly configure allowed hosts:

```bash
HOST="0.0.0.0"
MCP_ALLOWED_HOSTS="self-context.example.com,self-context.example.com:443"
MCP_ALLOWED_ORIGINS="https://chat.example.com"
```

For local Codex and Claude Code desktop usage, keep `HOST=127.0.0.1`.

## Performance

Warm the self-context cache before chat traffic:

```bash
MCP_WARM_CACHE_ON_START=true
```

or call MCP tool `warm_self_context_cache`.

The MCP default query path uses `scripts/query_engine.py`, backed by SQLite FTS, local embedding records, memory graph expansion, and answer-ready context packs. Dense embeddings and rerankers index `memory_atoms.jsonl`, `self_model.json`, and `context_packs.jsonl`, not raw Git patches.

Configure idle cache eviction:

```bash
MCP_CONTEXT_CACHE_TTL_MS=600000
MCP_CONTEXT_CACHE_SWEEP_INTERVAL_MS=60000
```

Set `MCP_CONTEXT_CACHE_TTL_MS=0` only for a dedicated process where permanently warm memory is acceptable.

## Health Endpoints

- `/live`: process liveness.
- `/ready`: `context_packs.jsonl`, `self_context.sqlite3`, embedding index readiness, and cache readiness when warm-on-start is enabled.
- `/health`: status.
- `/metrics`: request, failure, session, and cache counters.
- `/config`: redacted runtime config.

## Security Controls

- `MCP_AUTH_TOKEN`: bearer token for `/mcp`.
- `MCP_ALLOWED_HOSTS`: Host header allowlist.
- `MCP_ALLOWED_ORIGINS`: browser Origin allowlist.
- `MCP_DNS_REBINDING_PROTECTION`: defaults to `true`.
- `MCP_BODY_LIMIT`: request body limit in bytes.
- `MCP_MAX_SESSIONS`: active MCP session cap.
- `MCP_SESSION_TTL_MS`: idle session cleanup.
- `MCP_SESSION_SWEEP_INTERVAL_MS`: background interval that closes idle MCP sessions.
- `MCP_CONTEXT_CACHE_TTL_MS`: idle context cache eviction; default is 10 minutes.
- `MCP_CONTEXT_CACHE_SWEEP_INTERVAL_MS`: background interval that evicts expired self-context caches.

Clients authenticate with:

```text
Authorization: Bearer <MCP_AUTH_TOKEN>
```

## Validation

Run:

```bash
npm run check:mcp
npm run check:mcp:prod
python scripts/validate_ledger.py --ledger "<ledger-path>"
```

Before public deployment, verify `/config` redacts secrets and default `query_self_context` responses do not expose provenance or private source ids.
