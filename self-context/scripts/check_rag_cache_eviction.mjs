#!/usr/bin/env node

import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

import {
  evictExpiredSelfContextCaches,
  getSelfContextCacheStatus,
  querySelfContextFast,
} from "./self_context_query_cache.mjs";

const ledger = await mkdtemp(path.join(tmpdir(), "self-context-cache-"));

try {
  const derived = path.join(ledger, "derived");
  await mkdir(derived, { recursive: true });
  await writeFile(
    path.join(derived, "context_packs.jsonl"),
    `${JSON.stringify({
      id: "context:test",
      intent: "self_knowledge",
      title: "Cache eviction test",
      direct_answer: "frontend cache eviction regression test",
      useful_context: ["frontend cache eviction regression test"],
      behavioral_guidance: [],
      known_limits: [],
      memory_atoms: ["memory:test"],
      private_trace_refs: [],
      topics: ["frontend"],
      updated_at: "2026-01-01T00:00:00Z",
      retrieval_text: "frontend cache eviction regression test",
    })}\n`,
    "utf8",
  );
  await writeFile(path.join(derived, "provenance_links.jsonl"), "", "utf8");

  const query = await querySelfContextFast({ ledgerPath: ledger, query: "frontend cache eviction", top: 1 });
  assert.equal(query.answer_contexts.length, 1);
  assert.equal(getSelfContextCacheStatus(ledger).loaded, true);

  const evicted = evictExpiredSelfContextCaches({ ttlMs: 1, now: Date.now() + 10 });
  assert.equal(evicted.evicted, 1);
  assert.equal(getSelfContextCacheStatus(ledger).loaded, false);

  console.log("self-context cache eviction check passed");
} finally {
  await rm(ledger, { recursive: true, force: true });
}
