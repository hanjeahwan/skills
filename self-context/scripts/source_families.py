"""Shared v2.8 source-family contracts for self-context builders."""

from __future__ import annotations

from typing import Any


ARCHITECTURE_VERSION = "self-context-v2.8"
QUERY_ENGINE_VERSION = "hybrid-self-context-v2.8"

REQUIRED_SOURCE_FILES = [
    "git.jsonl",
    "github_pr_activity.jsonl",
    "github_pr_reviews.jsonl",
    "github_authority_signals.jsonl",
    "jira.jsonl",
    "jira_comments.jsonl",
    "jira_changelog.jsonl",
    "manual.jsonl",
    "code_style.jsonl",
]

OPTIONAL_SOURCE_FILES = [
    "career_facts.jsonl",
    "release_activity.jsonl",
    "jira_leadership_signals.jsonl",
    "architecture_material.jsonl",
    "agent_sessions.jsonl",
    "portfolio_cases.jsonl",
    "personal_material.jsonl",
]

SOURCE_FILES = [*REQUIRED_SOURCE_FILES, *OPTIONAL_SOURCE_FILES]

SOURCE_FAMILY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "career_facts": {
        "files": ["career_facts.jsonl", "manual.jsonl"],
        "memory_type": "declared_profile",
        "section_id": "self_model:declared_profile",
        "topic": "declared_profile",
        "empty_status": "Formal title, exact professional tenure, promotion history, and self-declared scope have not been imported as structured career facts yet.",
    },
    "github_pr_activity": {
        "files": ["github_pr_activity.jsonl", "github_pr_reviews.jsonl"],
        "memory_type": "review_style",
        "section_id": "self_model:review_style",
        "topic": "review_style",
        "empty_status": "Authored PR discussion and review-reasoning material has not been imported yet.",
    },
    "github_authority_signals": {
        "files": ["github_authority_signals.jsonl"],
        "memory_type": "repo_authority",
        "section_id": "self_model:repo_authority",
        "topic": "repo_authority",
        "empty_status": "CODEOWNERS, branch protection, review requests, mentions, and repo-permission signals have not been imported yet.",
    },
    "release_activity": {
        "files": ["release_activity.jsonl"],
        "memory_type": "release_ownership",
        "section_id": "self_model:release_ownership",
        "topic": "release_ownership",
        "empty_status": "Release, deploy, hotfix, workflow-run, and CI-failure ownership rows have not been imported as structured release activity yet.",
    },
    "jira_leadership_signals": {
        "files": ["jira_leadership_signals.jsonl", "jira.jsonl", "jira_comments.jsonl", "jira_changelog.jsonl"],
        "memory_type": "jira_leadership",
        "section_id": "self_model:jira_leadership",
        "topic": "jira_leadership",
        "empty_status": "Jira transition, QA, blocker, reopen, hotfix, and leadership-comment rows have not been imported yet.",
    },
    "architecture_material": {
        "files": ["architecture_material.jsonl"],
        "memory_type": "architecture_material",
        "section_id": "self_model:architecture_material",
        "topic": "architecture_material",
        "empty_status": "Architecture docs, RFCs, Confluence exports, migration plans, standards, and AI/MCP design docs have not been imported yet.",
    },
    "agent_sessions": {
        "files": ["agent_sessions.jsonl"],
        "memory_type": "agent_collaboration_style",
        "section_id": "self_model:agent_collaboration_style",
        "topic": "agent_collaboration",
        "empty_status": "Codex, Claude, Cursor, and agent-session history has not been imported into the clone ledger yet.",
    },
    "portfolio_cases": {
        "files": ["portfolio_cases.jsonl"],
        "memory_type": "portfolio_cases",
        "section_id": "self_model:portfolio_cases",
        "topic": "portfolio_cases",
        "empty_status": "Sanitized portfolio case studies, screenshots, product surfaces, and public-safe summaries have not been imported yet.",
    },
    "personal_material": {
        "files": ["personal_material.jsonl"],
        "memory_type": "personal_identity",
        "section_id": "self_model:personal_identity",
        "topic": "personal_identity",
        "empty_status": "Personal values, goals, life context, communication preferences, and boundaries have not been imported as structured personal material yet.",
    },
}

SOURCE_FAMILY_IDS = list(SOURCE_FAMILY_DEFINITIONS)
