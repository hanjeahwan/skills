#!/usr/bin/env python3
"""Shared helpers for retrieval benchmark specs, fingerprints, and eval status."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


BENCHMARK_SPEC_PATH = Path(__file__).resolve().parents[1] / "assets" / "retrieval_benchmarks.json"
STYLE_CONTRACTS = {"third_person_identity", "first_person_contract", "neutral_guidance"}
PROVENANCE_POLICIES = {"hidden_by_default", "required_when_requested"}
BENCHMARK_CASE_REQUIRED = {
    "id",
    "suite",
    "language",
    "query",
    "expected_intent",
    "expected_first_context",
    "style_contract",
    "provenance_policy",
    "must_contain",
    "must_not_contain",
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_path(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_benchmark_spec() -> list[dict[str, Any]]:
    rows = json.loads(BENCHMARK_SPEC_PATH.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{BENCHMARK_SPEC_PATH}: benchmark spec must be a non-empty JSON array")
    seen_ids: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"{BENCHMARK_SPEC_PATH}:{index}: each case must be an object")
        missing = sorted(BENCHMARK_CASE_REQUIRED - set(row))
        if missing:
            raise ValueError(f"{BENCHMARK_SPEC_PATH}:{index}: missing fields: {', '.join(missing)}")
        case_id = str(row.get("id", ""))
        if not case_id or case_id in seen_ids:
            raise ValueError(f"{BENCHMARK_SPEC_PATH}:{index}: duplicate or empty case id: {case_id!r}")
        seen_ids.add(case_id)
        if row["suite"] not in {"synthetic", "real"}:
            raise ValueError(f"{BENCHMARK_SPEC_PATH}:{index}: invalid suite: {row['suite']!r}")
        if row["language"] not in {"en", "zh-CN"}:
            raise ValueError(f"{BENCHMARK_SPEC_PATH}:{index}: invalid language: {row['language']!r}")
        if row["style_contract"] not in STYLE_CONTRACTS:
            raise ValueError(f"{BENCHMARK_SPEC_PATH}:{index}: invalid style_contract: {row['style_contract']!r}")
        if row["provenance_policy"] not in PROVENANCE_POLICIES:
            raise ValueError(f"{BENCHMARK_SPEC_PATH}:{index}: invalid provenance_policy: {row['provenance_policy']!r}")
        for field in ["must_contain", "must_not_contain"]:
            if not isinstance(row[field], list) or any(not isinstance(item, str) for item in row[field]):
                raise ValueError(f"{BENCHMARK_SPEC_PATH}:{index}: field {field} must be a string array")
    return rows


def benchmark_cases_for_suite(suite: str) -> list[dict[str, Any]]:
    rows = load_benchmark_spec()
    if suite == "all":
        return rows
    return [row for row in rows if row["suite"] == suite]


def expected_case_ids_for_suite(suite: str) -> set[str]:
    return {str(row["id"]) for row in benchmark_cases_for_suite(suite)}


def retrieval_input_fingerprints(ledger: Path) -> dict[str, Any]:
    derived = ledger / "derived"
    sqlite_manifest = read_json(derived / "self_context_index_manifest.json")
    embedding_manifest = read_json(derived / "memory_embeddings_manifest.json")
    return {
        "context_packs_sha256": sha256_path(derived / "context_packs.jsonl"),
        "sqlite_manifest_fingerprint": str(sqlite_manifest.get("fingerprint", "")),
        "embedding_manifest_fingerprint": str(embedding_manifest.get("fingerprint", "")),
    }


def retrieval_eval_is_stale(report: dict[str, Any], ledger: Path) -> bool:
    report_fingerprints = report.get("input_fingerprints") if isinstance(report.get("input_fingerprints"), dict) else {}
    current = retrieval_input_fingerprints(ledger)
    return report_fingerprints != current
