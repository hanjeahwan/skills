#!/usr/bin/env python3
"""Initialize a private self-context ledger outside the installed skill folder."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path

from ledger_paths import resolve_ledger_path, skill_root


DIRS = [
    "events",
    "sources",
    "derived",
    "exports",
]


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def init_ledger(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in DIRS:
        (path / child).mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    write_if_missing(
        path / "README.md",
        f"# Self Context Ledger\n\nInitialized: {now}\n\nPrivate user source material and distilled memory live here, not in the installed skill directory.\n",
    )
    write_if_missing(path / "events" / "inbox.md", "# Event Inbox\n\n")

    for jsonl in [
        path / "events" / "processed.jsonl",
        path / "sources" / "git.jsonl",
        path / "sources" / "github_pr_activity.jsonl",
        path / "sources" / "github_pr_reviews.jsonl",
        path / "sources" / "github_authority_signals.jsonl",
        path / "sources" / "jira.jsonl",
        path / "sources" / "jira_comments.jsonl",
        path / "sources" / "jira_changelog.jsonl",
        path / "sources" / "manual.jsonl",
        path / "sources" / "code_style.jsonl",
        path / "derived" / "memory_atoms.jsonl",
        path / "derived" / "context_packs.jsonl",
        path / "derived" / "provenance_links.jsonl",
        path / "derived" / "memory_graph_edges.jsonl",
    ]:
        write_if_missing(jsonl, "")

    assets = skill_root() / "assets"
    for name in ["self-context.schema.json", "sqlite-schema.sql"]:
        src = assets / name
        if src.exists():
            dst = path / name
            if not dst.exists():
                shutil.copyfile(src, dst)

    print(f"initialized self-context ledger at {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    args = parser.parse_args()
    init_ledger(resolve_ledger_path(args.ledger))


if __name__ == "__main__":
    main()
