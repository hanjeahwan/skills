#!/usr/bin/env python3
"""Persist GitHub PR, review, and PR-comment activity as raw ledger evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from ledger_paths import resolve_ledger_path


def jsonl_dumps(row: dict) -> str:
    return json.dumps(row, ensure_ascii=False).replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def run_gh_json(args: list[str], retries: int = 4) -> object:
    for attempt in range(retries):
        proc = subprocess.run(
            ["gh", "api", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        if proc.returncode == 0:
            output = proc.stdout.strip()
            return json.loads(output) if output else None

        combined = f"{proc.stdout}\n{proc.stderr}".lower()
        if ("secondary rate limit" in combined or "rate limit" in combined) and attempt < retries - 1:
            wait_seconds = 90 + attempt * 60
            print(f"GitHub API rate limit reached; waiting {wait_seconds}s", file=sys.stderr)
            time.sleep(wait_seconds)
            continue

        raise subprocess.CalledProcessError(proc.returncode, ["gh", "api", *args], proc.stdout, proc.stderr)

    raise RuntimeError("unreachable")


def paginated(endpoint: str) -> list[dict]:
    data = run_gh_json(["--paginate", "--slurp", endpoint])
    rows: list[dict] = []
    if isinstance(data, list):
        for page in data:
            if isinstance(page, list):
                rows.extend(item for item in page if isinstance(item, dict))
            elif isinstance(page, dict):
                rows.append(page)
    return rows


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_after(value: str | None, since: str | None) -> bool:
    if not since:
        return True
    value_dt = parse_timestamp(value)
    since_dt = parse_timestamp(since)
    if value_dt is None or since_dt is None:
        return True
    return value_dt > since_dt


def since_query(since: str | None) -> str:
    if not since:
        return ""
    return f"&since={urllib.parse.quote(since, safe='')}"


def list_pulls(repo: str, since: str | None) -> list[dict]:
    if not since:
        return paginated(f"repos/{repo}/pulls?state=all&per_page=100")

    rows: list[dict] = []
    page = 1
    while True:
        endpoint = f"repos/{repo}/pulls?state=all&sort=updated&direction=desc&per_page=100&page={page}"
        page_rows = run_gh_json([endpoint])
        if not isinstance(page_rows, list) or not page_rows:
            break

        recent = [pr for pr in page_rows if is_after(pr.get("updated_at"), since)]
        rows.extend(recent)
        if len(recent) < len(page_rows) or len(page_rows) < 100:
            break
        page += 1

    return rows


def existing_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()

    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        row_id = row.get("id")
        if isinstance(row_id, str):
            ids.add(row_id)
    return ids


def append_rows(path: Path, rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = existing_ids(path)
    written = 0
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            row_id = row.get("id")
            if not row_id or row_id in seen:
                continue
            seen.add(row_id)
            handle.write(jsonl_dumps(row) + "\n")
            written += 1
    return written


def pr_row(repo: str, pr: dict, ingested_at: str) -> dict:
    number = pr["number"]
    title = pr.get("title") or f"{repo}#{number}"
    merged_at = pr.get("merged_at") or pr.get("mergedAt") or ""
    author = pr.get("author") or {}
    if isinstance(author, dict):
        author_login = author.get("login") or ((pr.get("user") or {}).get("login") if isinstance(pr.get("user"), dict) else "")
    else:
        author_login = ""

    return {
        "id": f"pull_request:{repo}#{number}",
        "source_type": "pull_request",
        "source_id": f"{repo}#{number}",
        "occurred_at": merged_at or pr.get("created_at") or pr.get("createdAt") or pr.get("updated_at") or pr.get("updatedAt") or "",
        "title": title,
        "summary": title,
        "url_or_path": pr.get("html_url") or pr.get("url") or "",
        "raw_excerpt": {
            "repo": repo,
            "number": number,
            "author": author_login,
            "state": pr.get("state"),
            "merged_at": merged_at,
            "created_at": pr.get("created_at") or pr.get("createdAt"),
            "updated_at": pr.get("updated_at") or pr.get("updatedAt"),
            "comments": pr.get("comments") or pr.get("commentsCount"),
            "review_comments": pr.get("review_comments"),
            "changed_files": pr.get("changed_files"),
            "additions": pr.get("additions"),
            "deletions": pr.get("deletions"),
        },
        "tags": ["github", "pull_request", repo],
        "ingested_at": ingested_at,
    }


def discussion_comment_row(repo: str, pr: dict, comment: dict, ingested_at: str) -> dict:
    number = pr["number"]
    comment_id = comment["id"]
    title = f"PR discussion comment on {repo}#{number}"
    return {
        "id": f"pull_request_discussion_comment:{repo}#{number}:{comment_id}",
        "source_type": "pull_request_discussion_comment",
        "source_id": f"{repo}#{number}:{comment_id}",
        "occurred_at": comment.get("created_at") or comment.get("createdAt") or "",
        "title": title,
        "summary": comment.get("body_excerpt") or title,
        "url_or_path": comment.get("html_url") or comment.get("url") or pr.get("html_url") or "",
        "raw_excerpt": {
            "repo": repo,
            "number": number,
            "comment_id": comment_id,
            "pr_title": pr.get("title", ""),
            "pr_author": pr.get("author", ""),
            "body_excerpt": comment.get("body_excerpt", ""),
            "updated_at": comment.get("updated_at") or comment.get("updatedAt"),
        },
        "tags": ["github", "pull_request", "discussion_comment", repo],
        "ingested_at": ingested_at,
    }


def review_comment_row(repo: str, pr: dict, comment: dict, ingested_at: str) -> dict:
    number = pr["number"]
    comment_id = comment["id"]
    title = f"PR review comment on {repo}#{number}"
    return {
        "id": f"pull_request_review_comment:{repo}#{number}:{comment_id}",
        "source_type": "pull_request_review_comment",
        "source_id": f"{repo}#{number}:{comment_id}",
        "occurred_at": comment.get("created_at") or comment.get("createdAt") or "",
        "title": title,
        "summary": comment.get("body_excerpt") or title,
        "url_or_path": comment.get("html_url") or comment.get("url") or pr.get("html_url") or "",
        "raw_excerpt": {
            "repo": repo,
            "number": number,
            "comment_id": comment_id,
            "pr_title": pr.get("title", ""),
            "pr_author": pr.get("author", ""),
            "path": comment.get("path", ""),
            "body_excerpt": comment.get("body_excerpt", ""),
            "updated_at": comment.get("updated_at") or comment.get("updatedAt"),
        },
        "tags": ["github", "pull_request", "review_comment", repo],
        "ingested_at": ingested_at,
    }


def rows_from_scan(scan: dict, ingested_at: str) -> list[dict]:
    rows: list[dict] = []
    for repo, payload in (scan.get("repos") or {}).items():
        for pr in payload.get("authored_prs", []) or []:
            rows.append(pr_row(repo, pr, ingested_at))
        for pr in payload.get("issue_comment_prs", []) or []:
            for comment in pr.get("comment_excerpts", []) or []:
                rows.append(discussion_comment_row(repo, pr, comment, ingested_at))
        for pr in payload.get("review_comment_prs", []) or []:
            for comment in pr.get("comment_excerpts", []) or []:
                rows.append(review_comment_row(repo, pr, comment, ingested_at))
    return rows


def rows_from_repo_scan(repo: str, user: str, ingested_at: str, since: str | None) -> tuple[list[dict], dict]:
    pulls = list_pulls(repo, since)
    pr_by_number = {int(pr["number"]): pr for pr in pulls if pr.get("number") is not None}
    rows: list[dict] = []
    stats = {
        "repo": repo,
        "since": since,
        "pull_count": len(pulls),
        "authored_pr_count": 0,
        "discussion_comment_count": 0,
        "review_comment_count": 0,
    }

    for pr in pulls:
        author = ((pr.get("user") or {}).get("login") or "").lower()
        if author == user.lower():
            rows.append(pr_row(repo, pr, ingested_at))
            stats["authored_pr_count"] += 1

    discussion_by_pr: dict[int, list[dict]] = defaultdict(list)
    for comment in paginated(f"repos/{repo}/issues/comments?per_page=100{since_query(since)}"):
        author = ((comment.get("user") or {}).get("login") or "").lower()
        if author != user.lower():
            continue
        issue_url = comment.get("issue_url") or ""
        try:
            number = int(issue_url.rsplit("/", 1)[-1])
        except ValueError:
            continue
        if number in pr_by_number:
            discussion_by_pr[number].append(
                {
                    "id": comment.get("id"),
                    "created_at": comment.get("created_at"),
                    "updated_at": comment.get("updated_at"),
                    "body_excerpt": comment.get("body", "")[:500],
                    "html_url": comment.get("html_url"),
                }
            )

    for number, comments in discussion_by_pr.items():
        pr = pr_by_number[number]
        pr_info = {
            "number": number,
            "title": pr.get("title", ""),
            "author": (pr.get("user") or {}).get("login", ""),
            "html_url": pr.get("html_url", ""),
        }
        for comment in comments:
            rows.append(discussion_comment_row(repo, pr_info, comment, ingested_at))
            stats["discussion_comment_count"] += 1

    review_by_pr: dict[int, list[dict]] = defaultdict(list)
    for comment in paginated(f"repos/{repo}/pulls/comments?per_page=100{since_query(since)}"):
        author = ((comment.get("user") or {}).get("login") or "").lower()
        if author != user.lower():
            continue
        pull_url = comment.get("pull_request_url") or ""
        try:
            number = int(pull_url.rsplit("/", 1)[-1])
        except ValueError:
            continue
        if number in pr_by_number:
            review_by_pr[number].append(
                {
                    "id": comment.get("id"),
                    "created_at": comment.get("created_at"),
                    "updated_at": comment.get("updated_at"),
                    "path": comment.get("path"),
                    "body_excerpt": comment.get("body", "")[:500],
                    "html_url": comment.get("html_url"),
                }
            )

    for number, comments in review_by_pr.items():
        pr = pr_by_number[number]
        pr_info = {
            "number": number,
            "title": pr.get("title", ""),
            "author": (pr.get("user") or {}).get("login", ""),
            "html_url": pr.get("html_url", ""),
        }
        for comment in comments:
            rows.append(review_comment_row(repo, pr_info, comment, ingested_at))
            stats["review_comment_count"] += 1

    return rows, stats


def repos_from_git_source(ledger: Path) -> list[str]:
    repos: Counter[str] = Counter()
    path = ledger / "sources" / "git.jsonl"
    if not path.exists():
        return []
    for line in path.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        repo = (row.get("raw_excerpt") or {}).get("repo")
        if isinstance(repo, str) and repo:
            repos[repo] += 1
    return [repo for repo, _ in repos.most_common()]


def write_coverage(path: Path, rows: list[dict], stats: list[dict], written: int, ingested_at: str) -> None:
    source_counts = Counter(row.get("source_type") for row in rows)
    coverage = {
        "generated_at": ingested_at,
        "candidate_rows": len(rows),
        "written_rows": written,
        "source_type_counts": dict(sorted(source_counts.items())),
        "repo_stats": stats,
    }
    path.write_text(json.dumps(coverage, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--out", help="Output JSONL path. Defaults to <ledger>/sources/github_pr_activity.jsonl.")
    parser.add_argument("--coverage-out", help="Coverage JSON path. Defaults to <out>.coverage.json.")
    parser.add_argument("--from-scan-json", help="Convert a prior github-pr-review-leadership-scan JSON report without network calls.")
    parser.add_argument("--github-user", default="example-user", help="GitHub login to match for authored PRs and comments.")
    parser.add_argument("--repo", action="append", help="Repository owner/name to scan. Can be repeated.")
    parser.add_argument("--repos-from-git-source", action="store_true", help="Scan repositories already present in sources/git.jsonl.")
    parser.add_argument("--since", help="Only fetch PR/comment activity updated after this ISO timestamp.")
    parser.add_argument("--incremental", action="store_true", help="Use the previous coverage generated_at as --since when available.")
    parser.add_argument("--replace", action="store_true", help="Replace output before writing.")
    args = parser.parse_args()

    ledger = resolve_ledger_path(args.ledger)
    output = Path(args.out).expanduser().resolve() if args.out else ledger / "sources" / "github_pr_activity.jsonl"
    coverage = (
        Path(args.coverage_out).expanduser().resolve()
        if args.coverage_out
        else output.with_suffix(output.suffix + ".coverage.json")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.replace and output.exists():
        output.unlink()

    ingested_at = datetime.now(timezone.utc).isoformat()
    stats: list[dict] = []
    if args.from_scan_json:
        scan = json.loads(Path(args.from_scan_json).read_text(encoding="utf-8"))
        rows = rows_from_scan(scan, ingested_at)
        summary = scan.get("summary") or {}
        if summary:
            stats.append({"from_scan_json": args.from_scan_json, **summary})
    else:
        since = args.since
        if args.incremental and not since and coverage.exists():
            try:
                previous = json.loads(coverage.read_text(encoding="utf-8"))
                previous_generated_at = previous.get("generated_at")
                if isinstance(previous_generated_at, str) and previous_generated_at:
                    since = previous_generated_at
            except json.JSONDecodeError:
                since = None

        repos = list(args.repo or [])
        if args.repos_from_git_source:
            repos.extend(repos_from_git_source(ledger))
        repos = list(dict.fromkeys(repos))
        if not repos:
            raise SystemExit("provide --repo, --repos-from-git-source, or --from-scan-json")

        rows = []
        for repo in repos:
            try:
                repo_rows, repo_stats = rows_from_repo_scan(repo, args.github_user, ingested_at, since)
            except Exception as exc:
                stats.append({"repo": repo, "error": str(exc)})
                print(f"skipped {repo}: {exc}", file=sys.stderr)
                continue
            rows.extend(repo_rows)
            stats.append(repo_stats)

    written = append_rows(output, rows)
    write_coverage(coverage, rows, stats, written, ingested_at)
    print(f"candidate_rows={len(rows)} written_rows={written} output={output}")
    print(f"coverage={coverage}")


if __name__ == "__main__":
    main()
