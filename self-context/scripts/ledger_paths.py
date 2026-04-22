"""Shared path helpers for self-context ledger scripts."""

from __future__ import annotations

import os
from pathlib import Path


def default_ledger_path() -> Path:
    override = os.environ.get("SELF_CONTEXT_HOME")
    if override:
        return Path(override).expanduser().resolve()

    return (Path.home() / ".self-context" / "ledger").resolve()


def resolve_ledger_path(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return default_ledger_path()


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]
