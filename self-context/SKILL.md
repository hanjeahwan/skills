---
name: self-context
description: Build and maintain a private personal clone context system from Git commits, PRs, Jira tickets, codebases, notes, documents, chats, work events, personal material, and other durable records. Use this when the user wants to import private material, distill useful self-knowledge, build memory atoms, expose a self-context MCP, answer questions about the user, retrieve proof on demand, scan code style, or let another agent understand or act with the user's long-term context.
---

# Self Context

Use this skill to build a private, continuously improving personal context layer for agents. The product is not a career RAG, resume generator, report generator, or evidence browser. The product is an MCP-backed personal clone memory system: another agent can connect and ask what the user knows, how the user codes, what the user prefers, what the user has done, what context matters before acting for the user, and what is unknown or unsafe to assume.

## Core Rule

V2 is the only architecture. Do not preserve old RAG/evidence behavior for compatibility when it conflicts with self-context.

Default outputs must be useful personal context, not evidence chains. Provenance and source ids are internal tracking for refresh, audit, contradiction handling, privacy review, and explicit proof requests.

```text
┌─────────────────────────────┐
│ Private material             │
│ Git, Jira, PRs, notes, docs  │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Source ledger                │
│ normalized private facts     │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Memory atoms                 │
│ useful knowledge about me    │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Self model graph             │
│ topics, style, limits, gaps  │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Context packs                │
│ answer-ready MCP payloads    │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ query_self_context           │
│ useful context by default    │
└─────────────────────────────┘
```

## Ledger Location

Never store private user material inside the installed skill folder.

Use this location order:

1. `SELF_CONTEXT_HOME` if set.
2. An explicit user-selected path.
3. User profile default:
   - Windows: `%USERPROFILE%\.self-context\ledger`
   - macOS: `~/.self-context/ledger`
   - Linux: `~/.self-context/ledger`

## Ledger Layout

```text
self-context-ledger/
├── events/
│   ├── inbox.md
│   └── processed.jsonl
├── sources/
│   ├── git.jsonl
│   ├── github_pr_activity.jsonl
│   ├── github_pr_reviews.jsonl
│   ├── github_authority_signals.jsonl
│   ├── jira.jsonl
│   ├── jira_comments.jsonl
│   ├── jira_changelog.jsonl
│   ├── code_style.jsonl
│   └── manual.jsonl
├── derived/
│   ├── source_clusters.jsonl
│   ├── distillation_candidates.jsonl
│   ├── distillation_eval.json
│   ├── memory_atoms.jsonl
│   ├── self_model.json
│   ├── context_packs.jsonl
│   ├── provenance_links.jsonl
│   ├── memory_graph_edges.jsonl
│   ├── self_context.sqlite3
│   ├── self_context_index_manifest.json
│   ├── memory_embeddings.npz
│   ├── memory_embeddings_manifest.json
│   └── retrieval_eval.json
└── exports/
```

`exports/` is optional. Resumes, profiles, reports, case studies, and public artifacts are exports from memory. They are not the database and not the main retrieval surface.

## Retrieval Architecture

Use all applicable retrieval patterns:

- Multi-vector / parent context: search precise memory atoms and return larger context packs.
- RAPTOR-style hierarchy: use `self_model.json` sections as higher-level summaries.
- GraphRAG-style relationships: use self-model topic and memory graph edges for whole-person questions.
- Contextual Retrieval: each context pack contains enough surrounding context for standalone retrieval.
- Hybrid + rerank: combine lexical/topic/intent matching now; add local dense embeddings and rerank over memory/context, not raw Git patches.

Read `references/distilled-search-context-architecture.md` before changing retrieval behavior.

## Core Scripts

- `scripts/init_ledger.py`: initialize a private self-context ledger.
- `scripts/export_git_commits.py`: import local Git commits into `sources/git.jsonl`.
- `scripts/export_github_commits.py`: import GitHub commits through `gh api` without cloning.
- `scripts/export_github_history.py`: import long-range GitHub history with date slicing.
- `scripts/export_github_pr_activity.py`: import PRs, PR comments, review comments, review requests, authority signals, CODEOWNERS, and workflow signals.
- `scripts/export_jira_issues.py`: import Jira tickets, comments, and changelog records.
- `scripts/scan_code_style.py`: scan local repositories into `sources/code_style.jsonl`.
- `scripts/analyze_github_commit_patterns.py`: distill GitHub commit patches into code-style signals.
- `scripts/build_source_clusters.py`: build deterministic raw-source theme clusters and candidate memories before final atom generation.
- `scripts/build_memory_atoms.py`: distill raw sources into `derived/memory_atoms.jsonl`, `derived/provenance_links.jsonl`, `derived/memory_graph_edges.jsonl`, and `derived/self_model.json`.
- `scripts/build_context_packs.py`: build `derived/context_packs.jsonl` for MCP answers.
- `scripts/build_sqlite_index.py`: sync raw material, memory, context, provenance, graph edges, and FTS tables into `derived/self_context.sqlite3`.
- `scripts/build_memory_index.py`: build local embedding records over memory atoms, self model sections, and context packs.
- `scripts/query_engine.py`: hybrid retrieval engine using FTS, dense vectors, graph expansion, and optional rerank.
- `scripts/run_retrieval_benchmarks.py`: run bilingual synthetic and real-ledger retrieval benchmark suites and write `derived/retrieval_eval.json`.
- `scripts/query_self_context.py`: compatibility CLI wrapper around `query_engine.py`; hides provenance unless proof is requested.
- `scripts/self_context_query_cache.mjs`: fast in-process MCP query cache.
- `scripts/fastify_mcp_server.mjs`: production-capable Fastify MCP Streamable HTTP server.
- `scripts/redact_ledger_secrets.py`: redact secrets from private source material.
- `scripts/validate_ledger.py`: validate source files, v2.2 deep-distillation artifacts, SQLite/FTS counts, and embedding manifests.

Legacy RAG chunk scripts may exist during migration, but do not use them as the primary self-context path.

## MCP Tools

Primary tools:

- `query_self_context`: retrieve useful personal context. Default hides provenance.
- `get_self_context_status`: inspect source counts, self model, context pack manifest, retrieval regression status, and cache status.
- `rebuild_self_context`: regenerate memory atoms, self model, and context packs.
- `warm_self_context_cache`: preload context packs into server memory.
- `import_private_material`: append manual private material and refresh self-context.
- `scan_code_style_from_repo`: scan a local repo and refresh memory.
- `analyze_github_commit_code_patterns`: analyze imported GitHub commit patches and refresh memory.

Do not expose legacy evidence/career RAG query tools as primary tools.

## Answer Contract

Default answers should:

1. Answer directly.
2. Provide useful personal context.
3. Include behavioral guidance when the caller may act for the user.
4. Mention uncertainty, stale memory, private boundaries, or missing material.
5. Hide evidence ids, source ids, commit hashes, Jira keys, and internal trace ids.

Only include provenance when the caller explicitly asks for proof, audit, debugging, or source tracing.

## Build Flow

After importing or changing source material:

```bash
python scripts/build_memory_atoms.py --ledger "<ledger-path>"
python scripts/build_context_packs.py --ledger "<ledger-path>"
python scripts/build_sqlite_index.py --ledger "<ledger-path>"
uv run --with sentence-transformers python scripts/build_memory_index.py --ledger "<ledger-path>"
python scripts/run_retrieval_benchmarks.py --ledger "<ledger-path>" --suite real --write-report
python scripts/validate_ledger.py --ledger "<ledger-path>"
```

Query:

```bash
python scripts/query_self_context.py --ledger "<ledger-path>" --query "<question>" --top 5 --json
```

Proof mode:

```bash
python scripts/query_self_context.py --ledger "<ledger-path>" --query "show proof for <claim>" --include-provenance --json
```

## Golden Queries

Use these before considering retrieval ready:

```text
what do you know about Example User
how should I code in Example User's style
does Example User know React
what would Example User prefer for a frontend architecture decision
what are Example User's current work strengths
what personal preferences do we know about Example User
what should an agent know before acting as Example User
what is unknown or unsafe to assume about Example User
show proof for the React claim
```

Expected behavior:

- Default results are context packs, not raw chunks.
- Evidence/provenance appears only for proof requests.
- Career is one namespace inside the self model, not the product.
- Personal material can be added without changing architecture.
- Answers are useful to an agent trying to understand or act for the user.

## References

- `references/distilled-search-context-architecture.md`: v2 personal clone context architecture.
- `references/schema.md`: source ledger and v2 derived schema.
- `references/git-scanning.md`: Git/GitHub import flow.
- `references/jira-import.md`: Jira import flow.
- `references/code-style-analysis.md`: code-style extraction.
- `references/privacy.md`: redaction and private/public boundary rules.
- `references/production-mcp.md`: production MCP deployment, auth, and cache behavior.
