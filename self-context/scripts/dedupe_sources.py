#!/usr/bin/env python3
"""Remove duplicate JSONL records by id while preserving first occurrence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def dedupe(path: Path, dry_run: bool) -> tuple[int, int]:
    rows: list[str] = []
    seen: set[str] = set()
    duplicates = 0

    for line in path.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        row = json.loads(line)
        row_id = row.get("id")
        if row_id in seen:
            duplicates += 1
            continue
        if row_id:
            seen.add(row_id)
        rows.append(json.dumps(row, ensure_ascii=False))

    if not dry_run:
        path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")

    return len(rows), duplicates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="JSONL files to deduplicate")
    parser.add_argument("--dry-run", action="store_true", help="Report duplicates without rewriting files")
    args = parser.parse_args()

    for raw_path in args.paths:
        path = Path(raw_path).resolve()
        kept, duplicates = dedupe(path, args.dry_run)
        print(f"{path}: kept={kept} duplicates={duplicates}")


if __name__ == "__main__":
    main()
