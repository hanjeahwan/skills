# Personal Clone Search Context Architecture

Use this reference when redesigning the system from evidence retrieval into a personal clone memory layer. The goal is not a career RAG, not a resume generator, and not a proof report. The goal is a private MCP-backed memory system that lets agents ask useful questions about the person and receive context that feels like it belongs to that person.

## Core Decision

Build v2 as the only architecture. Do not preserve v1 retrieval behavior for compatibility when it conflicts with the personal clone goal.

The primary retrieval object is not a raw chunk, Markdown section, report, resume, or evidence link. The primary retrieval object is a distilled memory atom: a durable, useful, domain-neutral piece of knowledge about the subject.

Evidence and provenance still matter, but only as internal machinery for trust, debugging, refresh, contradiction handling, and explicit proof requests. They are not the default user-facing product.

```text
┌─────────────────────────────┐
│ Raw private material         │
│ Git, Jira, PRs, notes, docs  │
│ chats, preferences, history  │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Normalized source ledger      │
│ facts, dates, actors, spans   │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Distilled memory atoms        │
│ useful knowledge about me     │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Self model graph              │
│ topics, relationships, time   │
│ preferences, boundaries       │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Context packs                 │
│ answer-ready MCP payloads     │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Personal clone MCP            │
│ useful answers and behavior   │
└─────────────────────────────┘
```

## Product Goal

The MCP should let another agent ask:

- What does Hanje know?
- How does Hanje write code?
- What does Hanje care about in architecture, UX, quality, product, and delivery?
- What has Hanje done before?
- What would Hanje likely prefer in this decision?
- What context should I know before acting on Hanje's behalf?
- What personal, work, or knowledge material is known about Hanje?
- What is unknown, stale, private, or unsafe to assume?

The answer should be useful first. It should not look like a citation report unless the caller explicitly asks for proof.

## Why V1 Is The Wrong Shape

V1 treats `rag_chunks.jsonl` and generated Markdown sections as the main retrieval surface. That makes the system behave like a document search engine. It can find snippets, but it cannot reliably answer as a coherent personal memory.

The failure mode is structural:

- raw chunks are too low-level,
- Markdown profiles are presentation artifacts,
- count profiles are confidence signals, not self-knowledge,
- broad questions need whole-person synthesis,
- evidence links are provenance, not the product,
- career outputs are one domain, not the identity layer.

The v2 architecture must distill content into reusable memory first, then retrieve that memory for MCP answers.

## Research Basis

The design follows proven retrieval patterns, adapted for a personal memory system:

- Contextual Retrieval: add surrounding context before indexing and combine lexical retrieval, embeddings, and reranking.
- Hierarchical retrieval: retrieve across high-level summaries and lower-level detail instead of only short chunks.
- GraphRAG-style global search: use graph/community summaries for whole-corpus questions.
- Parent-child retrieval: search precise child units while returning larger, useful parent context.

For this skill:

- memory atom = precise searchable unit,
- context pack = parent context returned to MCP,
- provenance link = internal trace and refresh mechanism,
- raw material = private source of truth.

## Durable Files

Store v2 derived files under the private ledger:

```text
derived/
├── memory_atoms.jsonl
├── self_model.json
├── context_packs.jsonl
├── provenance_links.jsonl
├── memory_embeddings.npz
├── memory_embeddings_manifest.json
└── context_packs_manifest.json
```

Generated reports, resumes, profiles, and case studies are optional exports. They must not be the central retrieval database.

## Memory Atom

`derived/memory_atoms.jsonl` is the primary search corpus.

```json
{
  "id": "memory:code.react_next_practice",
  "subject": "hanjeahwan",
  "memory_type": "coding_style",
  "statement": "Hanje has React and Next.js frontend implementation practice as part of a broader product frontend profile.",
  "useful_context": [
    "Builds component-based UI with TypeScript and TSX.",
    "Uses hooks and state-oriented frontend patterns.",
    "Connects UI work to product flows, auth, forms, internal tooling, and delivery quality.",
    "React should be described alongside stronger broader frontend experience rather than as an isolated identity."
  ],
  "topics": ["frontend", "react", "nextjs", "typescript", "ui", "coding_style"],
  "facets": {
    "domain": "work",
    "time_scope": "multi_year",
    "confidence": "strong",
    "sensitivity": "private_work",
    "freshness": "current"
  },
  "query_patterns": [
    "does Hanje know React",
    "how does Hanje code React",
    "Hanje frontend coding style",
    "Hanje Next.js practice"
  ],
  "behavioral_use": "When an agent needs to answer or act with Hanje's frontend coding context, mention practical component, state, TypeScript, product-flow, and quality patterns before naming projects.",
  "guardrails": [
    "Do not answer with repository counts.",
    "Do not expose private source details unless proof is requested.",
    "Do not claim public portfolio proof unless sanitized artifacts exist."
  ],
  "provenance_refs": ["trace:memory.code.react_next_practice"],
  "updated_at": "2026-04-23T00:00:00Z"
}
```

Use these `memory_type` values:

- `identity`
- `capability`
- `coding_style`
- `decision_pattern`
- `preference`
- `communication_style`
- `work_history`
- `project_context`
- `personal_context`
- `relationship_context`
- `knowledge`
- `goal`
- `constraint`
- `private_boundary`
- `unknown_gap`

## Self Model

`derived/self_model.json` is the compact structured model of the subject.

It should group memory atoms into:

- identity and positioning,
- skills and knowledge,
- coding and work style,
- preferences and taste,
- communication style,
- current goals,
- long-running projects,
- important relationships or organizations,
- private boundaries,
- stale or uncertain areas,
- gaps that need more material.

The self model is not a biography. It is an operational model for agents that need to understand or act for the person.

## Context Pack

`derived/context_packs.jsonl` stores MCP-ready context. This is the default query result.

```json
{
  "id": "context:code.react_next_practice",
  "intent": "coding_style",
  "title": "React and Next.js practice",
  "direct_answer": "Hanje has evidence-backed React and Next.js practice, best understood as part of a broad product frontend engineering profile.",
  "useful_context": [
    "He tends to connect UI implementation with product flow correctness, state behavior, auth/forms, and maintainability.",
    "For coding-style answers, lead with practical component/state/TypeScript patterns, then mention examples only if needed."
  ],
  "behavioral_guidance": [
    "When writing code for him, prefer clear TypeScript, reusable components, explicit state boundaries, and production-oriented quality checks."
  ],
  "known_limits": [
    "Do not treat raw commit counts as the user-facing proof.",
    "Ask for public/sanitized examples before creating external portfolio claims."
  ],
  "memory_atoms": ["memory:code.react_next_practice"],
  "private_trace_refs": ["trace:memory.code.react_next_practice"],
  "topics": ["react", "nextjs", "frontend", "coding_style"],
  "updated_at": "2026-04-23T00:00:00Z"
}
```

MCP callers should receive context packs by default. Raw source ids and provenance traces should be hidden unless the caller asks for evidence, audit, debugging, or refresh details.

## Provenance Links

`derived/provenance_links.jsonl` is internal tracking.

It exists to support:

- refresh without reprocessing everything,
- confidence scoring,
- contradiction detection,
- stale memory cleanup,
- proof-on-demand,
- privacy audit,
- "why does the system think this?" debugging.

It is not a default display layer.

```json
{
  "id": "trace:memory.code.react_next_practice:source:code_style_signal...",
  "memory_id": "memory:code.react_next_practice",
  "source_id": "code_style_signal:...",
  "support_role": "primary",
  "strength": "strong",
  "reason": "Internal explanation of why this source supports the memory atom.",
  "visibility": "internal",
  "updated_at": "2026-04-23T00:00:00Z"
}
```

## MCP Query Contract

The primary tool should be `query_self_context`.

Default output:

```json
{
  "answer_context": {
    "direct_answer": "...",
    "useful_context": ["..."],
    "behavioral_guidance": ["..."],
    "known_limits": ["..."],
    "confidence": "strong"
  },
  "matched_memory": ["memory:..."],
  "private_trace_available": true
}
```

Only proof mode returns provenance:

```json
{
  "answer_context": { "...": "..." },
  "provenance": [
    {
      "source_id": "...",
      "source_type": "...",
      "reason": "..."
    }
  ]
}
```

## Query Pipeline

```text
1. Classify intent
   self_knowledge | act_as_me | coding_style | preference | work_context
   personal_context | project_context | relationship_context | proof | gap

2. Retrieve memory atoms
   FTS/BM25 + dense embedding over memory_atoms and context_packs

3. Expand self model graph
   related topics, preferences, time scope, privacy boundary, stale markers

4. Build context pack
   useful answer context + behavioral guidance + limits

5. Add provenance only when requested
   private trace -> source ids -> raw snippets

6. Return MCP payload
   useful context first, tracking data hidden by default
```

## Indexing Policy

Index first:

- `memory_atoms.jsonl`
- `context_packs.jsonl`
- selected `self_model.json` sections

Index only for proof/debug:

- `provenance_links.jsonl`
- raw source snippets

Do not embed every raw Git patch by default. Raw patches are source material for distillation and proof drill-down, not personal clone memory.

## SQLite Tables

The production local database should mirror JSONL:

```sql
memory_atoms(id, subject, memory_type, statement, useful_context_json, topics_json, facets_json, query_patterns_json, behavioral_use, guardrails_json, provenance_refs_json, updated_at)
self_model_sections(id, section_type, title, summary, memory_atoms_json, topics_json, updated_at)
context_packs(id, intent, title, direct_answer, useful_context_json, behavioral_guidance_json, known_limits_json, memory_atoms_json, private_trace_refs_json, topics_json, updated_at)
provenance_links(id, memory_id, source_id, source_type, support_role, strength, reason, visibility, updated_at)
memory_graph_edges(from_memory_id, to_memory_id, relation, weight, reason)
```

Add FTS over memory statement, useful context, topics, query patterns, behavioral guidance, and self model section summaries.

## Build Pipeline

```text
raw private material
  ▼
normalize + redact + dedupe
  ▼
extract candidate facts and patterns
  ▼
distill memory atoms
  ▼
build self model graph
  ▼
build MCP context packs
  ▼
index memory/context
  ▼
serve personal clone context
```

If an LLM is used during distillation, store its prompt version and source trace internally. Do not put LLM rationale in user-facing context.

## Answer Behavior

Default answers must:

1. answer the question directly,
2. provide useful personal context,
3. include behavior guidance when the caller may act for the user,
4. mention uncertainty or missing memory,
5. hide evidence/provenance unless requested.

Default answers must not:

- lead with project names,
- lead with counts,
- dump source ids,
- look like a resume,
- act as a generated documentation index,
- expose private material by accident.

## Golden Query Tests

Before shipping v2 retrieval, these queries must pass:

```text
what do you know about Hanje
how should I code in Hanje's style
does Hanje know React
what would Hanje prefer for a frontend architecture decision
what are Hanje's current work strengths
what personal preferences do we know about Hanje
what should an agent know before acting as Hanje
what is unknown or unsafe to assume about Hanje
show proof for the React claim
```

Expected behavior:

- Default answers return context packs, not raw chunks.
- Evidence/provenance appears only for proof requests.
- Career is one namespace inside the self model, not the whole model.
- Personal material can be added later without changing architecture.
- The answer is useful to an agent trying to understand or act for the person.

## Migration Plan

1. Replace v1 retrieval surface with `memory_atoms.jsonl`, `self_model.json`, and `context_packs.jsonl`.
2. Rename evidence-facing objects to internal `provenance_links`.
3. Build `scripts/build_memory_atoms.py` directly from existing GitHub, Jira, code-style, and manual raw sources.
4. Build `scripts/build_context_packs.py` for MCP-ready payloads.
5. Replace the primary MCP query tool with `query_self_context`.
6. Keep raw source search only as an internal proof/debug operation.
7. Update production checks around the golden queries above.
8. Treat resumes, profiles, and reports as optional exports generated from memory, not the reason the system exists.

## Source Links

- Anthropic Contextual Retrieval: https://www.anthropic.com/engineering/contextual-retrieval
- RAPTOR paper: https://arxiv.org/abs/2401.18059
- Microsoft GraphRAG overview: https://microsoft.github.io/graphrag//query/overview/
- Microsoft GraphRAG research blog: https://www.microsoft.com/en-us/research/blog/graphrag-new-tool-for-complex-data-discovery-now-on-github/
- Qdrant Hybrid Queries: https://qdrant.tech/documentation/search/hybrid-queries/
- Weaviate Hybrid Search: https://docs.weaviate.io/weaviate/concepts/search/hybrid-search
- LlamaIndex Property Graph Index: https://developers.llamaindex.ai/python/framework/module_guides/indexing/lpg_index_guide/
- LangChain ParentDocumentRetriever reference: https://api.python.langchain.com/en/latest/langchain/retrievers/langchain.retrievers.parent_document_retriever.ParentDocumentRetriever.html
