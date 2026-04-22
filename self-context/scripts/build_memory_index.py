#!/usr/bin/env python3
"""Build dense retrieval records for self-context memory and context packs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from ledger_paths import resolve_ledger_path


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"
TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_+.#/-]*", re.IGNORECASE)


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


def as_text(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(as_text(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return "" if value is None else str(value)


def fingerprint(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.as_posix()):
        digest.update(path.name.encode("utf-8"))
        if not path.exists():
            digest.update(b"missing")
            continue
        digest.update(path.read_bytes())
    return digest.hexdigest()


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


def hashed_embeddings(texts: list[str], dimension: int = 384) -> np.ndarray:
    matrix = np.zeros((len(texts), dimension), dtype=np.float32)
    for row_index, text in enumerate(texts):
        for token in tokenize(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "little") % dimension
            sign = -1.0 if digest[4] % 2 else 1.0
            matrix[row_index, bucket] += sign
        norm = math.sqrt(float(np.dot(matrix[row_index], matrix[row_index])))
        if norm > 0:
            matrix[row_index] /= norm
    return matrix


def sentence_transformer_embeddings(texts: list[str], model_name: str) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return np.asarray(embeddings, dtype=np.float32)


def context_id_for_memory(memory_id: str) -> str:
    return memory_id.replace("memory:", "context:", 1)


def build_records(derived: Path) -> list[dict[str, Any]]:
    atoms = read_jsonl(derived / "memory_atoms.jsonl")
    packs = read_jsonl(derived / "context_packs.jsonl")
    self_model = read_json(derived / "self_model.json")
    sections = self_model.get("sections", []) if isinstance(self_model.get("sections"), list) else []

    packs_by_memory: dict[str, list[str]] = {}
    for pack in packs:
        for memory_id in pack.get("memory_atoms", []):
            packs_by_memory.setdefault(str(memory_id), []).append(str(pack.get("id")))

    records: list[dict[str, Any]] = []
    for atom in atoms:
        memory_id = str(atom["id"])
        parent_context_ids = sorted(set([context_id_for_memory(memory_id), *packs_by_memory.get(memory_id, [])]))
        records.append(
            {
                "id": memory_id,
                "kind": "memory_atom",
                "intent": "",
                "parent_context_ids": parent_context_ids,
                "memory_atoms": [memory_id],
                "topics": atom.get("topics", []),
                "text": "\n".join(
                    [
                        "Kind: memory atom",
                        f"Type: {atom.get('memory_type', '')}",
                        f"Topics: {', '.join(atom.get('topics', []))}",
                        f"Statement: {atom.get('statement', '')}",
                        "Useful context:",
                        as_text(atom.get("useful_context")),
                        "Behavioral use:",
                        as_text(atom.get("behavioral_use")),
                        "Guardrails:",
                        as_text(atom.get("guardrails")),
                        "Query patterns:",
                        as_text(atom.get("query_patterns")),
                    ]
                ),
            }
        )

    for pack in packs:
        records.append(
            {
                "id": str(pack["id"]),
                "kind": "context_pack",
                "intent": pack.get("intent", ""),
                "parent_context_ids": [str(pack["id"])],
                "memory_atoms": pack.get("memory_atoms", []),
                "topics": pack.get("topics", []),
                "text": pack.get("retrieval_text")
                or "\n".join(
                    [
                        "Kind: context pack",
                        f"Intent: {pack.get('intent', '')}",
                        f"Title: {pack.get('title', '')}",
                        f"Direct answer: {pack.get('direct_answer', '')}",
                        as_text(pack.get("useful_context")),
                        as_text(pack.get("behavioral_guidance")),
                        as_text(pack.get("known_limits")),
                    ]
                ),
            }
        )

    for section in sections:
        section_id = str(section.get("id", "")).replace("self_model:", "context:self_model.", 1)
        records.append(
            {
                "id": str(section.get("id", section_id)),
                "kind": "self_model_section",
                "intent": section.get("intent", "self_knowledge"),
                "parent_context_ids": [section_id],
                "memory_atoms": section.get("memory_atoms", []),
                "topics": section.get("topics", []),
                "text": "\n".join(
                    [
                        "Kind: self model section",
                        f"Title: {section.get('title', '')}",
                        f"Level: {section.get('level', '')}",
                        f"Summary: {section.get('summary', '')}",
                        "Practical guidance:",
                        as_text(section.get("practical_guidance")),
                        "Decision biases:",
                        as_text(section.get("decision_biases")),
                        "Known limits:",
                        as_text(section.get("known_limits")),
                        f"Topics: {', '.join(section.get('topics', []))}",
                    ]
                ),
            }
        )

    unique = {record["id"] + ":" + record["kind"]: record for record in records}
    return list(unique.values())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--reranker-model", default=DEFAULT_RERANKER_MODEL)
    parser.add_argument("--backend", choices=["auto", "sentence-transformers", "hashing"], default="auto")
    parser.add_argument("--require-model", action="store_true", help="Fail instead of using hashing fallback when sentence-transformers is unavailable.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    ledger = resolve_ledger_path(args.ledger)
    derived = ledger / "derived"
    records = build_records(derived)
    texts = [record["text"] for record in records]
    backend = args.backend
    model_name = args.model

    if backend in {"auto", "sentence-transformers"}:
        try:
            embeddings = sentence_transformer_embeddings(texts, model_name)
            backend = "sentence-transformers"
        except Exception as exc:
            if args.require_model or backend == "sentence-transformers":
                raise RuntimeError(f"failed to build sentence-transformers embeddings: {exc}") from exc
            embeddings = hashed_embeddings(texts)
            backend = "hashing"
            model_name = "deterministic-token-hashing"
    else:
        embeddings = hashed_embeddings(texts)
        backend = "hashing"
        model_name = "deterministic-token-hashing"

    fallback_embeddings = hashed_embeddings(texts, int(embeddings.shape[1]) if len(embeddings.shape) == 2 else 384)
    index_path = derived / "memory_embeddings.npz"
    np.savez_compressed(
        index_path,
        embeddings=embeddings.astype(np.float32),
        fallback_embeddings=fallback_embeddings.astype(np.float32),
        records_json=np.array([json.dumps(records, ensure_ascii=False, sort_keys=True)]),
    )

    source_paths = [
        derived / "memory_atoms.jsonl",
        derived / "source_clusters.jsonl",
        derived / "distillation_candidates.jsonl",
        derived / "distillation_eval.json",
        derived / "identity_facts.json",
        derived / "identity_graph.json",
        derived / "voice_profile.json",
        derived / "voice_style_eval.json",
        derived / "agent_operating_context.json",
        derived / "context_packs.jsonl",
        derived / "self_model.json",
        derived / "memory_graph_edges.jsonl",
    ]
    manifest = {
        "generated_at": now_iso(),
        "architecture": "self-context-v2.8",
        "backend": backend,
        "model_name": model_name,
        "reranker_model": args.reranker_model,
        "normalized": True,
        "similarity": "dot_product_cosine",
        "chunk_count": len(records),
        "dimension": int(embeddings.shape[1]) if len(embeddings.shape) == 2 else 0,
        "source_path": ";".join(str(path) for path in source_paths),
        "index_path": str(index_path),
        "fingerprint": fingerprint(source_paths),
        "filters": {
            "indexed_kinds": ["memory_atom", "context_pack", "self_model_section"],
            "raw_sources_indexed": False,
        },
        "fallback_query_backend": "deterministic-token-hashing",
    }
    write_json(derived / "memory_embeddings_manifest.json", manifest)

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"memory_embeddings={index_path} records={len(records)} backend={backend}")


if __name__ == "__main__":
    main()
