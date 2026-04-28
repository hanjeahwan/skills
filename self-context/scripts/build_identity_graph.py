#!/usr/bin/env python3
"""Build dense identity facts, graph nodes, and answer-ready identity atoms."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from source_families import ARCHITECTURE_VERSION, SOURCE_FAMILY_DEFINITIONS, SOURCE_FILES

STACK_GROUPS = {
    "react_next": ["react", "next.js", "nextjs", ".tsx", ".jsx", "usestate", "useeffect", "usememo", "hooks"],
    "angular_rxjs": ["angular", "@angular", "rxjs", "observable", "ngmodule", "component", "oninit"],
    "typescript": ["typescript", ".ts", ".tsx", "interface", "type ", "enum", "generic"],
    "state_data_flow": ["zustand", "store", "state", "selector", "swr", "query", "mapper", "service"],
    "api_auth_security": ["api", "endpoint", "payload", "contract", "auth", "auth0", "cognito", "rbac", "permission", "token"],
    "analytics_reporting": ["analytics", "report", "reporting", "dashboard", "chart", "export", "insight"],
    "ci_cd_infra": ["github actions", ".github/workflows", "ci", "cd", "deploy", "pipeline", "semantic-release", "sentry"],
    "ai_agent_mcp": ["ai", "agent", "mcp", "chat", "skill", "openai", "gpt", "generative"],
    "testing_quality": ["test", "testing", "spec", "qa", "bug", "fix", "validation", "reopen"],
}

DOMAIN_GROUPS = {
    "recruiting_candidate": ["candidate", "recruit", "recruiting", "role fit", "assessment", "job", "profile", "hiring"],
    "employee_learning": ["employee", "learning", "course", "goal", "lxp", "action item", "go1"],
    "analytics_reporting": ["analytics", "report", "dashboard", "chart", "export", "insight"],
    "admin_internal_tools": ["admin", "console", "internal", "operator", "backoffice", "configuration"],
    "workflow_correctness": ["workflow", "status", "state", "disabled", "visibility", "permission", "empty", "missing"],
}

ROLE_GROUPS = {
    "frontend_lead_behavior": ["frontend", "review", "approve", "architecture", "qa", "release", "lead", "owner"],
    "architecture_reviewer": ["architecture", "contract", "shared", "migration", "api", "permission", "boundary"],
    "quality_gatekeeper": ["bug", "fix", "qa", "review", "validation", "maintainability", "reliability"],
    "delivery_owner": ["done", "release", "deployed", "qa", "stage", "production", "hotfix", "blocked"],
    "product_minded_engineer": ["workflow", "candidate", "employee", "analytics", "report", "customer", "product"],
    "agent_native_builder": ["agent", "mcp", "skill", "chat", "rag", "context", "ai"],
}


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


def stable_hash(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    if re.search(r"[+-]\d{4}$", text):
        text = f"{text[:-5]}{text[-5:-2]}:{text[-2:]}"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def month_label(value: datetime | None) -> str:
    return value.strftime("%B %Y") if value else ""


def years_between(start: datetime | None, end: datetime | None) -> float:
    if not start or not end or end < start:
        return 0.0
    return round((end - start).days / 365.2425, 1)


def as_text(value: Any) -> str:
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, list):
        return " ".join(as_text(item) for item in value)
    return "" if value is None else str(value)


def row_text(row: dict[str, Any]) -> str:
    return " ".join(
        [
            str(row.get("title", "")),
            str(row.get("summary", "")),
            as_text(row.get("raw_excerpt", {})),
            as_text(row.get("tags", [])),
            str(row.get("url_or_path", "")),
        ]
    ).lower()


def count_keyword_hits(rows: Iterable[dict[str, Any]], groups: dict[str, list[str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for group, keywords in groups.items():
        total = 0
        for row in rows:
            text = row_text(row)
            if any(keyword.lower() in text for keyword in keywords):
                total += 1
        counts[group] = total
    return counts


def source_ref(row: dict[str, Any]) -> dict[str, str]:
    return {
        "id": str(row.get("id", "")),
        "source_type": str(row.get("source_type", "")),
    }


def compact_list(values: Iterable[str], limit: int) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = re.sub(r"\s+", " ", str(value)).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
        if len(output) >= limit:
            break
    return output


def confidence_from_count(count: int) -> str:
    if count >= 100:
        return "strong"
    if count >= 20:
        return "medium"
    return "weak"


def freshness_from_latest(latest: datetime | None) -> str:
    if not latest:
        return "unknown"
    if latest.year >= 2025:
        return "current"
    if latest.year >= 2023:
        return "recent"
    return "historical"


def source_rows_by_file(ledger: Path) -> dict[str, list[dict[str, Any]]]:
    sources = ledger / "sources"
    return {name: read_jsonl(sources / name) for name in SOURCE_FILES}


def rows_for_files(rows_by_file: dict[str, list[dict[str, Any]]], files: list[str]) -> list[dict[str, Any]]:
    return [row for name in files for row in rows_by_file.get(name, [])]


def build_source_family_coverage(rows_by_file: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    coverage: dict[str, Any] = {}
    for family_id, definition in SOURCE_FAMILY_DEFINITIONS.items():
        files = [str(item) for item in definition["files"]]
        rows = rows_for_files(rows_by_file, files)
        coverage[family_id] = {
            "files": files,
            "rows": len(rows),
            "has_material": bool(rows),
            "status": "available" if rows else "unknown_gap",
            "memory_type": definition["memory_type"],
            "section_id": definition["section_id"],
            "unknown_gap": "" if rows else definition["empty_status"],
        }
    return coverage


def date_ranges(rows_by_file: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, Any], datetime | None, datetime | None]:
    ranges: dict[str, Any] = {}
    all_dates: list[datetime] = []
    for name, rows in rows_by_file.items():
        dates = [parsed for row in rows if (parsed := parse_dt(row.get("occurred_at")))]
        all_dates.extend(dates)
        ranges[name] = {
            "rows": len(rows),
            "earliest": min(dates).date().isoformat() if dates else "",
            "latest": max(dates).date().isoformat() if dates else "",
        }
    return ranges, min(all_dates) if all_dates else None, max(all_dates) if all_dates else None


def year_profile(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_year: dict[int, Counter[str]] = defaultdict(Counter)
    for row in rows:
        parsed = parse_dt(row.get("occurred_at"))
        if not parsed:
            continue
        by_year[parsed.year][str(row.get("source_type", ""))] += 1
    return [
        {
            "year": year,
            "total": sum(counter.values()),
            "source_types": dict(counter.most_common()),
        }
        for year, counter in sorted(by_year.items())
    ]


def repo_counts(rows: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        raw = row.get("raw_excerpt") if isinstance(row.get("raw_excerpt"), dict) else {}
        repo = raw.get("repo")
        if repo:
            counter[str(repo)] += 1
    return counter


def code_pattern_counts(rows: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        raw = row.get("raw_excerpt") if isinstance(row.get("raw_excerpt"), dict) else {}
        patterns = raw.get("patterns") if isinstance(raw.get("patterns"), dict) else {}
        for name, value in patterns.items():
            try:
                counter[str(name)] += int(value)
            except (TypeError, ValueError):
                counter[str(name)] += 1
    return counter


def matching_refs(rows: list[dict[str, Any]], keywords: list[str], limit: int = 80) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for row in rows:
        text = row_text(row)
        if any(keyword.lower() in text for keyword in keywords):
            refs.append(source_ref(row))
        if len(refs) >= limit:
            break
    return refs


def timeline_refs(rows: list[dict[str, Any]], limit: int = 80) -> list[dict[str, str]]:
    dated = [(parse_dt(row.get("occurred_at")), row) for row in rows]
    dated = [(dt, row) for dt, row in dated if dt]
    if not dated:
        return []
    dated.sort(key=lambda item: item[0])
    selected = [row for _dt, row in dated[:12]]
    selected.extend(row for _dt, row in dated[-12:])
    step = max(1, math.floor(len(dated) / 12))
    selected.extend(row for _dt, row in dated[::step][:12])
    refs = []
    seen: set[str] = set()
    for row in selected:
        row_id = str(row.get("id", ""))
        if not row_id or row_id in seen:
            continue
        seen.add(row_id)
        refs.append(source_ref(row))
        if len(refs) >= limit:
            break
    return refs


def trace_links(memory_id: str, trace_id: str, refs: list[dict[str, str]], generated_at: str, strength: str) -> list[dict[str, Any]]:
    links = []
    seen: set[str] = set()
    for index, ref in enumerate(refs[:80]):
        source_id = str(ref.get("id", ""))
        if not source_id or source_id in seen:
            continue
        seen.add(source_id)
        links.append(
            {
                "id": f"{trace_id}:{stable_hash(source_id, 12)}",
                "memory_id": memory_id,
                "source_id": source_id,
                "source_type": str(ref.get("source_type", "")),
                "support_role": "primary" if index < 8 else "supporting",
                "strength": strength,
                "reason": "Dense identity graph source signal supports this personal context memory.",
                "visibility": "internal",
                "updated_at": generated_at,
            }
        )
    return links


def build_identity_facts(ledger: Path, atoms: list[dict[str, Any]], generated_at: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, list[dict[str, str]]]]:
    rows_by_file = source_rows_by_file(ledger)
    all_rows = [row for rows in rows_by_file.values() for row in rows]
    ranges, earliest, latest = date_ranges(rows_by_file)
    years = years_between(earliest, latest)
    source_type_counts = Counter(str(row.get("source_type", "")) for row in all_rows)
    repos = repo_counts(all_rows)
    stack_counts = count_keyword_hits(all_rows, STACK_GROUPS)
    domain_counts = count_keyword_hits(all_rows, DOMAIN_GROUPS)
    role_counts = count_keyword_hits(all_rows, ROLE_GROUPS)
    pattern_counts = code_pattern_counts(rows_by_file.get("code_style.jsonl", []))
    review_rows = rows_by_file.get("github_pr_reviews.jsonl", [])
    authority_rows = rows_by_file.get("github_authority_signals.jsonl", [])
    jira_rows = rows_by_file.get("jira.jsonl", [])
    changelog_rows = rows_by_file.get("jira_changelog.jsonl", [])
    career_fact_rows = rows_by_file.get("career_facts.jsonl", [])
    release_rows = rows_by_file.get("release_activity.jsonl", [])
    jira_leadership_rows = rows_by_file.get("jira_leadership_signals.jsonl", [])
    architecture_rows = rows_by_file.get("architecture_material.jsonl", [])
    agent_session_rows = rows_by_file.get("agent_sessions.jsonl", [])
    portfolio_rows = rows_by_file.get("portfolio_cases.jsonl", [])
    personal_rows = rows_by_file.get("personal_material.jsonl", [])
    pr_activity_rows = rows_by_file.get("github_pr_activity.jsonl", [])
    source_family_coverage = build_source_family_coverage(rows_by_file)
    release_support_rows = release_rows + [
        row for row in all_rows if any(term in row_text(row) for term in ["release", "hotfix", "deploy", "ci", "workflow", "github actions", "pipeline"])
    ]
    jira_leadership_support_rows = jira_leadership_rows + jira_rows + rows_by_file.get("jira_comments.jsonl", []) + changelog_rows
    architecture_support_rows = architecture_rows + [
        row for row in all_rows if any(term in row_text(row) for term in ["architecture", "rfc", "migration", "standard", "design doc", "mcp", "agent"])
    ]

    declared_facts = [
        row
        for row in [*career_fact_rows, *rows_by_file.get("manual.jsonl", [])]
        if "declared" in row_text(row) or "formal" in row_text(row) or "title" in row_text(row)
    ]
    formal_years_declared = ""
    formal_title_declared = ""
    for row in declared_facts:
        text = row_text(row)
        if not formal_years_declared:
            match = re.search(r"(\d+(?:\.\d+)?)\s*(?:years|year|yrs)", text)
            if match:
                formal_years_declared = match.group(1)
        if not formal_title_declared and ("lead" in text or "title" in text):
            formal_title_declared = str(row.get("summary") or row.get("title") or "").strip()

    atom_topics = Counter(topic for atom in atoms for topic in atom.get("topics", []))
    atom_types = Counter(str(atom.get("memory_type", "")) for atom in atoms)

    facts = {
        "generated_at": generated_at,
        "architecture": "self-context-v2.8",
        "subject": "example-user",
        "source_family_coverage": source_family_coverage,
        "declared_profile": {
            "formal_title": formal_title_declared,
            "formal_experience_years": formal_years_declared,
            "declared_rows": len(declared_facts),
            "career_fact_rows": len(career_fact_rows),
            "confidence_class": "declared" if declared_facts else "unknown",
            "unknown_gap": "" if declared_facts else SOURCE_FAMILY_DEFINITIONS["career_facts"]["empty_status"],
        },
        "career_timeline": {
            "engineering_activity_start": earliest.date().isoformat() if earliest else "",
            "engineering_activity_end": latest.date().isoformat() if latest else "",
            "start_label": month_label(earliest),
            "end_label": month_label(latest),
            "evidence_backed_years": years,
            "evidence_backed_years_floor": int(math.floor(years)),
            "formal_experience_years": formal_years_declared,
            "formal_title": formal_title_declared,
            "confidence": "evidenced" if earliest and latest else "unknown",
            "year_profile": year_profile(all_rows),
        },
        "experience_scope": {
            "primary_scope": "frontend/product engineering",
            "secondary_scope": "backend-adjacent API, service, schema, serverless, CI/CD, release, and AI product systems",
            "full_stack_policy": "Treat the profile as frontend-heavy with strong full-product and backend-adjacent evidence; do not call all years formal full-stack tenure without a declared career fact.",
            "stack_signal_counts": stack_counts,
            "source_type_counts": dict(source_type_counts.most_common()),
            "top_repositories": [{"repo": repo, "rows": count} for repo, count in repos.most_common(12)],
        },
        "role_identity": {
            "role_signals": role_counts,
            "review_rows": len(review_rows),
            "authority_rows": len(authority_rows),
            "jira_assigned_or_owned_rows": len(jira_rows),
            "jira_transition_rows": len(changelog_rows),
            "formal_people_management": "unknown",
            "formal_fe_lead_title": formal_title_declared or "unknown",
        },
        "technical_stack": {
            "stack_signal_counts": stack_counts,
            "code_pattern_counts": dict(pattern_counts.most_common(20)),
            "strongest_stack_groups": [name for name, count in sorted(stack_counts.items(), key=lambda item: item[1], reverse=True) if count > 0][:10],
        },
        "domain_knowledge": {
            "domain_signal_counts": domain_counts,
            "strongest_domains": [name for name, count in sorted(domain_counts.items(), key=lambda item: item[1], reverse=True) if count > 0][:8],
        },
        "impact_profile": {
            "bug_quality_rows": stack_counts.get("testing_quality", 0),
            "ci_cd_rows": stack_counts.get("ci_cd_infra", 0),
            "review_rows": len(review_rows),
            "jira_done_or_release_rows": sum(1 for row in jira_rows + changelog_rows if any(term in row_text(row) for term in ["done", "release", "resolved", "qa", "production", "hotfix"])),
        },
        "relationship_authority": {
            "review_rows": len(review_rows),
            "authority_signal_rows": len(authority_rows),
            "repo_authority_distribution": [{"repo": repo, "rows": count} for repo, count in repo_counts(review_rows + authority_rows).most_common(12)],
        },
        "review_style": {
            "pr_activity_rows": len(pr_activity_rows),
            "review_rows": len(review_rows),
            "theme_signal_counts": count_keyword_hits(pr_activity_rows + review_rows, {**STACK_GROUPS, **ROLE_GROUPS}),
            "confidence_class": "evidenced" if pr_activity_rows or review_rows else "unknown",
            "unknown_gap": "" if pr_activity_rows or review_rows else SOURCE_FAMILY_DEFINITIONS["github_pr_activity"]["empty_status"],
        },
        "repo_authority": {
            "authority_signal_rows": len(authority_rows),
            "repo_authority_distribution": [{"repo": repo, "rows": count} for repo, count in repo_counts(authority_rows).most_common(12)],
            "confidence_class": "evidenced" if authority_rows else "unknown",
            "unknown_gap": "" if authority_rows else SOURCE_FAMILY_DEFINITIONS["github_authority_signals"]["empty_status"],
        },
        "release_ownership": {
            "release_activity_rows": len(release_rows),
            "supporting_release_rows": len(release_support_rows),
            "ci_cd_rows": stack_counts.get("ci_cd_infra", 0),
            "hotfix_or_deploy_rows": sum(1 for row in release_support_rows if any(term in row_text(row) for term in ["hotfix", "deploy", "release", "workflow", "ci"])),
            "confidence_class": "evidenced" if release_support_rows else "unknown",
            "unknown_gap": "" if release_support_rows else SOURCE_FAMILY_DEFINITIONS["release_activity"]["empty_status"],
        },
        "jira_leadership": {
            "jira_leadership_rows": len(jira_leadership_rows),
            "supporting_jira_rows": len(jira_leadership_support_rows),
            "qa_blocker_done_rows": sum(1 for row in jira_leadership_support_rows if any(term in row_text(row) for term in ["qa", "blocked", "blocker", "reopen", "hotfix", "done", "release"])),
            "confidence_class": "evidenced" if jira_leadership_support_rows else "unknown",
            "unknown_gap": "" if jira_leadership_support_rows else SOURCE_FAMILY_DEFINITIONS["jira_leadership_signals"]["empty_status"],
        },
        "architecture_material": {
            "architecture_rows": len(architecture_rows),
            "supporting_architecture_rows": len(architecture_support_rows),
            "confidence_class": "evidenced" if architecture_rows else "unknown",
            "unknown_gap": "" if architecture_rows else SOURCE_FAMILY_DEFINITIONS["architecture_material"]["empty_status"],
        },
        "agent_collaboration_style": {
            "agent_session_rows": len(agent_session_rows),
            "confidence_class": "evidenced" if agent_session_rows else "unknown",
            "unknown_gap": "" if agent_session_rows else SOURCE_FAMILY_DEFINITIONS["agent_sessions"]["empty_status"],
        },
        "portfolio_cases": {
            "portfolio_rows": len(portfolio_rows),
            "confidence_class": "declared" if portfolio_rows else "unknown",
            "unknown_gap": "" if portfolio_rows else SOURCE_FAMILY_DEFINITIONS["portfolio_cases"]["empty_status"],
        },
        "personal_identity": {
            "personal_material_rows": len(personal_rows),
            "confidence_class": "declared" if personal_rows else "unknown",
            "unknown_gap": "" if personal_rows else SOURCE_FAMILY_DEFINITIONS["personal_material"]["empty_status"],
        },
        "learning_trajectory": {
            "earliest_phase": "Angular/shared-library and enterprise frontend foundation" if earliest else "",
            "current_phase": "AI product, agent tooling, web infrastructure, and lead-level frontend delivery" if latest and latest.year >= 2025 else "",
            "atom_type_counts": dict(atom_types.most_common()),
            "top_atom_topics": dict(atom_topics.most_common(20)),
        },
        "confidence_policy": {
            "declared": "Only use for facts explicitly supplied in manual/private material.",
            "evidenced": "Use for facts directly backed by local Git, PR, review, Jira, code-style, or authored comment ranges.",
            "inferred": "Use for repeated behavior patterns across many work signals.",
            "unknown": "State as unknown when the ledger has no direct support.",
        },
        "source_date_ranges": ranges,
    }

    refs = {
        "career_timeline": timeline_refs(all_rows),
        "experience_scope": matching_refs(all_rows, ["frontend", "api", "service", "serverless", "ci", "deploy", "ai", "mcp", "agent"]),
        "role_identity": matching_refs(all_rows, ROLE_GROUPS["frontend_lead_behavior"]),
        "technical_stack": matching_refs(all_rows, [keyword for values in STACK_GROUPS.values() for keyword in values]),
        "impact_profile": matching_refs(all_rows, ["bug", "fix", "qa", "release", "hotfix", "reopen", "deploy", "ci"]),
        "review_authority": [source_ref(row) for row in (review_rows + authority_rows)[:80]],
        "learning_trajectory": timeline_refs(all_rows),
        "declared_profile": [source_ref(row) for row in declared_facts[:80]],
        "review_style": [source_ref(row) for row in (pr_activity_rows + review_rows)[:80]],
        "repo_authority": [source_ref(row) for row in authority_rows[:80]],
        "release_ownership": [source_ref(row) for row in release_support_rows[:80]],
        "jira_leadership": [source_ref(row) for row in jira_leadership_support_rows[:80]],
        "architecture_material": [source_ref(row) for row in architecture_rows[:80]],
        "agent_collaboration_style": [source_ref(row) for row in agent_session_rows[:80]],
        "portfolio_cases": [source_ref(row) for row in portfolio_rows[:80]],
        "personal_identity": [source_ref(row) for row in personal_rows[:80]],
    }

    graph = build_identity_graph(facts, generated_at)
    return facts, graph, refs


def build_identity_graph(facts: dict[str, Any], generated_at: str) -> dict[str, Any]:
    nodes = [
        {"id": "identity:career_timeline", "kind": "career_timeline", "label": "Evidence-backed engineering timeline"},
        {"id": "identity:experience_scope", "kind": "experience_scope", "label": "Frontend-heavy full-product scope"},
        {"id": "identity:role_identity", "kind": "role_identity", "label": "FE lead behavior and delivery authority"},
        {"id": "identity:technical_stack", "kind": "technical_stack", "label": "Frontend, API, infra, AI stack map"},
        {"id": "identity:impact_profile", "kind": "impact_profile", "label": "Bug reduction, QA, release, and infra impact"},
        {"id": "identity:review_authority", "kind": "review_authority", "label": "PR review and quality-gate authority"},
        {"id": "identity:learning_trajectory", "kind": "learning_trajectory", "label": "Growth from implementation to lead-level judgment"},
        {"id": "identity:declared_profile", "kind": "declared_profile", "label": "Declared title, tenure, scope, and promotion facts"},
        {"id": "identity:review_style", "kind": "review_style", "label": "Authored PR review reasoning and quality themes"},
        {"id": "identity:repo_authority", "kind": "repo_authority", "label": "Repository authority, review requests, and governance signals"},
        {"id": "identity:release_ownership", "kind": "release_ownership", "label": "Release, hotfix, workflow, deploy, and CI/CD ownership"},
        {"id": "identity:jira_leadership", "kind": "jira_leadership", "label": "Jira coordination, QA, blockers, reopen, and Done ownership"},
        {"id": "identity:architecture_material", "kind": "architecture_material", "label": "Architecture docs, RFCs, migration plans, and standards"},
        {"id": "identity:agent_collaboration_style", "kind": "agent_collaboration_style", "label": "Agent session history and collaboration preferences"},
        {"id": "identity:portfolio_cases", "kind": "portfolio_cases", "label": "Sanitized product case studies and showcase material"},
        {"id": "identity:personal_identity", "kind": "personal_identity", "label": "Personal values, goals, preferences, and life context"},
    ]
    edges = [
        {"from": "identity:career_timeline", "to": "identity:experience_scope", "relation": "supports", "weight": 0.9},
        {"from": "identity:experience_scope", "to": "identity:technical_stack", "relation": "refines", "weight": 0.85},
        {"from": "identity:role_identity", "to": "identity:review_authority", "relation": "supports", "weight": 0.85},
        {"from": "identity:role_identity", "to": "identity:impact_profile", "relation": "supports", "weight": 0.8},
        {"from": "identity:technical_stack", "to": "identity:learning_trajectory", "relation": "refines", "weight": 0.75},
        {"from": "identity:impact_profile", "to": "identity:experience_scope", "relation": "co_occurs_with", "weight": 0.7},
        {"from": "identity:declared_profile", "to": "identity:career_timeline", "relation": "supersedes", "weight": 0.95},
        {"from": "identity:review_style", "to": "identity:review_authority", "relation": "refines", "weight": 0.88},
        {"from": "identity:repo_authority", "to": "identity:role_identity", "relation": "supports", "weight": 0.82},
        {"from": "identity:release_ownership", "to": "identity:impact_profile", "relation": "supports", "weight": 0.82},
        {"from": "identity:jira_leadership", "to": "identity:delivery_leadership", "relation": "supports", "weight": 0.8},
        {"from": "identity:architecture_material", "to": "identity:architecture_judgment", "relation": "supports", "weight": 0.8},
        {"from": "identity:agent_collaboration_style", "to": "identity:agent_operating_context", "relation": "refines", "weight": 0.75},
        {"from": "identity:portfolio_cases", "to": "identity:impact_profile", "relation": "supports", "weight": 0.65},
        {"from": "identity:personal_identity", "to": "identity:agent_operating_context", "relation": "refines", "weight": 0.65},
    ]
    return {
        "generated_at": generated_at,
        "architecture": "self-context-v2.8",
        "subject": "example-user",
        "nodes": nodes,
        "edges": [{**edge, "updated_at": generated_at} for edge in edges],
        "source_sections": [
            "career_timeline",
            "experience_scope",
            "role_identity",
            "technical_stack",
            "impact_profile",
            "review_authority",
            "learning_trajectory",
            "declared_profile",
            "review_style",
            "repo_authority",
            "release_ownership",
            "jira_leadership",
            "architecture_material",
            "agent_collaboration_style",
            "portfolio_cases",
            "personal_identity",
        ],
        "summary": {
            "evidence_backed_years": facts.get("career_timeline", {}).get("evidence_backed_years"),
            "strongest_stack_groups": facts.get("technical_stack", {}).get("strongest_stack_groups", []),
            "strongest_domains": facts.get("domain_knowledge", {}).get("strongest_domains", []),
            "source_family_coverage": facts.get("source_family_coverage", {}),
        },
    }


def atom(
    memory_type: str,
    suffix: str,
    statement: str,
    useful_context: list[str],
    topics: list[str],
    query_patterns: list[str],
    behavioral_use: str,
    guardrails: list[str],
    facts: dict[str, Any],
    refs: list[dict[str, str]],
    generated_at: str,
    confidence: str = "strong",
    confidence_class: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    memory_id = f"memory:{memory_type}.{suffix}"
    trace_id = f"trace:{memory_type}.{suffix}"
    source_type_counts = Counter(ref["source_type"] for ref in refs)
    latest = parse_dt(facts.get("career_timeline", {}).get("engineering_activity_end"))
    row = {
        "id": memory_id,
        "subject": "example-user",
        "memory_type": memory_type,
        "statement": statement,
        "useful_context": useful_context,
        "topics": topics,
        "facets": {
            "domain": "work",
            "time_scope": "multi_year",
            "confidence": confidence,
            "confidence_class": confidence_class or ("evidenced" if confidence in {"strong", "medium"} else "inferred"),
            "sensitivity": "private_work",
            "freshness": freshness_from_latest(latest),
            "source": "dense_identity_graph_v2.8",
            "supporting_source_count": len(refs),
            "supporting_source_types": dict(source_type_counts.most_common()),
        },
        "query_patterns": query_patterns,
        "behavioral_use": behavioral_use,
        "guardrails": guardrails,
        "provenance_refs": [trace_id] if refs else [],
        "updated_at": generated_at,
    }
    return row, trace_links(memory_id, trace_id, refs, generated_at, confidence)


def build_identity_atoms(facts: dict[str, Any], refs: dict[str, list[dict[str, str]]], generated_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    timeline = facts["career_timeline"]
    start_label = timeline.get("start_label") or timeline.get("engineering_activity_start") or "the earliest local source"
    end_label = timeline.get("end_label") or timeline.get("engineering_activity_end") or "the latest local source"
    years = timeline.get("evidence_backed_years", 0)
    years_floor = timeline.get("evidence_backed_years_floor", 0)
    year_phrase = f"at least about {years_floor} years" if years_floor else "multi-year"
    atoms: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []

    def has_family_material(section: str) -> bool:
        value = facts.get(section, {})
        return isinstance(value, dict) and str(value.get("confidence_class", "")) != "unknown"

    def confidence_for(section: str) -> tuple[str, str]:
        return ("medium", "evidenced") if has_family_material(section) else ("weak", "unknown")

    def section_gap(section: str) -> str:
        value = facts.get(section, {})
        return str(value.get("unknown_gap", "")) if isinstance(value, dict) else ""

    definitions = [
        atom(
            "career_timeline",
            "evidence_backed_engineering_years",
            f"Example User's local work history spans {start_label} through {end_label}, supporting {year_phrase} of evidence-backed engineering activity.",
            [
                f"Use {years} years as the local-ledger activity span, not as a formal employment-tenure claim.",
                "If asked for total professional years, answer with the evidence-backed lower bound unless a declared career fact is available.",
                "For full-stack questions, combine this timeline with the experience-scope boundary instead of inflating backend tenure.",
            ],
            ["career_timeline", "experience", "work_history", "identity"],
            ["Example User years experience", "how many years exp", "Example User work history", "Example User 工作多久", "Example User 几年经验"],
            "Use this when answering career duration, years of experience, or work-history timeline questions.",
            [
                "Do not present evidence-backed activity years as formal employment tenure.",
                "Do not claim all years were full-stack years unless a declared career fact proves that.",
            ],
            facts,
            refs.get("career_timeline", []),
            generated_at,
        ),
        atom(
            "experience_scope",
            "frontend_heavy_full_product_scope",
            "Example User's strongest proven scope is frontend/product engineering with backend-adjacent API, service, schema, serverless, CI/CD, release, and AI-product work.",
            [
                "Describe him as frontend-heavy and full-product rather than purely frontend-only.",
                "He can reason across API contracts, auth boundaries, release pipelines, and agent tooling when delivery requires it.",
                "Full-stack wording should be scoped: strong backend-adjacent and infra evidence, but formal full-stack tenure remains unproven without manual career facts.",
            ],
            ["experience_scope", "frontend", "backend", "api_contract", "ci_cd", "ai_product", "full_stack"],
            ["Example User full stack experience", "Example User frontend backend scope", "Example User strengths", "Example User 强项", "Example User 全栈经验"],
            "Use this to answer what kind of engineering scope Example User can cover.",
            ["Do not flatten the profile into backend-only or frontend-only language."],
            facts,
            refs.get("experience_scope", []),
            generated_at,
        ),
        atom(
            "role_identity",
            "frontend_lead_quality_gate",
            "Example User behaves like a FE lead quality gate: architecture review, API-contract awareness, QA/release handoff, bug ownership, and delivery accountability show up repeatedly.",
            [
                "Use role identity as behavior first: reviewer, architecture checker, quality gate, and delivery owner.",
                "Formal people-management should stay unknown unless a declared source provides reporting-line evidence.",
                "When acting as him, bias toward frontend ownership that includes release and cross-team handoff responsibilities.",
            ],
            ["role_identity", "frontend_lead", "review", "delivery", "quality", "leadership"],
            ["what kind of engineer is Example User", "Example User role identity", "Example User FE lead", "Example User 是什么类型的工程师"],
            "Use this to answer identity, role, and authority questions.",
            ["Do not claim formal manager scope without declared evidence."],
            facts,
            refs.get("role_identity", []),
            generated_at,
        ),
        atom(
            "technical_stack",
            "frontend_api_infra_ai_stack",
            "Example User's technical map spans React/Next.js, Angular/RxJS, TypeScript, state/data flow, API/auth boundaries, analytics/reporting, CI/CD, and AI/MCP systems.",
            [
                "Use this as the broad stack map before narrowing to one framework.",
                "React should be framed as one strong frontend signal, not the whole identity.",
                "Angular/RxJS and older enterprise frontend work remain part of the long-term trajectory.",
            ],
            ["technical_stack", "react", "nextjs", "angular", "rxjs", "typescript", "api_contract", "ci_cd", "mcp"],
            ["Example User tech stack", "Example User React Angular TypeScript", "what technologies does Example User know", "Example User 技术栈"],
            "Use this when answering stack, framework, or code-practice capability questions.",
            ["Do not over-index on one framework when a broader stack map is more accurate."],
            facts,
            refs.get("technical_stack", []),
            generated_at,
        ),
        atom(
            "impact_profile",
            "bug_reduction_release_infra_impact",
            "Example User's impact pattern is visible in bug reduction, QA readiness, release flow, CI/CD/web infra, and repeated ownership of product correctness.",
            [
                "If business metrics are unavailable, phrase impact as bug reduction, delivery safety, QA/release readiness, and correctness improvements.",
                "CI/CD and web infra work should be treated as production delivery leverage, not side maintenance.",
                "Impact claims should stay tied to repeated work patterns unless exact company metrics are provided.",
            ],
            ["impact", "bug_reduction", "qa", "release", "ci_cd", "web_infra", "delivery"],
            ["Example User impact", "Example User bug reduction", "Example User production leadership", "Example User 影响力"],
            "Use this to answer impact, outcomes, and production-delivery questions without inventing business metrics.",
            ["Do not invent revenue, conversion, or business metric improvements."],
            facts,
            refs.get("impact_profile", []),
            generated_at,
        ),
        atom(
            "review_authority",
            "pr_quality_gate_authority",
            "Example User's PR-review profile supports quality-gate authority: reviewers and repos repeatedly rely on him for frontend architecture, contracts, maintainability, and release-sensitive approval.",
            [
                "Review authority should be described by topics and behavior, not approval count alone.",
                "Useful review themes include architecture, API/data contract, state behavior, UX correctness, maintainability, QA, and release risk.",
                "This is a strong lead-level signal when combined with delivery and ownership context.",
            ],
            ["review_authority", "review", "architecture", "api_contract", "quality", "maintainability", "delivery"],
            ["how does Example User review PRs", "Example User review authority", "Example User quality gate", "Example User review PR 关注什么"],
            "Use this when answering review, mentorship, or authority questions.",
            ["Do not reduce review authority to approval counts only."],
            facts,
            refs.get("review_authority", []),
            generated_at,
        ),
        atom(
            "learning_trajectory",
            "implementation_to_lead_ai_infra_growth",
            "Example User's growth trajectory moves from enterprise frontend implementation into architecture, delivery ownership, web infrastructure, and AI/agent product systems.",
            [
                "Use the trajectory to answer what has improved over time: scope, judgment, delivery accountability, and agent-native product thinking.",
                "Older Angular/shared-library work and newer AI/MCP/infra work should be connected as accumulated capability, not separate fragments.",
                "This supports clone behavior that considers history and accumulated judgment, not just current stack popularity.",
            ],
            ["learning_trajectory", "growth", "architecture", "delivery", "ai_product", "web_infra"],
            ["what has Example User improved over time", "Example User learning trajectory", "Example User growth", "Example User 这些年成长"],
            "Use this to answer growth, trajectory, and accumulated knowledge questions.",
            ["Do not assume personal-life growth from work-only sources."],
            facts,
            refs.get("learning_trajectory", []),
            generated_at,
        ),
        atom(
            "declared_profile",
            "formal_role_and_scope",
            (
                "Example User's declared profile should be the first source for formal title, years, promotion, and self-declared scope."
                if has_family_material("declared_profile")
                else f"Example User's declared profile is incomplete: {section_gap('declared_profile')}"
            ),
            [
                "Use declared career facts before inferring role, title, tenure, or promotion from work activity.",
                "If no declared fact exists, answer with the evidence-backed lower bound and name the formal gap.",
                "Keep formal FE Lead title, full-stack tenure, and management scope separate from inferred work behavior.",
            ],
            ["declared_profile", "career_timeline", "title", "years", "identity"],
            ["official role", "formal title", "years of experience", "正式职位", "年限"],
            "Use this when answering official role, title, years, promotion, or declared-scope questions.",
            ["Do not convert inferred work signals into formal title or tenure claims."],
            facts,
            refs.get("declared_profile", []),
            generated_at,
            *confidence_for("declared_profile"),
        ),
        atom(
            "review_style",
            "pr_reasoning_and_quality_themes",
            (
                "Example User's PR-review style centers on architecture, API/data contracts, state behavior, maintainability, UX correctness, QA readiness, and release risk."
                if has_family_material("review_style")
                else f"Example User's PR-review style has an import gap: {section_gap('review_style')}"
            ),
            [
                "Describe review style by what he checks, not by approval counts alone.",
                "Expect review to connect code structure with product behavior, API/data contracts, and release safety.",
                "Use PR review material as the main source for how he thinks during code review.",
            ],
            ["review_style", "review", "architecture", "api_contract", "quality", "maintainability"],
            ["how does Example User review PRs", "review style", "PR 关注什么", "代码审查"],
            "Use this for PR review behavior, quality-gate, and reviewer-personality questions.",
            ["Do not present low-information approvals as meaningful review reasoning."],
            facts,
            refs.get("review_style", []),
            generated_at,
            *confidence_for("review_style"),
        ),
        atom(
            "repo_authority",
            "frontend_decision_dependency",
            (
                "Repository authority signals show where teams rely on Example User for frontend decisions, review requests, governance, and approval paths."
                if has_family_material("repo_authority")
                else f"Example User's repository authority map is incomplete: {section_gap('repo_authority')}"
            ),
            [
                "Use repo authority for who relies on him, which repositories depend on him, and where his approval is structurally important.",
                "Treat CODEOWNERS, branch protection, permissions, review requests, and repeated mentions as stronger authority signals than generic contributions.",
                "Separate formal repo permissions from inferred repeated-review authority.",
            ],
            ["repo_authority", "review_request", "codeowners", "frontend_lead", "relationship_authority"],
            ["who relies on Example User", "frontend decisions", "repo authority", "谁依赖 Example User"],
            "Use this when answering repo authority, default reviewer, or decision-dependency questions.",
            ["Do not claim formal CODEOWNER or admin status unless the source family contains that specific signal."],
            facts,
            refs.get("repo_authority", []),
            generated_at,
            *confidence_for("repo_authority"),
        ),
        atom(
            "release_ownership",
            "ci_cd_hotfix_release_accountability",
            (
                "Example User's release ownership appears through CI/CD, web infrastructure, deploy, hotfix, workflow, and release-sensitive correctness work."
                if has_family_material("release_ownership")
                else f"Example User's release ownership has an import gap: {section_gap('release_ownership')}"
            ),
            [
                "Use release ownership for CI/CD, deploy, hotfix, workflow-run, release-bound PR, and production-readiness questions.",
                "Frame web infrastructure as delivery leverage when it improves release confidence and operational safety.",
                "Tie ownership to verifiable rows rather than claiming sole production authority.",
            ],
            ["release_ownership", "release", "hotfix", "ci_cd", "web_infra", "delivery"],
            ["release ownership", "CI/CD ownership", "hotfix", "负责过哪些 release", "CI/CD"],
            "Use this for release, deploy, hotfix, GitHub Actions, and CI failure ownership questions.",
            ["Do not claim sole release authority without explicit release-role material."],
            facts,
            refs.get("release_ownership", []),
            generated_at,
            *confidence_for("release_ownership"),
        ),
        atom(
            "jira_leadership",
            "qa_blocker_done_coordination",
            (
                "Example User's Jira leadership centers on moving work through QA, blockers, reopen, hotfix, review, release, and Done states with explicit coordination."
                if has_family_material("jira_leadership")
                else f"Example User's Jira leadership map is incomplete: {section_gap('jira_leadership')}"
            ),
            [
                "Use Jira leadership for QA handoff, blocker handling, reopen response, ticket transition, and Done-accountability questions.",
                "Look for coordination language that unblocks QA, backend, product, or release actors.",
                "Separate delivery ownership from formal people-management unless declared material proves it.",
            ],
            ["jira_leadership", "jira", "qa", "blocker", "release", "delivery"],
            ["Jira QA blockers Done", "coordinate Jira", "怎么协调 Jira 和 QA", "blocked reopen"],
            "Use this when answering Jira coordination, QA, blocker, and ticket-delivery questions.",
            ["Do not expose Jira keys by default."],
            facts,
            refs.get("jira_leadership", []),
            generated_at,
            *confidence_for("jira_leadership"),
        ),
        atom(
            "architecture_material",
            "docs_rfc_standards_gap",
            (
                "Example User's architecture material includes imported docs, RFCs, migration plans, standards, or AI/MCP design material."
                if has_family_material("architecture_material")
                else f"Example User's dedicated architecture-doc corpus is missing: {section_gap('architecture_material')}"
            ),
            [
                "Use this section for architecture-doc, RFC, standards, migration-plan, and Confluence-export questions.",
                "If dedicated docs are missing, say that architecture judgment is supported elsewhere but docs have not been imported.",
                "Do not present commit-derived architecture signals as architecture docs.",
            ],
            ["architecture_material", "architecture", "rfc", "migration", "standards", "docs"],
            ["architecture docs", "RFC", "migration plan", "架构文档", "标准"],
            "Use this when the caller asks about architecture docs or formal design material.",
            ["Do not invent Confluence, RFC, or formal architecture documents."],
            facts,
            refs.get("architecture_material", []),
            generated_at,
            *confidence_for("architecture_material"),
        ),
        atom(
            "agent_collaboration_style",
            "agent_session_correction_patterns",
            (
                "Example User's agent collaboration style should be distilled from Codex, Claude, Cursor, and agent-session correction patterns."
                if has_family_material("agent_collaboration_style")
                else f"Example User's agent-session corpus is missing: {section_gap('agent_collaboration_style')}"
            ),
            [
                "Use agent sessions to learn how he corrects agents, scopes tasks, demands proof, and prefers execution flow.",
                "Keep secrets, private paths, tokens, and third-party private content redacted before indexing session history.",
                "Until sessions are imported, rely on agent operating context and explicit manual preferences.",
            ],
            ["agent_collaboration", "agent", "codex", "claude", "cursor", "work_style"],
            ["how should an agent work with Example User", "agent collaboration", "agent 该怎么和 Example User 一起工作"],
            "Use this when an agent needs collaboration style beyond the general operating contract.",
            ["Do not infer life voice or private preferences from code-only evidence."],
            facts,
            refs.get("agent_collaboration_style", []),
            generated_at,
            *confidence_for("agent_collaboration_style"),
        ),
        atom(
            "portfolio_cases",
            "public_safe_product_showcase",
            (
                "Example User's portfolio cases should contain sanitized case studies, screenshots, product surfaces, and public-safe summaries."
                if has_family_material("portfolio_cases")
                else f"Example User's portfolio layer is not imported: {section_gap('portfolio_cases')}"
            ),
            [
                "Use portfolio cases only when public-safe summaries or screenshots have been imported.",
                "Keep product examples sanitized and avoid private screenshots or source paths by default.",
                "If portfolio material is missing, answer with the gap and suggest importing case studies.",
            ],
            ["portfolio_cases", "case_study", "showcase", "product_surface"],
            ["product case studies", "portfolio", "showcase", "作品案例"],
            "Use this for public portfolio, showcase, case-study, and screenshot questions.",
            ["Do not invent public case studies or screenshot evidence."],
            facts,
            refs.get("portfolio_cases", []),
            generated_at,
            *confidence_for("portfolio_cases"),
        ),
        atom(
            "personal_identity",
            "values_preferences_boundaries",
            (
                "Example User's personal identity layer should store declared values, goals, preferences, boundaries, and life context."
                if has_family_material("personal_identity")
                else f"Example User's personal material layer is sparse: {section_gap('personal_identity')}"
            ),
            [
                "Use personal material only when the user has explicitly imported or declared it.",
                "Keep work-derived persona separate from personal-life identity.",
                "For personal preference questions, state the known work-style preferences and the personal-material gap.",
            ],
            ["personal_identity", "values", "preferences", "boundaries", "life_context"],
            ["personal preferences", "values", "personal identity", "个人偏好", "价值观"],
            "Use this for personal preferences, values, goals, boundaries, and life-context questions.",
            ["Do not infer private life context from work logs."],
            facts,
            refs.get("personal_identity", []),
            generated_at,
            *confidence_for("personal_identity"),
        ),
    ]

    for atom_row, trace_rows in definitions:
        atoms.append(atom_row)
        traces.extend(trace_rows)
    return atoms, traces


def build_dense_identity_graph(
    ledger: Path,
    atoms: list[dict[str, Any]],
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    facts, graph, refs = build_identity_facts(ledger, atoms, generated_at)
    identity_atoms, identity_traces = build_identity_atoms(facts, refs, generated_at)
    return facts, graph, identity_atoms, identity_traces
