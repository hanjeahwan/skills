#!/usr/bin/env python3
"""Analyze GitHub commit patch evidence into durable code-style signals."""

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


CODE_SUFFIXES = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".html",
    ".scss",
    ".css",
    ".less",
    ".json",
    ".yml",
    ".yaml",
    ".md",
}

PATTERN_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("angular_component", re.compile(r"@Component\s*\(|\.component\.(ts|html|scss|less)\b")),
    ("angular_service", re.compile(r"@Injectable\s*\(|\.service\.ts\b|HttpClient\b")),
    ("angular_module_routing", re.compile(r"@NgModule\s*\(|RouterModule|\.module\.ts\b|\.routing\.ts\b")),
    ("rxjs_streams", re.compile(r"\bObservable\b|\bSubject\b|\bReplaySubject\b|\bcombineLatest\b|\bswitchMap\b|\btakeUntil\b|\bpipe\s*\(")),
    ("react_component", re.compile(r"\bfunction\s+[A-Z][A-Za-z0-9_]*\s*\(|\bconst\s+[A-Z][A-Za-z0-9_]*\s*[:=][^\n]*=>|React\.FC\b|\.tsx\b")),
    ("react_hooks", re.compile(r"\buse[A-Z][A-Za-z0-9_]*\s*\(")),
    ("zustand_store", re.compile(r"\bzustand\b|\bcreate\s*<|\bcreate\s*\(")),
    ("service_layer", re.compile(r"/services?/|\.service\.ts\b|Service\b|service:" )),
    ("api_http_contract", re.compile(r"/http/|HttpService|HttpClient|axios|fetch\s*\(|api[_-]?client|request<")),
    ("state_store", re.compile(r"/store/|/stores/|Store\b|selectors?|reducers?|actions?|effects?")),
    ("shared_library", re.compile(r"@example-org/(?:shared-ui|lookup)|/shared/|shared-library|libs?/")),
    ("rbac_auth", re.compile(r"Auth0|Cognito|RBAC|ACLService|permission|role|Token|Jwt|JWT")),
    ("feature_flag_analytics", re.compile(r"Unleash|Userpilot|Sentry|GTM|GA4|dataLayer|productFruits|feature[_-]?flag")),
    ("i18n_locale", re.compile(r"i18n|translate|Locale|locale|language|ngx-translate")),
    ("forms_validation", re.compile(r"FormGroup|FormControl|Validators|z\.object|yup\.object|react-hook-form")),
    ("unit_testing", re.compile(r"\bdescribe\s*\(|\bit\s*\(|\btest\s*\(|\.spec\.|\.test\.|jest|vitest|karma|jasmine")),
    ("e2e_testing", re.compile(r"playwright|cypress|\.e2e\.|page\.goto|cy\.visit")),
    ("lint_format_quality", re.compile(r"eslint|prettier|stylelint|husky|lint-staged|commitlint|tslint")),
    ("ci_cd_release", re.compile(r"\.github/workflows|github actions|semantic-release|deploy|sourcemap|pipeline|workflow|pnpm")),
    ("ai_agent_mcp", re.compile(r"\b(?:AI|OpenAI|GPT|MCP|agent|agents|assistant|chat|prompt|skill|skills)\b", re.IGNORECASE)),
]

KIND_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("component", re.compile(r"\.component\.|/components?/|\.tsx$")),
    ("service", re.compile(r"\.service\.|/services?/|/http/|/api/")),
    ("state", re.compile(r"/store/|/stores/|/state/|selector|reducer|action|effect")),
    ("test", re.compile(r"\.spec\.|\.test\.|__tests__|/tests?/")),
    ("e2e", re.compile(r"e2e|playwright|cypress")),
    ("workflow", re.compile(r"\.github/workflows|pipeline|deploy|semantic-release")),
    ("config", re.compile(r"package\.json|tsconfig|eslint|prettier|stylelint|angular\.json|vite\.config|next\.config")),
    ("style", re.compile(r"\.(scss|css|less)$")),
    ("template", re.compile(r"\.html$")),
    ("docs", re.compile(r"\.md$|/docs?/|/references?/|/skills?/")),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: str, length: int = 24) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def merge_code_style_rows(path: Path, source_prefix: str, new_rows: list[dict[str, Any]]) -> tuple[int, int]:
    existing = read_jsonl(path)
    kept = [
        row
        for row in existing
        if not (
            row.get("source_type") == "code_style_signal"
            and str(row.get("source_id", "")).startswith(source_prefix)
        )
    ]
    replaced = len(existing) - len(kept)
    by_id = {row["id"]: row for row in [*kept, *new_rows]}
    merged = sorted(by_id.values(), key=lambda row: (row.get("source_id", ""), row.get("id", "")))
    write_jsonl(path, merged)
    return replaced, len(merged)


def file_kind(path: str) -> str:
    lower = path.lower()
    for kind, pattern in KIND_RULES:
        if pattern.search(lower):
            return kind
    return "source"


def detect_patterns(text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for name, pattern in PATTERN_RULES:
        matches = pattern.findall(text)
        if matches:
            counts[name] += len(matches)
    return counts


def patch_added_lines(patch: str) -> str:
    lines = []
    for line in patch.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines)


def patch_removed_lines(patch: str) -> str:
    lines = []
    for line in patch.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("-"):
            lines.append(line[1:])
    return "\n".join(lines)


def commit_message_tags(title: str) -> list[str]:
    lowered = title.lower()
    tags = []
    for token in ["feat", "fix", "refactor", "test", "chore", "ci", "docs", "style", "perf"]:
        if lowered.startswith(f"{token}:") or lowered.startswith(f"{token}("):
            tags.append(f"commit_type:{token}")
    return tags


def iter_commit_files(row: dict[str, Any]) -> Iterable[dict[str, Any]]:
    raw = row.get("raw_excerpt") or {}
    for item in raw.get("files") or []:
        if isinstance(item, dict):
            yield item


def repo_filter_match(repo: str, include_repos: list[str] | None) -> bool:
    if not include_repos:
        return True
    lowered = repo.lower()
    return any(lowered == item.lower() for item in include_repos)


def collect(rows: list[dict[str, Any]], include_repos: list[str] | None) -> dict[str, Any]:
    repo_stats: dict[str, Any] = defaultdict(lambda: {
        "commit_count": 0,
        "file_count": 0,
        "additions": 0,
        "deletions": 0,
        "kind_counts": Counter(),
        "path_counts": Counter(),
        "pattern_counts": Counter(),
        "commit_type_counts": Counter(),
        "examples": [],
        "first_seen": "",
        "last_seen": "",
    })
    global_stats = {
        "commit_count": 0,
        "file_count": 0,
        "repo_counts": Counter(),
        "kind_counts": Counter(),
        "pattern_counts": Counter(),
        "commit_type_counts": Counter(),
    }

    for row in rows:
        raw = row.get("raw_excerpt") or {}
        repo = str(raw.get("repo", ""))
        if not repo_filter_match(repo, include_repos):
            continue
        stats = repo_stats[repo]
        occurred_at = str(row.get("occurred_at", ""))
        stats["commit_count"] += 1
        stats["additions"] += int(raw.get("additions", 0) or 0)
        stats["deletions"] += int(raw.get("deletions", 0) or 0)
        stats["first_seen"] = min([value for value in [stats["first_seen"], occurred_at] if value], default="")
        stats["last_seen"] = max(stats["last_seen"], occurred_at)
        global_stats["commit_count"] += 1
        global_stats["repo_counts"][repo] += 1

        tags = commit_message_tags(str(row.get("title", "")))
        stats["commit_type_counts"].update(tags)
        global_stats["commit_type_counts"].update(tags)

        commit_patterns = detect_patterns(f"{row.get('title', '')}\n{row.get('summary', '')}")
        stats["pattern_counts"].update(commit_patterns)
        global_stats["pattern_counts"].update(commit_patterns)

        for file_item in iter_commit_files(row):
            filename = str(file_item.get("filename", ""))
            suffix = Path(filename).suffix.lower()
            if suffix and suffix not in CODE_SUFFIXES:
                continue
            patch = str(file_item.get("patch_excerpt", ""))
            if not filename:
                continue
            text_for_patterns = f"{filename}\n{patch}"
            patterns = detect_patterns(text_for_patterns)
            kind = file_kind(filename)
            changes = int(file_item.get("changes", 0) or 0)
            stats["file_count"] += 1
            stats["kind_counts"][kind] += 1
            stats["path_counts"][filename] += 1
            stats["pattern_counts"].update(patterns)
            global_stats["file_count"] += 1
            global_stats["kind_counts"][kind] += 1
            global_stats["pattern_counts"].update(patterns)

            example_score = changes + (len(patterns) * 15) + (25 if kind in {"component", "service", "state", "test", "workflow", "config"} else 0)
            if patch and example_score >= 25:
                stats["examples"].append({
                    "score": example_score,
                    "repo": repo,
                    "commit_id": row.get("id", ""),
                    "sha": row.get("source_id", ""),
                    "commit_title": row.get("title", ""),
                    "occurred_at": occurred_at,
                    "url": row.get("url_or_path", ""),
                    "filename": filename,
                    "kind": kind,
                    "status": file_item.get("status", ""),
                    "changes": changes,
                    "patterns": dict(patterns),
                    "patch_excerpt": patch[:5000],
                    "added_lines_excerpt": patch_added_lines(patch)[:2400],
                    "removed_lines_excerpt": patch_removed_lines(patch)[:1000],
                })

    return {"repos": repo_stats, "global": global_stats}


def code_style_record(
    *,
    source_key: str,
    title: str,
    summary: str,
    raw_excerpt: dict[str, Any],
    tags: list[str],
    occurred_at: str,
    ingested_at: str,
    url_or_path: str,
) -> dict[str, Any]:
    return {
        "id": f"code_style_signal:{stable_hash(source_key)}",
        "source_type": "code_style_signal",
        "source_id": source_key,
        "occurred_at": occurred_at,
        "title": title,
        "summary": summary,
        "url_or_path": url_or_path,
        "raw_excerpt": raw_excerpt,
        "tags": ["code_style", "github_commit_patterns", *tags],
        "ingested_at": ingested_at,
    }


def records_from_stats(stats: dict[str, Any], max_examples_per_repo: int, generated_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    global_stats = stats["global"]
    global_key = "github_commit_patterns:global"
    rows.append(
        code_style_record(
            source_key=global_key,
            title="GitHub commit-derived global coding pattern profile",
            summary="Aggregated code-style patterns detected from GitHub commit diffs.",
            raw_excerpt={
                "category": "github_commit_pattern_summary",
                "scope": "global",
                "repo": {"slug": "github_commit_patterns/global"},
                "commit_count": global_stats["commit_count"],
                "file_count": global_stats["file_count"],
                "repo_counts": dict(global_stats["repo_counts"].most_common(30)),
                "kind_counts": dict(global_stats["kind_counts"].most_common()),
                "pattern_counts": dict(global_stats["pattern_counts"].most_common()),
                "commit_type_counts": dict(global_stats["commit_type_counts"].most_common()),
            },
            tags=["github", "commit_diff", "summary"],
            occurred_at=generated_at,
            ingested_at=generated_at,
            url_or_path="",
        )
    )

    for repo, repo_stats in sorted(stats["repos"].items(), key=lambda item: (-item[1]["commit_count"], item[0])):
        source_key = f"github_commit_patterns:{repo}:summary"
        rows.append(
            code_style_record(
                source_key=source_key,
                title=f"GitHub commit-derived coding pattern profile for {repo}",
                summary=f"Aggregated code-style patterns detected from {repo} GitHub commit diffs.",
                raw_excerpt={
                    "category": "github_commit_pattern_summary",
                    "scope": "repo",
                    "repo": {"slug": repo},
                    "commit_count": repo_stats["commit_count"],
                    "file_count": repo_stats["file_count"],
                    "additions": repo_stats["additions"],
                    "deletions": repo_stats["deletions"],
                    "first_seen": repo_stats["first_seen"],
                    "last_seen": repo_stats["last_seen"],
                    "kind_counts": dict(repo_stats["kind_counts"].most_common()),
                    "top_paths": dict(repo_stats["path_counts"].most_common(40)),
                    "pattern_counts": dict(repo_stats["pattern_counts"].most_common()),
                    "commit_type_counts": dict(repo_stats["commit_type_counts"].most_common()),
                },
                tags=["github", "commit_diff", "summary", f"repo:{repo}"],
                occurred_at=repo_stats["last_seen"] or generated_at,
                ingested_at=generated_at,
                url_or_path=f"https://github.com/{repo}",
            )
        )

        examples = sorted(repo_stats["examples"], key=lambda item: (-item["score"], item["filename"], item["sha"]))[:max_examples_per_repo]
        for example in examples:
            source_key = f"github_commit_patterns:{repo}:example:{example['sha']}:{example['filename']}"
            rows.append(
                code_style_record(
                    source_key=source_key,
                    title=f"Representative commit diff example: {repo}/{example['filename']}",
                    summary="Representative patch selected from GitHub commit diffs for code-style retrieval.",
                    raw_excerpt={
                        "category": "github_commit_code_example",
                        "repo": {"slug": repo},
                        "path": example["filename"],
                        "kind": example["kind"],
                        "commit_id": example["commit_id"],
                        "sha": example["sha"],
                        "commit_title": example["commit_title"],
                        "status": example["status"],
                        "changes": example["changes"],
                        "patterns": example["patterns"],
                        "excerpt": example["patch_excerpt"],
                        "added_lines_excerpt": example["added_lines_excerpt"],
                        "removed_lines_excerpt": example["removed_lines_excerpt"],
                    },
                    tags=["github", "commit_diff", "code_example", example["kind"], f"repo:{repo}"],
                    occurred_at=example["occurred_at"],
                    ingested_at=generated_at,
                    url_or_path=example["url"],
                )
            )
    return rows


def markdown_table(rows: list[tuple[str, str, str]]) -> list[str]:
    lines = ["| Area | Signal | Evidence |", "| --- | --- | --- |"]
    for area, signal, evidence in rows:
        lines.append(f"| {area.replace('|', '\\|')} | {signal.replace('|', '\\|')} | {evidence.replace('|', '\\|')} |")
    return lines


def profile_markdown(stats: dict[str, Any], generated_at: str) -> str:
    global_stats = stats["global"]
    top_patterns = global_stats["pattern_counts"].most_common(16)
    top_kinds = global_stats["kind_counts"].most_common(12)
    top_repos = global_stats["repo_counts"].most_common(20)
    rows = []
    for pattern, count in top_patterns[:12]:
        rows.append(("Recurring pattern", f"`{pattern}` appears {count} times in commit diffs", "`code_style_signal:" + stable_hash("github_commit_patterns:global") + "`"))
    lines = [
        "# GitHub Commit Code Pattern Profile",
        "",
        f"Generated: {generated_at}",
        "",
        "This profile is derived from GitHub commit diffs exported through `gh`, not from a local clone.",
        "",
        "## Coverage",
        "",
        f"- Commits analyzed: {global_stats['commit_count']}",
        f"- Changed files analyzed: {global_stats['file_count']}",
        f"- Repositories: {len(global_stats['repo_counts'])}",
        "",
        "## Top Repositories",
        "",
    ]
    lines.extend(f"- `{repo}`: {count} commits" for repo, count in top_repos)
    lines.extend(["", "## Dominant File Areas", ""])
    lines.extend(f"- `{kind}`: {count} changed files" for kind, count in top_kinds)
    lines.extend(["", "## Recurrent Code Patterns", ""])
    lines.extend(markdown_table(rows) if rows else ["No recurring patterns detected."])
    lines.extend(["", "## Repo-Specific Signals", ""])
    for repo, repo_stats in sorted(stats["repos"].items(), key=lambda item: (-item[1]["commit_count"], item[0]))[:30]:
        patterns = ", ".join(f"{name}={count}" for name, count in repo_stats["pattern_counts"].most_common(10))
        kinds = ", ".join(f"{name}={count}" for name, count in repo_stats["kind_counts"].most_common(8))
        evidence = f"`code_style_signal:{stable_hash(f'github_commit_patterns:{repo}:summary')}`"
        lines.extend([
            f"### {repo}",
            "",
            f"- Commits: {repo_stats['commit_count']}; files: {repo_stats['file_count']}; range: {repo_stats['first_seen']} to {repo_stats['last_seen']}",
            f"- File areas: {kinds or 'none'}",
            f"- Patterns: {patterns or 'none'}",
            f"- Evidence: {evidence}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def agent_instruction_markdown(stats: dict[str, Any], generated_at: str) -> str:
    global_patterns = [name for name, _ in stats["global"]["pattern_counts"].most_common(12)]
    lines = [
        "# Agent Coding Instructions From GitHub Commit Patterns",
        "",
        f"Generated: {generated_at}",
        "",
        "Use these instructions when no local repo scan is available but GitHub commit-derived code evidence exists.",
        "",
        "## Rules",
        "",
        "- Query `code_style` and `github_commit_patterns` evidence before writing code for a scanned repo.",
        "- Treat commit diffs as strong evidence for repeated patterns, but inspect local files when available before editing.",
        "- Match the repository's dominant file areas, imports, service/state boundaries, testing style, and CI conventions.",
        "- Cite `code_style_signal:*` evidence when explaining why a generated implementation follows the user's style.",
        "",
        "## Frequently Observed Patterns",
        "",
    ]
    lines.extend(f"- `{name}`" for name in global_patterns)
    lines.append("")
    return "\n".join(lines)


def update_profile_file(path: Path, section_title: str, section_body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = "# Coding Standards Profile\n\n"
    start_marker = f"<!-- BEGIN {section_title} -->"
    end_marker = f"<!-- END {section_title} -->"
    section = f"{start_marker}\n{section_body.rstrip()}\n{end_marker}\n"
    if start_marker in text and end_marker in text:
        pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker) + r"\n?", re.DOTALL)
        text = pattern.sub(section, text)
    else:
        text = text.rstrip() + "\n\n" + section
    path.write_text(text, encoding="utf-8")


def analyze(ledger: Path, include_repos: list[str] | None, max_examples_per_repo: int) -> dict[str, Any]:
    generated_at = now_iso()
    git_path = ledger / "sources" / "git.jsonl"
    rows = read_jsonl(git_path)
    stats = collect(rows, include_repos)
    records = records_from_stats(stats, max_examples_per_repo, generated_at)
    code_style_path = ledger / "sources" / "code_style.jsonl"
    replaced, total = merge_code_style_rows(code_style_path, "github_commit_patterns:", records)

    profile = profile_markdown(stats, generated_at)
    instructions = agent_instruction_markdown(stats, generated_at)
    (ledger / "profiles" / "github-commit-code-patterns.md").write_text(profile, encoding="utf-8")
    update_profile_file(ledger / "profiles" / "coding-standards-profile.md", "GITHUB COMMIT CODE PATTERNS", profile)
    update_profile_file(ledger / "profiles" / "agent-coding-instructions.md", "GITHUB COMMIT CODE PATTERNS", instructions)

    return {
        "ledger": str(ledger),
        "git_source": str(git_path),
        "code_style_out": str(code_style_path),
        "records_written": len(records),
        "records_replaced": replaced,
        "total_code_style_records": total,
        "commits_analyzed": stats["global"]["commit_count"],
        "files_analyzed": stats["global"]["file_count"],
        "repos_analyzed": len(stats["global"]["repo_counts"]),
        "profile": str(ledger / "profiles" / "github-commit-code-patterns.md"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--repo", action="append", help="Restrict analysis to owner/repo. Can be repeated.")
    parser.add_argument("--max-examples-per-repo", type=int, default=12)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = analyze(resolve_ledger_path(args.ledger), args.repo, args.max_examples_per_repo)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(
            " ".join(
                [
                    f"commits_analyzed={result['commits_analyzed']}",
                    f"files_analyzed={result['files_analyzed']}",
                    f"records_written={result['records_written']}",
                    f"out={result['code_style_out']}",
                ]
            )
        )


if __name__ == "__main__":
    main()
