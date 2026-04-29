#!/usr/bin/env python3
"""Run data-driven retrieval benchmarks for synthetic and real self-context ledgers."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_persona_sections import LEGACY_PHRASES, SOURCE_ID_PATTERNS
from build_voice_profile import VOICE_BANNED_PHRASES, is_first_person_or_directive
from ledger_paths import resolve_ledger_path
from query_engine import query_self_context

THIRD_PERSON_SUBJECT_PATTERN = re.compile(
    r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?(?:'s|\s+(?:is|has|functions|works|operates))\b"
)
from retrieval_benchmark_support import (
    benchmark_cases_for_suite,
    load_benchmark_spec,
    retrieval_eval_is_stale,
    retrieval_input_fingerprints,
    write_json,
)
from source_families import ARCHITECTURE_VERSION


SCRIPT_DIR = Path(__file__).resolve().parent
ARCHITECTURE = ARCHITECTURE_VERSION
REQUIRED_REAL_FILES = [
    "context_packs.jsonl",
    "self_context.sqlite3",
    "memory_embeddings.npz",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def run_script(name: str, *args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / name), *args],
        cwd=SCRIPT_DIR.parent,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if result.returncode != 0:
        raise RuntimeError(f"{name} failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result.stdout


def source_row(
    source_type: str,
    source_id: str,
    title: str,
    raw_excerpt: dict[str, Any],
    tags: list[str],
    occurred_at: str = "2026-01-01T00:00:00Z",
) -> dict[str, Any]:
    return {
        "id": f"{source_type}:{source_id}",
        "source_type": source_type,
        "source_id": source_id,
        "occurred_at": occurred_at,
        "title": title,
        "summary": title,
        "url_or_path": f"https://example.test/{source_id}",
        "raw_excerpt": raw_excerpt,
        "tags": tags,
        "ingested_at": now_iso(),
    }


def seed_ledger(ledger: Path) -> None:
    for child in ["events", "sources", "derived", "exports"]:
        (ledger / child).mkdir(parents=True, exist_ok=True)
    write_jsonl(ledger / "events" / "processed.jsonl", [])
    write_jsonl(
        ledger / "sources" / "git.jsonl",
        [
            source_row(
                "git_commit",
                f"react-{index}",
                "feat(ai): build React Next.js AI chat workflow with typed components and hooks",
                {
                    "repo": "example/product-web",
                    "files": [
                        {"filename": "src/app/chat/page.tsx", "patch_excerpt": "useState useMemo typed React component hooks async state"},
                        {"filename": ".github/workflows/deploy.yml", "patch_excerpt": "github actions deploy semantic-release"},
                    ],
                },
                ["github", "git", "react", "ai", "ci_cd"],
                occurred_at=("2019-02-12T00:00:00Z" if index == 0 else "2026-01-01T00:00:00Z"),
            )
            for index in range(6)
        ],
    )
    write_jsonl(
        ledger / "sources" / "github_pr_activity.jsonl",
        [
            source_row(
                "pull_request",
                f"pr-{index}",
                "fix(api): align lookup payload and report export response",
                {"repo": "example/product-web", "author": "example-user", "merged_at": "2026-01-02T00:00:00Z"},
                ["github", "pull_request"],
            )
            for index in range(4)
        ],
    )
    write_jsonl(
        ledger / "sources" / "github_pr_reviews.jsonl",
        [
            source_row(
                "pull_request_review",
                f"review-{index}",
                "PR review APPROVED frontend API contract and maintainability",
                {"repo": "example/product-web", "review_state": "APPROVED", "body_excerpt": "please keep API contract clear"},
                ["github", "review"],
            )
            for index in range(4)
        ],
    )
    write_jsonl(
        ledger / "sources" / "github_authority_signals.jsonl",
        [
            source_row(
                "github_review_request",
                f"request-{index}",
                "GitHub review requested for frontend architecture decision",
                {"repo": "example/product-web", "event": "review_requested", "requested_reviewer": "example-user"},
                ["github", "review_request"],
            )
            for index in range(3)
        ],
    )
    write_jsonl(
        ledger / "sources" / "jira.jsonl",
        [
            source_row(
                "jira_ticket",
                f"CC-{index}",
                "Customer bug: staging skills selection not working Done Release",
                {"key": f"CC-{index}", "status": "Done", "issue_type": "Customer - Bug", "fixVersions": ["Release dev"]},
                ["jira"],
            )
            for index in range(3)
        ],
    )
    write_jsonl(
        ledger / "sources" / "jira_comments.jsonl",
        [
            source_row(
                "jira_comment",
                f"CC-{index}:comment",
                "Updated QA: follow standard, rest fixed and ready for verification",
                {"key": f"CC-{index}", "authored_by_user": True, "body_excerpt": "follow standard, rest updated"},
                ["jira", "comment"],
            )
            for index in range(3)
        ],
    )
    write_jsonl(
        ledger / "sources" / "jira_changelog.jsonl",
        [
            source_row(
                "jira_changelog",
                f"CC-{index}:status",
                "Jira changelog status In Progress to Done",
                {"key": f"CC-{index}", "field": "status", "fromString": "In Progress", "toString": "Done"},
                ["jira", "changelog"],
            )
            for index in range(3)
        ],
    )
    write_jsonl(ledger / "sources" / "manual.jsonl", [])
    write_jsonl(
        ledger / "sources" / "code_style.jsonl",
        [
            source_row(
                "code_style_signal",
                f"style-{index}",
                "Representative React TSX hook and typed component example",
                {"patterns": {"react_component": 5, "react_hooks": 3, "lint_format_quality": 2}, "path": "src/components/Table.tsx"},
                ["code_style", "react", "typescript"],
            )
            for index in range(5)
        ],
    )
    write_jsonl(
        ledger / "sources" / "career_facts.jsonl",
        [
            source_row(
                "career_fact",
                "declared-fe-lead",
                "Declared formal role: Frontend Lead with frontend-heavy full-product scope",
                {"formal_title": "Frontend Lead", "declared_scope": "frontend-heavy product engineering", "formal_years": ""},
                ["career_fact", "declared"],
            )
        ],
    )
    write_jsonl(
        ledger / "sources" / "release_activity.jsonl",
        [
            source_row(
                "release_activity",
                f"release-{index}",
                "Resolved GitHub Actions deploy workflow failure for release-bound frontend work",
                {"repo": "example/product-web", "workflow": "deploy", "outcome": "fixed_ci_failure"},
                ["release", "ci_cd", "github_actions"],
            )
            for index in range(2)
        ],
    )
    write_jsonl(
        ledger / "sources" / "jira_leadership_signals.jsonl",
        [
            source_row(
                "jira_leadership_signal",
                f"leadership-{index}",
                "Coordinated QA blocker to Done with release handoff context",
                {"key": f"CC-{index}", "transition": "QA to Done", "authored_by_user": True},
                ["jira", "qa", "blocker", "done"],
            )
            for index in range(2)
        ],
    )
    write_jsonl(
        ledger / "sources" / "architecture_material.jsonl",
        [
            source_row(
                "architecture_material",
                "lookup-v4-migration",
                "Architecture note for lookup v4 migration and frontend contract standard",
                {"doc_type": "migration_plan", "summary": "typed API contract, rollout, QA risks"},
                ["architecture", "migration", "standards"],
            )
        ],
    )
    write_jsonl(
        ledger / "sources" / "agent_sessions.jsonl",
        [
            source_row(
                "agent_session",
                "codex-correction-style",
                "Agent session pattern: require exact scope, verification, and no unsupported claims",
                {"redacted": True, "patterns": ["verification", "scope_control", "proof_policy"]},
                ["agent", "codex", "collaboration"],
            )
        ],
    )
    write_jsonl(
        ledger / "sources" / "portfolio_cases.jsonl",
        [
            source_row(
                "portfolio_case",
                "ai-chat-workflow",
                "Sanitized portfolio case for AI chat workflow and reporting product surface",
                {"public_safe": True, "surface": "AI chat and analytics reporting"},
                ["portfolio", "case_study", "ai_product"],
            )
        ],
    )
    write_jsonl(
        ledger / "sources" / "personal_material.jsonl",
        [
            source_row(
                "personal_material",
                "engineering-values",
                "Personal work preference: direct execution, high technical bar, proof-first claims",
                {"values": ["clarity", "pragmatism", "rigor"], "boundary": "do not invent unsupported personal facts"},
                ["personal", "values", "preferences"],
            )
        ],
    )


def build_synthetic_ledger(ledger: Path) -> None:
    seed_ledger(ledger)
    run_script("build_memory_atoms.py", "--ledger", str(ledger), "--json")
    run_script("build_context_packs.py", "--ledger", str(ledger), "--json")
    run_script("build_sqlite_index.py", "--ledger", str(ledger), "--json")
    run_script("build_memory_index.py", "--ledger", str(ledger), "--backend", "hashing", "--json")


def has_real_ledger_ready(ledger: Path) -> bool:
    derived = ledger / "derived"
    return all((derived / name).exists() for name in REQUIRED_REAL_FILES)


def evaluate_style_contract(style_contract: str, direct_answer: str) -> tuple[bool, str]:
    lowered = direct_answer.lower()
    if style_contract == "first_person_contract":
        passed = is_first_person_or_directive(direct_answer)
        return passed, "direct_answer must be first-person or directive"
    if style_contract == "third_person_identity":
        passed = not is_first_person_or_directive(direct_answer) and any(
            token in lowered
            for token in ["example user ", "example user is", "example user's", "the engineer ", "he ", "his "]
        )
        passed = passed or (
            not is_first_person_or_directive(direct_answer)
            and bool(THIRD_PERSON_SUBJECT_PATTERN.search(direct_answer))
        )
        return passed, "direct_answer must stay in third-person identity form"
    passed = not any(phrase in lowered for phrase in LEGACY_PHRASES) and not any(phrase in lowered for phrase in VOICE_BANNED_PHRASES)
    return passed, "direct_answer must stay free of evidence-style or banned phrasing"


def has_source_leak(text: str) -> bool:
    return any(pattern.search(text) for pattern in SOURCE_ID_PATTERNS)


def answer_material_text(context: dict[str, Any]) -> str:
    material = context.get("answer_material") if isinstance(context.get("answer_material"), dict) else {}
    return json.dumps(material, ensure_ascii=False).lower()


def run_case(ledger: Path, case: dict[str, Any]) -> dict[str, Any]:
    result = query_self_context(ledger, case["query"], top=3)
    answer_contexts = result.get("answer_contexts", [])
    first = answer_contexts[0] if answer_contexts else {}
    first_text = json.dumps(first, ensure_ascii=False).lower()
    material_text = answer_material_text(first)
    serialized = json.dumps(result, ensure_ascii=False).lower()
    direct_answer = str(first.get("direct_answer", ""))
    checks: list[dict[str, Any]] = []

    def add_check(name: str, passed: bool, details: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "details": details})

    add_check("has_answer_context", bool(answer_contexts), "query must return at least one context")
    add_check("has_answer_material", bool(material_text), "first context must include answer_material")
    add_check("intent", result.get("intent") == case["expected_intent"], f"expected intent {case['expected_intent']}, got {result.get('intent')}")
    add_check(
        "first_context",
        str(first.get("id", "")) == case["expected_first_context"],
        f"expected first context {case['expected_first_context']}, got {first.get('id')}",
    )

    style_passed, style_details = evaluate_style_contract(str(case["style_contract"]), direct_answer)
    add_check("style_contract", style_passed, style_details)

    evidence_phrase_leak = (
        any(phrase in first_text for phrase in LEGACY_PHRASES)
        or any(phrase in first_text for phrase in VOICE_BANNED_PHRASES)
        or any(
            phrase in first_text
            for phrase in [
                "use this topic pack",
                "common implementation surfaces",
                "declared profile should",
                "release ownership layer",
                "my release ownership layer",
                "he likely",
                "private_trace_refs",
            ]
        )
    )

    if case["provenance_policy"] == "hidden_by_default":
        add_check("no_evidence_style", not evidence_phrase_leak, "first context must not include legacy evidence phrasing")
        add_check("answer_material_clean", "context pack" not in material_text and not has_source_leak(material_text), "answer_material must be answer-ready and source-id-free")
        add_check("provenance_hidden", "provenance" not in result, "default query must not return provenance")
        add_check(
            "trace_hidden",
            "private_trace_refs" not in serialized and "source_id" not in serialized and not has_source_leak(first_text),
            "default query must hide source ids and private trace refs",
        )
    else:
        provenance = result.get("provenance", [])
        add_check("provenance_available", bool(provenance), "explicit proof query must return provenance")
        add_check("source_ids_present", "source_id" in serialized, "proof query should expose source ids only in proof mode")

    for token in case.get("must_contain", []):
        add_check(f"must_contain:{token}", token.lower() in serialized, f"result must contain {token!r}")
    for token in case.get("must_not_contain", []):
        add_check(f"must_not_contain:{token}", token.lower() not in serialized, f"result must not contain {token!r}")

    return {
        "id": case["id"],
        "suite": case["suite"],
        "language": case["language"],
        "query": case["query"],
        "expected_intent": case["expected_intent"],
        "resolved_intent": result.get("intent"),
        "expected_first_context": case["expected_first_context"],
        "first_context_id": first.get("id"),
        "style_contract": case["style_contract"],
        "provenance_policy": case["provenance_policy"],
        "provenance_included": "provenance" in result,
        "checks": checks,
        "passes": all(check["passed"] for check in checks),
    }


def summarize_case_results(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    by_language: dict[str, dict[str, int]] = {}
    for item in case_results:
        bucket = by_language.setdefault(str(item["language"]), {"total": 0, "passed": 0, "failed": 0})
        bucket["total"] += 1
        if item.get("passes"):
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
    passed = sum(1 for item in case_results if item.get("passes"))
    total = len(case_results)
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "languages": by_language,
        "passes": total > 0 and passed == total,
    }


def run_suite(suite: str, ledger: Path | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cases = benchmark_cases_for_suite(suite)
    if suite == "synthetic":
        temp_ledger = Path(tempfile.mkdtemp(prefix="self-context-retrieval-"))
        try:
            build_synthetic_ledger(temp_ledger)
            case_results = [run_case(temp_ledger, case) for case in cases]
            summary = summarize_case_results(case_results)
            summary["skipped"] = False
            return summary, case_results
        finally:
            shutil.rmtree(temp_ledger, ignore_errors=True)

    assert ledger is not None
    if not has_real_ledger_ready(ledger):
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "languages": {},
            "passes": True,
            "skipped": True,
            "reason": "real ledger derived artifacts are not ready",
        }, []

    case_results = [run_case(ledger, case) for case in cases]
    summary = summarize_case_results(case_results)
    summary["skipped"] = False
    return summary, case_results


def build_report(suite_results: dict[str, Any], case_results: list[dict[str, Any]], ledger: Path | None) -> dict[str, Any]:
    cases_run = [item["id"] for item in case_results]
    report = {
        "generated_at": now_iso(),
        "architecture": ARCHITECTURE,
        "suite_results": suite_results,
        "summary": {
            "suites_run": sorted(suite_results.keys()),
            "cases_run": len(case_results),
            "cases_passed": sum(1 for item in case_results if item.get("passes")),
            "cases_failed": sum(1 for item in case_results if not item.get("passes")),
            "bilingualCoverage": {
                "en": any(item.get("language") == "en" for item in case_results),
                "zh-CN": any(item.get("language") == "zh-CN" for item in case_results),
            },
            "case_ids": cases_run,
        },
        "case_results": case_results,
        "input_fingerprints": retrieval_input_fingerprints(ledger) if ledger else {},
    }
    report["passes"] = all(summary.get("passes", False) for summary in suite_results.values())
    if ledger:
        report["stale"] = retrieval_eval_is_stale(report, ledger)
    else:
        report["stale"] = False
    return report


def main() -> None:
    load_benchmark_spec()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--suite", choices=["synthetic", "real", "all"], default="all")
    parser.add_argument("--write-report", action="store_true", help="Write derived/retrieval_eval.json for real-suite runs.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    resolved_ledger = resolve_ledger_path(args.ledger) if args.ledger or args.suite != "synthetic" or args.write_report else None
    suite_names = ["synthetic", "real"] if args.suite == "all" else [args.suite]
    suite_results: dict[str, Any] = {}
    case_results: list[dict[str, Any]] = []

    for suite_name in suite_names:
        summary, results = run_suite(suite_name, resolved_ledger)
        suite_results[suite_name] = summary
        case_results.extend(results)

    report = build_report(suite_results, case_results, resolved_ledger if "real" in suite_results and not suite_results["real"].get("skipped") else None)

    if args.write_report:
        if args.suite not in {"real", "all"} or not resolved_ledger:
            raise SystemExit("--write-report requires a real ledger suite")
        derived = resolved_ledger / "derived"
        if suite_results.get("real", {}).get("skipped"):
            raise SystemExit("real ledger is not ready; cannot write retrieval_eval.json")
        write_json(derived / "retrieval_eval.json", report)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"retrieval_benchmarks suites={','.join(suite_names)} "
            f"cases={report['summary']['cases_run']} passed={report['summary']['cases_passed']} failed={report['summary']['cases_failed']}"
        )

    if not report.get("passes", False):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
