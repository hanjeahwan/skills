CREATE TABLE IF NOT EXISTS raw_material (
  id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  source_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  url_or_path TEXT NOT NULL,
  raw_excerpt_json TEXT NOT NULL,
  tags_json TEXT NOT NULL,
  ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_atoms (
  id TEXT PRIMARY KEY,
  subject TEXT NOT NULL,
  memory_type TEXT NOT NULL,
  statement TEXT NOT NULL,
  useful_context_json TEXT NOT NULL,
  topics_json TEXT NOT NULL,
  facets_json TEXT NOT NULL,
  query_patterns_json TEXT NOT NULL,
  behavioral_use TEXT NOT NULL,
  guardrails_json TEXT NOT NULL,
  provenance_refs_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_clusters (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  memory_type TEXT NOT NULL,
  statement TEXT NOT NULL,
  useful_context_json TEXT NOT NULL,
  topics_json TEXT NOT NULL,
  source_count INTEGER NOT NULL,
  confidence TEXT NOT NULL,
  metadata_json TEXT NOT NULL,
  source_refs_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS distillation_candidates (
  id TEXT PRIMARY KEY,
  memory_id TEXT NOT NULL,
  trace_id TEXT NOT NULL,
  source_cluster_id TEXT NOT NULL,
  memory_type TEXT NOT NULL,
  statement TEXT NOT NULL,
  useful_context_json TEXT NOT NULL,
  topics_json TEXT NOT NULL,
  facets_json TEXT NOT NULL,
  query_patterns_json TEXT NOT NULL,
  behavioral_use TEXT NOT NULL,
  guardrails_json TEXT NOT NULL,
  source_refs_json TEXT NOT NULL,
  quality_flags_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS self_model_sections (
  id TEXT PRIMARY KEY,
  section_type TEXT NOT NULL,
  intent TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  practical_guidance_json TEXT NOT NULL,
  decision_biases_json TEXT NOT NULL,
  known_limits_json TEXT NOT NULL,
  memory_atoms_json TEXT NOT NULL,
  topics_json TEXT NOT NULL,
  level TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS context_packs (
  id TEXT PRIMARY KEY,
  intent TEXT NOT NULL,
  title TEXT NOT NULL,
  direct_answer TEXT NOT NULL,
  useful_context_json TEXT NOT NULL,
  behavioral_guidance_json TEXT NOT NULL,
  known_limits_json TEXT NOT NULL,
  memory_atoms_json TEXT NOT NULL,
  private_trace_refs_json TEXT NOT NULL,
  topics_json TEXT NOT NULL,
  retrieval_text TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS provenance_links (
  id TEXT PRIMARY KEY,
  memory_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  source_type TEXT NOT NULL,
  support_role TEXT NOT NULL,
  strength TEXT NOT NULL,
  reason TEXT NOT NULL,
  visibility TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (memory_id) REFERENCES memory_atoms(id)
);

CREATE TABLE IF NOT EXISTS memory_graph_edges (
  from_memory_id TEXT NOT NULL,
  to_memory_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  weight REAL NOT NULL,
  reason TEXT NOT NULL,
  PRIMARY KEY (from_memory_id, to_memory_id, relation)
);

CREATE INDEX IF NOT EXISTS idx_raw_material_source
ON raw_material(source_type, source_id);

CREATE INDEX IF NOT EXISTS idx_memory_atoms_type
ON memory_atoms(memory_type);

CREATE INDEX IF NOT EXISTS idx_source_clusters_type
ON source_clusters(memory_type);

CREATE INDEX IF NOT EXISTS idx_distillation_candidates_memory
ON distillation_candidates(memory_id);

CREATE INDEX IF NOT EXISTS idx_context_packs_intent
ON context_packs(intent);

CREATE INDEX IF NOT EXISTS idx_provenance_links_memory
ON provenance_links(memory_id);

CREATE VIRTUAL TABLE IF NOT EXISTS memory_atoms_fts
USING fts5(id UNINDEXED, statement, useful_context_json, topics_json, query_patterns_json, behavioral_use);

CREATE VIRTUAL TABLE IF NOT EXISTS context_packs_fts
USING fts5(id UNINDEXED, title, direct_answer, useful_context_json, behavioral_guidance_json, known_limits_json, topics_json, retrieval_text);
