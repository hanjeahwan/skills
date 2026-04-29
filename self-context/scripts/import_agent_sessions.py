#!/usr/bin/env python3
"""Import redacted agent-session patterns into the self-context ledger."""

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


MAX_PROMPTS_PER_PROVIDER = 900
MAX_ROWS_PER_PROVIDER = 40

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"ATATT[A-Za-z0-9_\-=]{20,}"),
    re.compile(r"(?i)\b(?:pss|pass|password|pwd|api[_-]?key|token|secret)\s*=\s*[^\s,;]+"),
    re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"),
]
WINDOWS_PATH_RE = re.compile(r"(?<![A-Za-z])[A-Za-z]:(?:\\+|/+)[^\s\"'<>|]+")
RELATIVE_PATH_RE = re.compile(r"\b(?:[\w.-]+(?:\\|/)+){2,}[\w.-]+")
URL_RE = re.compile(r"https?://([A-Za-z0-9.\-]+)(?:/[^\s\"'<>]*)?")

SIGNAL_RULES = {
    "implementation": ["implement", "execute", "执行", "继续", "build", "make", "add", "update", "fix", "迁移"],
    "verification": ["test", "check", "validate", "verify", "run", "验证", "测试", "检查", "通过"],
    "architecture": ["plan", "architecture", "design", "refactor", "架构", "重构", "方案", "计划"],
    "agent_tooling": ["mcp", "agent", "codex", "claude", "cursor", "skill", "rag", "subagent", "tool"],
    "frontend_ui": ["react", "angular", "next", "ui", "figma", "component", "frontend", "前端", "页面"],
    "product_quality": ["production", "prod", "quality", "stable", "gate", "eval", "benchmark", "稳定", "生产"],
    "career_profile": ["resume", "linkedin", "recruiter", "hire", "profile", "job", "简历", "找工作"],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def redact_text(text: str) -> str:
    redacted = str(text or "")
    redacted = URL_RE.sub(lambda match: f"[url:{match.group(1)}]", redacted)
    redacted = WINDOWS_PATH_RE.sub("[local-path]", redacted)
    redacted = RELATIVE_PATH_RE.sub("[local-path]", redacted)
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[redacted]", redacted)
    redacted = " ".join(redacted.replace("\n", " ").split())
    return redacted[:420]


def epoch_to_iso(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return now_iso()
    if number > 10_000_000_000:
        number = number / 1000
    return datetime.fromtimestamp(number, timezone.utc).isoformat()


def classify(text: str) -> list[str]:
    lowered = text.lower()
    signals = []
    for signal, terms in SIGNAL_RULES.items():
        if any(term in lowered for term in terms):
            signals.append(signal)
    return signals


def load_codex_prompts(home: Path) -> list[dict[str, Any]]:
    rows = []
    for row in read_jsonl(home / ".codex" / "history.jsonl")[:MAX_PROMPTS_PER_PROVIDER]:
        text = redact_text(str(row.get("text", "")))
        if len(text) < 12:
            continue
        rows.append(
            {
                "provider": "codex",
                "session_id": str(row.get("session_id", "")),
                "occurred_at": epoch_to_iso(row.get("ts")),
                "text": text,
            }
        )
    return rows


def load_claude_prompts(home: Path) -> list[dict[str, Any]]:
    raw_rows = read_jsonl(home / ".claude" / "history.jsonl")
    rows = []
    for row in raw_rows[-MAX_PROMPTS_PER_PROVIDER:]:
        text = redact_text(str(row.get("display", "")))
        if len(text) < 12:
            continue
        rows.append(
            {
                "provider": "claude",
                "session_id": str(row.get("sessionId", "")),
                "occurred_at": epoch_to_iso(row.get("timestamp")),
                "project": redact_text(str(row.get("project", ""))),
                "text": text,
            }
        )
    return rows


def source_row(provider: str, session_id: str, prompts: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    signal_counts: Counter[str] = Counter()
    snippets = []
    projects: Counter[str] = Counter()
    occurred_at = prompts[0].get("occurred_at") or generated_at
    for prompt in prompts:
        text = str(prompt.get("text", ""))
        signal_counts.update(classify(text))
        project = str(prompt.get("project", ""))
        if project:
            projects[project] += 1
        if len(snippets) < 6 and any(signal in classify(text) for signal in ["verification", "architecture", "agent_tooling", "product_quality"]):
            snippets.append(text)
    session_hash = stable_hash(f"{provider}:{session_id or prompts[0].get('text', '')}")
    top_signals = [signal for signal, count in signal_counts.most_common(8) if count]
    title_signal = ", ".join(top_signals[:4]) or "agent collaboration"
    return {
        "id": f"agent_session:{provider}:{session_hash}",
        "source_id": f"agent_session:{provider}:{session_hash}",
        "source_type": "agent_session",
        "title": f"Agent session pattern: {provider} {title_signal}",
        "summary": f"Redacted {provider} session history shows collaboration signals around {title_signal}.",
        "occurred_at": occurred_at,
        "ingested_at": generated_at,
        "url_or_path": provider,
        "tags": sorted({"agent_sessions", "agent_collaboration", "work_style", *top_signals}),
        "topics": sorted({"agent_sessions", "agent_collaboration", "work_style", *top_signals}),
        "confidence": "evidenced",
        "raw_excerpt": {
            "provider": provider,
            "session_hash": session_hash,
            "prompt_count": len(prompts),
            "signal_counts": dict(signal_counts.most_common()),
            "project_hints": [project for project, _ in projects.most_common(5)],
            "representative_user_requests": snippets,
            "collaboration_guidance": [
                "Expect iterative execution with frequent validation, not just planning.",
                "Keep proof, tests, production gates, and concrete file changes visible.",
                "Redact secrets, local paths, and private transcript content before using session evidence.",
            ],
            "guardrails": [
                "Do not expose raw prompts, session ids, local paths, tokens, or private third-party content by default.",
                "Do not infer personal-life preferences from work-agent sessions.",
            ],
        },
    }


def build_rows(prompts: list[dict[str, Any]], generated_at: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for prompt in prompts:
        provider = str(prompt.get("provider", "unknown"))
        session_id = str(prompt.get("session_id", "")) or stable_hash(str(prompt.get("text", "")), 12)
        grouped[(provider, session_id)].append(prompt)

    rows = []
    provider_counts: Counter[str] = Counter()
    for (provider, session_id), session_prompts in sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True):
        if provider_counts[provider] >= MAX_ROWS_PER_PROVIDER:
            continue
        if not any(classify(str(prompt.get("text", ""))) for prompt in session_prompts):
            continue
        rows.append(source_row(provider, session_id, session_prompts, generated_at))
        provider_counts[provider] += 1
    return rows


def import_sessions(ledger: Path, home: Path) -> dict[str, Any]:
    generated_at = now_iso()
    prompts = [*load_codex_prompts(home), *load_claude_prompts(home)]
    rows = build_rows(prompts, generated_at)
    target = ledger / "sources" / "agent_sessions.jsonl"
    write_jsonl(target, rows)
    providers = Counter(row["raw_excerpt"]["provider"] for row in rows)
    return {
        "ledger": str(ledger),
        "source_path": str(target),
        "prompt_count": len(prompts),
        "rows": len(rows),
        "providers": dict(providers.most_common()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--home", default=str(Path.home()), help="User home directory containing .codex/.claude.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    summary = import_sessions(resolve_ledger_path(args.ledger), Path(args.home))
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"imported {summary['rows']} agent session rows into {summary['source_path']}")


if __name__ == "__main__":
    main()
