#!/usr/bin/env python3
"""Redact secret-like values from evidence ledger JSONL files."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ledger_paths import resolve_ledger_path


REDACTED = "<REDACTED_SECRET>"

SENSITIVE_FIELD_NAMES = {
    "access_token",
    "accesstoken",
    "api_key",
    "apikey",
    "api_token",
    "apitoken",
    "client_id",
    "clientid",
    "client_secret",
    "clientsecret",
    "dsn",
    "id_token",
    "idtoken",
    "jira_api_token",
    "jiraapitoken",
    "password",
    "passwd",
    "pwd",
    "refresh_token",
    "refreshtoken",
    "secret",
    "token",
}


@dataclass(frozen=True)
class RedactionRule:
    name: str
    pattern: re.Pattern[str]
    replacement: str


RULES = [
    RedactionRule(
        "atlassian_api_token",
        re.compile(r"ATATT[A-Za-z0-9_\-=]+"),
        "<REDACTED_ATLASSIAN_TOKEN>",
    ),
    RedactionRule(
        "github_token",
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"),
        "<REDACTED_GITHUB_TOKEN>",
    ),
    RedactionRule(
        "github_fine_grained_token",
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
        "<REDACTED_GITHUB_TOKEN>",
    ),
    RedactionRule(
        "aws_access_key_id",
        re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
        "<REDACTED_AWS_ACCESS_KEY_ID>",
    ),
    RedactionRule(
        "sentry_dsn_url",
        re.compile(r"https://[^\"'\s<>]+@[^\"'\s<>]*ingest\.sentry\.io/[A-Za-z0-9_/.-]+"),
        "<REDACTED_SENTRY_DSN>",
    ),
]

ASSIGNMENT_PATTERN = re.compile(
    r"(?P<prefix>\b(?:"
    r"jira_api_token|api[_-]?token|apiToken|access[_-]?token|accessToken|"
    r"refresh[_-]?token|refreshToken|id[_-]?token|idToken|"
    r"password|passwd|pwd|secret|client[_-]?secret|clientSecret|"
    r"client[_-]?id|clientId|api[_-]?key|apiKey|dsn"
    r")\b\s*[:=]\s*)"
    r"(?P<quote>[\"']?)"
    r"(?P<value>[^\"'\s,;}\]]+)"
    r"(?P=quote)",
    re.IGNORECASE,
)

LONG_KEY_ASSIGNMENT_PATTERN = re.compile(
    r"(?P<prefix>\bkey\b\s*=\s*)"
    r"(?P<quote>[\"'])"
    r"(?P<value>[A-Za-z0-9_\-]{16,})"
    r"(?P=quote)",
    re.IGNORECASE,
)

PUSHER_CONSTRUCTOR_PATTERN = re.compile(
    r"(?P<prefix>\bnew\s+Pusher\s*\(\s*)"
    r"(?P<quote>[\"'])"
    r"(?P<value>[A-Za-z0-9_\-]{16,})"
    r"(?P=quote)",
)

BEARER_PATTERN = re.compile(r"(?P<prefix>\bBearer\s+)(?P<value>[A-Za-z0-9._\-]{20,})")


def normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def should_skip_value(value: str) -> bool:
    return value.startswith("<REDACTED_")


def redact_assignment(match: re.Match[str], stats: Counter[str], rule_name: str) -> str:
    value = match.group("value")
    if should_skip_value(value):
        return match.group(0)
    stats[rule_name] += 1
    quote = match.group("quote")
    return f"{match.group('prefix')}{quote}{REDACTED}{quote}"


def redact_string(value: str, stats: Counter[str]) -> str:
    result = value

    for rule in RULES:
        def replace_rule(match: re.Match[str], *, rule: RedactionRule = rule) -> str:
            matched = match.group(0)
            if should_skip_value(matched):
                return matched
            stats[rule.name] += 1
            return rule.replacement

        result = rule.pattern.sub(replace_rule, result)

    result = ASSIGNMENT_PATTERN.sub(
        lambda match: redact_assignment(match, stats, "sensitive_assignment"),
        result,
    )
    result = LONG_KEY_ASSIGNMENT_PATTERN.sub(
        lambda match: redact_assignment(match, stats, "long_key_assignment"),
        result,
    )
    result = PUSHER_CONSTRUCTOR_PATTERN.sub(
        lambda match: redact_assignment(match, stats, "pusher_constructor_key"),
        result,
    )
    result = BEARER_PATTERN.sub(
        lambda match: redact_assignment(match, stats, "bearer_token"),
        result,
    )
    return result


def redact_value(value: Any, stats: Counter[str]) -> Any:
    if isinstance(value, str):
        return redact_string(value, stats)
    if isinstance(value, list):
        return [redact_value(item, stats) for item in value]
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, nested in value.items():
            normalized = normalize_key(str(key))
            if normalized in SENSITIVE_FIELD_NAMES and nested not in (None, "", REDACTED):
                stats[f"sensitive_field:{key}"] += 1
                redacted[key] = REDACTED
                continue
            redacted[key] = redact_value(nested, stats)
        return redacted
    return value


def default_jsonl_paths(ledger: Path) -> list[Path]:
    paths: list[Path] = []
    for directory in [ledger / "sources", ledger / "events", ledger / "derived"]:
        if directory.exists():
            paths.extend(sorted(directory.glob("*.jsonl")))
    return paths


def redact_jsonl_file(path: Path, dry_run: bool) -> tuple[int, Counter[str], list[str]]:
    stats: Counter[str] = Counter()
    changed_rows = 0
    output_lines: list[str] = []
    changed_ids: list[str] = []

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSONL: {exc}") from exc

        row_stats: Counter[str] = Counter()
        redacted = redact_value(row, row_stats)
        if row_stats:
            changed_rows += 1
            stats.update(row_stats)
            changed_ids.append(str(row.get("id", f"line:{line_number}")))
            output_lines.append(json.dumps(redacted, ensure_ascii=False, separators=(",", ":")))
        else:
            output_lines.append(line)

    if changed_rows and not dry_run:
        path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")

    return changed_rows, stats, changed_ids


def write_report(
    ledger: Path,
    per_file: dict[str, dict[str, Any]],
    dry_run: bool,
    report_prefix: str,
) -> tuple[Path, Path]:
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    reports_dir = ledger / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = reports_dir / f"{report_prefix}.json"
    md_path = reports_dir / f"{report_prefix}.md"

    totals = Counter()
    changed_rows = 0
    changed_files = 0
    for item in per_file.values():
        if item["changed_rows"]:
            changed_files += 1
        changed_rows += item["changed_rows"]
        totals.update(item["rules"])

    payload = {
        "generated_at": generated_at,
        "dry_run": dry_run,
        "ledger": str(ledger),
        "changed_files": changed_files,
        "changed_rows": changed_rows,
        "rule_counts": dict(sorted(totals.items())),
        "files": per_file,
        "value_policy": "Report intentionally stores counts and evidence ids only; it never stores original secret-like values.",
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Secret Redaction Report",
        "",
        f"Generated: {generated_at}",
        "",
        "## Summary",
        "",
        f"- Mode: {'dry-run' if dry_run else 'applied'}",
        f"- Changed files: {changed_files}",
        f"- Changed rows: {changed_rows}",
        "- Original secret-like values are not stored in this report.",
        "",
        "## Rule Counts",
        "",
    ]
    if totals:
        for name, count in sorted(totals.items()):
            lines.append(f"- `{name}`: {count}")
    else:
        lines.append("- No pending redactions.")

    lines.extend(["", "## Files", ""])
    for filename, item in sorted(per_file.items()):
        if not item["changed_rows"]:
            continue
        lines.append(f"### `{filename}`")
        lines.append("")
        lines.append(f"- Changed rows: {item['changed_rows']}")
        lines.append(f"- Evidence ids: {', '.join(f'`{row_id}`' for row_id in item['changed_ids'][:20])}")
        if len(item["changed_ids"]) > 20:
            lines.append(f"- Additional evidence ids omitted: {len(item['changed_ids']) - 20}")
        lines.append("")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--dry-run", action="store_true", help="Report pending redactions without rewriting JSONL files.")
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        help="Specific JSONL file to redact. Can be passed more than once. Defaults to ledger sources/events/derived JSONL files.",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write a redaction report under ledger/reports.",
    )
    parser.add_argument(
        "--report-prefix",
        default="secret-redaction-report-2026-04-22",
        help="Report file prefix when --write-report is used.",
    )
    args = parser.parse_args()

    ledger = resolve_ledger_path(args.ledger)
    paths = [Path(path).expanduser().resolve() for path in args.paths] if args.paths else default_jsonl_paths(ledger)

    per_file: dict[str, dict[str, Any]] = {}
    total_rows = 0
    total_rules: Counter[str] = Counter()

    for path in paths:
        if not path.exists():
            raise FileNotFoundError(path)
        changed_rows, stats, changed_ids = redact_jsonl_file(path, args.dry_run)
        rel_path = str(path.relative_to(ledger)) if path.is_relative_to(ledger) else str(path)
        per_file[rel_path] = {
            "changed_rows": changed_rows,
            "rules": dict(sorted(stats.items())),
            "changed_ids": changed_ids,
        }
        total_rows += changed_rows
        total_rules.update(stats)
        print(f"{path}: changed_rows={changed_rows} rules={dict(sorted(stats.items()))}")

    print(f"total_changed_rows={total_rows}")
    print(f"total_rule_counts={dict(sorted(total_rules.items()))}")

    if args.write_report:
        md_path, json_path = write_report(ledger, per_file, args.dry_run, args.report_prefix)
        print(f"wrote_report={md_path}")
        print(f"wrote_report_json={json_path}")


if __name__ == "__main__":
    main()
