#!/usr/bin/env node

import assert from "node:assert/strict";

import { buildFastifyApp } from "./fastify_mcp_server.mjs";

const config = {
  host: "127.0.0.1",
  port: 3333,
  nodeEnv: "test",
  bodyLimit: 1_048_576,
  requestTimeout: 120_000,
  connectionTimeout: 10_000,
  keepAliveTimeout: 72_000,
  maxSessions: 4,
  sessionTtlMs: 60_000,
  sessionSweepIntervalMs: 30_000,
  contextCacheTtlMs: 10 * 60_000,
  contextCacheSweepIntervalMs: 60_000,
  requireAuth: true,
  authToken: "test-token",
  allowedHosts: ["127.0.0.1:3333", "localhost:3333"],
  allowedOrigins: ["http://127.0.0.1:5173"],
  enableDnsRebindingProtection: true,
  warmCacheOnStart: false,
  logLevel: "silent",
};

const app = buildFastifyApp({ config });

try {
  {
    const response = await app.inject({
      method: "GET",
      url: "/live",
      headers: { host: "127.0.0.1:3333" },
    });
    assert.equal(response.statusCode, 200);
    assert.equal(response.json().ok, true);
  }

  {
    const response = await app.inject({
      method: "GET",
      url: "/health",
      headers: { host: "127.0.0.1:3333" },
    });
    assert.equal(response.statusCode, 200);
    assert.equal(response.json().ok, true);
    assert.equal(typeof response.json().index.retrievalEvalReady, "boolean");
    assert.equal(typeof response.json().index.retrievalEvalStale, "boolean");
    assert.equal(typeof response.json().index.identityFactsReady, "boolean");
    assert.equal(typeof response.json().index.identityGraphReady, "boolean");
    assert.equal(typeof response.json().index.allSourceFamiliesRecognized, "boolean");
    assert.equal(typeof response.json().index.careerTimelineReady, "boolean");
    assert.equal(typeof response.json().index.experienceScopeReady, "boolean");
  }

  {
    const response = await app.inject({
      method: "GET",
      url: "/ready",
      headers: { host: "127.0.0.1:3333" },
    });
    assert.equal(response.statusCode, 200);
    assert.equal(typeof response.json().contextPacksReady, "boolean");
    assert.equal(typeof response.json().sqliteReady, "boolean");
    assert.equal(typeof response.json().embeddingsReady, "boolean");
    assert.equal(typeof response.json().identityFactsReady, "boolean");
    assert.equal(typeof response.json().identityGraphReady, "boolean");
    assert.equal(typeof response.json().allSourceFamiliesRecognized, "boolean");
    assert.equal(typeof response.json().careerTimelineReady, "boolean");
    assert.equal(typeof response.json().experienceScopeReady, "boolean");
    assert.equal(typeof response.json().voiceProfileReady, "boolean");
    assert.equal(typeof response.json().voiceStyleReady, "boolean");
    assert.equal(typeof response.json().agentOperatingContextReady, "boolean");
    assert.equal(typeof response.json().retrievalEvalReady, "boolean");
    assert.equal(typeof response.json().retrievalEvalStale, "boolean");
  }

  {
    const response = await app.inject({
      method: "POST",
      url: "/mcp",
      headers: {
        host: "127.0.0.1:3333",
        accept: "application/json, text/event-stream",
      },
      payload: { jsonrpc: "2.0", id: 1, method: "tools/list", params: {} },
    });
    assert.equal(response.statusCode, 401);
    assert.equal(response.json().error, "unauthorized");
  }

  {
    const response = await app.inject({
      method: "POST",
      url: "/mcp",
      headers: {
        host: "evil.example",
        authorization: "Bearer test-token",
        accept: "application/json, text/event-stream",
      },
      payload: { jsonrpc: "2.0", id: 1, method: "tools/list", params: {} },
    });
    assert.equal(response.statusCode, 403);
    assert.equal(response.json().error, "host_not_allowed");
  }

  {
    const response = await app.inject({
      method: "OPTIONS",
      url: "/mcp",
      headers: {
        host: "127.0.0.1:3333",
        origin: "http://127.0.0.1:5173",
      },
    });
    assert.equal(response.statusCode, 204);
    assert.equal(response.headers["access-control-allow-origin"], "http://127.0.0.1:5173");
  }

  {
    const response = await app.inject({
      method: "POST",
      url: "/mcp",
      headers: {
        host: "127.0.0.1:3333",
        authorization: "Bearer test-token",
        "mcp-session-id": "stale-session",
        accept: "application/json, text/event-stream",
      },
      payload: { jsonrpc: "2.0", id: 1, method: "tools/list", params: {} },
    });
    assert.equal(response.statusCode, 404);
    assert.equal(response.json().error.code, -32001);
  }

  {
    const response = await app.inject({
      method: "GET",
      url: "/metrics",
      headers: { host: "127.0.0.1:3333" },
    });
    assert.equal(response.statusCode, 200);
    assert.equal(typeof response.json().requestsTotal, "number");
  }

  {
    const initialize = await app.inject({
      method: "POST",
      url: "/mcp",
      headers: {
        host: "127.0.0.1:3333",
        authorization: "Bearer test-token",
        accept: "application/json, text/event-stream",
      },
      payload: {
        jsonrpc: "2.0",
        id: 2,
        method: "initialize",
        params: {
          protocolVersion: "2025-06-18",
          capabilities: {},
          clientInfo: { name: "production-check", version: "0.0.0" },
        },
      },
    });
    assert.equal(initialize.statusCode, 200);
    const sessionId = initialize.headers["mcp-session-id"];
    assert.equal(typeof sessionId, "string");

    const tools = await app.inject({
      method: "POST",
      url: "/mcp",
      headers: {
        host: "127.0.0.1:3333",
        authorization: "Bearer test-token",
        "mcp-session-id": sessionId,
        accept: "application/json, text/event-stream",
      },
      payload: { jsonrpc: "2.0", id: 3, method: "tools/list", params: {} },
    });
    assert.equal(tools.statusCode, 200);
    const toolNames = tools.json().result.tools.map((tool) => tool.name);
    assert.ok(toolNames.includes("query_self_context"));
    assert.ok(toolNames.includes("get_self_context_status"));
    assert.ok(toolNames.includes("get_agent_operating_context"));
    assert.ok(toolNames.includes("rebuild_self_context"));
    assert.ok(toolNames.includes("import_private_material"));
    assert.equal(toolNames.includes("query_evidence_rag"), false);
    assert.equal(toolNames.includes("query_career_rag"), false);
  }

  console.log("production MCP smoke checks passed");
} finally {
  await app.close();
}
