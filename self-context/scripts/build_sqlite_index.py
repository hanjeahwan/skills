#!/usr/bin/env python3
"""Build the local SQLite/FTS index for self-context retrieval."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ledger_paths import resolve_ledger_path
from source_families import ARCHITECTURE_VERSION, SOURCE_FILES


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
    return rows


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def json_text(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False, sort_keys=True)


def source_fingerprint(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.as_posix()):
        digest.update(path.name.encode("utf-8"))
        if not path.exists():
            digest.update(b"missing")
            continue
        stat = path.stat()
        digest.update(str(stat.st_size).encode("utf-8"))
        digest.update(str(int(stat.st_mtime_ns)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def execute_schema(connection: sqlite3.Connection, schema_path: Path) -> None:
    connection.executescript(schema_path.read_text(encoding="utf-8"))


def clear_tables(connection: sqlite3.Connection) -> None:
    for table in [
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
    ]:
        connection.execute(f"DELETE FROM {table}")


def insert_raw_material(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT OR REPLACE INTO raw_material
        (id, source_type, source_id, occurred_at, title, summary, url_or_path, raw_excerpt_json, tags_json, ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                str(row.get("id", "")),
                str(row.get("source_type", "")),
                str(row.get("source_id", "")),
                str(row.get("occurred_at", "")),
                str(row.get("title", "")),
                str(row.get("summary", "")),
                str(row.get("url_or_path", "")),
                json_text(row.get("raw_excerpt")),
                json_text(row.get("tags")),
                str(row.get("ingested_at", "")),
            )
            for row in rows
            if row.get("id")
        ],
    )


def insert_memory_atoms(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT OR REPLACE INTO memory_atoms
        (id, subject, memory_type, statement, useful_context_json, topics_json, facets_json,
         query_patterns_json, behavioral_use, guardrails_json, provenance_refs_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["id"],
                row.get("subject", ""),
                row.get("memory_type", ""),
                row.get("statement", ""),
                json_text(row.get("useful_context")),
                json_text(row.get("topics")),
                json_text(row.get("facets")),
                json_text(row.get("query_patterns")),
                row.get("behavioral_use", ""),
                json_text(row.get("guardrails")),
                json_text(row.get("provenance_refs")),
                row.get("updated_at", ""),
            )
            for row in rows
        ],
    )
    connection.executemany(
        """
        INSERT INTO memory_atoms_fts
        (id, statement, useful_context_json, topics_json, query_patterns_json, behavioral_use)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["id"],
                row.get("statement", ""),
                json_text(row.get("useful_context")),
                json_text(row.get("topics")),
                json_text(row.get("query_patterns")),
                row.get("behavioral_use", ""),
            )
            for row in rows
        ],
    )


def insert_source_clusters(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT OR REPLACE INTO source_clusters
        (id, title, memory_type, statement, useful_context_json, topics_json, source_count,
         confidence, metadata_json, source_refs_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["id"],
                row.get("title", ""),
                row.get("memory_type", ""),
                row.get("statement", ""),
                json_text(row.get("useful_context")),
                json_text(row.get("topics")),
                int(row.get("source_count", 0) or 0),
                row.get("confidence", ""),
                json_text(
                    {
                        "source_type_counts": row.get("source_type_counts", {}),
                        "time_span": row.get("time_span", {}),
                        "representative_terms": row.get("representative_terms", []),
                        "file_areas": row.get("file_areas", []),
                        "matched_rules": row.get("matched_rules", []),
                    }
                ),
                json_text(row.get("source_refs")),
                row.get("updated_at", ""),
            )
            for row in rows
        ],
    )


def insert_distillation_candidates(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT OR REPLACE INTO distillation_candidates
        (id, memory_id, trace_id, source_cluster_id, memory_type, statement, useful_context_json,
         topics_json, facets_json, query_patterns_json, behavioral_use, guardrails_json,
         source_refs_json, quality_flags_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["id"],
                row.get("memory_id", ""),
                row.get("trace_id", ""),
                row.get("source_cluster_id", ""),
                row.get("memory_type", ""),
                row.get("statement", ""),
                json_text(row.get("useful_context")),
                json_text(row.get("topics")),
                json_text(row.get("facets")),
                json_text(row.get("query_patterns")),
                row.get("behavioral_use", ""),
                json_text(row.get("guardrails")),
                json_text(row.get("source_refs")),
                json_text(row.get("quality_flags")),
                row.get("updated_at", ""),
            )
            for row in rows
        ],
    )


def insert_self_model_sections(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT OR REPLACE INTO self_model_sections
        (id, section_type, intent, title, summary, practical_guidance_json, decision_biases_json,
         known_limits_json, memory_atoms_json, topics_json, level, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["id"],
                row.get("section_type", ""),
                row.get("intent", "self_knowledge"),
                row.get("title", ""),
                row.get("summary", ""),
                json_text(row.get("practical_guidance")),
                json_text(row.get("decision_biases")),
                json_text(row.get("known_limits")),
                json_text(row.get("memory_atoms")),
                json_text(row.get("topics")),
                row.get("level", ""),
                row.get("updated_at", ""),
            )
            for row in rows
        ],
    )


def insert_context_packs(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT OR REPLACE INTO context_packs
        (id, intent, title, direct_answer, useful_context_json, behavioral_guidance_json,
         known_limits_json, memory_atoms_json, private_trace_refs_json, topics_json, retrieval_text, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["id"],
                row.get("intent", ""),
                row.get("title", ""),
                row.get("direct_answer", ""),
                json_text(row.get("useful_context")),
                json_text(row.get("behavioral_guidance")),
                json_text(row.get("known_limits")),
                json_text(row.get("memory_atoms")),
                json_text(row.get("private_trace_refs")),
                json_text(row.get("topics")),
                row.get("retrieval_text", ""),
                row.get("updated_at", ""),
            )
            for row in rows
        ],
    )
    connection.executemany(
        """
        INSERT INTO context_packs_fts
        (id, title, direct_answer, useful_context_json, behavioral_guidance_json, known_limits_json, topics_json, retrieval_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["id"],
                row.get("title", ""),
                row.get("direct_answer", ""),
                json_text(row.get("useful_context")),
                json_text(row.get("behavioral_guidance")),
                json_text(row.get("known_limits")),
                json_text(row.get("topics")),
                row.get("retrieval_text", ""),
            )
            for row in rows
        ],
    )


def insert_provenance(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT OR REPLACE INTO provenance_links
        (id, memory_id, source_id, source_type, support_role, strength, reason, visibility, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["id"],
                row.get("memory_id", ""),
                row.get("source_id", ""),
                row.get("source_type", ""),
                row.get("support_role", ""),
                row.get("strength", ""),
                row.get("reason", ""),
                row.get("visibility", "internal"),
                row.get("updated_at", ""),
            )
            for row in rows
        ],
    )


def insert_edges(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT OR REPLACE INTO memory_graph_edges
        (from_memory_id, to_memory_id, relation, weight, reason)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                row.get("from_memory_id", ""),
                row.get("to_memory_id", ""),
                row.get("relation", ""),
                float(row.get("weight", 0.0) or 0.0),
                row.get("reason", ""),
            )
            for row in rows
            if row.get("from_memory_id") and row.get("to_memory_id") and row.get("relation")
        ],
    )


def table_count(connection: sqlite3.Connection, table: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    ledger = resolve_ledger_path(args.ledger)
    derived = ledger / "derived"
    db_path = derived / "self_context.sqlite3"
    schema_path = Path(__file__).resolve().parents[1] / "assets" / "sqlite-schema.sql"

    raw_rows = [row for name in SOURCE_FILES for row in read_jsonl(ledger / "sources" / name)]
    source_clusters = read_jsonl(derived / "source_clusters.jsonl")
    distillation_candidates = read_jsonl(derived / "distillation_candidates.jsonl")
    atoms = read_jsonl(derived / "memory_atoms.jsonl")
    context_packs = read_jsonl(derived / "context_packs.jsonl")
    provenance = read_jsonl(derived / "provenance_links.jsonl")
    edges = read_jsonl(derived / "memory_graph_edges.jsonl")
    self_model = read_json(derived / "self_model.json")
    sections = self_model.get("sections", []) if isinstance(self_model.get("sections"), list) else []

    derived.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        execute_schema(connection, schema_path)
        clear_tables(connection)
        insert_raw_material(connection, raw_rows)
        insert_source_clusters(connection, source_clusters)
        insert_distillation_candidates(connection, distillation_candidates)
        insert_memory_atoms(connection, atoms)
        insert_self_model_sections(connection, sections)
        insert_context_packs(connection, context_packs)
        insert_provenance(connection, provenance)
        insert_edges(connection, edges)
        connection.commit()
        counts = {
            "raw_material": table_count(connection, "raw_material"),
            "source_clusters": table_count(connection, "source_clusters"),
            "distillation_candidates": table_count(connection, "distillation_candidates"),
            "memory_atoms": table_count(connection, "memory_atoms"),
            "self_model_sections": table_count(connection, "self_model_sections"),
            "context_packs": table_count(connection, "context_packs"),
            "provenance_links": table_count(connection, "provenance_links"),
            "memory_graph_edges": table_count(connection, "memory_graph_edges"),
            "memory_atoms_fts": table_count(connection, "memory_atoms_fts"),
            "context_packs_fts": table_count(connection, "context_packs_fts"),
        }

    fingerprint_paths = [
        *(ledger / "sources" / name for name in SOURCE_FILES),
        derived / "memory_atoms.jsonl",
        derived / "source_clusters.jsonl",
        derived / "distillation_candidates.jsonl",
        derived / "distillation_eval.json",
        derived / "identity_facts.json",
        derived / "identity_graph.json",
        derived / "voice_profile.json",
        derived / "voice_style_eval.json",
        derived / "agent_operating_context.json",
        derived / "self_model.json",
        derived / "context_packs.jsonl",
        derived / "provenance_links.jsonl",
        derived / "memory_graph_edges.jsonl",
    ]
    manifest = {
        "generated_at": now_iso(),
        "architecture": "self-context-v2.8",
        "backend": "sqlite-fts5",
        "db_path": str(db_path),
        "fingerprint": source_fingerprint(fingerprint_paths),
        "counts": counts,
    }
    write_json(derived / "self_context_index_manifest.json", manifest)

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"sqlite_index={db_path} context_packs={counts['context_packs']} memory_atoms={counts['memory_atoms']}")


if __name__ == "__main__":
    main()
