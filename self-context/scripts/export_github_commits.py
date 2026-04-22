#!/usr/bin/env python3
"""Export GitHub commits without cloning repositories."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def rate_limit_wait_seconds() -> int:
    result = subprocess.run(
        ["gh", "api", "rate_limit"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    data = json.loads(result.stdout)
    resources = data.get("resources") or {}
    now = int(time.time())

    for bucket in ["search", "core"]:
        info = resources.get(bucket) or {}
        if int(info.get("remaining", 1)) <= 0:
            reset = int(info.get("reset", now))
            return max(1, reset - now + 2)

    return 5


def run_gh(args: list[str]) -> str:
    for attempt in range(4):
        result = subprocess.run(
            ["gh", *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            return result.stdout

        combined = f"{result.stdout}\n{result.stderr}".lower()
        if "rate limit exceeded" in combined and attempt < 3:
            wait_seconds = rate_limit_wait_seconds()
            print(f"GitHub API rate limit reached; waiting {wait_seconds}s before retry", file=sys.stderr)
            time.sleep(wait_seconds)
            continue

        raise subprocess.CalledProcessError(result.returncode, ["gh", *args], result.stdout, result.stderr)

    raise RuntimeError("unreachable")


def gh_json(args: list[str]) -> object:
    return json.loads(run_gh(args))


def build_query(args: argparse.Namespace) -> str:
    parts = [f"author:{args.author}"]
    if args.since or args.until:
        since = args.since or "*"
        until = args.until or "*"
        parts.append(f"author-date:{since}..{until}")
    if args.repo:
        for repo in args.repo:
            parts.append(f"repo:{repo}")
    if args.org:
        for org in args.org:
            parts.append(f"org:{org}")
    if args.user:
        for user in args.user:
            parts.append(f"user:{user}")
    return " ".join(parts)


def search_commits(args: argparse.Namespace) -> list[dict]:
    query = build_query(args)
    per_page = min(args.per_page, 100)
    page = 1
    items: list[dict] = []

    while True:
        response = gh_json(
            [
                "api",
                "--method",
                "GET",
                "search/commits",
                "-H",
                "Accept: application/vnd.github+json",
                "-f",
                f"q={query}",
                "-F",
                f"per_page={per_page}",
                "-F",
                f"page={page}",
            ]
        )
        if not isinstance(response, dict):
            raise RuntimeError("unexpected GitHub search response")

        page_items = response.get("items", [])
        if not isinstance(page_items, list):
            raise RuntimeError("unexpected GitHub search items")
        items.extend(page_items)

        if args.max_count and len(items) >= args.max_count:
            return items[: args.max_count]
        if len(page_items) < per_page:
            return items
        if page >= args.max_pages:
            return items
        page += 1


def commit_detail(repo: str, sha: str) -> dict:
    response = gh_json(["api", "--method", "GET", f"repos/{repo}/commits/{sha}"])
    if not isinstance(response, dict):
        raise RuntimeError(f"unexpected commit detail for {repo}@{sha}")
    return response


def patch_excerpt(value: str | None, max_lines: int) -> str:
    if not value:
        return ""
    lines = value.splitlines()
    return "\n".join(lines[:max_lines])


def detail_to_raw_evidence(detail: dict, repo: str, max_files: int, patch_lines: int, now: str) -> dict:
    commit = detail.get("commit", {})
    author = commit.get("author") or {}
    message = commit.get("message") or ""
    title = message.splitlines()[0] if message else detail.get("sha", "")
    stats = detail.get("stats") or {}
    files = []

    for file_item in (detail.get("files") or [])[:max_files]:
        files.append(
            {
                "filename": file_item.get("filename", ""),
                "status": file_item.get("status", ""),
                "additions": file_item.get("additions", 0),
                "deletions": file_item.get("deletions", 0),
                "changes": file_item.get("changes", 0),
                "patch_excerpt": patch_excerpt(file_item.get("patch"), patch_lines),
            }
        )

    sha = detail.get("sha", "")
    return {
        "id": f"git_commit:{repo}:{sha}",
        "source_type": "git_commit",
        "source_id": sha,
        "occurred_at": author.get("date", ""),
        "title": title,
        "summary": message,
        "url_or_path": detail.get("html_url", ""),
        "raw_excerpt": {
            "repo": repo,
            "author_name": author.get("name", ""),
            "author_email": author.get("email", ""),
            "additions": stats.get("additions", 0),
            "deletions": stats.get("deletions", 0),
            "total": stats.get("total", 0),
            "files": files,
        },
        "tags": ["github", "git", repo],
        "ingested_at": now,
    }


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


def export(args: argparse.Namespace) -> None:
    output_path = Path(args.out).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.replace and output_path.exists():
        output_path.unlink()

    now = datetime.now(timezone.utc).isoformat()
    seen = existing_ids(output_path)
    exported = 0
    skipped: list[dict[str, str]] = []

    with output_path.open("a", encoding="utf-8") as handle:
        for item in search_commits(args):
            repo_info = item.get("repository") or {}
            repo = repo_info.get("full_name")
            sha = item.get("sha")
            if not repo or not sha:
                continue
            row_id = f"git_commit:{repo}:{sha}"
            if row_id in seen:
                continue
            seen.add(row_id)

            try:
                detail = commit_detail(repo, sha)
            except Exception as exc:
                skipped.append({"repo": repo, "sha": sha, "error": str(exc)})
                continue

            row = detail_to_raw_evidence(detail, repo, args.max_files, args.patch_lines, now)
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
            exported += 1

    print(f"exported {exported} new GitHub commits to {output_path}")
    if skipped:
        print(f"skipped {len(skipped)} GitHub commits that failed detail fetch")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author", required=True, help="GitHub username for commit search")
    parser.add_argument("--out", required=True, help="Output JSONL path")
    parser.add_argument("--since", help="Start date, YYYY-MM-DD")
    parser.add_argument("--until", help="End date, YYYY-MM-DD")
    parser.add_argument("--repo", action="append", help="Restrict to owner/repo. Can be repeated.")
    parser.add_argument("--org", action="append", help="Restrict to organization. Can be repeated.")
    parser.add_argument("--user", action="append", help="Restrict to user-owned repos. Can be repeated.")
    parser.add_argument("--max-count", type=int, help="Maximum commits to export")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximum search pages to request")
    parser.add_argument("--per-page", type=int, default=100, help="Search results per page, max 100")
    parser.add_argument("--max-files", type=int, default=200, help="Maximum files to keep per commit")
    parser.add_argument("--patch-lines", type=int, default=80, help="Patch lines to keep per file")
    parser.add_argument("--replace", action="store_true", help="Replace the output file before exporting")
    export(parser.parse_args())


if __name__ == "__main__":
    main()
