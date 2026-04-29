#!/usr/bin/env python3
"""Validate self-context ledger JSONL files with built-in schema checks."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

from build_persona_sections import CANONICAL_SECTION_IDS, LEGACY_PHRASES, SOURCE_ID_PATTERNS
from build_voice_profile import VOICE_BANNED_PHRASES, is_first_person_or_directive
from ledger_paths import resolve_ledger_path
from retrieval_benchmark_support import expected_case_ids_for_suite, retrieval_eval_is_stale
from source_families import ARCHITECTURE_VERSION, REQUIRED_SOURCE_FILES, SOURCE_FAMILY_IDS, SOURCE_FILES


RAW_REQUIRED = {
    "id",
    "source_type",
    "source_id",
    "occurred_at",
    "title",
    "summary",
    "url_or_path",
    "raw_excerpt",
    "tags",
    "ingested_at",
}

MEMORY_ATOM_REQUIRED = {
    "id",
    "subject",
    "memory_type",
    "statement",
    "useful_context",
    "topics",
    "facets",
    "query_patterns",
    "behavioral_use",
    "guardrails",
    "provenance_refs",
    "updated_at",
}

CONTEXT_PACK_REQUIRED = {
    "id",
    "intent",
    "title",
    "direct_answer",
    "answer_material",
    "useful_context",
    "behavioral_guidance",
    "known_limits",
    "memory_atoms",
    "private_trace_refs",
    "topics",
    "updated_at",
}

ANSWER_MATERIAL_REQUIRED = {
    "headline",
    "talking_points",
    "evidence_summary",
    "caveats",
    "suggested_followups",
}

PRODUCT_ANSWER_BANNED_PHRASES = {
    "use this topic pack",
    "common implementation surfaces",
    "raw source evidence",
    "declared profile should",
    "release ownership layer",
    "my release ownership layer",
    "he likely",
    "context pack",
    "private_trace_refs",
}

PROVENANCE_REQUIRED = {
    "id",
    "memory_id",
    "source_id",
    "source_type",
    "support_role",
    "strength",
    "reason",
    "visibility",
    "updated_at",
}

GRAPH_EDGE_REQUIRED = {
    "from_memory_id",
    "to_memory_id",
    "relation",
    "weight",
    "reason",
}

SOURCE_CLUSTER_REQUIRED = {
    "id",
    "title",
    "memory_type",
    "statement",
    "useful_context",
    "topics",
    "source_count",
    "source_type_counts",
    "confidence",
    "source_refs",
    "updated_at",
}

DISTILLATION_CANDIDATE_REQUIRED = {
    "id",
    "memory_id",
    "trace_id",
    "source_cluster_id",
    "subject",
    "memory_type",
    "statement",
    "useful_context",
    "topics",
    "facets",
    "query_patterns",
    "behavioral_use",
    "guardrails",
    "source_refs",
    "quality_flags",
    "updated_at",
}

EMBEDDING_MANIFEST_REQUIRED = {
    "backend",
    "model_name",
    "normalized",
    "similarity",
    "chunk_count",
    "dimension",
    "source_path",
    "index_path",
    "fingerprint",
    "filters",
}

SQLITE_MANIFEST_REQUIRED = {
    "backend",
    "db_path",
    "fingerprint",
    "counts",
}

SELF_MODEL_SECTION_REQUIRED = {
    "id",
    "section_type",
    "intent",
    "title",
    "summary",
    "practical_guidance",
    "decision_biases",
    "known_limits",
    "memory_atoms",
    "topics",
    "updated_at",
}

PERSONA_EVAL_REQUIRED = {
    "generated_at",
    "architecture",
    "legacyAtomsPruned",
    "retainedMemoryAtoms",
    "personaSections",
    "personaSynthesisReady",
    "agentOperatingContextReady",
    "voiceProfileReady",
    "voiceStyleReady",
    "checks",
    "passes",
}

VOICE_PROFILE_REQUIRED = {
    "generated_at",
    "architecture",
    "tone_rules",
    "directive_patterns",
    "preferred_openings",
    "preferred_constraints",
    "banned_phrases",
    "source_stats",
}

VOICE_STYLE_EVAL_REQUIRED = {
    "generated_at",
    "architecture",
    "voiceProfileReady",
    "voiceStyleReady",
    "source_stats",
    "checks",
    "passes",
}

AGENT_OPERATING_CONTEXT_REQUIRED = {
    "id",
    "generated_at",
    "operating_summary",
    "preferred_work_style",
    "decision_rules",
    "quality_non_negotiables",
    "domain_biases",
    "unsafe_assumptions",
    "ask_before_acting",
    "proof_policy",
    "topics",
    "source_sections",
}

IDENTITY_FACTS_REQUIRED = {
    "generated_at",
    "architecture",
    "subject",
    "source_family_coverage",
    "declared_profile",
    "career_timeline",
    "experience_scope",
    "role_identity",
    "technical_stack",
    "domain_knowledge",
    "impact_profile",
    "relationship_authority",
    "review_style",
    "repo_authority",
    "release_ownership",
    "jira_leadership",
    "architecture_material",
    "agent_collaboration_style",
    "portfolio_cases",
    "personal_identity",
    "learning_trajectory",
    "confidence_policy",
    "source_date_ranges",
}

IDENTITY_GRAPH_REQUIRED = {
    "generated_at",
    "architecture",
    "subject",
    "nodes",
    "edges",
    "source_sections",
    "summary",
}

RETRIEVAL_EVAL_REQUIRED = {
    "generated_at",
    "architecture",
    "suite_results",
    "summary",
    "case_results",
    "input_fingerprints",
    "passes",
}


def validate_jsonl(path: Path, required: set[str]) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        errors.append(f"missing file: {path}")
        return errors

    seen: set[str] = set()
    for index, line in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{index}: invalid JSON: {exc}")
            continue
        missing = sorted(required - set(row))
        if missing:
            errors.append(f"{path}:{index}: missing fields: {', '.join(missing)}")
        row_id = row.get("id")
        if row_id in seen:
            errors.append(f"{path}:{index}: duplicate id: {row_id}")
        if row_id:
            seen.add(row_id)
    return errors


def validate_embedding_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return errors
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]

    missing = sorted(EMBEDDING_MANIFEST_REQUIRED - set(manifest))
    if missing:
        errors.append(f"{path}: missing fields: {', '.join(missing)}")
    index_path = Path(str(manifest.get("index_path", "")))
    if not index_path.exists():
        errors.append(f"{path}: missing embedding index: {index_path}")
    if int(manifest.get("chunk_count", 0) or 0) <= 0:
        errors.append(f"{path}: chunk_count must be positive")
    if int(manifest.get("dimension", 0) or 0) <= 0:
        errors.append(f"{path}: dimension must be positive")
    return errors


def validate_sqlite_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return errors
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]
    missing = sorted(SQLITE_MANIFEST_REQUIRED - set(manifest))
    if missing:
        errors.append(f"{path}: missing fields: {', '.join(missing)}")
    db_path = Path(str(manifest.get("db_path", "")))
    if not db_path.exists():
        errors.append(f"{path}: missing sqlite db: {db_path}")
        return errors
    required_tables = {
        "raw_material",
        "source_clusters",
        "distillation_candidates",
        "memory_atoms",
        "self_model_sections",
        "context_packs",
        "provenance_links",
        "memory_graph_edges",
        "memory_atoms_fts",
        "context_packs_fts",
    }
    try:
        with sqlite3.connect(db_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')"
                )
            }
            missing_tables = sorted(required_tables - tables)
            if missing_tables:
                errors.append(f"{db_path}: missing tables: {', '.join(missing_tables)}")
            for table in required_tables & tables:
                count = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                manifest_count = manifest.get("counts", {}).get(table)
                if manifest_count is not None and int(manifest_count) != count:
                    errors.append(f"{db_path}: count mismatch for {table}: manifest={manifest_count} actual={count}")
            memory_count = int(connection.execute("SELECT COUNT(*) FROM memory_atoms").fetchone()[0])
            memory_fts_count = int(connection.execute("SELECT COUNT(*) FROM memory_atoms_fts").fetchone()[0])
            context_count = int(connection.execute("SELECT COUNT(*) FROM context_packs").fetchone()[0])
            context_fts_count = int(connection.execute("SELECT COUNT(*) FROM context_packs_fts").fetchone()[0])
            if memory_count != memory_fts_count:
                errors.append(f"{db_path}: memory_atoms FTS count mismatch: {memory_count} != {memory_fts_count}")
            if context_count != context_fts_count:
                errors.append(f"{db_path}: context_packs FTS count mismatch: {context_count} != {context_fts_count}")
    except sqlite3.Error as exc:
        errors.append(f"{db_path}: sqlite validation failed: {exc}")
    return errors


def validate_distillation_eval(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing file: {path}"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]
    errors: list[str] = []
    if value.get("architecture") != "self-context-v2.2":
        errors.append(f"{path}: architecture must be self-context-v2.2")
    if int(value.get("candidate_count", 0) or 0) <= 0:
        errors.append(f"{path}: candidate_count must be positive")
    quality = value.get("quality") if isinstance(value.get("quality"), dict) else {}
    if quality.get("passes") is not True:
        errors.append(f"{path}: distillation quality checks did not pass")
    return errors


def has_duplicate_prefix_id(identifier: str) -> bool:
    for prefix in ("memory:", "context:", "candidate:", "trace:"):
        if identifier.startswith(prefix):
            body = identifier[len(prefix) :]
            parts = body.split(".")
            return len(parts) >= 2 and parts[0] == parts[1]
    return False


def validate_memory_atom_content(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing file: {path}"]
    errors: list[str] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        statement = str(row.get("statement", "")).lower()
        if any(statement.startswith(phrase) for phrase in LEGACY_PHRASES):
            errors.append(f"{path}:{index}: legacy statement phrase must not appear")
        if has_duplicate_prefix_id(str(row.get("id", ""))):
            errors.append(f"{path}:{index}: duplicated type prefix in id: {row.get('id')}")
    return errors


def validate_context_pack_content(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing file: {path}"]
    errors: list[str] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        material = row.get("answer_material") if isinstance(row.get("answer_material"), dict) else {}
        missing = sorted(ANSWER_MATERIAL_REQUIRED - set(material))
        if missing:
            errors.append(f"{path}:{index}: answer_material missing fields: {', '.join(missing)}")
            continue
        text_fields = [str(material.get("headline", ""))]
        for field in ["talking_points", "evidence_summary", "caveats", "suggested_followups"]:
            value = material.get(field, [])
            if not isinstance(value, list):
                errors.append(f"{path}:{index}: answer_material.{field} must be a list")
                continue
            text_fields.extend(str(item) for item in value)
        if not str(material.get("headline", "")).strip():
            errors.append(f"{path}:{index}: answer_material.headline must be non-empty")
        if not material.get("talking_points"):
            errors.append(f"{path}:{index}: answer_material.talking_points must be non-empty")
        if not material.get("evidence_summary"):
            errors.append(f"{path}:{index}: answer_material.evidence_summary must be non-empty")
        lowered = " ".join(text_fields).lower()
        if (
            any(phrase in lowered for phrase in PRODUCT_ANSWER_BANNED_PHRASES)
            or any(phrase in lowered for phrase in LEGACY_PHRASES)
            or any(phrase in lowered for phrase in VOICE_BANNED_PHRASES)
        ):
            errors.append(f"{path}:{index}: answer_material contains internal or evidence-style phrasing")
        for pattern in SOURCE_ID_PATTERNS:
            if pattern.findall(" ".join(text_fields)):
                errors.append(f"{path}:{index}: source identifier leaked into answer_material")
                break
    return errors


def validate_self_model(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing file: {path}"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]
    errors: list[str] = []
    if value.get("architecture") != "self-context-v2.8":
        errors.append(f"{path}: architecture must be self-context-v2.8")
    sections = value.get("sections") if isinstance(value.get("sections"), list) else []
    section_ids = [str(section.get("id", "")) for section in sections]
    missing_sections = [section_id for section_id in CANONICAL_SECTION_IDS if section_id not in section_ids]
    if missing_sections:
        errors.append(f"{path}: missing canonical sections: {', '.join(missing_sections)}")
    for section in sections:
        missing = sorted(SELF_MODEL_SECTION_REQUIRED - set(section))
        if missing:
            errors.append(f"{path}: section {section.get('id')}: missing fields: {', '.join(missing)}")
        text_fields = [
            str(section.get("summary", "")),
            *[str(item) for item in section.get("practical_guidance", [])],
            *[str(item) for item in section.get("decision_biases", [])],
            *[str(item) for item in section.get("known_limits", [])],
        ]
        lowered = " ".join(text_fields).lower()
        if any(phrase in lowered for phrase in LEGACY_PHRASES) or any(phrase in lowered for phrase in VOICE_BANNED_PHRASES):
            errors.append(f"{path}: section {section.get('id')}: legacy phrase leaked into synthesized section")
        for pattern in SOURCE_ID_PATTERNS:
            hits = pattern.findall(" ".join(text_fields))
            if hits:
                errors.append(f"{path}: section {section.get('id')}: source identifier leaked into section text")
                break
    return errors


def validate_voice_profile(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing file: {path}"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]
    errors: list[str] = []
    missing = sorted(VOICE_PROFILE_REQUIRED - set(value))
    if missing:
        errors.append(f"{path}: missing fields: {', '.join(missing)}")
        return errors
    if value.get("architecture") != "self-context-v2.8":
        errors.append(f"{path}: architecture must be self-context-v2.8")
    source_stats = value.get("source_stats") if isinstance(value.get("source_stats"), dict) else {}
    if int(source_stats.get("authored_rows", 0) or 0) <= 0:
        errors.append(f"{path}: source_stats.authored_rows must be positive")
    for field in ["tone_rules", "directive_patterns", "preferred_openings", "preferred_constraints", "banned_phrases"]:
        field_value = value.get(field, [])
        if not isinstance(field_value, list) or not field_value:
            errors.append(f"{path}: field {field} must be a non-empty list")
    return errors


def validate_agent_operating_context(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing file: {path}"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]
    errors: list[str] = []
    missing = sorted(AGENT_OPERATING_CONTEXT_REQUIRED - set(value))
    if missing:
        errors.append(f"{path}: missing fields: {', '.join(missing)}")
        return errors
    list_fields = [
        "preferred_work_style",
        "decision_rules",
        "quality_non_negotiables",
        "domain_biases",
        "unsafe_assumptions",
        "ask_before_acting",
        "proof_policy",
        "topics",
        "source_sections",
    ]
    text_fields = [str(value.get("operating_summary", ""))]
    text_fields.extend(str(value.get(field, "")) for field in ["id", "generated_at"])
    for field in list_fields:
        field_value = value.get(field, [])
        if not isinstance(field_value, list) or not field_value:
            errors.append(f"{path}: field {field} must be a non-empty list")
            continue
        text_fields.extend(str(item) for item in field_value)
    lowered = " ".join(text_fields).lower()
    if any(phrase in lowered for phrase in LEGACY_PHRASES) or any(phrase in lowered for phrase in VOICE_BANNED_PHRASES):
        errors.append(f"{path}: legacy phrase leaked into agent operating context")
    for pattern in SOURCE_ID_PATTERNS:
        hits = pattern.findall(" ".join(text_fields))
        if hits:
            errors.append(f"{path}: source identifier leaked into agent operating context")
            break
    if str(value.get("id")) != "self_model:agent_operating_context":
        errors.append(f"{path}: id must be self_model:agent_operating_context")
    if not is_first_person_or_directive(str(value.get("operating_summary", ""))):
        errors.append(f"{path}: operating_summary must be first-person or directive")
    for field in list_fields:
        field_value = value.get(field, [])
        if field not in {"topics", "source_sections"} and not 3 <= len(field_value) <= 5:
            errors.append(f"{path}: field {field} must contain between 3 and 5 items")
    if not 3 <= len(value.get("topics", [])) <= 5:
        errors.append(f"{path}: field topics must contain between 3 and 5 items")
    if not 3 <= len(value.get("source_sections", [])) <= 5:
        errors.append(f"{path}: field source_sections must contain between 3 and 5 items")
    return errors


def validate_voice_style_eval(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing file: {path}"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]
    errors: list[str] = []
    missing = sorted(VOICE_STYLE_EVAL_REQUIRED - set(value))
    if missing:
        errors.append(f"{path}: missing fields: {', '.join(missing)}")
    if value.get("architecture") != "self-context-v2.8":
        errors.append(f"{path}: architecture must be self-context-v2.8")
    if value.get("passes") is not True or value.get("voiceProfileReady") is not True or value.get("voiceStyleReady") is not True:
        errors.append(f"{path}: voice style checks did not pass")
    return errors


def validate_identity_facts(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing file: {path}"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]
    errors: list[str] = []
    missing = sorted(IDENTITY_FACTS_REQUIRED - set(value))
    if missing:
        errors.append(f"{path}: missing fields: {', '.join(missing)}")
        return errors
    if value.get("architecture") != "self-context-v2.8":
        errors.append(f"{path}: architecture must be self-context-v2.8")
    source_family_coverage = value.get("source_family_coverage") if isinstance(value.get("source_family_coverage"), dict) else {}
    missing_families = sorted(set(SOURCE_FAMILY_IDS) - set(source_family_coverage))
    if missing_families:
        errors.append(f"{path}: missing source family coverage: {', '.join(missing_families)}")
    for family_id in SOURCE_FAMILY_IDS:
        family = source_family_coverage.get(family_id) if isinstance(source_family_coverage.get(family_id), dict) else {}
        status = str(family.get("status", ""))
        if status not in {"available", "unknown_gap"}:
            errors.append(f"{path}: source_family_coverage.{family_id}.status must be available or unknown_gap")
        if status == "unknown_gap" and not str(family.get("unknown_gap", "")):
            errors.append(f"{path}: source_family_coverage.{family_id}.unknown_gap must explain empty optional material")
    timeline = value.get("career_timeline") if isinstance(value.get("career_timeline"), dict) else {}
    for field in ["engineering_activity_start", "engineering_activity_end", "evidence_backed_years", "confidence"]:
        if str(timeline.get(field, "")) == "":
            errors.append(f"{path}: career_timeline.{field} must be present")
    try:
        evidence_years = float(timeline.get("evidence_backed_years", 0))
    except (TypeError, ValueError):
        evidence_years = -1
    if evidence_years < 0:
        errors.append(f"{path}: career_timeline.evidence_backed_years must be non-negative")
    scope = value.get("experience_scope") if isinstance(value.get("experience_scope"), dict) else {}
    if not scope.get("primary_scope") or not scope.get("full_stack_policy"):
        errors.append(f"{path}: experience_scope must include primary_scope and full_stack_policy")
    confidence_policy = value.get("confidence_policy") if isinstance(value.get("confidence_policy"), dict) else {}
    for label in ["declared", "evidenced", "inferred", "unknown"]:
        if not confidence_policy.get(label):
            errors.append(f"{path}: confidence_policy.{label} must be present")
    return errors


def validate_identity_graph(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing file: {path}"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]
    errors: list[str] = []
    missing = sorted(IDENTITY_GRAPH_REQUIRED - set(value))
    if missing:
        errors.append(f"{path}: missing fields: {', '.join(missing)}")
        return errors
    if value.get("architecture") != "self-context-v2.8":
        errors.append(f"{path}: architecture must be self-context-v2.8")
    nodes = value.get("nodes") if isinstance(value.get("nodes"), list) else []
    edges = value.get("edges") if isinstance(value.get("edges"), list) else []
    if len(nodes) < 7:
        errors.append(f"{path}: identity graph must include dense identity nodes")
    if len(edges) < 5:
        errors.append(f"{path}: identity graph must include relationship edges")
    source_sections = {str(item) for item in value.get("source_sections", [])} if isinstance(value.get("source_sections"), list) else set()
    required_sections = {
        "declared_profile",
        "review_style",
        "repo_authority",
        "release_ownership",
        "jira_leadership",
        "architecture_material",
        "agent_collaboration_style",
        "portfolio_cases",
        "personal_identity",
    }
    missing_sections = sorted(required_sections - source_sections)
    if missing_sections:
        errors.append(f"{path}: missing v2.8 identity graph source sections: {', '.join(missing_sections)}")
    return errors


def validate_persona_eval(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing file: {path}"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]
    errors: list[str] = []
    missing = sorted(PERSONA_EVAL_REQUIRED - set(value))
    if missing:
        errors.append(f"{path}: missing fields: {', '.join(missing)}")
    if value.get("architecture") != "self-context-v2.8":
        errors.append(f"{path}: architecture must be self-context-v2.8")
    if value.get("passes") is not True or value.get("personaSynthesisReady") is not True:
        errors.append(f"{path}: persona synthesis checks did not pass")
    if value.get("agentOperatingContextReady") is not True:
        errors.append(f"{path}: agent operating context is not ready")
    if value.get("voiceProfileReady") is not True:
        errors.append(f"{path}: voice profile is not ready")
    if value.get("voiceStyleReady") is not True:
        errors.append(f"{path}: voice style is not ready")
    sections = value.get("personaSections") if isinstance(value.get("personaSections"), list) else []
    missing_sections = [section_id for section_id in CANONICAL_SECTION_IDS if section_id not in sections]
    if missing_sections:
        errors.append(f"{path}: missing canonical persona sections: {', '.join(missing_sections)}")
    return errors


def validate_retrieval_eval(path: Path, ledger: Path) -> list[str]:
    if not path.exists():
        return [f"missing file: {path}"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]
    errors: list[str] = []
    missing = sorted(RETRIEVAL_EVAL_REQUIRED - set(value))
    if missing:
        errors.append(f"{path}: missing fields: {', '.join(missing)}")
        return errors
    if value.get("architecture") != "self-context-v2.8":
        errors.append(f"{path}: architecture must be self-context-v2.8")
    if value.get("passes") is not True:
        errors.append(f"{path}: retrieval benchmark did not pass")
    suite_results = value.get("suite_results") if isinstance(value.get("suite_results"), dict) else {}
    real_suite = suite_results.get("real") if isinstance(suite_results.get("real"), dict) else {}
    if not real_suite:
        errors.append(f"{path}: suite_results.real is required")
    elif real_suite.get("passes") is not True or real_suite.get("skipped") is True:
        errors.append(f"{path}: real retrieval suite must pass and must not be skipped")
    case_results = value.get("case_results") if isinstance(value.get("case_results"), list) else []
    actual_case_ids = {str(item.get("id", "")) for item in case_results}
    missing_case_ids = sorted(expected_case_ids_for_suite("real") - actual_case_ids)
    if missing_case_ids:
        errors.append(f"{path}: missing real benchmark cases: {', '.join(missing_case_ids)}")
    languages = {str(item.get("language", "")) for item in case_results if str(item.get("suite")) == "real"}
    if {"en", "zh-CN"} - languages:
        errors.append(f"{path}: real benchmark must include both en and zh-CN coverage")
    failing_cases = [str(item.get("id", "")) for item in case_results if item.get("passes") is not True]
    if failing_cases:
        errors.append(f"{path}: failing benchmark cases present: {', '.join(failing_cases)}")
    input_fingerprints = value.get("input_fingerprints") if isinstance(value.get("input_fingerprints"), dict) else {}
    for field in ["context_packs_sha256", "sqlite_manifest_fingerprint", "embedding_manifest_fingerprint"]:
        if not str(input_fingerprints.get(field, "")):
            errors.append(f"{path}: input_fingerprints.{field} must be present")
    if retrieval_eval_is_stale(value, ledger):
        errors.append(f"{path}: retrieval eval is stale relative to current context/index fingerprints")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    args = parser.parse_args()
    ledger = resolve_ledger_path(args.ledger)

    errors: list[str] = []
    for name in REQUIRED_SOURCE_FILES:
        errors.extend(validate_jsonl(ledger / "sources" / name, RAW_REQUIRED))
    for name in sorted(set(SOURCE_FILES) - set(REQUIRED_SOURCE_FILES)):
        path = ledger / "sources" / name
        if path.exists():
            errors.extend(validate_jsonl(path, RAW_REQUIRED))
    processed = ledger / "events" / "processed.jsonl"
    if processed.exists():
        errors.extend(validate_jsonl(processed, RAW_REQUIRED))
    for name, required in [
        ("source_clusters.jsonl", SOURCE_CLUSTER_REQUIRED),
        ("distillation_candidates.jsonl", DISTILLATION_CANDIDATE_REQUIRED),
        ("memory_atoms.jsonl", MEMORY_ATOM_REQUIRED),
        ("context_packs.jsonl", CONTEXT_PACK_REQUIRED),
        ("provenance_links.jsonl", PROVENANCE_REQUIRED),
        ("memory_graph_edges.jsonl", GRAPH_EDGE_REQUIRED),
    ]:
        path = ledger / "derived" / name
        if path.exists():
            errors.extend(validate_jsonl(path, required))
    errors.extend(validate_memory_atom_content(ledger / "derived" / "memory_atoms.jsonl"))
    errors.extend(validate_context_pack_content(ledger / "derived" / "context_packs.jsonl"))
    errors.extend(validate_self_model(ledger / "derived" / "self_model.json"))
    errors.extend(validate_persona_eval(ledger / "derived" / "persona_synthesis_eval.json"))
    errors.extend(validate_identity_facts(ledger / "derived" / "identity_facts.json"))
    errors.extend(validate_identity_graph(ledger / "derived" / "identity_graph.json"))
    errors.extend(validate_voice_profile(ledger / "derived" / "voice_profile.json"))
    errors.extend(validate_voice_style_eval(ledger / "derived" / "voice_style_eval.json"))
    errors.extend(validate_agent_operating_context(ledger / "derived" / "agent_operating_context.json"))
    errors.extend(validate_embedding_manifest(ledger / "derived" / "memory_embeddings_manifest.json"))
    errors.extend(validate_sqlite_manifest(ledger / "derived" / "self_context_index_manifest.json"))
    errors.extend(validate_distillation_eval(ledger / "derived" / "distillation_eval.json"))
    errors.extend(validate_retrieval_eval(ledger / "derived" / "retrieval_eval.json", ledger))

    if errors:
        for error in errors:
            print(error)
        raise SystemExit(1)

    print(f"self-context ledger is valid: {ledger}")


if __name__ == "__main__":
    main()
