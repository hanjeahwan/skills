#!/usr/bin/env python3
"""Append a manual work event to sources/manual.jsonl."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timezone

from ledger_paths import resolve_ledger_path


def stable_id(title: str, occurred_at: str, action: str) -> str:
    raw = f"{occurred_at}\n{title}\n{action}".encode("utf-8")
    return "manual_event:" + hashlib.sha256(raw).hexdigest()[:16]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Event date")
    parser.add_argument("--title", required=True)
    parser.add_argument("--context", default="")
    parser.add_argument("--problem", default="")
    parser.add_argument("--action", required=True)
    parser.add_argument("--result", default="")
    parser.add_argument("--technologies", default="")
    parser.add_argument("--impact", default="")
    parser.add_argument("--links", default="")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    ledger = resolve_ledger_path(args.ledger)
    path = ledger / "sources" / "manual.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)

    row = {
        "id": stable_id(args.title, args.date, args.action),
        "source_type": "manual_event",
        "source_id": stable_id(args.title, args.date, args.action).removeprefix("manual_event:"),
        "occurred_at": args.date,
        "title": args.title,
        "summary": args.action,
        "url_or_path": args.links,
        "raw_excerpt": {
            "context": args.context,
            "problem": args.problem,
            "action": args.action,
            "result": args.result,
            "technologies": args.technologies,
            "impact": args.impact,
            "notes": args.notes,
        },
        "tags": ["manual"],
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }

    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"imported manual event {row['id']} into {path}")


if __name__ == "__main__":
    main()
