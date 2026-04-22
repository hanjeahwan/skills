#!/usr/bin/env python3
"""Build v2 self-context memory atoms from private source material."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from build_persona_sections import build_persona_sections
from build_identity_graph import build_dense_identity_graph
from build_source_clusters import build_source_clusters_and_candidates
from build_voice_profile import build_voice_profile
from ledger_paths import resolve_ledger_path
from source_families import ARCHITECTURE_VERSION, SOURCE_FILES


MEMORY_TYPES = {
    "identity",
    "capability",
    "coding_style",
    "decision_pattern",
    "preference",
    "communication_style",
    "work_history",
    "project_context",
    "personal_context",
    "relationship_context",
    "knowledge",
    "goal",
    "constraint",
    "private_boundary",
    "unknown_gap",
    "declared_profile",
    "career_timeline",
    "experience_scope",
    "role_identity",
    "technical_stack",
    "impact_profile",
    "review_style",
    "review_authority",
    "repo_authority",
    "release_ownership",
    "jira_leadership",
    "architecture_material",
    "agent_collaboration_style",
    "portfolio_cases",
    "personal_identity",
    "learning_trajectory",
}

TOPIC_HINTS: dict[str, list[str]] = {
    "frontend": ["frontend", "front-end", "ui", "ux", "component", "web app", "angular", "react", "next"],
    "react": ["react", "next", "next.js", "nextjs", "tsx", "jsx", "hook"],
    "angular": ["angular", "rxjs", "ngrx"],
    "typescript": ["typescript", "type-safe", "type safe", "tsx"],
    "ai_product": ["ai", "gpt", "llm", "copilot", "generative", "mcp", "agent"],
    "leadership": ["lead", "leadership", "review", "quality gate", "mentor", "coordination", "authority"],
    "quality": ["quality", "testing", "test", "maintainability", "review", "bug", "reliability"],
    "delivery": ["release", "delivery", "deploy", "rollout", "done", "qa", "hotfix"],
    "ci_cd": ["ci", "cd", "cicd", "github actions", "workflow", "deploy", "semantic-release", "sentry"],
    "architecture": ["architecture", "migration", "platform", "shared library", "design", "system"],
    "product": ["product", "workflow", "candidate", "employee", "recruiting", "analytics", "reporting"],
    "security": ["auth", "rbac", "permission", "security", "cognito", "auth0"],
    "performance": ["performance", "cost", "cache", "optimization", "quota", "latency"],
    "documentation": ["documentation", "docs", "onboarding", "knowledge", "standards"],
    "personal": ["personal", "preference", "goal", "life", "family", "habit"],
}

HEADING_MEMORY_HINTS: list[tuple[str, str]] = [
    ("react", "coding_style"),
    ("code", "coding_style"),
    ("frontend", "capability"),
    ("quality", "decision_pattern"),
    ("review", "decision_pattern"),
    ("lead", "decision_pattern"),
    ("ai", "capability"),
    ("cicd", "capability"),
    ("ci/cd", "capability"),
    ("infra", "capability"),
    ("architecture", "decision_pattern"),
    ("ownership", "work_history"),
    ("delivery", "work_history"),
    ("gap", "unknown_gap"),
    ("guardrail", "private_boundary"),
]

SKIP_PROFILE_HEADINGS = {
    "case studies",
    "profiles",
    "reports",
    "evidence map",
    "generated assets",
    "output assets",
}

SOURCE_ID_PATTERN = re.compile(r"`([^`\n]+:[^`\n]+)`")
SECTION_PATTERN = re.compile(r"(?m)^###\s+(.+?)\s*$")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
PATH_PATTERN = re.compile(r"[A-Za-z0-9_.\-/\\]+\.(?:ts|tsx|js|jsx|html|scss|css|json|ya?ml|md|py|sql)", re.IGNORECASE)

SIGNAL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "frontend_product_engineering": {
        "memory_type": "capability",
        "statement": "Raw Git, PR, Jira, and code evidence supports broad product frontend engineering across complex enterprise workflows.",
        "useful_context": [
            "Builds user-facing and internal product UI where state, validation, forms, tables, workflow correctness, and API alignment matter.",
            "The strongest center of gravity is product frontend delivery rather than isolated visual UI or narrow framework usage.",
        ],
        "topics": ["frontend", "product", "delivery"],
        "guardrails": ["Do not reduce this to repository activity; describe the product engineering behavior it supports."],
        "query_patterns": ["what does Hanje know", "Hanje frontend product engineering", "what has Hanje built"],
    },
    "react_next_typescript": {
        "memory_type": "coding_style",
        "statement": "Raw code and commit evidence supports React/Next.js and typed TSX practice as part of Hanje's frontend engineering profile.",
        "useful_context": [
            "When answering React questions, lead with component structure, hooks/state behavior, TypeScript clarity, and product-flow correctness.",
            "React should be presented as one part of a broader frontend capability profile, not as the only identity.",
        ],
        "topics": ["frontend", "react", "typescript"],
        "guardrails": ["Do not cite commit counts as the answer; use counts only as internal confidence."],
        "query_patterns": ["does Hanje know React", "how does Hanje code React", "Hanje Next.js style"],
    },
    "angular_enterprise": {
        "memory_type": "capability",
        "statement": "Raw source evidence supports long-running Angular enterprise application and shared package work.",
        "useful_context": [
            "Shows Angular module, component, template, routing, RxJS/service, and shared library work across maintained product systems.",
            "This is historical depth and enterprise maintenance experience, not necessarily a current-only stack preference.",
        ],
        "topics": ["frontend", "angular", "typescript"],
        "guardrails": ["Distinguish historical Angular depth from current framework preference when answering."],
        "query_patterns": ["Hanje Angular experience", "enterprise frontend Angular", "RxJS frontend practice"],
    },
    "api_data_contract_alignment": {
        "memory_type": "capability",
        "statement": "Raw work evidence supports API and data-contract alignment across frontend payloads, lookups, DTOs, reports, and exports.",
        "useful_context": [
            "Keeps UI behavior aligned with backend response shapes, lookup migrations, request payloads, query parameters, and export/report correctness.",
            "Useful when an agent needs to reason about data shape changes before writing frontend code for Hanje.",
        ],
        "topics": ["frontend", "architecture", "product"],
        "guardrails": ["Call this frontend/backend contract alignment unless stronger backend ownership evidence is present."],
        "query_patterns": ["API contract", "data mapping", "lookup migration", "report export correctness"],
    },
    "ai_product_agent_work": {
        "memory_type": "capability",
        "statement": "Raw source evidence supports AI-facing product and agent tooling work, including chat, structured AI UI, skills, MCP, and generative workflows.",
        "useful_context": [
            "Works on AI product surfaces and agent infrastructure where prompts, generated output, structured context, and UI orchestration meet product workflows.",
            "Frame this as AI product engineering and agent-tooling contribution, not model research unless separate evidence exists.",
        ],
        "topics": ["ai_product", "frontend", "architecture"],
        "guardrails": ["Do not claim model-training or research-science ownership from product integration evidence alone."],
        "query_patterns": ["Hanje AI product work", "MCP agent tooling", "generative UI"],
    },
    "security_auth_rbac": {
        "memory_type": "capability",
        "statement": "Raw work evidence supports security-sensitive frontend boundaries around authentication, authorization, RBAC, route guards, and session behavior.",
        "useful_context": [
            "Relevant when code touches login/logout, Auth0/Cognito migration, token/session metadata, permissions, access states, or unauthorized UI behavior.",
        ],
        "topics": ["security", "frontend", "architecture"],
        "guardrails": ["Describe this as security-sensitive frontend work unless formal security ownership is separately proven."],
        "query_patterns": ["auth RBAC", "security sensitive frontend", "Cognito Auth0 migration"],
    },
    "ci_cd_web_infra": {
        "memory_type": "capability",
        "statement": "Raw source evidence supports CI/CD and web infrastructure contribution around workflows, release automation, deploy configuration, and observability plumbing.",
        "useful_context": [
            "Includes GitHub Actions, workflow files, semantic release, build/deploy configuration, Sentry or sourcemap flows, and web-app infrastructure signals.",
            "This context matters when an agent plans release, deploy, build, or repo automation work for Hanje.",
        ],
        "topics": ["ci_cd", "delivery", "architecture"],
        "guardrails": ["Do not infer production deploy ownership from workflow file evidence alone without release actor evidence."],
        "query_patterns": ["web app infra", "CI/CD", "GitHub Actions", "release automation"],
    },
    "quality_reliability_debugging": {
        "memory_type": "decision_pattern",
        "statement": "Raw Jira, PR, and commit evidence supports production-quality debugging and reliability behavior across bugs, hotfixes, QA, and customer-visible issues.",
        "useful_context": [
            "Tends to work through customer bugs, staging issues, release-bound fixes, Sentry/error context, and behavior regressions with delivery accountability.",
            "Use this when an agent needs to predict Hanje's bias toward concrete reproduction, correctness, and production impact.",
        ],
        "topics": ["quality", "delivery", "product"],
        "guardrails": ["Use proxy impact language unless explicit incident metrics or before/after support data exists."],
        "query_patterns": ["debugging style", "bug reduction", "production reliability", "hotfix"],
    },
    "frontend_quality_gate": {
        "memory_type": "decision_pattern",
        "statement": "Raw PR review and authority evidence supports frontend quality-gate behavior through review requests, approvals, comments, and repository reliance.",
        "useful_context": [
            "When asked how Hanje leads frontend quality, emphasize review judgment, maintainability, API contract awareness, UX correctness, and delivery risk control.",
            "Approval activity should be interpreted alongside review-request and authority signals, not as a shallow count.",
        ],
        "topics": ["leadership", "frontend", "quality"],
        "guardrails": ["Do not equate approvals with leadership unless review themes or authority signals support the claim."],
        "query_patterns": ["frontend quality gate", "PR review style", "Hanje review authority"],
    },
    "delivery_ownership": {
        "memory_type": "work_history",
        "statement": "Raw Jira changelog, assignment, PR, and release evidence supports delivery ownership across tickets, QA handoffs, Done transitions, and release-bound work.",
        "useful_context": [
            "Useful when explaining ownership: Hanje appears in assigned tickets, status movement, release/fixVersion context, and merged PR delivery paths.",
            "This supports delivery accountability more than generic task participation.",
        ],
        "topics": ["delivery", "leadership", "product"],
        "guardrails": ["Do not claim formal people-management scope unless title or reporting-line evidence exists."],
        "query_patterns": ["delivery ownership", "release accountability", "ticket ownership"],
    },
    "shared_library_platform": {
        "memory_type": "decision_pattern",
        "statement": "Raw code evidence supports leverage-oriented shared library, package, and reusable component/platform work.",
        "useful_context": [
            "Shows preference for reusable packages, shared components, cross-app consistency, and platform-level frontend leverage when the same pattern repeats.",
        ],
        "topics": ["architecture", "frontend", "quality"],
        "guardrails": ["Do not call this full design-system governance unless token/component ownership evidence is present."],
        "query_patterns": ["shared library", "frontend platform", "reusable components"],
    },
    "documentation_enablement": {
        "memory_type": "decision_pattern",
        "statement": "Raw source evidence supports enablement through docs, standards, migration notes, review guidance, and reusable instructions.",
        "useful_context": [
            "Turns repeated knowledge into reusable guidance for teammates or agents when patterns need to survive beyond one PR.",
        ],
        "topics": ["documentation", "leadership", "quality"],
        "guardrails": ["Do not overstate mentoring scope without explicit mentoring or onboarding evidence."],
        "query_patterns": ["documentation", "standards", "migration plan", "mentoring"],
    },
    "workflow_ui_systems": {
        "memory_type": "capability",
        "statement": "Raw source evidence supports complex workflow UI work across forms, tables, dashboards, filters, drawers, validation, and state-heavy product flows.",
        "useful_context": [
            "This is useful when an agent needs to write UI for Hanje: prioritize clear state boundaries, validation behavior, data loading states, and workflow correctness.",
            "The pattern is operational product UI, not only static pages or visual styling.",
        ],
        "topics": ["frontend", "product", "quality"],
        "guardrails": ["Do not reduce workflow UI evidence to CSS or visual-only implementation."],
        "query_patterns": ["workflow UI", "forms tables dashboard", "state-heavy frontend"],
    },
    "recruiting_candidate_domain": {
        "memory_type": "work_history",
        "statement": "Raw source evidence supports recruiting, candidate, role-fit, assessment, job, and talent-domain product knowledge.",
        "useful_context": [
            "When answering product-domain questions, mention recruiting and candidate workflows as known work context where frontend, data, and product correctness intersect.",
        ],
        "topics": ["product", "frontend", "delivery"],
        "guardrails": ["Do not expose customer or candidate private data."],
        "query_patterns": ["candidate workflow", "recruiting product", "role fit", "assessment"],
    },
    "employee_lxp_goals_domain": {
        "memory_type": "work_history",
        "statement": "Raw Jira and source evidence supports employee, LXP, goals, action items, courses, and learning workflow product knowledge.",
        "useful_context": [
            "Useful when the agent needs context around employee experience workflows, goal progress, learning/course actions, and operational HR product behavior.",
        ],
        "topics": ["product", "delivery", "quality"],
        "guardrails": ["Avoid claiming HR strategy ownership; keep this to product implementation context."],
        "query_patterns": ["LXP goals", "employee workflows", "learning product"],
    },
    "analytics_reporting_exports": {
        "memory_type": "capability",
        "statement": "Raw source evidence supports analytics, reporting, dashboard, export, and data-presentation product work.",
        "useful_context": [
            "For analytics/reporting code, prioritize data correctness, empty/loading states, filters, export shape, and alignment with backend contracts.",
        ],
        "topics": ["product", "frontend", "architecture"],
        "guardrails": ["Do not invent business metrics; describe technical/reporting correctness unless metrics are supplied."],
        "query_patterns": ["analytics reporting", "dashboard export", "data presentation"],
    },
    "backend_data_supporting_work": {
        "memory_type": "capability",
        "statement": "Raw source evidence supports supporting backend/data work around APIs, repositories, schemas, services, and serverless functions.",
        "useful_context": [
            "Treat this as supporting full-stack context around frontend delivery and data contracts, useful when frontend changes require backend shape awareness.",
        ],
        "topics": ["architecture", "product", "frontend"],
        "guardrails": ["Present backend as supporting evidence unless stronger backend architecture ownership proof is added."],
        "query_patterns": ["backend data support", "serverless API schema", "repository service layer"],
    },
    "modernization_quality_standards": {
        "memory_type": "decision_pattern",
        "statement": "Raw source evidence supports modernization and quality-standard work through refactors, migrations, dependency changes, linting, formatting, and cleanup.",
        "useful_context": [
            "When acting as Hanje, prefer maintainable upgrades, type/lint cleanup, dependency alignment, and refactors that reduce future delivery drag.",
        ],
        "topics": ["quality", "architecture", "typescript"],
        "guardrails": ["Separate quality tooling evidence from measured test coverage unless coverage reports exist."],
        "query_patterns": ["modernization", "refactoring", "quality standards", "dependency migration"],
    },
    "performance_cost_optimization": {
        "memory_type": "decision_pattern",
        "statement": "Raw source evidence supports cost, quota, caching, performance, and efficiency-aware engineering behavior.",
        "useful_context": [
            "Useful when an agent makes architecture choices for Hanje: consider API usage, cache behavior, build/runtime cost, and maintainable performance wins.",
        ],
        "topics": ["performance", "architecture", "quality"],
        "guardrails": ["Do not claim dollar impact unless explicit company metrics are supplied."],
        "query_patterns": ["performance", "cost optimization", "cache quota latency"],
    },
    "communication_coordination": {
        "memory_type": "communication_style",
        "statement": "Raw Jira comment and PR discussion evidence supports concise coordination around updates, standards, QA/product handoff, and decision clarification.",
        "useful_context": [
            "Communication evidence is most useful for agent behavior: be direct, state what changed, explain standards, and unblock the next actor.",
        ],
        "topics": ["leadership", "delivery", "quality"],
        "guardrails": ["Do not expose private teammate names or comment content by default."],
        "query_patterns": ["communication style", "coordination", "unblock QA product"],
    },
    "unknown_public_portfolio": {
        "memory_type": "unknown_gap",
        "statement": "The self-context memory does not yet have enough sanitized public portfolio artifacts to safely make public showcase claims.",
        "useful_context": [
            "Agents should ask for screenshots, sanitized case studies, or public links before creating external-facing portfolio claims.",
        ],
        "topics": ["personal", "product"],
        "guardrails": ["Do not invent public proof; request sanitized material first."],
        "query_patterns": ["portfolio proof", "public case study", "what is missing"],
    },
}

SIGNAL_MIN_COUNTS = {
    "unknown_public_portfolio": 0,
    "communication_coordination": 2,
    "frontend_quality_gate": 3,
    "delivery_ownership": 3,
    "react_next_typescript": 3,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def slug(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", ".", value.lower()).strip(".")
    return text or stable_hash(value, 10)


def clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = EMAIL_PATTERN.sub("<REDACTED_EMAIL>", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


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


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def latest_profile(ledger: Path, basename: str) -> Path | None:
    profiles = ledger / "profiles"
    stable = profiles / f"{basename}.md"
    if stable.exists():
        return stable
    matches = sorted(profiles.glob(f"{basename}-*.md"), key=lambda item: item.name, reverse=True)
    return matches[0] if matches else None


def split_sections(markdown: str) -> list[tuple[str, str]]:
    matches = list(SECTION_PATTERN.finditer(markdown))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections.append((match.group(1).strip(), markdown[start:end].strip()))
    return sections


def extract_claim(section: str) -> str:
    match = re.search(r"(?m)^Claim:\s*(.+?)(?:\n\n|\nDistilled content:|\nEvidence confidence:|$)", section, re.DOTALL)
    if not match:
        first = next((line for line in section.splitlines() if line.strip()), "")
        return clean_text(first)
    return clean_text(match.group(1))


def extract_bullets_after(label: str, section: str) -> list[str]:
    pattern = rf"(?ms)^{re.escape(label)}:\s*\n(?P<body>.*?)(?:\n[A-Z][A-Za-z ]+:\s|\n###\s|$)"
    match = re.search(pattern, section)
    if not match:
        return []
    bullets: list[str] = []
    for line in match.group("body").splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            item = clean_text(stripped[2:])
            if re.search(r"`(?:profiles|reports|case-studies)/", item):
                continue
            bullets.append(item)
    return [item for item in bullets if item]


def extract_guardrails(section: str) -> list[str]:
    guardrails = extract_bullets_after("Guardrails", section)
    match = re.search(r"(?m)^Guardrail:\s*(.+)$", section)
    if match:
        guardrails.append(clean_text(match.group(1)))
    return sorted(set(item for item in guardrails if item))


def extract_confidence(section: str) -> str:
    match = re.search(r"(?i)Evidence confidence:\s*([a-z_ -]+)", section)
    if not match:
        return "medium"
    value = clean_text(match.group(1)).lower()
    for option in ["strong", "medium", "weak"]:
        if option in value:
            return option
    return "medium"


def topics_for(*values: str) -> list[str]:
    haystack = " ".join(values).lower()
    topics = {
        topic
        for topic, hints in TOPIC_HINTS.items()
        if any(hint in haystack for hint in hints)
    }
    return sorted(topics or {"self_context"})


def memory_type_for(heading: str, claim: str, topics: list[str]) -> str:
    haystack = f"{heading} {claim}".lower()
    for hint, memory_type in HEADING_MEMORY_HINTS:
        if hint in haystack:
            return memory_type
    if "personal" in topics:
        return "personal_context"
    if "documentation" in topics:
        return "knowledge"
    return "capability"


def query_patterns_for(heading: str, topics: list[str], memory_type: str) -> list[str]:
    base = [
        heading,
        f"what does Hanje know about {heading}",
        f"how does Hanje think about {heading}",
    ]
    if memory_type == "coding_style":
        base.append(f"how should I code in Hanje's {heading} style")
    if "react" in topics:
        base.extend(["does Hanje know React", "Hanje React practice", "Hanje Next.js practice"])
    if "leadership" in topics:
        base.extend(["Hanje leadership style", "how Hanje reviews work"])
    return sorted(set(clean_text(item) for item in base if clean_text(item)))


def source_type_from_id(source_id: str) -> str:
    return source_id.split(":", 1)[0] if ":" in source_id else "unknown"


def stringify_raw(raw: Any) -> str:
    if isinstance(raw, (dict, list)):
        return json.dumps(raw, ensure_ascii=False, sort_keys=True)
    return clean_text(raw)


def source_text(row: dict[str, Any]) -> str:
    raw = row.get("raw_excerpt")
    text = " ".join(
        [
            clean_text(row.get("title")),
            clean_text(row.get("summary")),
            " ".join(str(item) for item in row.get("tags", []) if item),
            stringify_raw(raw),
        ]
    )
    return text.lower()


def raw_dict(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("raw_excerpt")
    return raw if isinstance(raw, dict) else {}


def file_paths_from_row(row: dict[str, Any]) -> list[str]:
    raw = raw_dict(row)
    paths: list[str] = []
    for item in raw.get("files", []) if isinstance(raw.get("files"), list) else []:
        if isinstance(item, dict) and item.get("filename"):
            paths.append(str(item["filename"]))
    for key in ["path", "file", "filename", "url_or_path"]:
        if raw.get(key):
            paths.append(str(raw[key]))
    paths.extend(PATH_PATTERN.findall(source_text(row)))
    return sorted(set(path.replace("\\", "/") for path in paths if path))


def row_source_ref(row: dict[str, Any]) -> dict[str, str]:
    return {
        "id": str(row.get("id") or row.get("source_id") or stable_hash(json.dumps(row, sort_keys=True, default=str))),
        "source_type": str(row.get("source_type") or source_type_from_id(str(row.get("id", "")))),
    }


def signal_names_for_row(row: dict[str, Any]) -> set[str]:
    text = source_text(row)
    raw = raw_dict(row)
    source_type = str(row.get("source_type", "")).lower()
    paths = file_paths_from_row(row)
    path_text = " ".join(paths).lower()
    signals: set[str] = set()

    if any(hint in text for hint in TOPIC_HINTS["frontend"]) or any(path.endswith((".ts", ".tsx", ".html", ".scss", ".css")) for path in paths):
        signals.add("frontend_product_engineering")
    if any(hint in text for hint in TOPIC_HINTS["react"]) or any(path.endswith((".tsx", ".jsx")) for path in paths):
        signals.add("react_next_typescript")
    if any(hint in text for hint in TOPIC_HINTS["angular"]) or any("angular" in path or path.endswith(".component.ts") for path in paths):
        signals.add("angular_enterprise")
    if "typescript" in text or ".ts" in path_text or ".tsx" in path_text:
        signals.add("react_next_typescript" if "react" in text or ".tsx" in path_text else "angular_enterprise")
    if any(hint in text for hint in TOPIC_HINTS["ai_product"]):
        signals.add("ai_product_agent_work")
    if any(hint in text for hint in TOPIC_HINTS["security"]):
        signals.add("security_auth_rbac")
    if any(hint in text for hint in TOPIC_HINTS["ci_cd"]) or ".github/workflows" in path_text or "web-app-infra" in text:
        signals.add("ci_cd_web_infra")
    if any(word in text for word in ["api", "payload", "lookup", "dto", "schema", "response", "request", "query param", "export", "report"]):
        signals.add("api_data_contract_alignment")
    if any(word in text for word in ["bug", "fix", "hotfix", "error", "sentry", "staging", "customer", "qa", "reopen", "regression"]):
        signals.add("quality_reliability_debugging")
    if any(word in text for word in ["shared", "library", "package", "component library", "ng-packages", "web-foundation"]):
        signals.add("shared_library_platform")
    if any(word in text for word in ["docs", "documentation", "readme", "standard", "migration", "onboarding", "guide"]):
        signals.add("documentation_enablement")
    if any(word in text for word in ["form", "table", "dashboard", "drawer", "filter", "search", "workflow", "validation", "modal", "tooltip"]):
        signals.add("workflow_ui_systems")
    if any(word in text for word in ["candidate", "recruit", "role", "job", "assessment", "talent", "profile"]):
        signals.add("recruiting_candidate_domain")
    if any(word in text for word in ["employee", "lxp", "goal", "course", "learning", "action item", "go1"]):
        signals.add("employee_lxp_goals_domain")
    if any(word in text for word in ["analytics", "reporting", "report", "dashboard", "export", "chart", "insight"]):
        signals.add("analytics_reporting_exports")
    if any(word in text for word in ["backend", "serverless", "lambda", "repository", "service layer", "schema", "database", "sql"]):
        signals.add("backend_data_supporting_work")
    if any(word in text for word in ["refactor", "migration", "upgrade", "dependency", "lint", "format", "cleanup", "type-safe", "test"]):
        signals.add("modernization_quality_standards")
    if any(word in text for word in ["performance", "cache", "quota", "cost", "optimization", "latency", "speed"]):
        signals.add("performance_cost_optimization")
    if source_type in {"pull_request_review", "github_review_request"} or "review_requested" in text or "approved" in text:
        signals.add("frontend_quality_gate")
    if source_type in {"jira_ticket", "jira_changelog"} or any(word in text for word in ["done", "release", "fixversions", "code review", "in progress"]):
        signals.add("delivery_ownership")
    if source_type == "jira_comment" and (raw.get("authored_by_user") or raw.get("mentions_user")):
        signals.add("communication_coordination")

    patterns = raw.get("patterns") if isinstance(raw.get("patterns"), dict) else {}
    if patterns:
        pattern_text = " ".join(patterns.keys()).lower()
        if "react" in pattern_text or "hooks" in pattern_text:
            signals.add("react_next_typescript")
        if "angular" in pattern_text or "rxjs" in pattern_text:
            signals.add("angular_enterprise")
        if "shared" in pattern_text:
            signals.add("shared_library_platform")
        if "lint" in pattern_text or "test" in pattern_text:
            signals.add("quality_reliability_debugging")
        if "service" in pattern_text or "api" in pattern_text:
            signals.add("api_data_contract_alignment")

    return signals


def confidence_for_count(count: int) -> str:
    if count >= 20:
        return "strong"
    if count >= 5:
        return "medium"
    return "weak"


def freshness_for_refs(rows: list[dict[str, Any]]) -> str:
    years = []
    for row in rows:
        occurred = str(row.get("occurred_at", ""))
        match = re.match(r"(\d{4})", occurred)
        if match:
            years.append(int(match.group(1)))
    if not years:
        return "unknown"
    if max(years) >= 2025:
        return "current"
    if max(years) >= 2023:
        return "recent"
    return "historical"


def trace_links_for_memory(
    memory_id: str,
    trace_id: str,
    refs: list[dict[str, str]],
    generated_at: str,
    strength: str,
) -> list[dict[str, Any]]:
    links = []
    seen: set[str] = set()
    for index, ref in enumerate(refs[:80]):
        source_id = ref["id"]
        if source_id in seen:
            continue
        seen.add(source_id)
        links.append(
            {
                "id": f"{trace_id}:{stable_hash(source_id, 12)}",
                "memory_id": memory_id,
                "source_id": source_id,
                "source_type": ref["source_type"],
                "support_role": "primary" if index < 8 else "supporting",
                "strength": strength,
                "reason": "Raw source signal supports this distilled self-context memory.",
                "visibility": "internal",
                "updated_at": generated_at,
            }
        )
    return links


def build_source_native_atoms(ledger: Path, generated_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows_by_signal: dict[str, list[dict[str, Any]]] = defaultdict(list)
    refs_by_signal: dict[str, list[dict[str, str]]] = defaultdict(list)
    source_rows: list[dict[str, Any]] = []

    for name in SOURCE_FILES:
        for row in read_jsonl(ledger / "sources" / name):
            source_rows.append(row)
            for signal in signal_names_for_row(row):
                rows_by_signal[signal].append(row)
                refs_by_signal[signal].append(row_source_ref(row))

    rows_by_signal["unknown_public_portfolio"] = []
    refs_by_signal["unknown_public_portfolio"] = []

    atoms: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    for signal, definition in SIGNAL_DEFINITIONS.items():
        rows = rows_by_signal.get(signal, [])
        min_count = SIGNAL_MIN_COUNTS.get(signal, 1)
        if len(rows) < min_count:
            continue
        memory_type = str(definition["memory_type"])
        memory_id = f"memory:{memory_type}.{signal}"
        trace_id = f"trace:{memory_type}.{signal}"
        strength = "medium" if signal == "unknown_public_portfolio" else confidence_for_count(len(rows))
        topics = sorted(set(definition.get("topics", [])))
        refs = refs_by_signal.get(signal, [])
        source_types = Counter(ref["source_type"] for ref in refs)
        repos = Counter()
        jira_keys = set()
        for row in rows:
            raw = raw_dict(row)
            if raw.get("repo"):
                repos[str(raw["repo"])] += 1
            if raw.get("key"):
                jira_keys.add(str(raw["key"]))

        atoms.append(
            {
                "id": memory_id,
                "subject": "hanjeahwan",
                "memory_type": memory_type,
                "statement": definition["statement"],
                "useful_context": definition["useful_context"],
                "topics": topics,
                "facets": {
                    "domain": "personal" if "personal" in topics else "work",
                    "time_scope": "multi_year" if len(rows) >= 10 else "event_cluster",
                    "confidence": strength,
                    "sensitivity": "private_work" if signal != "unknown_public_portfolio" else "private_boundary",
                    "freshness": freshness_for_refs(rows),
                    "source": "source_native_distiller",
                    "supporting_source_count": len(refs),
                    "supporting_source_types": dict(source_types.most_common()),
                    "representative_repos": [repo for repo, _ in repos.most_common(8)],
                    "representative_jira_keys": sorted(jira_keys)[:12],
                },
                "query_patterns": sorted(set(definition.get("query_patterns", []))),
                "behavioral_use": (
                    "Use this distilled memory as answer-ready personal context. "
                    "Lead with practical behavior, preferences, and limits; keep raw evidence hidden unless proof is requested."
                ),
                "guardrails": definition["guardrails"],
                "provenance_refs": [trace_id],
                "updated_at": generated_at,
            }
        )
        traces.extend(trace_links_for_memory(memory_id, trace_id, refs, generated_at, strength))

    return atoms, traces, source_rows


def build_profile_atoms(ledger: Path, generated_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    path = latest_profile(ledger, "master-evidence-profile")
    if not path:
        return [], []

    markdown = path.read_text(encoding="utf-8")
    atoms: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []

    for heading, section in split_sections(markdown):
        if heading.strip().lower() in SKIP_PROFILE_HEADINGS:
            continue
        claim = extract_claim(section)
        if not claim or claim.lower().startswith("representative evidence"):
            continue
        useful_context = extract_bullets_after("Distilled content", section)
        if not useful_context:
            useful_context = [claim]
        topics = topics_for(heading, claim, " ".join(useful_context))
        memory_type = memory_type_for(heading, claim, topics)
        memory_id = f"memory:{memory_type}.{slug(heading)}"
        provenance_ref = f"trace:{memory_id.removeprefix('memory:')}"
        guardrails = extract_guardrails(section)
        evidence_ids = sorted(set(SOURCE_ID_PATTERN.findall(section)))

        atoms.append(
            {
                "id": memory_id,
                "subject": "hanjeahwan",
                "memory_type": memory_type,
                "statement": claim,
                "useful_context": useful_context[:8],
                "topics": topics,
                "facets": {
                    "domain": "work",
                    "time_scope": "multi_year",
                    "confidence": extract_confidence(section),
                    "sensitivity": "private_work",
                    "freshness": "current",
                    "source": path.relative_to(ledger).as_posix(),
                },
                "query_patterns": query_patterns_for(heading, topics, memory_type),
                "behavioral_use": (
                    "Use this memory to answer with useful personal context first. "
                    "Do not lead with project names, counts, or private source ids unless proof is requested."
                ),
                "guardrails": guardrails
                or [
                    "Do not expose private source details unless proof is requested.",
                    "Do not turn this memory into a resume claim unless the caller asks for an export.",
                ],
                "provenance_refs": [provenance_ref],
                "updated_at": generated_at,
            }
        )

        for evidence_id in evidence_ids:
            traces.append(
                {
                    "id": f"{provenance_ref}:{stable_hash(evidence_id, 12)}",
                    "memory_id": memory_id,
                    "source_id": evidence_id,
                    "source_type": source_type_from_id(evidence_id),
                    "support_role": "supporting",
                    "strength": extract_confidence(section),
                    "reason": "Internal source trace used to refresh or audit this memory atom.",
                    "visibility": "internal",
                    "updated_at": generated_at,
                }
            )

    return atoms, traces


def build_manual_atoms(ledger: Path, generated_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = read_jsonl(ledger / "sources" / "manual.jsonl")
    atoms: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    for row in rows:
        raw = row.get("raw_excerpt") if isinstance(row.get("raw_excerpt"), dict) else {}
        title = clean_text(row.get("title") or row.get("summary") or row.get("id"))
        if not title:
            continue
        context = [
            clean_text(raw.get(key))
            for key in ["context", "problem", "action", "result", "impact", "notes"]
            if clean_text(raw.get(key))
        ]
        if not context and clean_text(row.get("summary")):
            context = [clean_text(row.get("summary"))]
        topics = topics_for(title, " ".join(context), "personal")
        memory_type = "personal_context" if "personal" in topics else "work_history"
        memory_id = f"memory:{memory_type}.{slug(title)}.{stable_hash(str(row.get('id')), 8)}"
        trace_id = f"trace:{memory_id.removeprefix('memory:')}"
        atoms.append(
            {
                "id": memory_id,
                "subject": "hanjeahwan",
                "memory_type": memory_type,
                "statement": title,
                "useful_context": context[:8],
                "topics": topics,
                "facets": {
                    "domain": "personal" if memory_type == "personal_context" else "work",
                    "time_scope": "event",
                    "confidence": "strong",
                    "sensitivity": "private",
                    "freshness": "current",
                    "source": "sources/manual.jsonl",
                },
                "query_patterns": query_patterns_for(title, topics, memory_type),
                "behavioral_use": "Use this memory as personal context. Do not expose private detail unless the caller is authorized and asks for it.",
                "guardrails": ["Respect privacy boundaries around manual personal material."],
                "provenance_refs": [trace_id],
                "updated_at": generated_at,
            }
        )
        traces.append(
            {
                "id": f"{trace_id}:{stable_hash(str(row.get('id')), 12)}",
                "memory_id": memory_id,
                "source_id": str(row.get("id", "")),
                "source_type": str(row.get("source_type", "manual_event")),
                "support_role": "primary",
                "strength": "strong",
                "reason": "Manual material supplied by the user.",
                "visibility": "internal",
                "updated_at": generated_at,
            }
        )
    return atoms, traces


def build_candidate_atoms(candidates: list[dict[str, Any]], generated_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    atoms: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    for candidate in candidates:
        memory_id = str(candidate.get("memory_id", ""))
        trace_id = str(candidate.get("trace_id", ""))
        if not memory_id or not trace_id:
            continue
        atoms.append(
            {
                "id": memory_id,
                "subject": str(candidate.get("subject", "hanjeahwan")),
                "memory_type": str(candidate.get("memory_type", "knowledge")),
                "statement": str(candidate.get("statement", "")),
                "useful_context": [str(item) for item in candidate.get("useful_context", [])],
                "topics": [str(item) for item in candidate.get("topics", [])],
                "facets": candidate.get("facets", {}),
                "query_patterns": [str(item) for item in candidate.get("query_patterns", [])],
                "behavioral_use": str(candidate.get("behavioral_use", "")),
                "guardrails": [str(item) for item in candidate.get("guardrails", [])],
                "provenance_refs": [trace_id],
                "updated_at": generated_at,
            }
        )
        seen: set[str] = set()
        strength = str(candidate.get("facets", {}).get("confidence", "medium"))
        for index, ref in enumerate(candidate.get("source_refs", [])[:80]):
            source_id = str(ref.get("id", ""))
            if not source_id or source_id in seen:
                continue
            seen.add(source_id)
            traces.append(
                {
                    "id": f"{trace_id}:{stable_hash(source_id, 12)}",
                    "memory_id": memory_id,
                    "source_id": source_id,
                    "source_type": str(ref.get("source_type", source_type_from_id(source_id))),
                    "support_role": "primary" if index < 8 else "supporting",
                    "strength": strength,
                    "reason": "Source cluster supports this deeper distilled self-context memory.",
                    "visibility": "internal",
                    "updated_at": generated_at,
                }
            )
    return atoms, traces


def build_source_coverage_model(ledger: Path) -> dict[str, int]:
    sources = ledger / "sources"
    counts = {}
    for name in SOURCE_FILES:
        counts[name] = len(read_jsonl(sources / name))
    return counts


def dedupe_atoms(atoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for atom in atoms:
        existing = by_id.get(atom["id"])
        if not existing:
            by_id[atom["id"]] = atom
            continue
        existing["useful_context"] = sorted(set(existing["useful_context"]) | set(atom["useful_context"]))
        existing["topics"] = sorted(set(existing["topics"]) | set(atom["topics"]))
        existing["guardrails"] = sorted(set(existing["guardrails"]) | set(atom["guardrails"]))
        existing["provenance_refs"] = sorted(set(existing["provenance_refs"]) | set(atom["provenance_refs"]))
    return sorted(by_id.values(), key=lambda row: (row["memory_type"], row["id"]))


def dedupe_traces(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted({row["id"]: row for row in traces}.values(), key=lambda row: (row["memory_id"], row["id"]))


def build_graph_edges(atoms: list[dict[str, Any]], generated_at: str) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    by_id = {atom["id"]: atom for atom in atoms}
    by_topic: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for atom in atoms:
        for topic in atom.get("topics", []):
            by_topic[str(topic)].append(atom)

    for topic, group in by_topic.items():
        group = sorted(group, key=lambda item: item["id"])
        for atom in group:
            peers = [peer for peer in group if peer["id"] != atom["id"]][:4]
            for peer in peers:
                edges.append(
                    {
                        "from_memory_id": atom["id"],
                        "to_memory_id": peer["id"],
                        "relation": "belongs_to_topic",
                        "weight": 0.35,
                        "reason": f"Both memories belong to the {topic} topic cluster.",
                        "topic": topic,
                        "updated_at": generated_at,
                    }
                )
        for left, right in zip(group[:10], group[1:11]):
            edges.append(
                {
                    "from_memory_id": left["id"],
                    "to_memory_id": right["id"],
                    "relation": "co_occurs_with",
                    "weight": 0.45,
                    "reason": f"These memories repeatedly co-occur in the {topic} topic cluster.",
                    "topic": topic,
                    "updated_at": generated_at,
                }
            )

    allowed = {"supports", "contrasts", "refines", "belongs_to_topic", "co_occurs_with", "supersedes", "needs_more_evidence"}
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for edge in edges:
        if edge["relation"] not in allowed:
            continue
        key = (edge["from_memory_id"], edge["to_memory_id"], edge["relation"])
        if edge["from_memory_id"] == edge["to_memory_id"]:
            continue
        existing = unique.get(key)
        if not existing or float(edge.get("weight", 0)) > float(existing.get("weight", 0)):
            unique[key] = edge
    return sorted(unique.values(), key=lambda row: (row["relation"], row["from_memory_id"], row["to_memory_id"]))


def build_self_model(
    atoms: list[dict[str, Any]],
    source_counts: dict[str, int],
    generated_at: str,
    voice_profile: dict[str, Any],
    deep_distillation: dict[str, Any] | None = None,
    identity_facts: dict[str, Any] | None = None,
    identity_graph: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    topic_counts: Counter[str] = Counter()
    personal_atom_count = 0
    for atom in atoms:
        topic_counts.update(atom.get("topics", []))
        facets = atom.get("facets", {}) if isinstance(atom.get("facets"), dict) else {}
        if str(atom.get("memory_type", "")) == "personal_context" or (
            str(atom.get("memory_type", "")) == "personal_identity" and str(facets.get("confidence_class", "")) != "unknown"
        ):
            personal_atom_count += 1
    sections, persona_eval, agent_operating_context, voice_style_eval = build_persona_sections(
        atoms,
        generated_at,
        sparse_personal_context=personal_atom_count == 0,
        voice_profile=voice_profile,
    )

    topic_clusters = []
    for topic, _count in topic_counts.most_common(20):
        group = [atom for atom in atoms if topic in atom.get("topics", [])]
        if not group:
            continue
        topic_clusters.append(
            {
                "id": f"topic:{topic}",
                "topic": topic,
                "summary": " ".join(str(atom.get("statement", "")) for atom in group[:3]),
                "memory_atoms": [str(atom.get("id", "")) for atom in group],
                "level": "topic_cluster",
            }
        )

    edges = build_graph_edges(atoms, generated_at)

    return (
        {
            "subject": "hanjeahwan",
            "generated_at": generated_at,
            "architecture": "self-context-v2.8",
            "source_counts": source_counts,
            "memory_count": len(atoms),
            "retained_memory_atoms": len(atoms),
            "legacy_atoms_pruned": True,
            "deep_distillation": deep_distillation or {},
            "dense_identity": {
                "ready": bool(identity_facts and identity_graph),
                "identityFactsReady": bool(identity_facts),
                "identityGraphReady": bool(identity_graph),
                "identity_sections": [
                    "self_model:declared_profile",
                    "self_model:career_timeline",
                    "self_model:experience_scope",
                    "self_model:role_identity",
                    "self_model:technical_stack",
                    "self_model:impact_profile",
                    "self_model:review_style",
                    "self_model:review_authority",
                    "self_model:repo_authority",
                    "self_model:release_ownership",
                    "self_model:jira_leadership",
                    "self_model:architecture_material",
                    "self_model:agent_collaboration_style",
                    "self_model:portfolio_cases",
                    "self_model:personal_identity",
                    "self_model:learning_trajectory",
                ],
            },
            "persona_synthesis": {
                "ready": persona_eval.get("passes", False),
                "sections": persona_eval.get("personaSections", []),
                "agent_operating_context_ready": persona_eval.get("agentOperatingContextReady", False),
                "voice_profile_ready": persona_eval.get("voiceProfileReady", False),
                "voice_style_ready": persona_eval.get("voiceStyleReady", False),
            },
            "top_topics": dict(topic_counts.most_common(20)),
            "sections": sections,
            "agent_operating_context": agent_operating_context,
            "topic_clusters": topic_clusters,
            "memory_graph_edges": edges,
            "hierarchy": {
                "levels": ["memory_atom", "topic_cluster", "self_model_section", "whole_person_summary"],
                "retrieval_policy": "Search canonical self_model sections first, expand through retained atoms and topic clusters, and return answer-ready context packs before provenance.",
            },
            "default_answer_contract": [
                "Answer directly.",
                "Provide useful personal clone context.",
                "Add behavioral guidance when the caller may act for the user.",
                "State boundaries and unknowns when the ledger is sparse.",
                "Hide provenance unless proof is requested.",
            ],
        },
        persona_eval,
        agent_operating_context,
        voice_style_eval,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    ledger = resolve_ledger_path(args.ledger)
    generated_at = now_iso()
    atoms: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []

    source_clusters, distillation_candidates, distillation_eval = build_source_clusters_and_candidates(ledger, generated_at)
    candidate_atoms, candidate_traces = build_candidate_atoms(distillation_candidates, generated_at)
    manual_atoms, manual_traces = build_manual_atoms(ledger, generated_at)
    atoms.extend(candidate_atoms)
    atoms.extend(manual_atoms)
    traces.extend(candidate_traces)
    traces.extend(manual_traces)
    identity_facts, identity_graph, identity_atoms, identity_traces = build_dense_identity_graph(ledger, atoms, generated_at)
    atoms.extend(identity_atoms)
    traces.extend(identity_traces)

    atoms = dedupe_atoms(atoms)
    traces = dedupe_traces(traces)
    source_counts = build_source_coverage_model(ledger)
    voice_profile = build_voice_profile(ledger, generated_at)
    self_model, persona_eval, agent_operating_context, voice_style_eval = build_self_model(
        atoms,
        source_counts,
        generated_at,
        voice_profile,
        distillation_eval,
        identity_facts,
        identity_graph,
    )
    graph_edges = self_model.get("memory_graph_edges", [])

    derived = ledger / "derived"
    write_jsonl(derived / "source_clusters.jsonl", source_clusters)
    write_jsonl(derived / "distillation_candidates.jsonl", distillation_candidates)
    write_json(derived / "distillation_eval.json", distillation_eval)
    write_json(derived / "persona_synthesis_eval.json", persona_eval)
    write_json(derived / "identity_facts.json", identity_facts)
    write_json(derived / "identity_graph.json", identity_graph)
    write_json(derived / "voice_profile.json", voice_profile)
    write_json(derived / "voice_style_eval.json", voice_style_eval)
    write_json(derived / "agent_operating_context.json", agent_operating_context)
    write_jsonl(derived / "memory_atoms.jsonl", atoms)
    write_jsonl(derived / "provenance_links.jsonl", traces)
    write_jsonl(derived / "memory_graph_edges.jsonl", graph_edges)
    write_json(derived / "self_model.json", self_model)

    summary = {
        "ledger": str(ledger),
        "memory_atoms": len(atoms),
        "source_clusters": len(source_clusters),
        "distillation_candidates": len(distillation_candidates),
        "provenance_links": len(traces),
        "memory_graph_edges": len(graph_edges),
        "distillation_eval": str(derived / "distillation_eval.json"),
        "persona_synthesis_eval": str(derived / "persona_synthesis_eval.json"),
        "voice_profile": str(derived / "voice_profile.json"),
        "voice_style_eval": str(derived / "voice_style_eval.json"),
        "agent_operating_context": str(derived / "agent_operating_context.json"),
        "identity_facts": str(derived / "identity_facts.json"),
        "identity_graph": str(derived / "identity_graph.json"),
        "source_counts": source_counts,
        "self_model": str(derived / "self_model.json"),
        "legacyAtomsPruned": True,
        "retainedMemoryAtoms": len(atoms),
        "personaSynthesisReady": persona_eval.get("passes", False),
        "agentOperatingContextReady": persona_eval.get("agentOperatingContextReady", False),
        "voiceProfileReady": persona_eval.get("voiceProfileReady", False),
        "voiceStyleReady": persona_eval.get("voiceStyleReady", False),
        "identityFactsReady": bool(identity_facts),
        "identityGraphReady": bool(identity_graph),
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"memory_atoms={len(atoms)} provenance_links={len(traces)} ledger={ledger}")


if __name__ == "__main__":
    main()
