import { timingSafeEqual } from "node:crypto";

const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "::1"]);
const DEFAULT_BODY_LIMIT = 1_048_576;
const DEFAULT_CONTEXT_CACHE_TTL_MS = 10 * 60_000;

function parseIntegerEnv(name, fallback) {
  const raw = process.env[name];
  if (!raw) return fallback;
  const value = Number.parseInt(raw, 10);
  if (!Number.isFinite(value) || value <= 0) {
    throw new Error(`${name} must be a positive integer`);
  }
  return value;
}

function parseNonNegativeIntegerEnv(name, fallback) {
  const raw = process.env[name];
  if (!raw) return fallback;
  const value = Number.parseInt(raw, 10);
  if (!Number.isFinite(value) || value < 0) {
    throw new Error(`${name} must be a non-negative integer`);
  }
  return value;
}

function parseBooleanEnv(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined || raw === "") return fallback;
  if (["1", "true", "yes", "on"].includes(raw.toLowerCase())) return true;
  if (["0", "false", "no", "off"].includes(raw.toLowerCase())) return false;
  throw new Error(`${name} must be boolean-like`);
}

function parseCsvEnv(name) {
  return (process.env[name] || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function isLoopbackHost(host) {
  return LOOPBACK_HOSTS.has(host);
}

function defaultAllowedHosts(host, port) {
  const values = new Set();
  if (isLoopbackHost(host)) {
    values.add(`${host}:${port}`);
    values.add(`127.0.0.1:${port}`);
    values.add(`localhost:${port}`);
    values.add(`[::1]:${port}`);
  }
  return [...values];
}

function redactConfig(config) {
  return {
    ...config,
    authToken: config.authToken ? "<configured>" : "",
  };
}

function envName(name) {
  return `MCP_${name}`;
}

export function loadServerConfig() {
  const host = process.env.HOST || process.env[envName("HOST")] || "127.0.0.1";
  const port = process.env.PORT ? parseIntegerEnv("PORT", 3333) : parseIntegerEnv(envName("PORT"), 3333);
  const nodeEnv = process.env.NODE_ENV || "development";
  const publicBind = !isLoopbackHost(host);
  const requireAuth = parseBooleanEnv(envName("REQUIRE_AUTH"), nodeEnv === "production" || publicBind);
  const authToken = process.env[envName("AUTH_TOKEN")] || "";
  const allowedHosts = parseCsvEnv(envName("ALLOWED_HOSTS"));
  const resolvedAllowedHosts = allowedHosts.length ? allowedHosts : defaultAllowedHosts(host, port);
  const allowedOrigins = parseCsvEnv(envName("ALLOWED_ORIGINS"));
  const sessionTtlMs = parseIntegerEnv(envName("SESSION_TTL_MS"), 30 * 60_000);
  const defaultSessionSweepIntervalMs = Math.min(60_000, Math.max(1_000, Math.floor(sessionTtlMs / 2)));

  if (publicBind && !allowedHosts.length) {
    throw new Error("MCP_ALLOWED_HOSTS must be set when binding to a non-loopback host");
  }
  if (requireAuth && !authToken) {
    throw new Error("MCP_AUTH_TOKEN must be set when MCP_REQUIRE_AUTH=true, NODE_ENV=production, or HOST is non-loopback");
  }

  return {
    host,
    port,
    nodeEnv,
    bodyLimit: parseIntegerEnv(envName("BODY_LIMIT"), DEFAULT_BODY_LIMIT),
    requestTimeout: parseIntegerEnv(envName("REQUEST_TIMEOUT_MS"), 120_000),
    connectionTimeout: parseIntegerEnv(envName("CONNECTION_TIMEOUT_MS"), 10_000),
    keepAliveTimeout: parseIntegerEnv(envName("KEEP_ALIVE_TIMEOUT_MS"), 72_000),
    maxSessions: parseIntegerEnv(envName("MAX_SESSIONS"), 64),
    sessionTtlMs,
    sessionSweepIntervalMs: parseIntegerEnv(envName("SESSION_SWEEP_INTERVAL_MS"), defaultSessionSweepIntervalMs),
    contextCacheTtlMs: parseNonNegativeIntegerEnv(envName("CONTEXT_CACHE_TTL_MS"), DEFAULT_CONTEXT_CACHE_TTL_MS),
    contextCacheSweepIntervalMs: parseIntegerEnv(envName("CONTEXT_CACHE_SWEEP_INTERVAL_MS"), 60_000),
    requireAuth,
    authToken,
    allowedHosts: resolvedAllowedHosts,
    allowedOrigins,
    enableDnsRebindingProtection: parseBooleanEnv(envName("DNS_REBINDING_PROTECTION"), true),
    warmCacheOnStart: parseBooleanEnv(envName("WARM_CACHE_ON_START"), nodeEnv === "production"),
    logLevel: process.env.LOG_LEVEL || process.env[envName("LOG_LEVEL")] || (nodeEnv === "production" ? "info" : "info"),
  };
}

export function buildLoggerOptions(config) {
  return {
    level: config.logLevel,
    redact: {
      paths: [
        "req.headers.authorization",
        "req.headers.cookie",
        "req.headers['x-api-key']",
        "req.headers['x-mcp-auth']",
        "headers.authorization",
        "headers.cookie",
        "headers['x-api-key']",
        "headers['x-mcp-auth']",
      ],
      censor: "<redacted>",
    },
  };
}

function safeCompare(left, right) {
  const leftBuffer = Buffer.from(left);
  const rightBuffer = Buffer.from(right);
  if (leftBuffer.length !== rightBuffer.length) return false;
  return timingSafeEqual(leftBuffer, rightBuffer);
}

function bearerToken(request) {
  const header = request.headers.authorization;
  if (typeof header === "string" && header.toLowerCase().startsWith("bearer ")) {
    return header.slice(7).trim();
  }
  const mcpHeader = request.headers["x-mcp-auth"];
  return typeof mcpHeader === "string" ? mcpHeader.trim() : "";
}

function isMcpPath(request) {
  return request.url === "/mcp" || request.url.startsWith("/mcp?");
}

function checkHost(request, config) {
  if (!config.enableDnsRebindingProtection || !config.allowedHosts.length) return true;
  const host = request.headers.host;
  return typeof host === "string" && config.allowedHosts.includes(host);
}

function checkOrigin(request, config) {
  const origin = request.headers.origin;
  if (!origin || !config.allowedOrigins.length) return true;
  return config.allowedOrigins.includes(origin);
}

function setCorsHeaders(reply, request, config) {
  const origin = request.headers.origin;
  if (origin && config.allowedOrigins.includes(origin)) {
    reply.header("access-control-allow-origin", origin);
    reply.header("vary", "origin");
  }
  reply.header("access-control-allow-methods", "GET, POST, DELETE, OPTIONS");
  reply.header("access-control-allow-headers", "content-type, authorization, mcp-session-id, mcp-protocol-version, x-mcp-auth");
  reply.header("access-control-expose-headers", "mcp-session-id, mcp-protocol-version");
}

export function createMetrics(config) {
  return {
    startedAt: new Date().toISOString(),
    requestsTotal: 0,
    mcpRequestsTotal: 0,
    authFailuresTotal: 0,
    hostFailuresTotal: 0,
    originFailuresTotal: 0,
    errorsTotal: 0,
    activeSessions: 0,
    maxSessions: config.maxSessions,
    sessionSweepsTotal: 0,
    sessionsPrunedTotal: 0,
    lastSessionPruneAt: "",
    contextCacheSweepsTotal: 0,
    contextCacheEvictionsTotal: 0,
    lastContextCacheEvictionAt: "",
    lastErrorAt: "",
  };
}

export function registerProductionHooks(app, config, metrics) {
  app.addHook("onRequest", async (request, reply) => {
    metrics.requestsTotal += 1;
    if (isMcpPath(request)) metrics.mcpRequestsTotal += 1;

    reply.header("x-content-type-options", "nosniff");
    reply.header("cache-control", "no-store");
    setCorsHeaders(reply, request, config);

    if (!checkHost(request, config)) {
      metrics.hostFailuresTotal += 1;
      return reply.code(403).send({ ok: false, error: "host_not_allowed" });
    }

    if (!checkOrigin(request, config)) {
      metrics.originFailuresTotal += 1;
      return reply.code(403).send({ ok: false, error: "origin_not_allowed" });
    }

    if (request.method === "OPTIONS") {
      return reply.code(204).send();
    }

    if (isMcpPath(request) && config.requireAuth && !safeCompare(bearerToken(request), config.authToken)) {
      metrics.authFailuresTotal += 1;
      reply.header("www-authenticate", "Bearer");
      return reply.code(401).send({ ok: false, error: "unauthorized" });
    }
  });

  app.addHook("onResponse", async (request, reply) => {
    request.log.info(
      {
        method: request.method,
        url: request.url,
        statusCode: reply.statusCode,
        responseTimeMs: Math.round(reply.elapsedTime),
      },
      "request completed",
    );
  });

  app.addHook("onError", async (_request, _reply, error) => {
    metrics.errorsTotal += 1;
    metrics.lastErrorAt = new Date().toISOString();
    app.log.error({ err: error }, "request error");
  });

  app.setErrorHandler((error, _request, reply) => {
    metrics.errorsTotal += 1;
    metrics.lastErrorAt = new Date().toISOString();
    reply.status(error.statusCode && error.statusCode >= 400 ? error.statusCode : 500).send({
      ok: false,
      error: "internal_error",
      message: error.message,
    });
  });
}

export function publicConfig(config) {
  return redactConfig(config);
}
