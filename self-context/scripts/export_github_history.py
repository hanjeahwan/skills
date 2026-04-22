#!/usr/bin/env python3
"""Export GitHub commit history by date-slicing search queries, without cloning."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from export_github_commits import commit_detail, detail_to_raw_evidence, gh_json


@dataclass(frozen=True)
class Scope:
    qualifier: str
    value: str

    @property
    def label(self) -> str:
        return f"{self.qualifier}:{self.value}"


@dataclass(frozen=True)
class Window:
    start: date
    end: date
    scope: Scope | None


def parse_day(value: str) -> date:
    return date.fromisoformat(value)


def date_chunks(start: date, end: date, days: int) -> Iterable[tuple[date, date]]:
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=days - 1), end)
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def scopes(args: argparse.Namespace) -> list[Scope | None]:
    result: list[Scope | None] = []
    for repo in args.repo or []:
        result.append(Scope("repo", repo))
    for org in args.org or []:
        result.append(Scope("org", org))
    for user in args.user or []:
        result.append(Scope("user", user))
    return result or [None]


def author_qualifier(args: argparse.Namespace) -> str:
    return f"{args.author_mode}:{args.author}"


def date_qualifier(args: argparse.Namespace, window: Window) -> str:
    return f"{args.date_mode}-date:{window.start.isoformat()}..{window.end.isoformat()}"


def query(args: argparse.Namespace, window: Window) -> str:
    parts = [author_qualifier(args), date_qualifier(args, window)]
    if window.scope:
        parts.append(window.scope.label)
    return " ".join(parts)


def search_page(search_query: str, page: int, per_page: int) -> dict:
    response = gh_json(
        [
            "api",
            "--method",
            "GET",
            "search/commits",
            "-H",
            "Accept: application/vnd.github+json",
            "-f",
            f"q={search_query}",
            "-F",
            f"per_page={per_page}",
            "-F",
            f"page={page}",
        ]
    )
    if not isinstance(response, dict):
        raise RuntimeError("unexpected GitHub search response")
    return response


def total_count(args: argparse.Namespace, window: Window) -> int:
    response = search_page(query(args, window), page=1, per_page=1)
    value = response.get("total_count", 0)
    return int(value) if isinstance(value, int) else 0


def split_window(window: Window) -> tuple[Window, Window]:
    total_days = (window.end - window.start).days
    midpoint = window.start + timedelta(days=total_days // 2)
    return (
        Window(window.start, midpoint, window.scope),
        Window(midpoint + timedelta(days=1), window.end, window.scope),
    )


def discover_windows(args: argparse.Namespace, initial: Window, coverage: list[dict]) -> list[Window]:
    count = total_count(args, initial)
    coverage.append(
        {
            "scope": initial.scope.label if initial.scope else "all-accessible",
            "start": initial.start.isoformat(),
            "end": initial.end.isoformat(),
            "total_count": count,
            "phase": "discover",
        }
    )

    if count <= args.split_threshold:
        return [initial]
    if initial.start >= initial.end:
        coverage.append(
            {
                "scope": initial.scope.label if initial.scope else "all-accessible",
                "start": initial.start.isoformat(),
                "end": initial.end.isoformat(),
                "total_count": count,
                "phase": "warning",
                "message": "single-day window exceeds split threshold; results may be truncated by GitHub search limits",
            }
        )
        return [initial]

    left, right = split_window(initial)
    return [*discover_windows(args, left, coverage), *discover_windows(args, right, coverage)]


def fetch_window(
    args: argparse.Namespace,
    window: Window,
    seen: set[str],
    handle,
    coverage: list[dict],
    remaining: int | None,
) -> int:
    search_query = query(args, window)
    first = search_page(search_query, page=1, per_page=args.per_page)
    total = int(first.get("total_count", 0))
    total_pages = min(args.max_pages, max(1, math.ceil(total / args.per_page)))
    now = datetime.now(timezone.utc).isoformat()
    exported = 0
    fetched_items = 0
    skipped: list[dict[str, str]] = []

    for page in range(1, total_pages + 1):
        response = first if page == 1 else search_page(search_query, page=page, per_page=args.per_page)
        items = response.get("items", [])
        if not isinstance(items, list):
            raise RuntimeError("unexpected GitHub search items")
        if not items:
            break

        fetched_items += len(items)
        for item in items:
            repo_info = item.get("repository") or {}
            repo = repo_info.get("full_name")
            sha = item.get("sha")
            if not repo or not sha:
                continue
            row_id = f"git_commit:{repo}:{sha}"
            if row_id in seen:
                continue
            if remaining is not None and exported >= remaining:
                break

            try:
                detail = commit_detail(repo, sha)
            except Exception as exc:
                skipped.append(
                    {
                        "repo": repo,
                        "sha": sha,
                        "error": str(exc),
                    }
                )
                continue
            row = detail_to_raw_evidence(detail, repo, args.max_files, args.patch_lines, now)
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
            seen.add(row_id)
            exported += 1

        if remaining is not None and exported >= remaining:
            break

    coverage.append(
        {
            "scope": window.scope.label if window.scope else "all-accessible",
            "start": window.start.isoformat(),
            "end": window.end.isoformat(),
            "total_count": total,
            "fetched_search_items": fetched_items,
            "exported_new_records": exported,
            "skipped_records": skipped,
            "phase": "fetch",
            "truncated": total_pages * args.per_page < total,
        }
    )
    return exported


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
    coverage_path = Path(args.coverage_out).expanduser().resolve() if args.coverage_out else output_path.with_suffix(".coverage.json")

    if args.replace and output_path.exists():
        output_path.unlink()

    seen = existing_ids(output_path)
    coverage: list[dict] = []
    start = parse_day(args.since)
    end = parse_day(args.until) if args.until else date.today()
    if end < start:
        raise ValueError("--until must be on or after --since")

    initial_windows = [
        Window(chunk_start, chunk_end, scope)
        for scope in scopes(args)
        for chunk_start, chunk_end in date_chunks(start, end, args.initial_window_days)
    ]

    final_windows: list[Window] = []
    for window in initial_windows:
        final_windows.extend(discover_windows(args, window, coverage))

    exported = 0
    with output_path.open("a", encoding="utf-8") as handle:
        for window in final_windows:
            remaining = None if args.max_count is None else args.max_count - exported
            if remaining is not None and remaining <= 0:
                break
            exported += fetch_window(args, window, seen, handle, coverage, remaining)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "author_mode": args.author_mode,
        "author": args.author,
        "date_mode": args.date_mode,
        "since": start.isoformat(),
        "until": end.isoformat(),
        "output": str(output_path),
        "exported_new_records": exported,
        "unique_records_seen": len(seen),
        "windows": coverage,
    }
    coverage_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"exported {exported} new GitHub commits to {output_path}")
    print(f"wrote coverage report to {coverage_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author", required=True, help="GitHub username or email value, depending on --author-mode")
    parser.add_argument(
        "--author-mode",
        choices=["author", "author-email", "committer", "committer-email"],
        default="author",
        help="GitHub commit search qualifier",
    )
    parser.add_argument("--date-mode", choices=["author", "committer"], default="author", help="Date qualifier prefix")
    parser.add_argument("--since", required=True, help="Start date, YYYY-MM-DD")
    parser.add_argument("--until", help="End date, YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--out", required=True, help="Output JSONL path")
    parser.add_argument("--coverage-out", help="Coverage report JSON path")
    parser.add_argument("--repo", action="append", help="Restrict to owner/repo. Can be repeated.")
    parser.add_argument("--org", action="append", help="Restrict to organization. Can be repeated.")
    parser.add_argument("--user", action="append", help="Restrict to user-owned repos. Can be repeated.")
    parser.add_argument("--initial-window-days", type=int, default=92, help="Initial query window size")
    parser.add_argument("--split-threshold", type=int, default=900, help="Split windows above this total_count")
    parser.add_argument("--max-count", type=int, help="Maximum new records to export, useful for testing")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximum pages per leaf window")
    parser.add_argument("--per-page", type=int, default=100, help="Search results per page, max 100")
    parser.add_argument("--max-files", type=int, default=200, help="Maximum files to keep per commit")
    parser.add_argument("--patch-lines", type=int, default=80, help="Patch lines to keep per file")
    parser.add_argument("--replace", action="store_true", help="Replace the output file before exporting")
    export(parser.parse_args())


if __name__ == "__main__":
    main()
