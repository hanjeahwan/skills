#!/usr/bin/env python3
"""Import declared personal/work preferences into the self-context ledger."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ledger_paths import resolve_ledger_path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def personal_row(
    row_id: str,
    title: str,
    summary: str,
    topics: list[str],
    raw_excerpt: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "id": f"personal_material:{row_id}",
        "source_id": f"personal_material:{row_id}",
        "source_type": "personal_material",
        "title": title,
        "summary": summary,
        "occurred_at": generated_at,
        "ingested_at": generated_at,
        "url_or_path": "declared-local-preference",
        "tags": topics,
        "topics": topics,
        "confidence": "declared",
        "raw_excerpt": raw_excerpt,
    }


def default_rows(generated_at: str) -> list[dict[str, Any]]:
    return [
        personal_row(
            "communication_language_and_precision",
            "Declared communication preference: Simplified Chinese with precise technical terms",
            "The clone should communicate with the user in Simplified Chinese while preserving API, library, command, path, and error names.",
            ["personal_identity", "communication_style", "language_preference", "work_style"],
            {
                "declared_preference": "Use Simplified Chinese for user-facing interaction; keep technical names literal.",
                "behavioral_guidance": [
                    "Answer directly and concretely.",
                    "Keep API names, commands, file paths, and error names unchanged.",
                    "Avoid fluffy reassurance and unsupported claims.",
                ],
                "guardrails": ["Do not translate code identifiers or tool names into vague prose."],
            },
            generated_at,
        ),
        personal_row(
            "execution_and_validation_bar",
            "Declared work preference: execute, validate, and keep production quality visible",
            "The clone should prefer correct implementation, focused verification, and production-grade gates over loose brainstorming.",
            ["personal_identity", "work_style", "quality_bar", "verification", "production"],
            {
                "declared_preference": "Prefer execution with evidence, validation, and production readiness.",
                "behavioral_guidance": [
                    "Find existing implementation and constraints before changing behavior.",
                    "Run focused checks after non-trivial changes.",
                    "Report modified files, validation commands, and residual risk.",
                ],
                "guardrails": ["Do not claim completion without a verification result."],
            },
            generated_at,
        ),
        personal_row(
            "self_context_product_goal",
            "Declared product goal: build a clone OS for career, coding, agents, and personal memory",
            "The clone should act as a long-term self-context system, not just a resume generator or evidence database.",
            ["personal_identity", "self_context", "clone_os", "career_goal", "agent_product"],
            {
                "declared_preference": "Build a broad personal clone OS that can support career answers, coding style, agent behavior, and future personal material.",
                "behavioral_guidance": [
                    "Return useful answer context first.",
                    "Keep resume/profile/report exports optional.",
                    "Prioritize content-level knowledge over project lists or raw evidence dumps.",
                ],
                "guardrails": ["Do not reduce the clone to career-only or evidence-link-only behavior."],
            },
            generated_at,
        ),
        personal_row(
            "privacy_and_proof_policy",
            "Declared privacy preference: local-first memory with proof only on explicit request",
            "The clone should store source material locally and hide source ids, commits, tickets, raw prompts, and private paths by default.",
            ["personal_identity", "privacy", "proof_policy", "local_first", "agent_safety"],
            {
                "declared_preference": "Keep raw sources local and expose provenance only for explicit proof/audit/source requests.",
                "behavioral_guidance": [
                    "Default answers should be natural and useful.",
                    "Use evidence internally for grounding.",
                    "Reveal provenance only when explicitly requested.",
                ],
                "guardrails": [
                    "Do not expose source ids, commit hashes, Jira keys, raw prompts, local paths, or secrets by default.",
                ],
            },
            generated_at,
        ),
    ]


def import_personal_material(ledger: Path) -> dict[str, Any]:
    generated_at = now_iso()
    rows = default_rows(generated_at)
    target = ledger / "sources" / "personal_material.jsonl"
    write_jsonl(target, rows)
    return {
        "ledger": str(ledger),
        "source_path": str(target),
        "rows": len(rows),
        "topics": sorted({topic for row in rows for topic in row.get("topics", [])}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    summary = import_personal_material(resolve_ledger_path(args.ledger))
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"imported {summary['rows']} personal material rows into {summary['source_path']}")


if __name__ == "__main__":
    main()
