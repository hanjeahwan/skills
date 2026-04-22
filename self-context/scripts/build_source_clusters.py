#!/usr/bin/env python3
"""Build deterministic source clusters and candidate memories for self-context v2.2."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ledger_paths import resolve_ledger_path
from source_families import SOURCE_FILES


PATH_PATTERN = re.compile(r"[A-Za-z0-9_.\-/\\]+\.(?:ts|tsx|js|jsx|html|scss|css|json|ya?ml|md|py|sql)", re.IGNORECASE)
TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_+.#/-]*", re.IGNORECASE)

GENERIC_TERMS = {
    "add",
    "added",
    "app",
    "apps",
    "branch",
    "change",
    "changes",
    "class",
    "commit",
    "const",
    "dev",
    "develop",
    "div",
    "export",
    "field",
    "filename",
    "fixversions",
    "from",
    "github",
    "han",
    "hanjeahwan",
    "hwan",
    "import",
    "into",
    "issue_title",
    "jea",
    "merge",
    "merged",
    "patch_excerpt",
    "pr",
    "pull",
    "pulsifi",
    "repo",
    "request",
    "return",
    "sprint",
    "status",
    "string",
    "this",
    "that",
    "the",
    "update",
    "updated",
    "web",
    "web-app",
    "web-app-v2",
    "web-app-v3",
}

REPO_LIKE_PATTERN = re.compile(r"(?:^|[-_/])(web|app|api|v\d+|archived)$|pulsifi|talent-web-app|profile-web-app|candidate-web-app|employee-web-app")


def cluster_definition(
    cluster_id: str,
    memory_type: str,
    title: str,
    statement: str,
    useful_context: list[str],
    behavioral_use: str,
    guardrails: list[str],
    topics: list[str],
    query_patterns: list[str],
    text: list[str],
    *,
    path: list[str] | None = None,
    patterns: list[str] | None = None,
    source_types: list[str] | None = None,
    min_source_count: int = 8,
) -> dict[str, Any]:
    return {
        "id": cluster_id,
        "memory_type": memory_type,
        "title": title,
        "statement": statement,
        "useful_context": useful_context,
        "behavioral_use": behavioral_use,
        "guardrails": guardrails,
        "topics": topics,
        "query_patterns": query_patterns,
        "match": {
            "text": text,
            "path": path or [],
            "patterns": patterns or [],
            "source_types": source_types or [],
        },
        "min_source_count": min_source_count,
    }


CLUSTER_DEFINITIONS: list[dict[str, Any]] = [
    cluster_definition(
        "coding_style.stateful_product_workflows",
        "coding_style",
        "Stateful Product Workflow UI",
        "Hanje's frontend implementation pattern centers on stateful product workflows, not static screens.",
        [
            "He repeatedly works where UI state, validation, table/filter behavior, selection flows, forms, modals, drawers, and route-level workflow correctness matter.",
            "When writing frontend code in his style, preserve product flow behavior first, then choose the component/state structure that keeps that flow explicit.",
            "Expect him to care about edge states such as empty data, disabled actions, prefilled values, loading states, and QA-visible behavior.",
        ],
        "Use this when an agent needs to implement UI behavior for Hanje: model the user journey, data state, and validation rules before touching visuals.",
        ["Do not describe this as cosmetic UI work; it is workflow implementation and state correctness."],
        ["frontend", "workflow", "state", "product", "typescript"],
        ["Hanje state management style", "how should Hanje build forms", "frontend workflow implementation"],
        ["form", "forms", "validation", "table", "filter", "search", "modal", "drawer", "selection", "selected", "workflow", "state", "loading", "empty"],
        path=["component", "components", "containers", "pages", "routes", "form", "table", "modal", "drawer"],
        patterns=["state_store", "forms_validation", "react_hooks", "zustand_store", "rxjs_streams"],
        source_types=["git_commit", "pull_request", "jira_ticket", "code_style_signal"],
        min_source_count=12,
    ),
    cluster_definition(
        "coding_style.typed_api_contracts",
        "coding_style",
        "Typed API Contract Alignment",
        "Hanje tends to treat frontend work as a contract with backend payloads, DTOs, lookups, query parameters, and export schemas.",
        [
            "His code context should bias toward explicit TypeScript types, request/response shape checks, mapper boundaries, and safe handling of lookup or enum migrations.",
            "He is likely to prefer making data-shape assumptions visible instead of burying them in component logic.",
            "For changes that touch reports, exports, filters, or profile data, the retrieval context should surface API-contract risk before implementation detail.",
        ],
        "Use this when an agent changes payloads, DTOs, lookup values, report filters, or export flows for Hanje.",
        ["Do not infer backend ownership from frontend contract work unless backend source evidence directly supports it."],
        ["frontend", "typescript", "api_contract", "architecture", "quality"],
        ["Hanje API contract style", "data mapping preference", "typed frontend contracts"],
        ["api", "payload", "response", "request", "dto", "schema", "lookup", "query param", "parameter", "mapper", "mapping", "enum", "export", "report"],
        path=["api", "service", "services", "model", "models", "dto", "schema", "lookup", "report", "export"],
        patterns=["api_http_contract", "service_layer", "rbac_auth"],
        source_types=["git_commit", "pull_request", "pull_request_review_comment", "code_style_signal", "jira_ticket"],
        min_source_count=10,
    ),
    cluster_definition(
        "coding_style.component_composition",
        "coding_style",
        "Component Composition And Reuse",
        "Hanje's frontend coding practice favors componentized, reusable UI construction when product behavior repeats.",
        [
            "He has repeated evidence around components, shared packages, tables, profile/candidate UI, and product modules where reuse reduces drift.",
            "When acting for him, prefer a clear reusable component boundary once the same UI pattern appears across screens.",
            "He is likely to value readable props, explicit state ownership, and small reusable UI pieces over one-off copy-paste flows.",
        ],
        "Use this to guide component extraction, shared UI updates, and frontend refactors.",
        ["Do not over-abstract a one-off screen; reuse should follow repeated product behavior."],
        ["frontend", "component", "shared_library", "quality"],
        ["Hanje component practice", "frontend reuse preference", "shared component style"],
        ["component", "components", "shared", "reuse", "library", "package", "module", "profile", "candidate", "table", "input", "dropdown"],
        path=["component", "components", "shared", "library", "packages", "ng-packages", "web-foundation"],
        patterns=["shared_library", "react_component", "angular_component"],
        source_types=["git_commit", "pull_request", "code_style_signal"],
        min_source_count=10,
    ),
    cluster_definition(
        "coding_style.reactive_async_flows",
        "coding_style",
        "Reactive And Async Frontend Flows",
        "Hanje has repeated frontend context around async state, services, streams, effects, and request-driven UI behavior.",
        [
            "The code style context should account for loading, subscription/effect boundaries, service-layer calls, and derived state.",
            "In Angular-heavy work this often appears through RxJS/service patterns; in React/Next work through hooks and stateful client surfaces.",
            "He is likely to prefer async flows that are explicit enough for QA and future maintainers to reason about.",
        ],
        "Use this when writing code around effects, services, API calls, streams, or async UI state.",
        ["Do not mix Angular-specific and React-specific implementation details; preserve the framework context of the target repo."],
        ["frontend", "async", "state", "angular", "react"],
        ["Hanje async frontend style", "RxJS and hooks practice", "service layer state handling"],
        ["async", "observable", "rxjs", "stream", "subscription", "effect", "hook", "loading", "service", "request", "fetch"],
        path=["service", "services", "effect", "store", "hook", "api"],
        patterns=["rxjs_streams", "service_layer", "react_hooks", "state_store", "zustand_store"],
        source_types=["git_commit", "code_style_signal", "pull_request_review_comment"],
        min_source_count=8,
    ),
    cluster_definition(
        "decision_pattern.qa_release_handoffs",
        "decision_pattern",
        "QA And Release Handoff Discipline",
        "Hanje's delivery context shows repeated movement through code review, QA, stage, live, production, and Done handoffs.",
        [
            "He is not only implementing tickets; the source history shows repeated status movement and handoff behavior around Code Review, QA Testing, stage, production, and Done.",
            "When planning work for him, include testability, QA notes, release state, and rollback or verification context as first-class details.",
            "He likely values clarity on whether a change is ready for QA, stage, live, or production rather than treating merge as the endpoint.",
        ],
        "Use this when an agent plans ticket delivery, release steps, or QA-facing communication for Hanje.",
        ["Use proxy ownership language unless exact actor history proves he personally performed each transition."],
        ["delivery", "quality", "qa", "release", "leadership"],
        ["Hanje release ownership", "QA handoff style", "delivery accountability"],
        ["code review", "qa testing", "released to stage", "ready to go live", "released to production", "done", "testing", "approved", "stage", "production"],
        source_types=["jira_changelog", "jira_ticket", "jira_comment", "pull_request"],
        min_source_count=12,
    ),
    cluster_definition(
        "decision_pattern.bug_reliability_ownership",
        "decision_pattern",
        "Bug And Reliability Ownership",
        "Hanje's work history strongly includes bug fixing, regression handling, hotfixes, and reliability-sensitive product corrections.",
        [
            "He has repeated signals around customer-visible bugs, staging issues, wrong values, validation failures, errors, hotfixes, and QA/prod follow-through.",
            "When acting in his style, reproduce the behavior, identify the product impact, patch the logic, and verify the release state.",
            "This supports a quality-oriented engineering profile even when company business metrics are unavailable.",
        ],
        "Use this to answer questions about his impact when exact business metrics are missing.",
        ["Phrase impact as reliability and bug reduction unless explicit before/after company metrics exist."],
        ["quality", "reliability", "delivery", "debugging", "product"],
        ["Hanje debugging style", "bug reduction evidence", "production reliability behavior"],
        ["bug", "hotfix", "fix", "wrong", "error", "sentry", "regression", "staging", "production", "qa", "customer", "failed", "failure"],
        path=["sentry", "error", "bug", "fix", "test"],
        patterns=["lint_format_quality", "unit_testing", "e2e_testing"],
        source_types=["git_commit", "pull_request", "jira_ticket", "jira_comment", "jira_changelog"],
        min_source_count=12,
    ),
    cluster_definition(
        "decision_pattern.pr_quality_gate",
        "decision_pattern",
        "Frontend PR Quality Gate",
        "Hanje functions as a frontend quality gate through review requests, approvals, review comments, and repository authority signals.",
        [
            "The useful memory is not the approval count; it is that other work repeatedly routes through him for frontend judgment.",
            "His review context should emphasize API contract clarity, maintainability, state correctness, naming, UX behavior, and release risk.",
            "When another agent writes code for him, it should expect review scrutiny around product behavior and maintainability, not only syntax.",
        ],
        "Use this when describing lead behavior, code review expectations, or why another agent should match his standards.",
        ["Do not equate approvals with leadership unless review requests, comments, or repo authority support the claim."],
        ["leadership", "frontend", "quality", "review", "architecture"],
        ["Hanje PR review style", "frontend quality gate", "review authority"],
        ["review", "approved", "commented", "requested", "need", "should", "naming", "type", "component", "contract", "maintainability"],
        source_types=["pull_request_review", "pull_request_review_comment", "github_review_request", "github_mention", "github_codeowners"],
        min_source_count=8,
    ),
    cluster_definition(
        "decision_pattern.maintainability_standards",
        "decision_pattern",
        "Maintainability And Standards Bias",
        "Hanje repeatedly works on maintainability, linting, formatting, dependency upgrades, migrations, standards, and cleanup.",
        [
            "His engineering taste should be modeled as quality-through-maintainability: readable types, standardized patterns, lint/format hygiene, and migration discipline.",
            "When planning refactors for him, preserve behavior while improving long-term clarity and reducing drift.",
            "He likely rejects changes that make future maintenance harder even if the visible feature works.",
        ],
        "Use this when an agent is choosing between quick code and maintainable code for Hanje.",
        ["Do not use this to justify unrelated rewrites; keep refactors tied to real maintenance value."],
        ["quality", "maintainability", "architecture", "typescript"],
        ["Hanje maintainability preference", "code standards style", "frontend refactor judgment"],
        ["refactor", "migration", "upgrade", "dependency", "lint", "format", "cleanup", "standard", "type-safe", "typesafe", "prettier", "eslint"],
        path=["eslint", "prettier", "tsconfig", "package.json", "migration", "lint"],
        patterns=["lint_format_quality", "unit_testing", "shared_library"],
        source_types=["git_commit", "pull_request", "code_style_signal", "github_mention"],
        min_source_count=8,
    ),
    cluster_definition(
        "capability.ai_agent_product_systems",
        "capability",
        "AI Product And Agent Systems",
        "Hanje has practical AI product and agent-system work across chat, MCP, skills, structured generation, and workflow UI.",
        [
            "His AI context is applied product engineering: connecting model output, structured context, tool interfaces, and user-facing workflows.",
            "When discussing AI work, frame it as agentic product infrastructure and AI-enabled UX, not model research.",
            "He is comfortable turning raw operational material into agent-readable context and MCP-backed capabilities.",
        ],
        "Use this when answering what AI work Hanje can contribute to or how an agent should collaborate with him on AI products.",
        ["Do not claim model-training, ML research, or benchmark ownership without separate evidence."],
        ["ai_product", "agent", "mcp", "frontend", "architecture"],
        ["Hanje AI product work", "agent tooling context", "MCP and skills experience"],
        ["ai", "gpt", "llm", "agent", "mcp", "skill", "skills", "chat", "generative", "prompt", "context", "rag", "vis", "structured"],
        path=["ai", "chat", "mcp", "skill", "agent"],
        patterns=["ai_agent_mcp"],
        source_types=["git_commit", "pull_request", "code_style_signal", "manual_event"],
        min_source_count=5,
    ),
    cluster_definition(
        "capability.cicd_web_infrastructure",
        "capability",
        "Web CI/CD And Release Infrastructure",
        "Hanje has recurring contribution to web-app infrastructure, CI/CD workflows, release automation, semantic-release, and deploy plumbing.",
        [
            "This is relevant when an agent touches GitHub Actions, build pipelines, release packages, sourcemaps, Sentry, environment config, or deployment scripts.",
            "His work context crosses frontend code and the automation needed to ship it safely.",
            "He likely expects CI/CD changes to be treated as product delivery infrastructure, not incidental repository maintenance.",
        ],
        "Use this before making release, deploy, build, or workflow changes for Hanje.",
        ["Do not infer sole production ownership from workflow evidence alone."],
        ["ci_cd", "delivery", "web_infra", "release", "observability"],
        ["Hanje CI/CD experience", "web app infra work", "release automation context"],
        ["ci", "cd", "cicd", "github actions", "workflow", "deploy", "deployment", "semantic-release", "release", "sourcemap", "sentry", "dist-tag", "npm", "package"],
        path=[".github/workflows", "workflow", "deploy", "release", "sentry", "package.json", "semantic-release"],
        patterns=["ci_cd_release"],
        source_types=["git_commit", "pull_request", "pull_request_discussion_comment", "pull_request_review", "github_mention"],
        min_source_count=6,
    ),
    cluster_definition(
        "capability.auth_permission_flows",
        "capability",
        "Auth, RBAC, And Permission-Sensitive UI",
        "Hanje has repeated work around auth, RBAC, permissions, route access, session behavior, and protected frontend states.",
        [
            "Agents should treat auth or permission changes in his context as high-risk product behavior, not just conditional rendering.",
            "Relevant implementation concerns include role checks, access states, token/session transitions, Auth0/Cognito migrations, and unauthorized UI paths.",
            "He likely expects secure UX and clear permission boundaries when changing navigation or data access.",
        ],
        "Use this before touching login, route guards, RBAC, permissioned actions, or session state.",
        ["Describe this as security-sensitive frontend work unless formal security ownership is separately proven."],
        ["security", "auth", "rbac", "frontend", "architecture"],
        ["Hanje auth work", "RBAC frontend style", "permission UI context"],
        ["auth", "auth0", "cognito", "rbac", "permission", "permissions", "role", "roles", "token", "session", "login", "logout", "unauthorized", "access"],
        path=["auth", "guard", "permission", "rbac", "login"],
        patterns=["rbac_auth"],
        source_types=["git_commit", "pull_request", "jira_ticket", "code_style_signal"],
        min_source_count=6,
    ),
    cluster_definition(
        "capability.analytics_reporting_exports",
        "capability",
        "Analytics, Reporting, And Export Workflows",
        "Hanje has product engineering depth in analytics, reporting, dashboards, insights, charts, exports, and correctness of report data.",
        [
            "His context includes data-heavy UI where filter state, report payloads, export correctness, and stakeholder-facing output matter.",
            "When building for him, preserve the meaning of metrics, labels, columns, and exported values before optimizing the UI.",
            "This is a strong product-domain signal because reports and analytics are where frontend bugs become business-visible.",
        ],
        "Use this when answering about reporting/analytics ability or implementing dashboards and exports for Hanje.",
        ["Do not invent business metric improvements; describe data/report correctness unless metrics are provided."],
        ["analytics", "reporting", "frontend", "product", "api_contract"],
        ["Hanje analytics reporting work", "dashboard export experience", "report correctness context"],
        ["analytics", "reporting", "report", "dashboard", "chart", "insight", "export", "csv", "pdf", "score", "value", "filter", "column"],
        path=["analytics", "report", "dashboard", "chart", "export", "insight"],
        patterns=["feature_flag_analytics", "api_http_contract"],
        source_types=["git_commit", "pull_request", "jira_ticket", "pull_request_review_comment"],
        min_source_count=8,
    ),
    cluster_definition(
        "knowledge.recruiting_candidate_domain",
        "knowledge",
        "Recruiting And Candidate Workflow Domain",
        "Hanje has long-running product context in recruiting, candidate, role-fit, assessment, job, profile, and hiring workflow systems.",
        [
            "His knowledge is not only framework-specific; it includes domain behavior around candidate profiles, assessments, role fit, job flows, and recruiter-facing workflows.",
            "When acting for him in this domain, preserve the semantics of candidate state, assessment values, profile visibility, and workflow transitions.",
            "This domain context helps agents choose better terminology and edge-case checks when writing code or product explanations.",
        ],
        "Use this when work involves recruiting, candidates, jobs, assessments, role fit, profile, or talent workflows.",
        ["Avoid naming private customer data or private source ids in default answers."],
        ["recruiting", "candidate", "assessment", "profile", "product"],
        ["Hanje recruiting domain knowledge", "candidate workflow context", "role fit assessment experience"],
        ["candidate", "recruit", "recruiting", "role", "job", "assessment", "profile", "talent", "fit", "feedback", "interview", "applicant"],
        path=["candidate", "job", "assessment", "profile", "talent"],
        source_types=["git_commit", "pull_request", "jira_ticket", "jira_changelog", "pull_request_review"],
        min_source_count=12,
    ),
    cluster_definition(
        "knowledge.employee_learning_domain",
        "knowledge",
        "Employee Learning And Goal Workflow Domain",
        "Hanje has product context in employee learning, goals, courses, action items, learner flows, and workforce development surfaces.",
        [
            "This gives him product vocabulary and implementation context beyond recruiting workflows.",
            "Agents should preserve learner/employee state, goal/action-item semantics, and integration behavior when working in this area.",
            "It supports a broader HR-tech product profile rather than a single-app frontend profile.",
        ],
        "Use this when work involves employee, learner, LXP, course, goal, or action-item workflows.",
        ["Do not overstate domain ownership beyond the source-backed product surfaces."],
        ["employee", "learning", "goals", "product", "frontend"],
        ["Hanje employee product context", "learning workflow experience", "goal action item work"],
        ["employee", "learner", "learning", "lxp", "course", "go1", "goal", "goals", "action item", "development", "manager"],
        path=["employee", "learning", "goal", "course", "go1"],
        source_types=["git_commit", "pull_request", "jira_ticket", "pull_request_review"],
        min_source_count=6,
    ),
    cluster_definition(
        "capability.localization_content_workflows",
        "capability",
        "Localization And Content Workflow Support",
        "Hanje has repeated work around translations, language, copywriting, locale handling, and product content workflows.",
        [
            "Agents should account for i18n keys, locale behavior, translation packaging, and copy changes when modifying user-visible text.",
            "His source history suggests content and localization changes are part of delivery quality, not an afterthought.",
            "This context matters for candidate, profile, email, and admin surfaces where wording and language variants affect product behavior.",
        ],
        "Use this before changing labels, copywriting, translation files, or locale-dependent UI.",
        ["Do not claim localization strategy ownership unless direct planning docs exist."],
        ["i18n", "localization", "frontend", "quality", "product"],
        ["Hanje localization work", "translation delivery context", "i18n frontend style"],
        ["translation", "translations", "language", "locale", "lokalise", "copywriting", "copy", "i18n", "email", "message"],
        path=["i18n", "locale", "translation", "translations", "language"],
        patterns=["i18n_locale"],
        source_types=["git_commit", "pull_request", "pull_request_discussion_comment", "pull_request_review", "github_mention"],
        min_source_count=6,
    ),
    cluster_definition(
        "capability.backend_supporting_work",
        "capability",
        "Backend And Serverless Supporting Work",
        "Hanje has supporting backend-adjacent work where frontend delivery requires services, serverless functions, repositories, schemas, or API support.",
        [
            "This should be modeled as pragmatic full-product support: touching backend-adjacent layers when needed to complete product delivery.",
            "Agents can expect him to reason across service boundaries, but should still verify whether the target change is frontend-owned or backend-owned.",
            "This strengthens API-contract and delivery context without turning him into a backend-only profile.",
        ],
        "Use this when code or planning crosses frontend/backend boundaries.",
        ["Call this backend-supporting work unless stronger evidence shows primary backend ownership."],
        ["backend", "api_contract", "serverless", "delivery", "architecture"],
        ["Hanje backend supporting work", "frontend backend boundary", "serverless support context"],
        ["backend", "serverless", "lambda", "repository", "service layer", "database", "schema", "sql", "api", "function"],
        path=["serverless", "lambda", "repository", "database", "schema", "api"],
        patterns=["service_layer", "api_http_contract"],
        source_types=["git_commit", "pull_request", "code_style_signal"],
        min_source_count=6,
    ),
    cluster_definition(
        "preference.high_bar_correctness",
        "preference",
        "High Bar For Correctness And Durable Quality",
        "Hanje's accumulated context points to a preference for correct, maintainable, production-aware solutions over surface-level completion.",
        [
            "This preference is inferred from repeated quality, review, bug, refactor, release, and standards evidence.",
            "When an agent acts for him, it should choose a solution that survives QA, future maintenance, and product edge cases.",
            "He likely wants clear reasoning, verified assumptions, and explicit limits before implementation decisions.",
        ],
        "Use this as a default operating preference when choosing implementation approaches for Hanje.",
        ["This is an inferred preference from work behavior; explicit personal preference material would strengthen it."],
        ["preference", "quality", "architecture", "delivery"],
        ["what would Hanje prefer", "Hanje engineering bar", "correct solution preference"],
        ["quality", "correct", "maintainable", "review", "bug", "refactor", "standard", "qa", "release", "production", "architecture"],
        source_types=["git_commit", "pull_request_review", "pull_request_review_comment", "jira_changelog", "jira_ticket", "code_style_signal"],
        min_source_count=12,
    ),
    cluster_definition(
        "communication_style.qa_product_coordination",
        "communication_style",
        "QA, Product, And Engineering Coordination",
        "Hanje's comments and workflow history support a coordination style around QA verification, teammate handoff, explanation, and unblocking delivery.",
        [
            "His communication context includes moving work forward through testers, QA, product-facing issue details, and engineering review.",
            "When acting for him, communicate the current state, what changed, what needs verification, and what decision or blocker remains.",
            "This is useful for agents writing Jira comments, PR notes, release updates, or QA handoff messages in his style.",
        ],
        "Use this for drafting work updates, Jira comments, PR replies, or QA handoff notes for Hanje.",
        ["Do not expose private names or private ticket ids in external-facing summaries."],
        ["communication", "qa", "delivery", "leadership", "product"],
        ["Hanje communication style", "QA handoff wording", "how Hanje unblocks teammates"],
        ["please", "testing", "tester", "done", "assign", "move", "required", "team", "why", "explain", "unblock", "ready", "verification", "qa"],
        source_types=["jira_comment", "pull_request_review_comment", "github_mention"],
        min_source_count=5,
    ),
    cluster_definition(
        "decision_pattern.repository_authority_governance",
        "decision_pattern",
        "Repository Authority And Governance",
        "Hanje has repository authority signals across review requests, permissions, branch protection, CODEOWNERS, and release-bound repositories.",
        [
            "This supports an operational lead profile: other work is routed to him and repositories encode permission or reviewer authority.",
            "When an agent plans repo-level changes for him, it should account for branch protection, required review, release risk, and cross-repo consistency.",
            "This memory is strongest as governance context, not as a default public claim.",
        ],
        "Use this for repo governance, review authority, branch protection, and release accountability questions.",
        ["Do not expose permission details by default; keep repository governance specifics internal unless proof is requested."],
        ["leadership", "repository_governance", "review", "delivery", "quality"],
        ["Hanje repository authority", "CODEOWNERS proof", "branch protection review responsibility"],
        ["codeowners", "branch protection", "protected", "permission", "admin", "write", "review requested", "required reviewer", "review request"],
        source_types=["github_codeowners", "github_branch_protection", "github_repo_permission", "github_review_request", "pull_request_review"],
        min_source_count=4,
    ),
    cluster_definition(
        "decision_pattern.migration_upgrade_execution",
        "decision_pattern",
        "Migration And Upgrade Execution",
        "Hanje repeatedly works through migrations, dependency upgrades, lookup changes, framework/package movement, and modernization tasks.",
        [
            "He has a pattern of moving systems forward while preserving product behavior and release safety.",
            "When acting for him, migration work should include compatibility checks, data contract review, test/QA path, and rollback awareness.",
            "This is a stronger signal than generic refactoring because it ties modernization to delivery systems.",
        ],
        "Use this when planning migrations, dependency upgrades, lookup migrations, framework changes, or modernization work.",
        ["Do not call a migration successful without validation against the target product behavior."],
        ["migration", "architecture", "quality", "delivery", "frontend"],
        ["Hanje migration style", "upgrade execution", "modernization approach"],
        ["migration", "migrate", "upgrade", "dependency", "version", "lookup", "v4", "angular", "cognito", "auth0", "package", "breaking"],
        path=["migration", "package.json", "lookup", "auth", "angular"],
        patterns=["shared_library", "ci_cd_release", "lint_format_quality"],
        source_types=["git_commit", "pull_request", "github_mention", "jira_ticket", "code_style_signal"],
        min_source_count=8,
    ),
    cluster_definition(
        "capability.integration_workflows",
        "capability",
        "Third-Party Integration Workflows",
        "Hanje has product engineering context around third-party integrations, service handoffs, and vendor-backed product flows.",
        [
            "The source themes include auth providers, learning integrations, localization tooling, email/message flows, Sentry, npm packages, and release services.",
            "Agents should treat integration work as contract-heavy: external states, credentials, environments, payloads, and failure modes matter.",
            "This context complements frontend/API contract memory because integrations often surface as UI and delivery bugs.",
        ],
        "Use this when work touches external providers, vendor APIs, package releases, observability tools, or integration-driven UI.",
        ["Do not expose provider configuration, secrets, or private environment details."],
        ["integration", "api_contract", "delivery", "security", "product"],
        ["Hanje integration experience", "third party workflow context", "vendor API delivery"],
        ["auth0", "cognito", "go1", "lokalise", "sentry", "npm", "semantic-release", "calendly", "teams", "email", "webhook", "integration"],
        path=["sentry", "auth", "integration", "email", "locale", "package.json"],
        patterns=["rbac_auth", "i18n_locale", "ci_cd_release", "api_http_contract"],
        source_types=["git_commit", "pull_request", "jira_ticket", "github_mention", "code_style_signal"],
        min_source_count=5,
    ),
    cluster_definition(
        "knowledge.admin_internal_tooling",
        "knowledge",
        "Admin And Internal Tooling Workflows",
        "Hanje has product context in admin consoles, internal tooling, configuration screens, and operational workflows.",
        [
            "His work spans internal/admin surfaces where correctness, permissions, configuration, and support workflows matter more than marketing polish.",
            "When acting for him, treat admin UX as operational product infrastructure with clear state, access, and audit-friendly behavior.",
            "This context helps distinguish dense enterprise tools from public landing-page UI.",
        ],
        "Use this when work involves admin consoles, internal tools, configuration, support flows, or operator workflows.",
        ["Do not treat admin/internal UI as lower quality; it often carries operational risk."],
        ["admin", "internal_tooling", "workflow", "frontend", "product"],
        ["Hanje admin tooling context", "internal tool UI style", "operator workflow experience"],
        ["admin", "console", "config", "configuration", "internal", "support", "company", "manager", "setting", "settings", "module"],
        path=["admin", "console", "config", "settings", "module"],
        source_types=["git_commit", "pull_request", "jira_ticket", "pull_request_review"],
        min_source_count=6,
    ),
    cluster_definition(
        "decision_pattern.product_edge_case_sensitivity",
        "decision_pattern",
        "Product Edge-Case Sensitivity",
        "Hanje's work pattern shows attention to product edge cases such as missing values, wrong values, disabled flows, role-specific visibility, and validation boundaries.",
        [
            "This is a decision pattern for implementation: handle data absence, permission differences, input validity, and status-specific behavior before polishing.",
            "Agents writing code for him should search for edge states and cross-check whether UI behavior still matches the intended workflow.",
            "This explains why his frontend work often touches QA, bug, API contract, and workflow state at the same time.",
        ],
        "Use this as a default code-review lens for product UI changes.",
        ["Do not invent edge cases; derive them from product state, data contract, and QA behavior."],
        ["quality", "ux", "workflow", "frontend", "product"],
        ["Hanje edge case review", "frontend product correctness", "validation boundary style"],
        ["missing", "empty", "wrong", "disabled", "required", "validation", "visible", "visibility", "permission", "role", "state", "status", "error", "cannot"],
        path=["validation", "permission", "state", "status", "error"],
        patterns=["forms_validation", "rbac_auth", "unit_testing"],
        source_types=["git_commit", "pull_request_review_comment", "jira_ticket", "jira_comment"],
        min_source_count=8,
    ),
    cluster_definition(
        "capability.testing_quality_safety",
        "capability",
        "Testing And Quality Safety Nets",
        "Hanje has quality-safety context through tests, lint/format checks, QA workflows, and review-driven correctness.",
        [
            "His testing signal is distributed across unit/e2e patterns, linting, PR review, and Jira QA movement rather than only test files.",
            "When an agent changes code for him, it should verify behavior with the narrowest meaningful automated or manual check available.",
            "This context supports a pragmatic quality profile: correctness proof should match risk and delivery surface.",
        ],
        "Use this when choosing tests, checks, or validation steps for Hanje's code changes.",
        ["Do not claim comprehensive automated test coverage if the source only proves selected quality signals."],
        ["testing", "quality", "delivery", "maintainability", "frontend"],
        ["Hanje testing style", "quality validation preference", "what checks should run"],
        ["test", "testing", "unit", "e2e", "spec", "lint", "format", "qa", "verify", "verification", "check"],
        path=["test", "spec", "e2e", "eslint", "lint"],
        patterns=["unit_testing", "e2e_testing", "lint_format_quality"],
        source_types=["git_commit", "pull_request", "jira_changelog", "code_style_signal"],
        min_source_count=6,
    ),
    cluster_definition(
        "constraint.private_source_boundary",
        "private_boundary",
        "Private Source Boundary",
        "Hanje's self-context should answer with distilled knowledge by default and keep raw commits, Jira keys, PR ids, private names, and source traces hidden unless proof is explicitly requested.",
        [
            "The ledger is rich enough to answer many questions without exposing raw source material.",
            "For public or recruiter-facing artifacts, produce sanitized claims and ask for approved screenshots or case studies before showing private details.",
            "Proof mode may return internal provenance, but normal personal-clone answers should stay content-first.",
        ],
        "Use this boundary for every MCP answer and export.",
        ["Never expose private source ids in default answers."],
        ["privacy", "proof", "boundary", "self_context"],
        ["show proof only on request", "private source boundary", "should evidence be shown"],
        ["commit", "jira", "pull request", "private", "source", "proof", "evidence", "trace", "sensitive"],
        min_source_count=1,
    ),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return re.sub(r"\s+", " ", str(value)).strip()


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


def raw_dict(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("raw_excerpt")
    return raw if isinstance(raw, dict) else {}


def stringify_raw_excerpt(row: dict[str, Any]) -> str:
    raw = raw_dict(row)
    if not raw:
        return clean_text(row.get("raw_excerpt"))
    selected: dict[str, Any] = {}
    for key in [
        "repo",
        "path",
        "file",
        "filename",
        "body_excerpt",
        "patch_excerpt",
        "issue_title",
        "comment_body",
        "pr_title",
        "review_state",
        "field",
        "fromString",
        "toString",
        "status",
        "labels",
        "components",
        "fixVersions",
        "patterns",
    ]:
        if key in raw:
            selected[key] = raw[key]
    files = raw.get("files")
    if isinstance(files, list):
        compact_files = []
        for item in files[:20]:
            if isinstance(item, dict):
                compact_files.append(
                    {
                        "filename": item.get("filename", ""),
                        "patch_excerpt": clean_text(item.get("patch_excerpt", ""))[:240],
                    }
                )
            elif isinstance(item, str):
                compact_files.append(item[:240])
        if compact_files:
            selected["files"] = compact_files
    return clean_text(selected)


def source_text(row: dict[str, Any]) -> str:
    return " ".join(
        [
            clean_text(row.get("title")),
            clean_text(row.get("summary")),
            " ".join(str(item) for item in row.get("tags", []) if item),
            stringify_raw_excerpt(row),
        ]
    ).lower()


def file_paths_from_row(row: dict[str, Any]) -> list[str]:
    raw = raw_dict(row)
    paths: list[str] = []
    files = raw.get("files")
    if isinstance(files, list):
        for item in files:
            if isinstance(item, dict) and item.get("filename"):
                paths.append(str(item["filename"]))
            elif isinstance(item, str):
                paths.append(item)
    for key in ["path", "file", "filename", "url_or_path"]:
        if raw.get(key):
            paths.append(str(raw[key]))
    paths.extend(PATH_PATTERN.findall(source_text(row)))
    return sorted(set(path.replace("\\", "/").lower() for path in paths if path))


def pattern_names_from_row(row: dict[str, Any]) -> set[str]:
    raw = raw_dict(row)
    patterns = raw.get("patterns") if isinstance(raw.get("patterns"), dict) else {}
    return {str(name).lower() for name in patterns.keys()}


def source_ref(row: dict[str, Any]) -> dict[str, str]:
    source_id = str(row.get("id") or row.get("source_id") or stable_hash(json.dumps(row, sort_keys=True, default=str)))
    return {
        "id": source_id,
        "source_type": str(row.get("source_type", "")),
    }


def prepare_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared = []
    for row in rows:
        prepared.append(
            {
                "row": row,
                "text": source_text(row),
                "paths": file_paths_from_row(row),
                "patterns": pattern_names_from_row(row),
                "source_type": str(row.get("source_type", "")),
                "source_ref": source_ref(row),
            }
        )
    return prepared


def confidence_for_count(count: int) -> str:
    if count >= 40:
        return "strong"
    if count >= 12:
        return "medium"
    return "weak"


def freshness_for_rows(rows: list[dict[str, Any]]) -> str:
    years: list[int] = []
    for row in rows:
        match = re.match(r"(\d{4})", str(row.get("occurred_at", "")))
        if match:
            years.append(int(match.group(1)))
    if not years:
        return "unknown"
    if max(years) >= 2025:
        return "current"
    if max(years) >= 2023:
        return "recent"
    return "historical"


def time_span_for_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    dates = sorted(str(row.get("occurred_at", "")) for row in rows if row.get("occurred_at"))
    return {
        "first_seen": dates[0] if dates else "",
        "last_seen": dates[-1] if dates else "",
        "freshness": freshness_for_rows(rows),
    }


def token_summary(rows: list[dict[str, Any]], limit: int = 12) -> list[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        for token in TOKEN_PATTERN.findall(source_text(row)):
            normalized = token.lower().strip("-_/")
            if len(normalized) < 3 or normalized in GENERIC_TERMS or REPO_LIKE_PATTERN.search(normalized):
                continue
            if normalized.isdigit():
                continue
            counter[normalized] += 1
    return [token for token, _ in counter.most_common(limit)]


def token_summary_from_prepared(prepared_rows: list[dict[str, Any]], limit: int = 12) -> list[str]:
    counter: Counter[str] = Counter()
    for prepared in prepared_rows:
        for token in TOKEN_PATTERN.findall(str(prepared.get("text", ""))):
            normalized = token.lower().strip("-_/")
            if len(normalized) < 3 or normalized in GENERIC_TERMS or REPO_LIKE_PATTERN.search(normalized):
                continue
            if normalized.isdigit():
                continue
            counter[normalized] += 1
    return [token for token, _ in counter.most_common(limit)]


def file_area_for_path(path: str) -> str:
    lowered = path.lower()
    if ".github/workflows" in lowered or "workflow" in lowered:
        return "ci_cd_workflow"
    if "component" in lowered or lowered.endswith((".tsx", ".jsx", ".html", ".scss")):
        return "ui_component"
    if "service" in lowered or "api" in lowered:
        return "service_api"
    if "store" in lowered or "state" in lowered:
        return "state_store"
    if "test" in lowered or "spec" in lowered:
        return "test_quality"
    if "i18n" in lowered or "translation" in lowered or "locale" in lowered:
        return "localization"
    if "auth" in lowered or "permission" in lowered or "rbac" in lowered:
        return "auth_permission"
    if "report" in lowered or "dashboard" in lowered or "analytics" in lowered or "export" in lowered:
        return "analytics_reporting"
    if "package" in lowered or "library" in lowered or "shared" in lowered:
        return "shared_package"
    return "product_code"


def file_area_summary(rows: list[dict[str, Any]], limit: int = 8) -> list[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        for path in file_paths_from_row(row):
            counter[file_area_for_path(path)] += 1
    return [area for area, _ in counter.most_common(limit)]


def file_area_summary_from_prepared(prepared_rows: list[dict[str, Any]], limit: int = 8) -> list[str]:
    counter: Counter[str] = Counter()
    for prepared in prepared_rows:
        for path in prepared.get("paths", []):
            counter[file_area_for_path(str(path))] += 1
    return [area for area, _ in counter.most_common(limit)]


def source_type_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(row.get("source_type", "")) for row in rows).most_common())


def row_score(row: dict[str, Any], definition: dict[str, Any]) -> tuple[int, list[str]]:
    match = definition.get("match", {})
    text = source_text(row)
    paths = file_paths_from_row(row)
    patterns = pattern_names_from_row(row)
    source_type = str(row.get("source_type", ""))
    score = 0
    semantic_score = 0
    hits: list[str] = []

    source_types = {str(item) for item in match.get("source_types", [])}
    if source_types and source_type in source_types:
        score += 2
        hits.append(f"source_type:{source_type}")

    for hint in match.get("text", []):
        lowered = str(hint).lower()
        if lowered and lowered in text:
            score += 2
            semantic_score += 2
            hits.append(f"text:{lowered}")

    for hint in match.get("path", []):
        lowered = str(hint).lower()
        if lowered and any(lowered in path for path in paths):
            score += 3
            semantic_score += 3
            hits.append(f"path:{lowered}")

    for hint in match.get("patterns", []):
        lowered = str(hint).lower()
        if lowered in patterns:
            score += 5
            semantic_score += 5
            hits.append(f"pattern:{lowered}")

    if semantic_score <= 0:
        return 0, []
    if source_types and source_type not in source_types and score < 6:
        return 0, []
    return score, sorted(set(hits))


def prepared_row_score(prepared: dict[str, Any], definition: dict[str, Any]) -> tuple[int, list[str]]:
    match = definition.get("match", {})
    text = str(prepared.get("text", ""))
    paths = [str(path) for path in prepared.get("paths", [])]
    patterns = {str(pattern) for pattern in prepared.get("patterns", set())}
    source_type = str(prepared.get("source_type", ""))
    score = 0
    semantic_score = 0
    hits: list[str] = []

    source_types = {str(item) for item in match.get("source_types", [])}
    if source_types and source_type in source_types:
        score += 2
        hits.append(f"source_type:{source_type}")

    for hint in match.get("text", []):
        lowered = str(hint).lower()
        if lowered and lowered in text:
            score += 2
            semantic_score += 2
            hits.append(f"text:{lowered}")

    for hint in match.get("path", []):
        lowered = str(hint).lower()
        if lowered and any(lowered in path for path in paths):
            score += 3
            semantic_score += 3
            hits.append(f"path:{lowered}")

    for hint in match.get("patterns", []):
        lowered = str(hint).lower()
        if lowered in patterns:
            score += 5
            semantic_score += 5
            hits.append(f"pattern:{lowered}")

    if semantic_score <= 0:
        return 0, []
    if source_types and source_type not in source_types and score < 6:
        return 0, []
    return score, sorted(set(hits))


def build_cluster(definition: dict[str, Any], prepared_rows: list[dict[str, Any]], generated_at: str) -> dict[str, Any] | None:
    scored: list[tuple[int, dict[str, Any], list[str]]] = []
    for prepared in prepared_rows:
        score, hits = prepared_row_score(prepared, definition)
        if score > 0:
            scored.append((score, prepared, hits))

    scored.sort(key=lambda item: (item[0], str(item[1]["row"].get("occurred_at", ""))), reverse=True)
    min_count = int(definition.get("min_source_count", 1))
    if len(scored) < min_count:
        return None

    matched_prepared = [prepared for _score, prepared, _hits in scored]
    matched_rows = [prepared["row"] for prepared in matched_prepared]
    hit_counter: Counter[str] = Counter()
    for _score, _prepared, hits in scored:
        hit_counter.update(hits)
    refs = [prepared["source_ref"] for _score, prepared, _hits in scored]
    time_span = time_span_for_rows(matched_rows)
    source_counts = source_type_counts(matched_rows)
    representative_terms = token_summary_from_prepared(matched_prepared)
    file_areas = file_area_summary_from_prepared(matched_prepared)

    return {
        "id": f"cluster:{definition['id']}",
        "title": definition["title"],
        "memory_type": definition["memory_type"],
        "statement": definition["statement"],
        "useful_context": definition["useful_context"],
        "behavioral_use": definition["behavioral_use"],
        "guardrails": definition["guardrails"],
        "topics": definition["topics"],
        "query_patterns": definition["query_patterns"],
        "source_count": len(scored),
        "source_type_counts": source_counts,
        "time_span": time_span,
        "confidence": confidence_for_count(len(scored)),
        "representative_terms": representative_terms,
        "file_areas": file_areas,
        "matched_rules": [hit for hit, _ in hit_counter.most_common(16)],
        "source_refs": refs[:160],
        "updated_at": generated_at,
    }


def derived_context_for_cluster(cluster: dict[str, Any]) -> list[str]:
    context = list(cluster.get("useful_context", []))
    file_areas = cluster.get("file_areas", [])
    if file_areas:
        context.append(f"Common implementation surfaces in this cluster include {', '.join(file_areas[:6])}.")
    return context[:9]


def candidate_for_cluster(cluster: dict[str, Any]) -> dict[str, Any]:
    memory_type = str(cluster["memory_type"])
    suffix = str(cluster["id"]).removeprefix("cluster:")
    duplicate_prefix = f"{memory_type}."
    if suffix.startswith(duplicate_prefix):
        suffix = suffix[len(duplicate_prefix) :]
    memory_id = f"memory:{memory_type}.{suffix}"
    trace_id = f"trace:{memory_type}.{suffix}"
    source_count = int(cluster.get("source_count", 0))
    return {
        "id": f"candidate:{memory_type}.{suffix}",
        "memory_id": memory_id,
        "trace_id": trace_id,
        "source_cluster_id": cluster["id"],
        "subject": "hanjeahwan",
        "memory_type": memory_type,
        "statement": cluster["statement"],
        "useful_context": derived_context_for_cluster(cluster),
        "topics": cluster.get("topics", []),
        "facets": {
            "domain": "work",
            "time_scope": "multi_year" if source_count >= 20 else "event_cluster",
            "confidence": cluster.get("confidence", "weak"),
            "sensitivity": "private_work",
            "freshness": cluster.get("time_span", {}).get("freshness", "unknown"),
            "source": "source_cluster_distiller_v2.2",
            "source_cluster_id": cluster["id"],
            "supporting_source_count": source_count,
            "supporting_source_types": cluster.get("source_type_counts", {}),
            "file_areas": cluster.get("file_areas", []),
            "representative_terms": cluster.get("representative_terms", []),
        },
        "query_patterns": cluster.get("query_patterns", []),
        "behavioral_use": cluster.get("behavioral_use", ""),
        "guardrails": cluster.get("guardrails", []),
        "source_refs": cluster.get("source_refs", []),
        "quality_flags": ["answer_ready", "content_first", "provenance_hidden_by_default"],
        "updated_at": cluster.get("updated_at", ""),
    }


def read_source_rows(ledger: Path) -> list[dict[str, Any]]:
    return [row for name in SOURCE_FILES for row in read_jsonl(ledger / "sources" / name)]


def build_source_clusters_and_candidates(ledger: Path, generated_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows = read_source_rows(ledger)
    prepared_rows = prepare_rows(rows)
    clusters = [
        cluster
        for definition in CLUSTER_DEFINITIONS
        for cluster in [build_cluster(definition, prepared_rows, generated_at)]
        if cluster is not None
    ]
    clusters.sort(key=lambda row: (str(row.get("memory_type", "")), str(row.get("id", ""))))
    candidates = [candidate_for_cluster(cluster) for cluster in clusters]
    eval_summary = evaluate_distillation(rows, clusters, candidates, generated_at)
    return clusters, candidates, eval_summary


def evaluate_distillation(
    source_rows: list[dict[str, Any]],
    clusters: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    source_total = len(source_rows)
    covered_source_ids = {
        ref.get("id")
        for cluster in clusters
        for ref in cluster.get("source_refs", [])
        if ref.get("id")
    }
    by_memory_type = Counter(str(candidate.get("memory_type", "")) for candidate in candidates)
    weak_candidates = [
        candidate["id"]
        for candidate in candidates
        if candidate.get("facets", {}).get("confidence") == "weak"
    ]
    evidence_like = [
        candidate["id"]
        for candidate in candidates
        if candidate.get("memory_type") != "private_boundary"
        and any(token in str(candidate.get("statement", "")).lower() for token in ["commit count", "jira key", "source id"])
    ]
    missing_guardrails = [
        candidate["id"]
        for candidate in candidates
        if not candidate.get("guardrails")
    ]
    return {
        "generated_at": generated_at,
        "architecture": "self-context-v2.2",
        "source_total": source_total,
        "cluster_count": len(clusters),
        "candidate_count": len(candidates),
        "covered_source_count_lower_bound": len(covered_source_ids),
        "cluster_source_assignments": sum(int(cluster.get("source_count", 0) or 0) for cluster in clusters),
        "cluster_coverage_lower_bound": round(len(covered_source_ids) / source_total, 4) if source_total else 0.0,
        "memory_type_counts": dict(by_memory_type.most_common()),
        "quality": {
            "weak_candidate_count": len(weak_candidates),
            "weak_candidates": weak_candidates[:20],
            "evidence_like_statement_count": len(evidence_like),
            "evidence_like_statements": evidence_like[:20],
            "missing_guardrail_count": len(missing_guardrails),
            "missing_guardrails": missing_guardrails[:20],
            "passes": not evidence_like and not missing_guardrails and bool(candidates),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    ledger = resolve_ledger_path(args.ledger)
    generated_at = now_iso()
    clusters, candidates, eval_summary = build_source_clusters_and_candidates(ledger, generated_at)
    derived = ledger / "derived"
    write_jsonl(derived / "source_clusters.jsonl", clusters)
    write_jsonl(derived / "distillation_candidates.jsonl", candidates)
    write_json(derived / "distillation_eval.json", eval_summary)

    if args.json:
        print(json.dumps(eval_summary, ensure_ascii=False, indent=2))
    else:
        print(f"source_clusters={len(clusters)} distillation_candidates={len(candidates)} ledger={ledger}")


if __name__ == "__main__":
    main()
