# Self Context Schema

The ledger stores private user material outside the installed skill folder. The core v2 database is memory-first: raw sources are preserved for refresh and proof, while MCP answers use memory atoms and context packs.

## Directory Layout

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

`exports/` is optional. Do not use generated resumes, profiles, or reports as the retrieval source of truth.

## Raw Material

Raw source rows preserve source facts without over-interpreting them.

Required fields:

- `id`: stable unique id.
- `source_type`: source category such as `git_commit`, `pull_request`, `jira_ticket`, `jira_comment`, `jira_changelog`, `code_style_signal`, `manual_event`, or `project_note`.
- `source_id`: commit hash, PR id, Jira key, manual id, or document id.
- `occurred_at`: ISO-8601 timestamp or date.
- `title`: short factual title.
- `summary`: neutral summary.
- `url_or_path`: link or local path.
- `raw_excerpt`: direct excerpt, diff summary, or structured metadata.
- `tags`: raw source tags.
- `ingested_at`: ISO-8601 timestamp.

## Memory Atom

`derived/memory_atoms.jsonl` is the primary self-context corpus.

Required fields:

- `id`: stable id such as `memory:coding_style.react_next`.
- `subject`: user identity key.
- `memory_type`: `identity`, `capability`, `coding_style`, `decision_pattern`, `preference`, `communication_style`, `work_history`, `project_context`, `personal_context`, `relationship_context`, `knowledge`, `goal`, `constraint`, `private_boundary`, or `unknown_gap`.
- `statement`: concise memory statement.
- `useful_context`: practical context an agent can use.
- `topics`: searchable topic labels.
- `facets`: confidence, domain, sensitivity, freshness, and time scope.
- `query_patterns`: phrases this memory should answer.
- `behavioral_use`: how an agent should use the memory.
- `guardrails`: uncertainty, privacy boundaries, stale warnings, or overclaim limits.
- `provenance_refs`: internal trace refs.
- `updated_at`: generation timestamp.

## Source Cluster

`derived/source_clusters.jsonl` stores deterministic theme clusters built directly from raw Git, PR, Jira, and code-style material before final memory atom generation.

Required fields:

- `id`
- `title`
- `memory_type`
- `statement`
- `useful_context`
- `topics`
- `source_count`
- `source_type_counts`
- `confidence`
- `source_refs`
- `updated_at`

Clusters are internal distillation scaffolding. They are useful for rebuild, audit, and refinement, but are not the default MCP answer surface.

## Distillation Candidate

`derived/distillation_candidates.jsonl` stores answer-ready candidate memories produced from source clusters before they are committed into `memory_atoms.jsonl`.

Required fields:

- `id`
- `memory_id`
- `trace_id`
- `source_cluster_id`
- `subject`
- `memory_type`
- `statement`
- `useful_context`
- `topics`
- `facets`
- `query_patterns`
- `behavioral_use`
- `guardrails`
- `source_refs`
- `quality_flags`
- `updated_at`

`derived/distillation_eval.json` records the v2.2 deep-distillation quality checks. Validation must fail if these checks do not pass.

## Self Model

`derived/self_model.json` groups memory atoms into operational sections:

- identity and positioning,
- skills and knowledge,
- coding/work style,
- preferences and taste,
- goals,
- constraints and private boundaries,
- stale or unknown areas,
- memory graph edges.

This is not a biography. It is an operational model for agents.

## Context Pack

`derived/context_packs.jsonl` is the default MCP retrieval output.

Required fields:

- `id`: stable context id.
- `intent`: `self_knowledge`, `act_as_me`, `coding_style`, `preference`, `work_context`, `personal_context`, `project_context`, `relationship_context`, `proof`, or `gap`.
- `title`: short label.
- `direct_answer`: answer spine.
- `useful_context`: usable details.
- `behavioral_guidance`: how an agent should apply the context.
- `known_limits`: uncertainty and privacy boundaries.
- `memory_atoms`: referenced memory atom ids.
- `private_trace_refs`: internal provenance refs.
- `topics`: topic labels.
- `retrieval_text`: contextualized retrieval text.
- `updated_at`: generation timestamp.

## Provenance Link

`derived/provenance_links.jsonl` is internal. It is not shown by default.

Required fields:

- `id`
- `memory_id`
- `source_id`
- `source_type`
- `support_role`
- `strength`
- `reason`
- `visibility`
- `updated_at`

Use provenance only for refresh, audit, contradiction handling, privacy review, and explicit proof requests.

## SQLite / FTS Index

`derived/self_context.sqlite3` mirrors the JSONL files for production query performance. It stores raw material, source clusters, distillation candidates, memory atoms, self model sections, context packs, provenance links, and memory graph edges. FTS5 tables index only answer-context surfaces: memory atoms and context packs. Raw source snippets and distillation scaffolding are preserved for proof/debug and are not part of default retrieval.

`derived/self_context_index_manifest.json` records the SQLite backend, database path, source fingerprint, and table counts. Validation must fail when manifest counts and actual table counts diverge.

## Embedding Index

`derived/memory_embeddings.npz` stores vector records for memory atoms, context packs, and self model sections. It does not embed every raw Git patch. `derived/memory_embeddings_manifest.json` records model name, dimension, fingerprint, and fallback query backend.

## Retrieval Eval

`derived/retrieval_eval.json` stores the v2.6 retrieval regression report for the real ledger. It records bilingual benchmark case results, suite summaries, pass/fail state, and fingerprints for `context_packs.jsonl`, `self_context_index_manifest.json`, and `memory_embeddings_manifest.json`.

Validation must fail when:

- the report is missing,
- any real-ledger benchmark case fails,
- required English or Simplified Chinese cases are missing, or
- the stored input fingerprints no longer match the current derived retrieval artifacts.
