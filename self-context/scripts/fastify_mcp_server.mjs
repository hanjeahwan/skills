#!/usr/bin/env node

import { spawn } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import { existsSync, readFileSync, statSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import Fastify from "fastify";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";
import * as z from "zod/v4";

import {
  evictExpiredSelfContextCaches,
  getSelfContextCacheStatus,
  invalidateSelfContextCache,
  querySelfContextFast,
  warmSelfContextCache,
} from "./self_context_query_cache.mjs";
import {
  buildLoggerOptions,
  createMetrics,
  loadServerConfig,
  publicConfig,
  registerProductionHooks,
} from "./mcp_production.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SKILL_ROOT = path.resolve(__dirname, "..");
const DEFAULT_LEDGER = path.join(homedir(), ".self-context", "ledger");
const PYTHON = process.env.PYTHON || "python";
const UV = process.env.UV || "uv";

function resolveLedgerPath(value) {
  const configured = value || process.env.SELF_CONTEXT_HOME;
  if (configured) return path.resolve(configured);
  return path.resolve(DEFAULT_LEDGER);
}

function scriptPath(name) {
  return path.join(SKILL_ROOT, "scripts", name);
}

function textResult(text, structuredContent = undefined, isError = false) {
  return {
    content: [{ type: "text", text }],
    ...(structuredContent === undefined ? {} : { structuredContent }),
    ...(isError ? { isError: true } : {}),
  };
}

function runProcess(command, args, options = {}) {
  const timeoutMs = options.timeoutMs ?? 120_000;
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      cwd: SKILL_ROOT,
      shell: false,
      env: {
        ...process.env,
        PYTHONIOENCODING: "utf-8",
      },
    });

    let stdout = "";
    let stderr = "";
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGTERM");
    }, timeoutMs);

    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    child.on("error", (error) => {
      clearTimeout(timer);
      resolve({ code: -1, stdout, stderr: `${stderr}${error.message}`, timedOut });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code: code ?? 0, stdout, stderr, timedOut });
    });
  });
}

async function runPythonScript(name, args, options = {}) {
  return runProcess(PYTHON, [scriptPath(name), ...args], options);
}

async function runUvPythonScript(name, args, options = {}) {
  return runProcess(UV, ["run", "--with", "sentence-transformers", "python", scriptPath(name), ...args], options);
}

function jsonlCount(filePath) {
  if (!existsSync(filePath)) return 0;
  return statSync(filePath).size === 0
    ? 0
    : readFileSync(filePath, "utf8").split(/\r?\n/).filter((line) => line.trim()).length;
}

async function readJsonIfExists(filePath) {
  if (!existsSync(filePath)) return null;
  return JSON.parse(await readFile(filePath, "utf8"));
}

function sha256File(filePath) {
  if (!existsSync(filePath)) return "";
  return createHash("sha256").update(readFileSync(filePath)).digest("hex");
}

async function retrievalEvalStatus(ledgerPath) {
  const derivedDir = path.join(ledgerPath, "derived");
  const evalPath = path.join(derivedDir, "retrieval_eval.json");
  const sqliteManifest = await readJsonIfExists(path.join(derivedDir, "self_context_index_manifest.json"));
  const embeddingManifest = await readJsonIfExists(path.join(derivedDir, "memory_embeddings_manifest.json"));
  const report = await readJsonIfExists(evalPath);
  const currentInputFingerprints = {
    context_packs_sha256: sha256File(path.join(derivedDir, "context_packs.jsonl")),
    sqlite_manifest_fingerprint: String(sqliteManifest?.fingerprint || ""),
    embedding_manifest_fingerprint: String(embeddingManifest?.fingerprint || ""),
  };
  const reportInputFingerprints =
    report && typeof report.input_fingerprints === "object" && report.input_fingerprints
      ? report.input_fingerprints
      : {};
  const stale =
    !report ||
    reportInputFingerprints.context_packs_sha256 !== currentInputFingerprints.context_packs_sha256 ||
    reportInputFingerprints.sqlite_manifest_fingerprint !== currentInputFingerprints.sqlite_manifest_fingerprint ||
    reportInputFingerprints.embedding_manifest_fingerprint !== currentInputFingerprints.embedding_manifest_fingerprint;
  return {
    path: evalPath,
    report,
    summary: report?.summary ?? null,
    ready: report?.passes === true && !stale,
    stale,
    inputFingerprints: currentInputFingerprints,
  };
}

function parseJsonOutput(result) {
  if (result.code !== 0) {
    return {
      ok: false,
      text: result.stderr || result.stdout || `Process failed with code ${result.code}`,
      data: null,
    };
  }
  try {
    return { ok: true, text: result.stdout, data: JSON.parse(result.stdout) };
  } catch (error) {
    const firstBrace = result.stdout.indexOf("{");
    const lastBrace = result.stdout.lastIndexOf("}");
    if (firstBrace >= 0 && lastBrace > firstBrace) {
      try {
        const jsonText = result.stdout.slice(firstBrace, lastBrace + 1);
        return { ok: true, text: result.stdout, data: JSON.parse(jsonText) };
      } catch {
        // Fall through to the original parse error below.
      }
    }
    return {
      ok: false,
      text: `Command succeeded but stdout was not JSON: ${error instanceof Error ? error.message : String(error)}\n\n${result.stdout}`,
      data: null,
    };
  }
}

async function selfContextStatus(ledgerPath) {
  const sourcesDir = path.join(ledgerPath, "sources");
  const derivedDir = path.join(ledgerPath, "derived");
  const sourceFiles = [
    "git.jsonl",
    "github_pr_activity.jsonl",
    "github_pr_reviews.jsonl",
    "github_authority_signals.jsonl",
    "jira.jsonl",
    "jira_comments.jsonl",
    "jira_changelog.jsonl",
    "manual.jsonl",
    "code_style.jsonl",
    "career_facts.jsonl",
    "release_activity.jsonl",
    "jira_leadership_signals.jsonl",
    "architecture_material.jsonl",
    "agent_sessions.jsonl",
    "portfolio_cases.jsonl",
    "personal_material.jsonl",
  ];
  const sourceCounts = Object.fromEntries(
    sourceFiles.map((file) => [file, jsonlCount(path.join(sourcesDir, file))]),
  );
  const contextManifest = await readJsonIfExists(path.join(derivedDir, "context_packs_manifest.json"));
  const embeddingManifest = await readJsonIfExists(path.join(derivedDir, "memory_embeddings_manifest.json"));
  const sqliteManifest = await readJsonIfExists(path.join(derivedDir, "self_context_index_manifest.json"));
  const distillationEval = await readJsonIfExists(path.join(derivedDir, "distillation_eval.json"));
  const personaEval = await readJsonIfExists(path.join(derivedDir, "persona_synthesis_eval.json"));
  const identityFacts = await readJsonIfExists(path.join(derivedDir, "identity_facts.json"));
  const identityGraph = await readJsonIfExists(path.join(derivedDir, "identity_graph.json"));
  const voiceProfile = await readJsonIfExists(path.join(derivedDir, "voice_profile.json"));
  const voiceStyleEval = await readJsonIfExists(path.join(derivedDir, "voice_style_eval.json"));
  const agentOperatingContext = await readJsonIfExists(path.join(derivedDir, "agent_operating_context.json"));
  const retrievalEval = await retrievalEvalStatus(ledgerPath);
  const selfModel = await readJsonIfExists(path.join(derivedDir, "self_model.json"));
  const sourceClusterCount = jsonlCount(path.join(derivedDir, "source_clusters.jsonl"));
  const distillationCandidateCount = jsonlCount(path.join(derivedDir, "distillation_candidates.jsonl"));
  const memoryAtomCount = jsonlCount(path.join(derivedDir, "memory_atoms.jsonl"));
  const provenanceCount = jsonlCount(path.join(derivedDir, "provenance_links.jsonl"));
  const sectionCount = Array.isArray(selfModel?.sections) ? selfModel.sections.length : 0;
  const sourceTotal = Object.values(sourceCounts).reduce((sum, count) => sum + count, 0);
  const sourceToMemoryCoverage = sourceTotal > 0 ? Number((provenanceCount / sourceTotal).toFixed(3)) : 0;
  const sourceFamilyCoverage = identityFacts?.source_family_coverage ?? {};
  const expectedSourceFamilies = [
    "career_facts",
    "github_pr_activity",
    "github_authority_signals",
    "release_activity",
    "jira_leadership_signals",
    "architecture_material",
    "agent_sessions",
    "portfolio_cases",
    "personal_material",
  ];
  const allSourceFamiliesRecognized = expectedSourceFamilies.every((family) => Boolean(sourceFamilyCoverage?.[family]));
  return {
    ledgerPath,
    sourceCounts,
    sourceTotal,
    sourceToMemoryCoverage,
    sourceFamilyCoverage,
    allSourceFamiliesRecognized,
    expectedSourceFamilies,
    distillation: distillationEval,
    personaSynthesis: personaEval,
    identityFacts,
    identityGraph,
    voiceProfile,
    voiceStyle: voiceStyleEval,
    agentOperatingContext,
    retrievalEval: retrievalEval.report,
    selfModel,
    contextPacks: contextManifest,
    sqliteIndex: sqliteManifest,
    memoryEmbeddings: embeddingManifest,
    selfContextCache: getSelfContextCacheStatus(ledgerPath),
    files: {
      memoryAtoms: existsSync(path.join(derivedDir, "memory_atoms.jsonl")),
      sourceClusters: existsSync(path.join(derivedDir, "source_clusters.jsonl")),
      distillationCandidates: existsSync(path.join(derivedDir, "distillation_candidates.jsonl")),
      distillationEval: existsSync(path.join(derivedDir, "distillation_eval.json")),
      personaSynthesisEval: existsSync(path.join(derivedDir, "persona_synthesis_eval.json")),
      identityFacts: existsSync(path.join(derivedDir, "identity_facts.json")),
      identityGraph: existsSync(path.join(derivedDir, "identity_graph.json")),
      voiceProfile: existsSync(path.join(derivedDir, "voice_profile.json")),
      voiceStyleEval: existsSync(path.join(derivedDir, "voice_style_eval.json")),
      agentOperatingContext: existsSync(path.join(derivedDir, "agent_operating_context.json")),
      retrievalEval: existsSync(path.join(derivedDir, "retrieval_eval.json")),
      selfModel: existsSync(path.join(derivedDir, "self_model.json")),
      contextPacks: existsSync(path.join(derivedDir, "context_packs.jsonl")),
      provenanceLinks: existsSync(path.join(derivedDir, "provenance_links.jsonl")),
      memoryGraphEdges: existsSync(path.join(derivedDir, "memory_graph_edges.jsonl")),
      sqliteIndex: existsSync(path.join(derivedDir, "self_context.sqlite3")),
      memoryEmbeddings: existsSync(path.join(derivedDir, "memory_embeddings.npz")),
    },
    counts: {
      sourceClusters: sourceClusterCount,
      distillationCandidates: distillationCandidateCount,
      memoryAtoms: memoryAtomCount,
      retainedMemoryAtoms: personaEval?.retainedMemoryAtoms ?? memoryAtomCount,
      provenanceLinks: provenanceCount,
      contextPacks: contextManifest?.context_packs ?? 0,
      memoryGraphEdges: contextManifest?.memory_graph_edges ?? 0,
      personaSections: sectionCount,
      identityGraphNodes: Array.isArray(identityGraph?.nodes) ? identityGraph.nodes.length : 0,
      identityGraphEdges: Array.isArray(identityGraph?.edges) ? identityGraph.edges.length : 0,
    },
    legacyAtomsPruned: personaEval?.legacyAtomsPruned === true,
    personaSynthesisReady: personaEval?.personaSynthesisReady === true,
    identityFactsReady:
      identityFacts?.architecture === "self-context-v2.8" &&
      Boolean(identityFacts?.career_timeline?.engineering_activity_start) &&
      Boolean(identityFacts?.experience_scope?.primary_scope) &&
      allSourceFamiliesRecognized,
    identityGraphReady:
      identityGraph?.architecture === "self-context-v2.8" &&
      Array.isArray(identityGraph?.nodes) &&
      identityGraph.nodes.length >= 7 &&
      Array.isArray(identityGraph?.edges) &&
      identityGraph.edges.length >= 5,
    identityFactsPath: path.join(derivedDir, "identity_facts.json"),
    identityGraphPath: path.join(derivedDir, "identity_graph.json"),
    careerTimelineReady: Array.isArray(selfModel?.sections)
      ? selfModel.sections.some((section) => section?.id === "self_model:career_timeline")
      : false,
    experienceScopeReady: Array.isArray(selfModel?.sections)
      ? selfModel.sections.some((section) => section?.id === "self_model:experience_scope")
      : false,
    voiceProfileReady: voiceStyleEval?.voiceProfileReady === true && existsSync(path.join(derivedDir, "voice_profile.json")),
    voiceStyleReady: voiceStyleEval?.voiceStyleReady === true && existsSync(path.join(derivedDir, "voice_style_eval.json")),
    agentOperatingContextReady: personaEval?.agentOperatingContextReady === true && existsSync(path.join(derivedDir, "agent_operating_context.json")),
    agentOperatingContextPath: path.join(derivedDir, "agent_operating_context.json"),
    retrievalEvalReady: retrievalEval.ready,
    retrievalEvalPath: retrievalEval.path,
    retrievalEvalSummary: retrievalEval.summary,
    retrievalEvalStale: retrievalEval.stale,
  };
}

async function rebuildSelfContext(resolvedLedger) {
  const memory = await runPythonScript("build_memory_atoms.py", ["--ledger", resolvedLedger, "--json"], {
    timeoutMs: 300_000,
  });
  const parsedMemory = parseJsonOutput(memory);
  if (!parsedMemory.ok) {
    return {
      ok: false,
      text: parsedMemory.text,
      structured: { memory: { code: memory.code, stdout: memory.stdout, stderr: memory.stderr } },
    };
  }

  const contexts = await runPythonScript("build_context_packs.py", ["--ledger", resolvedLedger, "--json"], {
    timeoutMs: 300_000,
  });
  const parsedContexts = parseJsonOutput(contexts);
  if (!parsedContexts.ok) {
    return {
      ok: false,
      text: parsedContexts.text,
      structured: {
        memory: parsedMemory.data,
        contexts: { code: contexts.code, stdout: contexts.stdout, stderr: contexts.stderr },
      },
    };
  }

  const sqlite = await runPythonScript("build_sqlite_index.py", ["--ledger", resolvedLedger, "--json"], {
    timeoutMs: 300_000,
  });
  const parsedSqlite = parseJsonOutput(sqlite);
  if (!parsedSqlite.ok) {
    return {
      ok: false,
      text: parsedSqlite.text,
      structured: {
        memory: parsedMemory.data,
        contexts: parsedContexts.data,
        sqlite: { code: sqlite.code, stdout: sqlite.stdout, stderr: sqlite.stderr },
      },
    };
  }

  const embeddings = await runUvPythonScript("build_memory_index.py", ["--ledger", resolvedLedger, "--json"], {
    timeoutMs: 600_000,
  });
  const parsedEmbeddings = parseJsonOutput(embeddings);
  if (!parsedEmbeddings.ok) {
    return {
      ok: false,
      text: parsedEmbeddings.text,
      structured: {
        memory: parsedMemory.data,
        contexts: parsedContexts.data,
        sqlite: parsedSqlite.data,
        embeddings: { code: embeddings.code, stdout: embeddings.stdout, stderr: embeddings.stderr },
      },
    };
  }

  const retrievalEval = await runPythonScript(
    "run_retrieval_benchmarks.py",
    ["--ledger", resolvedLedger, "--suite", "real", "--write-report", "--json"],
    { timeoutMs: 300_000 },
  );
  const parsedRetrievalEval = parseJsonOutput(retrievalEval);
  if (!parsedRetrievalEval.ok) {
    return {
      ok: false,
      text: parsedRetrievalEval.text,
      structured: {
        memory: parsedMemory.data,
        contexts: parsedContexts.data,
        sqlite: parsedSqlite.data,
        embeddings: parsedEmbeddings.data,
        retrievalEval: { code: retrievalEval.code, stdout: retrievalEval.stdout, stderr: retrievalEval.stderr },
      },
    };
  }

  const validation = await runPythonScript("validate_ledger.py", ["--ledger", resolvedLedger], {
    timeoutMs: 120_000,
  });
  if (validation.code !== 0) {
    return {
      ok: false,
      text: validation.stderr || validation.stdout || `Validation failed with code ${validation.code}`,
      structured: {
        memory: parsedMemory.data,
        contexts: parsedContexts.data,
        sqlite: parsedSqlite.data,
        embeddings: parsedEmbeddings.data,
        retrievalEval: parsedRetrievalEval.data,
        validation: { code: validation.code, stdout: validation.stdout, stderr: validation.stderr },
      },
    };
  }

  invalidateSelfContextCache(resolvedLedger);
  return {
    ok: true,
    text: JSON.stringify(
      {
        memory: parsedMemory.data,
        contexts: parsedContexts.data,
        sqlite: parsedSqlite.data,
        embeddings: parsedEmbeddings.data,
        retrievalEval: parsedRetrievalEval.data,
        validation: validation.stdout.trim(),
      },
      null,
      2,
    ),
    structured: {
      memory: parsedMemory.data,
      contexts: parsedContexts.data,
      sqlite: parsedSqlite.data,
      embeddings: parsedEmbeddings.data,
      retrievalEval: parsedRetrievalEval.data,
      validation: validation.stdout.trim(),
    },
  };
}

async function getAgentOperatingContextPayload(resolvedLedger, includeProvenance = false) {
  const agentPath = path.join(resolvedLedger, "derived", "agent_operating_context.json");
  const agentOperatingContext = await readJsonIfExists(agentPath);
  if (!agentOperatingContext) {
    return {
      ok: false,
      text: `Missing agent operating context: ${agentPath}. Run rebuild_self_context first.`,
      structured: { ledgerPath: resolvedLedger, agentOperatingContextPath: agentPath },
    };
  }

  const structured = { ...agentOperatingContext };
  if (includeProvenance) {
    const proofResult = await runPythonScript(
      "query_engine.py",
      [
        "--ledger",
        resolvedLedger,
        "--query",
        "what should an agent know before acting as Hanje",
        "--intent",
        "act_as_me",
        "--top",
        "1",
        "--include-provenance",
        "--json",
      ],
      { timeoutMs: 30_000 },
    );
    const parsed = parseJsonOutput(proofResult);
    if (parsed.ok) {
      structured.provenance = parsed.data?.provenance || [];
    } else {
      structured.provenance_error = parsed.text;
    }
  }

  return {
    ok: true,
    text: JSON.stringify(structured, null, 2),
    structured,
  };
}

function registerSelfContextTools(server) {
  const querySelfContextInputSchema = z.object({
    query: z.string().min(1).describe("Question about the user or context needed to act with the user's preferences and memory."),
    ledgerPath: z.string().optional(),
    intent: z
      .enum([
        "self_knowledge",
        "act_as_me",
        "coding_style",
        "preference",
        "work_context",
        "personal_context",
        "project_context",
        "relationship_context",
        "proof",
        "gap",
      ])
      .optional(),
    top: z.number().int().min(1).max(20).default(5),
    includeProvenance: z.boolean().default(false).describe("Only set true for proof, audit, debug, or refresh questions."),
    minScore: z.number().min(0).default(0),
    rerank: z.boolean().default(false).describe("Try local CrossEncoder reranking. Slower; useful for deep/manual queries."),
  });
  const agentOperatingContextInputSchema = z.object({
    ledgerPath: z.string().optional().describe("Self-context ledger path. Defaults to the user profile ledger."),
    includeProvenance: z.boolean().default(false).describe("Only set true when the caller explicitly needs proof or audit trace."),
  });

  const importPrivateMaterialInputSchema = z.object({
    ledgerPath: z.string().optional(),
    date: z.string().optional(),
    title: z.string().min(1),
    context: z.string().optional(),
    problem: z.string().optional(),
    action: z.string().min(1),
    result: z.string().optional(),
    technologies: z.string().optional(),
    impact: z.string().optional(),
    links: z.string().optional(),
    notes: z.string().optional(),
  });

  server.registerTool(
    "get_self_context_status",
    {
      title: "Get Self Context Status",
      description: "Read source counts, self model, context pack manifest, and memory index status.",
      inputSchema: z.object({
        ledgerPath: z.string().optional().describe("Self-context ledger path. Defaults to the user profile ledger."),
      }),
      annotations: { readOnlyHint: true, idempotentHint: true },
    },
    async ({ ledgerPath }) => {
      const resolvedLedger = resolveLedgerPath(ledgerPath);
      const status = await selfContextStatus(resolvedLedger);
      return textResult(JSON.stringify(status, null, 2), status);
    },
  );

  server.registerTool(
    "get_agent_operating_context",
    {
      title: "Get Agent Operating Context",
      description: "Return the build-time operating contract an external agent should load before acting as the user.",
      inputSchema: agentOperatingContextInputSchema,
      annotations: { readOnlyHint: true, idempotentHint: true },
    },
    async ({ ledgerPath, includeProvenance }) => {
      const resolvedLedger = resolveLedgerPath(ledgerPath);
      const result = await getAgentOperatingContextPayload(resolvedLedger, includeProvenance);
      return textResult(result.text, result.structured, !result.ok);
    },
  );

  server.registerTool(
    "query_self_context",
    {
      title: "Query Self Context",
      description: "Retrieve useful personal clone context. Provenance stays hidden unless explicitly requested.",
      inputSchema: querySelfContextInputSchema,
      annotations: { readOnlyHint: true, idempotentHint: true },
    },
    async (input) => {
      const resolvedLedger = resolveLedgerPath(input.ledgerPath);
      const args = [
        "--ledger",
        resolvedLedger,
        "--query",
        input.query,
        "--top",
        String(input.top),
        "--min-score",
        String(input.minScore),
        "--json",
      ];
      if (input.intent) args.push("--intent", input.intent);
      if (input.includeProvenance) args.push("--include-provenance");
      if (input.rerank) args.push("--rerank");
      const queryResult = await runPythonScript("query_engine.py", args, { timeoutMs: input.rerank ? 120_000 : 30_000 });
      const parsed = parseJsonOutput(queryResult);
      if (parsed.ok) {
        return textResult(JSON.stringify(parsed.data, null, 2), parsed.data);
      }
      try {
        const result = await querySelfContextFast({ ...input, ledgerPath: resolvedLedger });
        result.meta = { ...result.meta, fallbackReason: parsed.text };
        return textResult(JSON.stringify(result, null, 2), result);
      } catch (error) {
        return textResult(
          `Self-context query failed: ${parsed.text}\nFallback failed: ${error instanceof Error ? error.message : String(error)}`,
          { error: parsed.text, fallbackError: error instanceof Error ? error.message : String(error) },
          true,
        );
      }
    },
  );

  server.registerTool(
    "warm_self_context_cache",
    {
      title: "Warm Self Context Cache",
      description: "Preload derived/context_packs.jsonl into MCP memory for low-latency self-context queries.",
      inputSchema: z.object({
        ledgerPath: z.string().optional(),
        forceReload: z.boolean().default(false),
      }),
      annotations: { readOnlyHint: true, idempotentHint: true },
    },
    async ({ ledgerPath, forceReload }) => {
      const resolvedLedger = resolveLedgerPath(ledgerPath);
      const status = await warmSelfContextCache(resolvedLedger, { forceReload });
      return textResult(JSON.stringify(status, null, 2), status);
    },
  );

  server.registerTool(
    "rebuild_self_context",
    {
      title: "Rebuild Self Context",
      description: "Regenerate memory atoms, self model, and context packs from private source material.",
      inputSchema: z.object({
        ledgerPath: z.string().optional(),
      }),
    },
    async ({ ledgerPath }) => {
      const resolvedLedger = resolveLedgerPath(ledgerPath);
      const result = await rebuildSelfContext(resolvedLedger);
      return textResult(result.text, result.structured, !result.ok);
    },
  );

  async function importPrivateMaterialHandler(input) {
    const resolvedLedger = resolveLedgerPath(input.ledgerPath);
    const args = ["--ledger", resolvedLedger, "--title", input.title, "--action", input.action];
    for (const [key, value] of Object.entries(input)) {
      if (!value || ["ledgerPath", "title", "action"].includes(key)) continue;
      args.push(`--${key}`, String(value));
    }
    const result = await runPythonScript("import_manual_event.py", args, { timeoutMs: 120_000 });
    if (result.code !== 0) {
      return textResult(result.stdout + (result.stderr ? `\nSTDERR:\n${result.stderr}` : ""), { code: result.code }, true);
    }
    const rebuild = await rebuildSelfContext(resolvedLedger);
    return textResult(
      `${result.stdout}\n\nSelf-context rebuild:\n${rebuild.text}`,
      { import: { code: result.code }, rebuild: rebuild.structured },
      !rebuild.ok,
    );
  }

  server.registerTool(
    "import_private_material",
    {
      title: "Import Private Material",
      description: "Append user-provided private material to sources/manual.jsonl and refresh self-context.",
      inputSchema: importPrivateMaterialInputSchema,
    },
    importPrivateMaterialHandler,
  );

  server.registerTool(
    "scan_code_style_from_repo",
    {
      title: "Scan Code Style From Repository",
      description: "Scan a local repository for coding patterns, then refresh self-context memory.",
      inputSchema: z.object({
        repoPath: z.string().min(1).describe("Local repository path to scan."),
        ledgerPath: z.string().optional(),
        author: z.string().optional().describe("Optional git author filter used to boost user-authored examples."),
        maxFiles: z.number().int().min(1).max(120).default(36),
        maxExampleChars: z.number().int().min(1000).max(20000).default(7000),
        rebuildContext: z.boolean().default(true).describe("Regenerate self-context after scanning."),
      }),
    },
    async (input) => {
      const resolvedLedger = resolveLedgerPath(input.ledgerPath);
      const args = [
        "--ledger",
        resolvedLedger,
        "--repo",
        path.resolve(input.repoPath),
        "--max-files",
        String(input.maxFiles),
        "--max-example-chars",
        String(input.maxExampleChars),
        "--json",
      ];
      if (input.author) args.push("--author", input.author);
      const scanResult = await runPythonScript("scan_code_style.py", args, { timeoutMs: 300_000 });
      const parsed = parseJsonOutput(scanResult);
      if (!parsed.ok) return textResult(parsed.text, { stderr: scanResult.stderr, stdout: scanResult.stdout }, true);

      const structured = { scan: parsed.data };
      let text = JSON.stringify(parsed.data, null, 2);
      if (input.rebuildContext) {
        const rebuild = await rebuildSelfContext(resolvedLedger);
        structured.rebuild = rebuild.structured;
        text += `\n\nSelf-context rebuild:\n${rebuild.text}`;
        if (!rebuild.ok) return textResult(text, structured, true);
      }
      return textResult(text, structured);
    },
  );

  server.registerTool(
    "analyze_github_commit_code_patterns",
    {
      title: "Analyze GitHub Commit Code Patterns",
      description: "Analyze GitHub commit patch evidence into coding memories, then refresh self-context.",
      inputSchema: z.object({
        ledgerPath: z.string().optional(),
        repo: z.array(z.string()).optional().describe("Optional owner/repo filters. Omit to analyze all repositories in sources/git.jsonl."),
        maxExamplesPerRepo: z.number().int().min(1).max(50).default(12),
        rebuildContext: z.boolean().default(true).describe("Regenerate self-context after analysis."),
      }),
    },
    async (input) => {
      const resolvedLedger = resolveLedgerPath(input.ledgerPath);
      const args = ["--ledger", resolvedLedger, "--max-examples-per-repo", String(input.maxExamplesPerRepo), "--json"];
      for (const repo of input.repo || []) args.push("--repo", repo);
      const analysisResult = await runPythonScript("analyze_github_commit_patterns.py", args, { timeoutMs: 300_000 });
      const parsed = parseJsonOutput(analysisResult);
      if (!parsed.ok) return textResult(parsed.text, { stderr: analysisResult.stderr, stdout: analysisResult.stdout }, true);

      const structured = { analysis: parsed.data };
      let text = JSON.stringify(parsed.data, null, 2);
      if (input.rebuildContext) {
        const rebuild = await rebuildSelfContext(resolvedLedger);
        structured.rebuild = rebuild.structured;
        text += `\n\nSelf-context rebuild:\n${rebuild.text}`;
        if (!rebuild.ok) return textResult(text, structured, true);
      }
      return textResult(text, structured);
    },
  );
}

function createSelfContextMcpServer() {
  const server = new McpServer({ name: "self-context", version: "0.2.0" });
  registerSelfContextTools(server);
  return server;
}

export function buildFastifyApp(options = {}) {
  const config = options.config || loadServerConfig();
  const metrics = createMetrics(config);
  const app = Fastify({
    logger: buildLoggerOptions(config),
    bodyLimit: config.bodyLimit,
    requestTimeout: config.requestTimeout,
    connectionTimeout: config.connectionTimeout,
    keepAliveTimeout: config.keepAliveTimeout,
    disableRequestLogging: true,
  });
  const sessions = new Map();
  let sessionSweepRunning = false;

  registerProductionHooks(app, config, metrics);

  function refreshSessionMetrics() {
    metrics.activeSessions = sessions.size;
  }

  async function closeSession(sessionId, session) {
    sessions.delete(sessionId);
    refreshSessionMetrics();
    try {
      await session.server.close();
    } catch (error) {
      app.log.warn({ err: error, sessionId }, "failed to close MCP session server");
    }
    try {
      await session.transport.close?.();
    } catch (error) {
      app.log.warn({ err: error, sessionId }, "failed to close MCP session transport");
    }
  }

  async function pruneExpiredSessions() {
    const now = Date.now();
    const expired = [...sessions.entries()].filter(([, session]) => now - session.lastSeenAt > config.sessionTtlMs);
    await Promise.all(expired.map(([sessionId, session]) => closeSession(sessionId, session)));
    return expired.length;
  }

  async function runSessionSweep() {
    if (sessionSweepRunning) return;
    sessionSweepRunning = true;
    try {
      const pruned = await pruneExpiredSessions();
      metrics.sessionSweepsTotal += 1;
      if (pruned > 0) {
        metrics.sessionsPrunedTotal += pruned;
        metrics.lastSessionPruneAt = new Date().toISOString();
      }
    } catch (error) {
      metrics.errorsTotal += 1;
      metrics.lastErrorAt = new Date().toISOString();
      app.log.error({ err: error }, "session sweep failed");
    } finally {
      sessionSweepRunning = false;
    }
  }

  function runContextCacheSweep() {
    try {
      const result = evictExpiredSelfContextCaches({ ttlMs: config.contextCacheTtlMs });
      metrics.contextCacheSweepsTotal += 1;
      if (result.evicted > 0) {
        metrics.contextCacheEvictionsTotal += result.evicted;
        metrics.lastContextCacheEvictionAt = new Date().toISOString();
        app.log.info({ evicted: result.evicted, retained: result.retained }, "idle self-context caches evicted");
      }
    } catch (error) {
      metrics.errorsTotal += 1;
      metrics.lastErrorAt = new Date().toISOString();
      app.log.error({ err: error }, "self-context cache sweep failed");
    }
  }

  const sessionSweepTimer = setInterval(() => void runSessionSweep(), config.sessionSweepIntervalMs);
  sessionSweepTimer.unref?.();

  const contextCacheSweepTimer =
    config.contextCacheTtlMs > 0 ? setInterval(() => runContextCacheSweep(), config.contextCacheSweepIntervalMs) : null;
  contextCacheSweepTimer?.unref?.();

  async function handleMcpRequest(transport, request, reply) {
    reply.hijack();
    try {
      await transport.handleRequest(request.raw, reply.raw, request.body);
    } catch (error) {
      app.log.error(error);
      if (!reply.raw.headersSent) {
        reply.raw.writeHead(500, { "content-type": "application/json" });
      }
      if (!reply.raw.writableEnded) {
        reply.raw.end(
          JSON.stringify({
            jsonrpc: "2.0",
            error: {
              code: -32603,
              message: error instanceof Error ? error.message : String(error),
            },
            id: null,
          }),
        );
      }
    }
  }

  app.get("/health", async () => {
    const ledgerPath = resolveLedgerPath();
    const status = await selfContextStatus(ledgerPath);
    return {
      ok: true,
      name: "self-context",
      transport: "mcp-streamable-http",
      uptimeSeconds: Math.round(process.uptime()),
      activeSessions: sessions.size,
      index: {
        sourceClustersReady: status.files.sourceClusters,
        sqliteReady: status.files.sqliteIndex,
        embeddingsReady: status.files.memoryEmbeddings,
        personaSynthesisReady: status.personaSynthesisReady,
        identityFactsReady: status.identityFactsReady,
        identityGraphReady: status.identityGraphReady,
        allSourceFamiliesRecognized: status.allSourceFamiliesRecognized,
        careerTimelineReady: status.careerTimelineReady,
        experienceScopeReady: status.experienceScopeReady,
        voiceProfileReady: status.voiceProfileReady,
        voiceStyleReady: status.voiceStyleReady,
        agentOperatingContextReady: status.agentOperatingContextReady,
        retrievalEvalReady: status.retrievalEvalReady,
        retrievalEvalStale: status.retrievalEvalStale,
        legacyAtomsPruned: status.legacyAtomsPruned,
      },
      selfContextCache: getSelfContextCacheStatus(ledgerPath),
    };
  });

  app.get("/live", async () => ({
    ok: true,
    uptimeSeconds: Math.round(process.uptime()),
  }));

  app.get("/ready", async () => {
    const ledgerPath = resolveLedgerPath();
    const contextsPath = path.join(ledgerPath, "derived", "context_packs.jsonl");
    const sourceClustersReady = existsSync(path.join(ledgerPath, "derived", "source_clusters.jsonl"));
    const contextPacksReady = existsSync(contextsPath);
    const sqliteReady = existsSync(path.join(ledgerPath, "derived", "self_context.sqlite3"));
    const embeddingsReady = existsSync(path.join(ledgerPath, "derived", "memory_embeddings.npz"));
    const personaEval = await readJsonIfExists(path.join(ledgerPath, "derived", "persona_synthesis_eval.json"));
    const identityFacts = await readJsonIfExists(path.join(ledgerPath, "derived", "identity_facts.json"));
    const identityGraph = await readJsonIfExists(path.join(ledgerPath, "derived", "identity_graph.json"));
    const selfModel = await readJsonIfExists(path.join(ledgerPath, "derived", "self_model.json"));
    const voiceStyleEval = await readJsonIfExists(path.join(ledgerPath, "derived", "voice_style_eval.json"));
    const sourceFamilyCoverage = identityFacts?.source_family_coverage ?? {};
    const expectedSourceFamilies = [
      "career_facts",
      "github_pr_activity",
      "github_authority_signals",
      "release_activity",
      "jira_leadership_signals",
      "architecture_material",
      "agent_sessions",
      "portfolio_cases",
      "personal_material",
    ];
    const allSourceFamiliesRecognized = expectedSourceFamilies.every((family) => Boolean(sourceFamilyCoverage?.[family]));
    const personaSynthesisReady = personaEval?.personaSynthesisReady === true;
    const identityFactsReady =
      identityFacts?.architecture === "self-context-v2.8" &&
      Boolean(identityFacts?.career_timeline?.engineering_activity_start) &&
      Boolean(identityFacts?.experience_scope?.primary_scope) &&
      allSourceFamiliesRecognized;
    const identityGraphReady =
      identityGraph?.architecture === "self-context-v2.8" &&
      Array.isArray(identityGraph?.nodes) &&
      identityGraph.nodes.length >= 7 &&
      Array.isArray(identityGraph?.edges) &&
      identityGraph.edges.length >= 5;
    const careerTimelineReady = Array.isArray(selfModel?.sections)
      ? selfModel.sections.some((section) => section?.id === "self_model:career_timeline")
      : false;
    const experienceScopeReady = Array.isArray(selfModel?.sections)
      ? selfModel.sections.some((section) => section?.id === "self_model:experience_scope")
      : false;
    const voiceProfileReady =
      voiceStyleEval?.voiceProfileReady === true && existsSync(path.join(ledgerPath, "derived", "voice_profile.json"));
    const voiceStyleReady =
      voiceStyleEval?.voiceStyleReady === true && existsSync(path.join(ledgerPath, "derived", "voice_style_eval.json"));
    const agentOperatingContextReady =
      personaEval?.agentOperatingContextReady === true &&
      existsSync(path.join(ledgerPath, "derived", "agent_operating_context.json"));
    const retrievalEval = await retrievalEvalStatus(ledgerPath);
    const cacheStatus = getSelfContextCacheStatus(ledgerPath);
    const cacheReady = !config.warmCacheOnStart || cacheStatus.loaded;
    return {
      ok:
        sourceClustersReady &&
        contextPacksReady &&
        sqliteReady &&
        embeddingsReady &&
        personaSynthesisReady &&
        identityFactsReady &&
        identityGraphReady &&
        careerTimelineReady &&
        experienceScopeReady &&
        voiceProfileReady &&
        voiceStyleReady &&
        agentOperatingContextReady &&
        retrievalEval.ready &&
        cacheReady,
      sourceClustersReady,
      contextPacksReady,
      sqliteReady,
      embeddingsReady,
      personaSynthesisReady,
      identityFactsReady,
      identityGraphReady,
      careerTimelineReady,
      experienceScopeReady,
      voiceProfileReady,
      voiceStyleReady,
      agentOperatingContextReady,
      retrievalEvalReady: retrievalEval.ready,
      retrievalEvalStale: retrievalEval.stale,
      allSourceFamiliesRecognized,
      sourceFamilyCoverage,
      cacheReady,
      selfContextCache: cacheStatus,
    };
  });

  app.get("/metrics", async () => ({
    ...metrics,
    uptimeSeconds: Math.round(process.uptime()),
    activeSessions: sessions.size,
    selfContextCache: getSelfContextCacheStatus(resolveLedgerPath()),
  }));

  app.get("/config", async () => ({
    ok: true,
    config: publicConfig(config),
  }));

  app.all("/mcp", async (request, reply) => {
    await pruneExpiredSessions();
    const sessionId = request.headers["mcp-session-id"];

    if (typeof sessionId === "string" && sessions.has(sessionId)) {
      const session = sessions.get(sessionId);
      session.lastSeenAt = Date.now();
      await handleMcpRequest(session.transport, request, reply);
      return;
    }

    if (typeof sessionId === "string") {
      reply.code(404).send({
        jsonrpc: "2.0",
        error: {
          code: -32001,
          message: "Session not found",
        },
        id: null,
      });
      return;
    }

    if (request.method === "POST" && !sessionId && isInitializeRequest(request.body)) {
      if (sessions.size >= config.maxSessions) {
        reply.code(503).send({
          jsonrpc: "2.0",
          error: {
            code: -32000,
            message: "Server busy: maximum MCP sessions reached",
          },
          id: null,
        });
        return;
      }
      const mcpServer = createSelfContextMcpServer();
      let transport;
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        enableJsonResponse: true,
        allowedHosts: config.allowedHosts,
        allowedOrigins: config.allowedOrigins,
        enableDnsRebindingProtection: config.enableDnsRebindingProtection,
        onsessioninitialized: (newSessionId) => {
          sessions.set(newSessionId, {
            transport,
            server: mcpServer,
            initializedAt: Date.now(),
            lastSeenAt: Date.now(),
          });
          refreshSessionMetrics();
        },
      });
      transport.onclose = () => {
        if (transport.sessionId) {
          sessions.delete(transport.sessionId);
          refreshSessionMetrics();
        }
      };
      await mcpServer.connect(transport);
      await handleMcpRequest(transport, request, reply);
      return;
    }

    reply.code(400).send({
      jsonrpc: "2.0",
      error: {
        code: -32000,
        message: "Bad Request: missing valid MCP session or initialize request",
      },
      id: null,
    });
  });

  app.addHook("onClose", async () => {
    clearInterval(sessionSweepTimer);
    if (contextCacheSweepTimer) clearInterval(contextCacheSweepTimer);
    await Promise.all([...sessions.entries()].map(([sessionId, session]) => closeSession(sessionId, session)));
    sessions.clear();
    refreshSessionMetrics();
  });

  return app;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  const config = loadServerConfig();
  const app = buildFastifyApp({ config });

  const shutdown = async (signal) => {
    app.log.info({ signal }, "shutting down Self Context MCP");
    try {
      await app.close();
      process.exit(0);
    } catch (error) {
      app.log.error({ err: error }, "shutdown failed");
      process.exit(1);
    }
  };

  process.once("SIGINT", () => void shutdown("SIGINT"));
  process.once("SIGTERM", () => void shutdown("SIGTERM"));

  try {
    const address = await app.listen({ host: config.host, port: config.port });
    if (config.warmCacheOnStart) {
      const cacheStatus = await warmSelfContextCache(resolveLedgerPath());
      app.log.info({ cacheStatus }, "self-context cache warmed");
    }
    app.log.info({ address, config: publicConfig(config) }, "Self Context MCP listening");
  } catch (error) {
    app.log.error({ err: error }, "failed to start Self Context MCP");
    process.exit(1);
  }
}
