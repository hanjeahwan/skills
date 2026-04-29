#!/usr/bin/env node

import assert from "node:assert/strict";
import { setTimeout as sleep } from "node:timers/promises";

import { buildFastifyApp } from "./fastify_mcp_server.mjs";

const config = {
  host: "127.0.0.1",
  port: 3333,
  nodeEnv: "test",
  bodyLimit: 1_048_576,
  requestTimeout: 120_000,
  connectionTimeout: 10_000,
  keepAliveTimeout: 72_000,
  maxSessions: 2,
  sessionTtlMs: 50,
  sessionSweepIntervalMs: 10,
  contextCacheTtlMs: 0,
  contextCacheSweepIntervalMs: 60_000,
  requireAuth: false,
  authToken: "",
  allowedHosts: ["127.0.0.1:3333", "localhost:3333"],
  allowedOrigins: [],
  enableDnsRebindingProtection: true,
  warmCacheOnStart: false,
  logLevel: "silent",
};

const app = buildFastifyApp({ config });

async function metrics() {
  const response = await app.inject({
    method: "GET",
    url: "/metrics",
    headers: { host: "127.0.0.1:3333" },
  });
  assert.equal(response.statusCode, 200);
  return response.json();
}

async function initializeSession() {
  const response = await app.inject({
    method: "POST",
    url: "/mcp",
    headers: {
      host: "127.0.0.1:3333",
      accept: "application/json, text/event-stream",
    },
    payload: {
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2025-06-18",
        capabilities: {},
        clientInfo: { name: "session-retention-repro", version: "0.0.0" },
      },
    },
  });

  assert.equal(response.statusCode, 200);
  assert.ok(response.headers["mcp-session-id"], "initialize response must include mcp-session-id");
}

try {
  await initializeSession();
  const afterInitialize = await metrics();
  assert.equal(afterInitialize.activeSessions, 1);

  await sleep(config.sessionTtlMs + 100);
  const afterTtl = await metrics();

  await initializeSession();
  await initializeSession();
  await initializeSession();
  const afterCapacityPressure = await metrics();

  console.log(
    JSON.stringify(
      {
        sessionTtlMs: config.sessionTtlMs,
        activeSessionsAfterInitialize: afterInitialize.activeSessions,
        activeSessionsAfterTtlWithoutMcpTraffic: afterTtl.activeSessions,
        activeSessionsAfterCapacityPressure: afterCapacityPressure.activeSessions,
      },
      null,
      2,
    ),
  );

  assert.equal(
    afterTtl.activeSessions,
    0,
    "expired MCP sessions should be reclaimed without requiring another /mcp request",
  );
  assert.equal(
    afterCapacityPressure.activeSessions,
    config.maxSessions,
    "inactive MCP sessions should be evicted instead of rejecting a new initialize request when capacity is full",
  );
} finally {
  await app.close();
}
