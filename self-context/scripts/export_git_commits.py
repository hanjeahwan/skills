#!/usr/bin/env python3
"""Export Git commits as evidence-ledger source JSONL."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


UNIT_SEP = "\x1f"


def run_git(repo: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout


def resolve_repo(repo: Path) -> Path:
    root = run_git(repo, ["rev-parse", "--show-toplevel"]).strip()
    return Path(root).resolve()


def parse_numstat(text: str) -> tuple[int, int, list[str]]:
    additions = 0
    deletions = 0
    files: list[str] = []

    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        add_raw, del_raw, path = parts
        files.append(path)
        if add_raw.isdigit():
            additions += int(add_raw)
        if del_raw.isdigit():
            deletions += int(del_raw)

    return additions, deletions, files


def build_log_args(args: argparse.Namespace) -> list[str]:
    log_args = ["log", f"--format=%H{UNIT_SEP}%aI{UNIT_SEP}%an{UNIT_SEP}%ae{UNIT_SEP}%s"]
    if args.author:
        log_args.append(f"--author={args.author}")
    if args.since:
        log_args.append(f"--since={args.since}")
    if args.until:
        log_args.append(f"--until={args.until}")
    if args.max_count:
        log_args.append(f"--max-count={args.max_count}")
    return log_args


def export_commits(args: argparse.Namespace) -> None:
    repo = resolve_repo(Path(args.repo).resolve())
    repo_slug = repo.name
    now = datetime.now(timezone.utc).isoformat()
    output_path = Path(args.out).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for line in run_git(repo, build_log_args(args)).splitlines():
        parts = line.split(UNIT_SEP)
        if len(parts) != 5:
            continue

        commit_hash, authored_at, author_name, author_email, subject = parts
        body = run_git(repo, ["show", "-s", "--format=%B", commit_hash]).strip()
        numstat = run_git(repo, ["show", "--numstat", "--format=", commit_hash])
        additions, deletions, files = parse_numstat(numstat)

        rows.append(
            {
                "id": f"git_commit:{repo_slug}:{commit_hash}",
                "source_type": "git_commit",
                "source_id": commit_hash,
                "occurred_at": authored_at,
                "title": subject,
                "summary": body,
                "url_or_path": str(repo),
                "raw_excerpt": {
                    "author_name": author_name,
                    "author_email": author_email,
                    "additions": additions,
                    "deletions": deletions,
                    "files": files[:200],
                },
                "tags": ["git", repo_slug],
                "ingested_at": now,
            }
        )

    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"exported {len(rows)} commits to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Path to a Git repository")
    parser.add_argument("--out", required=True, help="Output JSONL path")
    parser.add_argument("--author", help="Optional git log author filter")
    parser.add_argument("--since", help="Optional git log --since value")
    parser.add_argument("--until", help="Optional git log --until value")
    parser.add_argument("--max-count", type=int, help="Optional maximum commit count")
    export_commits(parser.parse_args())


if __name__ == "__main__":
    main()
