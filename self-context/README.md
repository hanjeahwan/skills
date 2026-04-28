# Self Context

Self Context is a local-first MCP and RAG memory engine for building an agent-usable model of a person from durable work and personal material.

It is designed for cases where an external agent needs more than a resume or keyword search. The engine distills raw sources into answer-ready context about how a person works, writes code, reviews decisions, handles delivery, communicates, and where the evidence is incomplete.

```text
┌──────────────────────────────┐
│ Private raw sources           │
│ Git, PRs, Jira, docs, notes   │
└───────────────┬──────────────┘
                ▼
┌──────────────────────────────┐
│ Source-native distillation    │
│ facts, signals, memory atoms  │
└───────────────┬──────────────┘
                ▼
┌──────────────────────────────┐
│ Identity graph + persona      │
│ sections, gaps, boundaries    │
└───────────────┬──────────────┘
                ▼
┌──────────────────────────────┐
│ Hybrid retrieval              │
│ SQLite FTS, vectors, rerank   │
└───────────────┬──────────────┘
                ▼
┌──────────────────────────────┐
│ MCP tools                     │
│ useful context, proof on ask  │
└──────────────────────────────┘
```

## What It Builds

- A private source ledger outside the repo.
- Memory atoms that describe useful knowledge about the subject, not raw evidence lists.
- Canonical self-model sections for identity, coding style, architecture judgment, quality bar, delivery leadership, AI product judgment, domain knowledge, and unknowns.
- An agent operating context for "act as me" or "work on my behalf" queries.
- SQLite FTS and optional local embedding index for hybrid retrieval.
- Retrieval regression checks with bilingual benchmark cases.
- A Fastify MCP server that exposes stable tools for other agents.

## Privacy Model

Real sources are private by default and must not be committed.

The public repo should contain:

- scripts
- schemas
- documentation
- synthetic benchmark fixtures
- public-safe examples

The private ledger should contain:

- Git commit exports
- PR and review activity
- Jira issues, comments, and changelogs
- code-style scans
- architecture notes
- agent session summaries
- portfolio and personal material
- generated indexes and derived memory files

Default ledger path:

```text
Windows: %USERPROFILE%\.self-context\ledger
macOS:   ~/.self-context/ledger
Linux:   ~/.self-context/ledger
```

## Quick Start

Install dependencies:

```bash
npm install
```

Initialize a private ledger:

```bash
python scripts/init_ledger.py --ledger "<ledger-path>"
```

Import material, then rebuild:

```bash
python scripts/build_memory_atoms.py --ledger "<ledger-path>"
python scripts/build_context_packs.py --ledger "<ledger-path>"
python scripts/build_sqlite_index.py --ledger "<ledger-path>"
python scripts/build_memory_index.py --ledger "<ledger-path>" --backend hashing
python scripts/run_retrieval_benchmarks.py --ledger "<ledger-path>" --suite real --write-report
python scripts/validate_ledger.py --ledger "<ledger-path>"
```

Query locally:

```bash
python scripts/query_self_context.py --ledger "<ledger-path>" --query "what should an agent know before acting as Example User" --json
```

Start the MCP server:

```bash
npm run start:mcp
```

## MCP Tools

- `query_self_context`: natural-language retrieval over the self model.
- `get_agent_operating_context`: structured bootstrap context for agents.
- `get_self_context_status`: index, retrieval, and source-family readiness.
- `rebuild_self_context`: rebuild derived memory and indexes.
- `import_private_material`: append manual material.
- `scan_code_style_from_repo`: scan a local repo for code-style signals.
- `analyze_github_commit_code_patterns`: summarize imported commit patches.

## Public Showcase Check

Before making a repository public, run:

```bash
npm run check:public
```

This checks syntax, synthetic retrieval behavior, and obvious private-data leaks such as real names, company terms, local ledger folders, and secret-like tokens.

## Suggested GitHub Positioning

Use a clear, accurate Featured title:

```text
Self-Context: MCP/RAG Personal AI Memory Engine
```

Avoid claiming that private company data, real Jira evidence, or production customer material is public. This repository is the engine; real evidence lives in the user's private ledger.

## Status

This project is a local-first personal AI memory engine, not a hosted SaaS and not a public evidence dump. It is suitable as a portfolio project when paired with a clean README, synthetic demo, privacy boundary, and public-safe screenshots or CLI output.
