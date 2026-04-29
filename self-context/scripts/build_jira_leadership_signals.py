#!/usr/bin/env python3
"""Distill Jira tickets, comments, and changelog rows into leadership signals."""

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


EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
URL_PATTERN = re.compile(r"https?://\S+")
MENTION_PATTERN = re.compile(r"@[A-Za-z][A-Za-z0-9 ._-]{1,80}")
SHA_PATTERN = re.compile(r"\b[a-f0-9]{7,40}\b", re.IGNORECASE)
SPACE_PATTERN = re.compile(r"\s+")

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "qa_handoff": ["qa", "testing", "tester", "verify", "verification", "staging", "uat"],
    "done_accountability": ["done", "resolved", "resolution", "released to production", "released"],
    "code_review_flow": ["code review", "review", "approved"],
    "release_context": ["release", "fixversions", "fix version", "production", "go live"],
    "hotfix_response": ["hotfix", "urgent", "customer - bug", "customer bug"],
    "blocker_response": ["blocked", "blocker", "flagged", "cannot", "unable"],
    "reopen_response": ["reopen", "reopened", "regression"],
    "standard_decision": ["standard", "expected", "not changing", "follow standard", "by design"],
    "coordination_update": ["updated", "follow up", "please", "need", "assigned", "move", "ready"],
}

HIGH_VALUE_FIELDS = {"status", "resolution", "fix version", "assignee", "flagged"}
DELIVERY_STATUSES = {
    "code review",
    "qa testing",
    "released to stage",
    "released to production",
    "done",
    "ready to go live",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


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


def clean_text(value: Any, *, max_length: int = 500) -> str:
    text = "" if value is None else str(value)
    text = EMAIL_PATTERN.sub("<REDACTED_EMAIL>", text)
    text = URL_PATTERN.sub("<REDACTED_URL>", text)
    text = MENTION_PATTERN.sub("@<MENTION>", text)
    text = SHA_PATTERN.sub("<REDACTED_SHA>", text)
    text = SPACE_PATTERN.sub(" ", text).strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "..."


def raw_dict(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("raw_excerpt")
    return raw if isinstance(raw, dict) else {}


def row_key(row: dict[str, Any]) -> str:
    raw = raw_dict(row)
    key = raw.get("key") or row.get("source_id") or ""
    return str(key).split(":", 1)[0]


def row_text(row: dict[str, Any]) -> str:
    raw = raw_dict(row)
    return " ".join(
        [
            str(row.get("title") or ""),
            str(row.get("summary") or ""),
            json.dumps(raw, ensure_ascii=False, sort_keys=True),
            " ".join(str(item) for item in row.get("tags", []) if item),
        ]
    ).lower()


def compact_list(values: Iterable[str], limit: int) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = clean_text(value, max_length=260)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
        if len(output) >= limit:
            break
    return output


def is_high_signal_comment(value: Any) -> bool:
    text = clean_text(value, max_length=500)
    lowered = text.lower()
    if len(lowered) < 35:
        return False
    if lowered in {"should be", "@<mention>", "done", "updated"}:
        return False
    if lowered.count("@<mention>") >= 1 and len(lowered.replace("@<mention>", "").strip()) < 20:
        return False
    return any(
        keyword in lowered
        for keyword in [
            "qa",
            "impact",
            "analysis",
            "standard",
            "release",
            "deploy",
            "testing",
            "verification",
            "regression",
            "route",
            "architecture",
            "migration",
            "updated",
            "not changing",
            "manual",
        ]
    )


def categories_for_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted(
        category
        for category, keywords in CATEGORY_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    )


def source_ref(row: dict[str, Any]) -> dict[str, str]:
    return {
        "id": str(row.get("id") or row.get("source_id") or stable_hash(json.dumps(row, sort_keys=True, default=str))),
        "source_type": str(row.get("source_type") or ""),
    }


def source_refs(rows: Iterable[dict[str, Any]], limit: int = 50) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        ref = source_ref(row)
        if not ref["id"] or ref["id"] in seen:
            continue
        seen.add(ref["id"])
        refs.append(ref)
        if len(refs) >= limit:
            break
    return refs


def latest_occurred(rows: Iterable[dict[str, Any]]) -> str:
    values = sorted(str(row.get("occurred_at") or "") for row in rows if row.get("occurred_at"))
    return values[-1] if values else ""


def status_transition(raw: dict[str, Any]) -> str:
    field = clean_text(raw.get("field"), max_length=80)
    from_value = clean_text(raw.get("fromString"), max_length=80)
    to_value = clean_text(raw.get("toString"), max_length=80)
    if not field:
        return ""
    if from_value or to_value:
        return f"{field}: {from_value or 'empty'} -> {to_value or 'empty'}"
    return field


def issue_type(row: dict[str, Any]) -> str:
    raw = raw_dict(row)
    return clean_text(raw.get("issue_type"), max_length=80)


def status_value(row: dict[str, Any]) -> str:
    raw = raw_dict(row)
    return clean_text(raw.get("status"), max_length=80)


def user_identity(rows: Iterable[dict[str, Any]]) -> dict[str, set[str]]:
    account_ids: set[str] = set()
    emails: set[str] = set()
    display_names: set[str] = set()
    for row in rows:
        raw = raw_dict(row)
        if raw.get("authored_by_user"):
            author = raw.get("comment_author") if isinstance(raw.get("comment_author"), dict) else {}
        elif raw.get("author_is_user"):
            author = raw.get("author") if isinstance(raw.get("author"), dict) else {}
        else:
            continue
        account_id = str(author.get("accountId") or "").strip().lower()
        email = str(author.get("emailAddress") or "").strip().lower()
        display_name = str(author.get("displayName") or "").strip().lower()
        if account_id:
            account_ids.add(account_id)
        if email:
            emails.add(email)
        if display_name:
            display_names.add(display_name)
    return {"account_ids": account_ids, "emails": emails, "display_names": display_names}


def is_user_owned_ticket(row: dict[str, Any], identity: dict[str, set[str]]) -> bool:
    raw = raw_dict(row)
    assignee = raw.get("assignee") if isinstance(raw.get("assignee"), dict) else {}
    account_id = str(assignee.get("accountId") or "").strip().lower()
    email = str(assignee.get("emailAddress") or "").strip().lower()
    display_name = str(assignee.get("displayName") or "").strip().lower()
    return (
        bool(account_id and account_id in identity["account_ids"])
        or bool(email and email in identity["emails"])
        or bool(display_name and display_name in identity["display_names"])
    )


def score_issue(rows: list[dict[str, Any]], identity: dict[str, set[str]]) -> int:
    text = " ".join(row_text(row) for row in rows)
    score = 0
    if any(raw_dict(row).get("author_is_user") for row in rows):
        score += 8
    if any(raw_dict(row).get("authored_by_user") for row in rows):
        score += 7
    if any(is_user_owned_ticket(row, identity) for row in rows):
        score += 4
    score += min(10, sum(1 for row in rows if "jira_changelog" == row.get("source_type")))
    score += min(6, sum(1 for row in rows if "jira_comment" == row.get("source_type")))
    for category in categories_for_text(text):
        score += 2 if category in {"qa_handoff", "done_accountability", "release_context", "hotfix_response"} else 1
    if "customer - bug" in text or "bug" in text:
        score += 2
    return score


def aggregate_row(
    suffix: str,
    title: str,
    summary: str,
    raw_excerpt: dict[str, Any],
    tags: list[str],
    support_rows: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    return {
        "id": f"jira_leadership_signal:aggregate.{suffix}",
        "source_type": "jira_leadership_signal",
        "source_id": f"aggregate.{suffix}",
        "occurred_at": latest_occurred(support_rows),
        "title": title,
        "summary": summary,
        "url_or_path": "",
        "raw_excerpt": {
            **raw_excerpt,
            "signal_kind": "aggregate",
            "source_refs": source_refs(support_rows, 80),
        },
        "tags": ["jira", "jira_leadership", *tags],
        "ingested_at": generated_at,
    }


def issue_row(key: str, rows: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    text = " ".join(row_text(row) for row in rows)
    categories = categories_for_text(text)
    ticket = next((row for row in rows if row.get("source_type") == "jira_ticket"), rows[0])
    comments = [row for row in rows if row.get("source_type") == "jira_comment"]
    changelogs = [row for row in rows if row.get("source_type") == "jira_changelog"]
    authored_comments = [row for row in comments if raw_dict(row).get("authored_by_user")]
    mention_comments = [row for row in comments if raw_dict(row).get("mentions_user")]
    authored_changelog = [row for row in changelogs if raw_dict(row).get("author_is_user")]
    transition_summaries = compact_list([status_transition(raw_dict(row)) for row in authored_changelog], 8)
    comment_samples = compact_list(
        [raw_dict(row).get("body_excerpt", "") for row in authored_comments if is_high_signal_comment(raw_dict(row).get("body_excerpt", ""))],
        5,
    )
    category_label = ", ".join(category.replace("_", " ") for category in categories[:4]) or "ticket delivery"
    type_label = issue_type(ticket) or "Jira work"
    status_label = status_value(ticket) or "unknown status"
    return {
        "id": f"jira_leadership_signal:issue.{stable_hash(key)}",
        "source_type": "jira_leadership_signal",
        "source_id": f"issue.{stable_hash(key)}",
        "occurred_at": latest_occurred(rows),
        "title": f"Jira leadership signal: {type_label} through {category_label}",
        "summary": f"Jira activity shows {type_label.lower()} ownership around {category_label}, ending in {status_label}.",
        "url_or_path": str(ticket.get("url_or_path") or ""),
        "raw_excerpt": {
            "key": key,
            "issue_type": type_label,
            "status": status_label,
            "category_tags": categories,
            "authored_comment_count": len(authored_comments),
            "mention_followup_count": len(mention_comments),
            "authored_transition_count": len(authored_changelog),
            "transition_summaries": transition_summaries,
            "authored_comment_excerpt_samples": comment_samples,
            "source_refs": source_refs(rows, 30),
        },
        "tags": ["jira", "jira_leadership", *categories],
        "ingested_at": generated_at,
    }


def build_rows(ledger: Path, max_issue_signals: int, generated_at: str) -> list[dict[str, Any]]:
    sources = ledger / "sources"
    tickets = read_jsonl(sources / "jira.jsonl")
    comments = read_jsonl(sources / "jira_comments.jsonl")
    changelogs = read_jsonl(sources / "jira_changelog.jsonl")
    all_rows = [*tickets, *comments, *changelogs]
    identity = user_identity(all_rows)

    comments_by_user = [row for row in comments if raw_dict(row).get("authored_by_user")]
    comments_mentioning_user = [row for row in comments if raw_dict(row).get("mentions_user")]
    user_changelogs = [row for row in changelogs if raw_dict(row).get("author_is_user")]
    high_value_user_changelogs = [
        row
        for row in user_changelogs
        if str(raw_dict(row).get("field", "")).lower() in HIGH_VALUE_FIELDS
        or str(raw_dict(row).get("toString", "")).lower() in DELIVERY_STATUSES
    ]
    owned_tickets = [row for row in tickets if is_user_owned_ticket(row, identity)]
    done_or_release_tickets = [
        row
        for row in owned_tickets
        if any(keyword in row_text(row) for keyword in ["done", "release", "hotfix", "production", "qa"])
    ]

    transition_fields = Counter(str(raw_dict(row).get("field") or "").lower() for row in user_changelogs)
    transition_targets = Counter(str(raw_dict(row).get("toString") or "").lower() for row in user_changelogs)
    issue_types = Counter(issue_type(row) for row in owned_tickets if issue_type(row))
    comment_categories = Counter(category for row in comments_by_user for category in categories_for_text(row_text(row)))
    workflow_categories = Counter(category for row in all_rows for category in categories_for_text(row_text(row)))

    rows: list[dict[str, Any]] = [
        aggregate_row(
            "transition_ownership",
            "Jira transition ownership around Code Review, QA, release, and Done",
            "Jira changelog history shows repeated personal movement of tickets through delivery-critical fields and statuses.",
            {
                "user_authored_changelog_rows": len(user_changelogs),
                "high_value_user_changelog_rows": len(high_value_user_changelogs),
                "transition_fields": dict(transition_fields.most_common(12)),
                "transition_targets": dict(transition_targets.most_common(16)),
                "delivery_status_targets": {
                    status: transition_targets.get(status, 0) for status in sorted(DELIVERY_STATUSES) if transition_targets.get(status, 0)
                },
            },
            ["transition_ownership", "qa_handoff", "done_accountability", "release_context"],
            high_value_user_changelogs or user_changelogs,
            generated_at,
        ),
        aggregate_row(
            "comment_coordination",
            "Jira comment coordination for QA, standards, follow-up, and unblock work",
            "Authored and mention-driven Jira comments show coordination around updates, standards, verification, and delivery handoff.",
            {
                "authored_comment_rows": len(comments_by_user),
                "mention_followup_rows": len(comments_mentioning_user),
                "comment_category_counts": dict(comment_categories.most_common(12)),
                "representative_authored_comment_excerpts": compact_list(
                    [
                        raw_dict(row).get("body_excerpt", "")
                        for row in comments_by_user
                        if is_high_signal_comment(raw_dict(row).get("body_excerpt", ""))
                    ],
                    12,
                ),
            },
            ["comment_coordination", "qa_handoff", "standard_decision", "coordination_update"],
            [*comments_by_user, *comments_mentioning_user],
            generated_at,
        ),
        aggregate_row(
            "ticket_delivery_scope",
            "Jira ticket ownership across bugs, releases, QA, hotfixes, and Done outcomes",
            "Assigned Jira work shows repeated delivery scope across bugs, improvements, release-bound tickets, QA, hotfix, and Done outcomes.",
            {
                "owned_ticket_rows": len(owned_tickets),
                "done_or_release_owned_ticket_rows": len(done_or_release_tickets),
                "issue_type_counts": dict(issue_types.most_common(16)),
                "workflow_category_counts": dict(workflow_categories.most_common(16)),
            },
            ["ticket_ownership", "done_accountability", "release_context", "hotfix_response"],
            done_or_release_tickets or owned_tickets,
            generated_at,
        ),
    ]

    by_issue: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in all_rows:
        key = row_key(row)
        if key:
            by_issue[key].append(row)

    scored_issues = sorted(
        ((score_issue(issue_rows, identity), key, issue_rows) for key, issue_rows in by_issue.items()),
        key=lambda item: (-item[0], latest_occurred(item[2]), item[1]),
    )
    for score, key, issue_rows in scored_issues:
        if score <= 0:
            continue
        rows.append(issue_row(key, issue_rows, generated_at))
        if len(rows) >= max_issue_signals + 3:
            break

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--max-issue-signals", type=int, default=180)
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    ledger = resolve_ledger_path(args.ledger)
    generated_at = now_iso()
    rows = build_rows(ledger, args.max_issue_signals, generated_at)
    output_path = ledger / "sources" / "jira_leadership_signals.jsonl"
    write_jsonl(output_path, rows)

    summary = {
        "generated_at": generated_at,
        "ledger": str(ledger),
        "output": str(output_path),
        "jira_leadership_signals": len(rows),
        "max_issue_signals": args.max_issue_signals,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"jira_leadership_signals={len(rows)} output={output_path}")


if __name__ == "__main__":
    main()
