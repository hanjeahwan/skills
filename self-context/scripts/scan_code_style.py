#!/usr/bin/env python3
"""Scan a local repository for code-style signals and representative examples."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ledger_paths import resolve_ledger_path


EXCLUDED_DIRS = {
    ".angular",
    ".git",
    ".next",
    ".turbo",
    ".vercel",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "out",
    "tmp",
}

CONFIG_NAMES = {
    "package.json",
    "tsconfig.json",
    "tsconfig.base.json",
    "angular.json",
    "nx.json",
    "turbo.json",
    "vite.config.ts",
    "vite.config.js",
    "next.config.ts",
    "next.config.js",
    "eslint.config.js",
    "eslint.config.mjs",
    ".eslintrc",
    ".eslintrc.json",
    ".eslintrc.js",
    ".prettierrc",
    ".prettierrc.json",
    "prettier.config.js",
    "prettier.config.mjs",
    "jest.config.ts",
    "jest.config.js",
    "vitest.config.ts",
    "vitest.config.js",
    "playwright.config.ts",
    "playwright.config.js",
    "cypress.config.ts",
    "cypress.config.js",
    "tailwind.config.ts",
    "tailwind.config.js",
}

CODE_SUFFIXES = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".vue",
    ".svelte",
    ".html",
    ".scss",
    ".css",
}

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)(\s*[:=]\s*)[\"']?[^\"'\s,}]+"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{20,}"),
]

DEPENDENCY_GROUPS = {
    "framework": [
        "@angular/core",
        "react",
        "next",
        "vue",
        "svelte",
        "vite",
    ],
    "state": [
        "@ngrx/store",
        "zustand",
        "redux",
        "@reduxjs/toolkit",
        "jotai",
        "recoil",
        "mobx",
        "rxjs",
    ],
    "data_fetching": [
        "swr",
        "@tanstack/react-query",
        "react-query",
        "apollo-client",
        "@apollo/client",
        "graphql",
        "axios",
    ],
    "forms_validation": [
        "react-hook-form",
        "formik",
        "zod",
        "yup",
        "class-validator",
    ],
    "ui": [
        "@mui/material",
        "antd",
        "tailwindcss",
        "styled-components",
        "@emotion/react",
        "framer-motion",
    ],
    "testing": [
        "jest",
        "vitest",
        "@testing-library/react",
        "@testing-library/angular",
        "playwright",
        "cypress",
    ],
    "quality": [
        "eslint",
        "prettier",
        "typescript",
        "husky",
        "lint-staged",
        "commitlint",
    ],
    "build_release": [
        "semantic-release",
        "nx",
        "turbo",
        "webpack",
        "rollup",
        "esbuild",
    ],
}

PATTERN_REGEXES = {
    "react_component": re.compile(r"\bfunction\s+[A-Z][A-Za-z0-9_]*\s*\(|\bconst\s+[A-Z][A-Za-z0-9_]*\s*[:=][^\n]*=>|React\.FC\b"),
    "react_hook": re.compile(r"\buse[A-Z][A-Za-z0-9_]*\s*\("),
    "angular_component": re.compile(r"@Component\s*\("),
    "angular_service": re.compile(r"@Injectable\s*\("),
    "rxjs": re.compile(r"\bObservable\b|\bpipe\s*\(|\bswitchMap\b|\bcombineLatest\b"),
    "zustand": re.compile(r"\bcreate\s*<|\bcreate\s*\("),
    "swr": re.compile(r"\buseSWR\b"),
    "react_query": re.compile(r"\buseQuery\b|\buseMutation\b"),
    "api_client": re.compile(r"\baxios\b|\bfetch\s*\(|\bHttpClient\b"),
    "schema_validation": re.compile(r"\bz\.object\b|\byup\.object\b"),
    "unit_test": re.compile(r"\bdescribe\s*\(|\bit\s*\(|\btest\s*\("),
    "e2e_test": re.compile(r"\bpage\.goto\b|\bcy\.visit\b"),
    "accessibility": re.compile(r"\baria-[a-z-]+|role=[\"']"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def redact(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(lambda match: f"{match.group(1)}{match.group(2) if match.lastindex and match.lastindex >= 2 else ''}<REDACTED>", text)
    return text


def run_git(repo: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def is_git_repo(repo: Path) -> bool:
    return bool(run_git(repo, ["rev-parse", "--is-inside-work-tree"]))


def git_root(repo: Path) -> Path:
    root = run_git(repo, ["rev-parse", "--show-toplevel"])
    return Path(root).resolve() if root else repo.resolve()


def normalize_remote(remote: str) -> str:
    remote = remote.strip()
    if not remote:
        return ""
    remote = remote.removesuffix(".git")
    match = re.search(r"[:/]([^/:]+/[^/]+)$", remote)
    if match:
        return match.group(1).lower()
    return stable_hash(remote, 12)


def repo_identity(repo: Path) -> dict[str, str]:
    remote = run_git(repo, ["config", "--get", "remote.origin.url"])
    slug = normalize_remote(remote)
    if not slug:
        slug = f"{repo.name.lower()}-{stable_hash(str(repo.resolve()), 8)}"
    branch = run_git(repo, ["branch", "--show-current"])
    head = run_git(repo, ["rev-parse", "--short=12", "HEAD"])
    return {
        "slug": slug.replace("\\", "/"),
        "remote": remote,
        "branch": branch,
        "head": head,
        "path": str(repo),
    }


def should_skip_path(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def list_repo_files(repo: Path) -> list[Path]:
    tracked = run_git(repo, ["ls-files", "--cached", "--others", "--exclude-standard"])
    files: list[Path] = []
    if tracked:
        for line in tracked.splitlines():
            if not line.strip():
                continue
            path = repo / line
            if path.is_file() and not should_skip_path(path.relative_to(repo)):
                files.append(path)
        return files

    for path in repo.rglob("*"):
        if path.is_file() and not should_skip_path(path.relative_to(repo)):
            files.append(path)
    return files


def read_text(path: Path, max_chars: int = 120_000) -> str:
    if path.stat().st_size > max_chars:
        return ""
    try:
        return redact(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return ""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def relative(repo: Path, path: Path) -> str:
    return path.relative_to(repo).as_posix()


def source_id(repo_slug: str, category: str, key: str) -> str:
    return f"{repo_slug}:{category}:{key}"


def record(
    *,
    repo: Path,
    repo_info: dict[str, str],
    category: str,
    key: str,
    title: str,
    summary: str,
    raw_excerpt: dict[str, Any],
    tags: list[str],
    url_or_path: str,
    occurred_at: str,
    ingested_at: str,
) -> dict[str, Any]:
    sid = source_id(repo_info["slug"], category, key)
    return {
        "id": f"code_style_signal:{stable_hash(sid, 24)}",
        "source_type": "code_style_signal",
        "source_id": sid,
        "occurred_at": occurred_at,
        "title": title,
        "summary": summary,
        "url_or_path": url_or_path,
        "raw_excerpt": {
            "repo": repo_info,
            "category": category,
            **raw_excerpt,
        },
        "tags": ["code_style", f"repo:{repo_info['slug']}", category, *tags],
        "ingested_at": ingested_at,
    }


def package_signal(repo: Path, repo_info: dict[str, str], ingested_at: str) -> dict[str, Any] | None:
    path = repo / "package.json"
    data = load_json(path)
    if not isinstance(data, dict):
        return None

    deps = {}
    for key in ["dependencies", "devDependencies", "peerDependencies"]:
        if isinstance(data.get(key), dict):
            deps.update(data[key])

    matched: dict[str, list[str]] = {}
    for group, names in DEPENDENCY_GROUPS.items():
        found = [name for name in names if name in deps]
        if found:
            matched[group] = found

    scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
    selected_scripts = {
        key: scripts[key]
        for key in sorted(scripts)
        if any(token in key.lower() for token in ["build", "test", "lint", "format", "type", "release", "deploy"])
    }
    summary = "Package scripts and dependencies define the repository's frontend stack, quality gates, and build workflow."
    return record(
        repo=repo,
        repo_info=repo_info,
        category="package",
        key="package.json",
        title=f"Code style package profile for {repo_info['slug']}",
        summary=summary,
        raw_excerpt={
            "path": "package.json",
            "package_manager": data.get("packageManager", ""),
            "engines": data.get("engines", {}),
            "scripts": selected_scripts,
            "dependency_groups": matched,
        },
        tags=["package", "dependencies", "scripts"],
        url_or_path=str(path),
        occurred_at=ingested_at,
        ingested_at=ingested_at,
    )


def config_records(repo: Path, repo_info: dict[str, str], files: list[Path], ingested_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(files, key=lambda item: relative(repo, item)):
        rel = relative(repo, path)
        name = path.name
        is_workflow = rel.startswith(".github/workflows/") and path.suffix.lower() in {".yml", ".yaml"}
        if name not in CONFIG_NAMES and not is_workflow:
            continue
        text = read_text(path, max_chars=80_000)
        if not text:
            continue
        excerpt = text[:3500]
        category = "cicd_config" if is_workflow else "tooling_config"
        rows.append(
            record(
                repo=repo,
                repo_info=repo_info,
                category=category,
                key=rel,
                title=f"Repository config: {rel}",
                summary=f"Configuration file used by the repository: {rel}",
                raw_excerpt={
                    "path": rel,
                    "line_count": text.count("\n") + 1,
                    "excerpt": excerpt,
                },
                tags=["config", path.suffix.lstrip(".") or "config"],
                url_or_path=str(path),
                occurred_at=ingested_at,
                ingested_at=ingested_at,
            )
        )
    return rows


def classify_code_file(rel: str) -> str:
    lower = rel.lower()
    name = Path(rel).name.lower()
    if any(token in lower for token in [".spec.", ".test.", "__tests__", "/tests/"]):
        return "test"
    if "playwright" in lower or "cypress" in lower or "/e2e/" in lower:
        return "e2e"
    if ".component." in name or "/components/" in lower:
        return "component"
    if ".service." in name or "/services/" in lower or "/api/" in lower:
        return "service"
    if ".store." in name or "/store/" in lower or "/stores/" in lower:
        return "state"
    if name.startswith("use") or "/hooks/" in lower:
        return "hook"
    if "/pages/" in lower or "/routes/" in lower or "/app/" in lower:
        return "route"
    if "/utils/" in lower or "/helpers/" in lower or "/lib/" in lower:
        return "utility"
    if path_suffix(rel) in {".css", ".scss"}:
        return "style"
    return "source"


def path_suffix(rel: str) -> str:
    return Path(rel).suffix.lower()


def detect_patterns(text: str) -> dict[str, int]:
    return {name: len(pattern.findall(text)) for name, pattern in PATTERN_REGEXES.items() if pattern.search(text)}


def authored_path_counts(repo: Path, author: str | None, max_commits: int) -> tuple[Counter[str], list[dict[str, str]]]:
    if not author:
        return Counter(), []
    output = run_git(
        repo,
        [
            "log",
            f"--author={author}",
            f"--max-count={max_commits}",
            "--date=short",
            "--name-only",
            "--format=commit:%H%x09%ad%x09%s",
        ],
    )
    counts: Counter[str] = Counter()
    commits: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in output.splitlines():
        if line.startswith("commit:"):
            parts = line.removeprefix("commit:").split("\t", 2)
            current = {
                "hash": parts[0] if len(parts) > 0 else "",
                "date": parts[1] if len(parts) > 1 else "",
                "title": parts[2] if len(parts) > 2 else "",
            }
            commits.append(current)
            continue
        if line.strip() and not line.startswith("commit:"):
            counts[line.strip()] += 1
    return counts, commits[:40]


def score_file(rel: str, kind: str, patterns: dict[str, int], authored_counts: Counter[str]) -> int:
    score = 0
    kind_weights = {
        "component": 14,
        "service": 14,
        "state": 13,
        "hook": 12,
        "route": 11,
        "test": 10,
        "e2e": 10,
        "utility": 8,
        "style": 5,
        "source": 4,
    }
    score += kind_weights.get(kind, 4)
    score += min(sum(patterns.values()), 20)
    score += min(authored_counts.get(rel, 0) * 3, 18)
    if rel.startswith(("src/", "app/", "packages/", "libs/")):
        score += 4
    if len(rel.split("/")) <= 5:
        score += 2
    return score


def representative_code_records(
    repo: Path,
    repo_info: dict[str, str],
    files: list[Path],
    authored_counts: Counter[str],
    max_files: int,
    max_example_chars: int,
    ingested_at: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates: list[tuple[int, str, str, dict[str, int], str, int]] = []
    extension_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    pattern_counts: Counter[str] = Counter()

    for path in files:
        rel = relative(repo, path)
        suffix = path.suffix.lower()
        if suffix not in CODE_SUFFIXES:
            continue
        if path.stat().st_size > 180_000:
            continue
        text = read_text(path, max_chars=180_000)
        if not text.strip():
            continue
        kind = classify_code_file(rel)
        patterns = detect_patterns(text)
        extension_counts[suffix] += 1
        kind_counts[kind] += 1
        pattern_counts.update(patterns)
        candidates.append((score_file(rel, kind, patterns, authored_counts), rel, kind, patterns, text, path.stat().st_size))

    by_kind: dict[str, list[tuple[int, str, str, dict[str, int], str, int]]] = defaultdict(list)
    for item in sorted(candidates, key=lambda row: (-row[0], row[1])):
        by_kind[item[2]].append(item)

    selected: list[tuple[int, str, str, dict[str, int], str, int]] = []
    for kind in ["component", "service", "state", "hook", "route", "test", "e2e", "utility", "style", "source"]:
        selected.extend(by_kind.get(kind, [])[:2])
    selected = sorted(selected, key=lambda row: (-row[0], row[1]))[:max_files]

    rows: list[dict[str, Any]] = []
    for score, rel, kind, patterns, text, size in selected:
        line_count = text.count("\n") + 1
        excerpt = text[:max_example_chars].rstrip()
        rows.append(
            record(
                repo=repo,
                repo_info=repo_info,
                category="code_example",
                key=rel,
                title=f"Representative {kind} code example: {rel}",
                summary=f"Representative {kind} file selected from repository structure, pattern signals, and authored history.",
                raw_excerpt={
                    "path": rel,
                    "kind": kind,
                    "language": path_suffix(rel).lstrip("."),
                    "line_count": line_count,
                    "size_bytes": size,
                    "selection_score": score,
                    "authored_touch_count": authored_counts.get(rel, 0),
                    "patterns": patterns,
                    "excerpt": excerpt,
                },
                tags=["code_example", kind, path_suffix(rel).lstrip(".")],
                url_or_path=str(repo / rel),
                occurred_at=ingested_at,
                ingested_at=ingested_at,
            )
        )

    stats = {
        "extension_counts": dict(extension_counts.most_common()),
        "kind_counts": dict(kind_counts.most_common()),
        "pattern_counts": dict(pattern_counts.most_common()),
        "candidate_count": len(candidates),
        "selected_count": len(rows),
    }
    return rows, stats


def architecture_record(
    repo: Path,
    repo_info: dict[str, str],
    files: list[Path],
    stats: dict[str, Any],
    authored_counts: Counter[str],
    authored_commits: list[dict[str, str]],
    author: str | None,
    ingested_at: str,
) -> dict[str, Any]:
    top_dirs: Counter[str] = Counter()
    code_dirs: Counter[str] = Counter()
    for path in files:
        rel = relative(repo, path)
        parts = rel.split("/")
        if parts:
            top_dirs[parts[0]] += 1
        if path.suffix.lower() in CODE_SUFFIXES and len(parts) > 1:
            code_dirs["/".join(parts[:2])] += 1

    raw = {
        "top_directories": dict(top_dirs.most_common(30)),
        "code_directories": dict(code_dirs.most_common(40)),
        "code_stats": stats,
        "author": author or "",
        "authored_top_paths": dict(authored_counts.most_common(40)),
        "authored_recent_commits": authored_commits,
    }
    return record(
        repo=repo,
        repo_info=repo_info,
        category="architecture",
        key="repository-structure",
        title=f"Repository architecture map for {repo_info['slug']}",
        summary="Directory, file-kind, pattern, and authored-history map for extracting coding conventions.",
        raw_excerpt=raw,
        tags=["architecture", "structure", "patterns"],
        url_or_path=str(repo),
        occurred_at=ingested_at,
        ingested_at=ingested_at,
    )


def read_existing_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def merge_rows(path: Path, repo_slug: str, new_rows: list[dict[str, Any]]) -> tuple[int, int]:
    existing = read_existing_jsonl(path)
    prefix = f"{repo_slug}:"
    kept = [
        row
        for row in existing
        if not (row.get("source_type") == "code_style_signal" and str(row.get("source_id", "")).startswith(prefix))
    ]
    by_id = {row["id"]: row for row in [*kept, *new_rows]}
    merged = sorted(by_id.values(), key=lambda row: (row.get("source_id", ""), row.get("id", "")))
    write_jsonl(path, merged)
    return len(existing) - len(kept), len(merged)


def rows_for_repo(rows: list[dict[str, Any]], repo_slug: str) -> list[dict[str, Any]]:
    prefix = f"{repo_slug}:"
    return [row for row in rows if str(row.get("source_id", "")).startswith(prefix)]


def summarize_dependency_groups(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    groups: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        raw = row.get("raw_excerpt") or {}
        for group, values in (raw.get("dependency_groups") or {}).items():
            for value in values:
                groups[group].add(str(value))
    return {key: sorted(values) for key, values in sorted(groups.items())}


def collect_pattern_counts(rows: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        raw = row.get("raw_excerpt") or {}
        if raw.get("category") == "architecture":
            counts.update((raw.get("code_stats") or {}).get("pattern_counts") or {})
        if raw.get("category") == "code_example":
            counts.update(raw.get("patterns") or {})
    return counts


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|")


def build_repo_profile(repo_slug: str, rows: list[dict[str, Any]], generated_at: str) -> str:
    deps = summarize_dependency_groups(rows)
    patterns = collect_pattern_counts(rows)
    examples = [row for row in rows if (row.get("raw_excerpt") or {}).get("category") == "code_example"]
    configs = [row for row in rows if (row.get("raw_excerpt") or {}).get("category") in {"tooling_config", "cicd_config", "package"}]
    architecture = next((row for row in rows if (row.get("raw_excerpt") or {}).get("category") == "architecture"), None)

    lines = [
        f"# Coding Standards Profile: {repo_slug}",
        "",
        f"Generated: {generated_at}",
        "",
        "## Evidence Scope",
        "",
        f"- Repo: `{repo_slug}`",
        f"- Code-style evidence records: {len(rows)}",
        f"- Config records: {len(configs)}",
        f"- Representative code examples: {len(examples)}",
        "",
        "## Stack And Tooling Signals",
        "",
    ]
    if deps:
        for group, values in deps.items():
            lines.append(f"- {group}: {', '.join(f'`{value}`' for value in values)}")
    else:
        lines.append("- No package dependency profile was detected.")

    lines.extend(["", "## Architecture And Patterns", ""])
    if architecture:
        raw = architecture.get("raw_excerpt") or {}
        code_stats = raw.get("code_stats") or {}
        for key, values in [
            ("File kinds", code_stats.get("kind_counts") or {}),
            ("Pattern counts", code_stats.get("pattern_counts") or {}),
            ("Authored top paths", raw.get("authored_top_paths") or {}),
        ]:
            if values:
                compact = ", ".join(f"{name}={count}" for name, count in list(values.items())[:16])
                lines.append(f"- {key}: {compact}")
        lines.append(f"- Evidence: `{architecture.get('id')}`")
    else:
        lines.append("- No architecture record was detected.")

    lines.extend(["", "## Agent Coding Guidance", ""])
    guidance = []
    if any(name in deps.get("framework", []) for name in ["react", "next"]):
        guidance.append("Use existing React/Next component, hook, routing, and test conventions from representative files before introducing new structure.")
    if "@angular/core" in deps.get("framework", []):
        guidance.append("Use existing Angular component/service/module conventions and RxJS patterns from representative files.")
    if patterns.get("api_client"):
        guidance.append("Follow established API client and data-fetching wrappers instead of creating ad hoc request code.")
    if patterns.get("schema_validation"):
        guidance.append("Preserve the repo's schema validation approach when adding forms or API boundaries.")
    if patterns.get("unit_test") or patterns.get("e2e_test"):
        guidance.append("Mirror existing test file structure and assertion style when adding behavior.")
    if not guidance:
        guidance.append("Read the cited representative files and match their naming, imports, error handling, and module boundaries.")
    lines.extend(f"- {item}" for item in guidance)

    lines.extend(["", "## Representative Examples", ""])
    if examples:
        lines.append("| Kind | Path | Evidence | Pattern Signals |")
        lines.append("| --- | --- | --- | --- |")
        for row in examples[:40]:
            raw = row.get("raw_excerpt") or {}
            pattern_text = ", ".join(f"{name}={count}" for name, count in (raw.get("patterns") or {}).items()) or "none"
            lines.append(
                f"| {markdown_escape(str(raw.get('kind', '')))} | `{markdown_escape(str(raw.get('path', '')))}` | `{row.get('id')}` | {markdown_escape(pattern_text)} |"
            )
    else:
        lines.append("No representative code examples were selected.")

    lines.extend(["", "## Config Evidence", ""])
    for row in configs[:40]:
        raw = row.get("raw_excerpt") or {}
        lines.append(f"- `{raw.get('path', row.get('source_id'))}` -> `{row.get('id')}`")

    lines.append("")
    return "\n".join(lines)


def build_agent_instructions(all_rows: list[dict[str, Any]], generated_at: str) -> str:
    repos = sorted({((row.get("raw_excerpt") or {}).get("repo") or {}).get("slug", "") for row in all_rows})
    repos = [repo for repo in repos if repo]
    lines = [
        "# Agent Coding Instructions",
        "",
        f"Generated: {generated_at}",
        "",
        "Use this profile when writing code for repositories that have been scanned into the private evidence ledger.",
        "",
        "## Operating Rules",
        "",
        "- Query `code_style` evidence before writing non-trivial code.",
        "- Match existing component, service, hook, state, API, validation, and test patterns from cited examples.",
        "- Prefer repository-local tooling and scripts discovered from package/config records.",
        "- Do not infer company-wide standards from a single example; cite the repo-specific evidence used.",
        "- If no scanned evidence exists for the target repo, scan the repo before claiming to follow the user's style.",
        "",
        "## Scanned Repositories",
        "",
    ]
    if repos:
        for repo in repos:
            rows = [row for row in all_rows if (((row.get("raw_excerpt") or {}).get("repo") or {}).get("slug") == repo)]
            lines.append(f"- `{repo}`: {len(rows)} code-style records")
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def write_profiles(ledger: Path, repo_slug: str, all_rows: list[dict[str, Any]], generated_at: str) -> None:
    repo_rows = rows_for_repo(all_rows, repo_slug)
    profile_dir = ledger / "profiles" / "code-style"
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / f"{repo_slug.replace('/', '__')}.md").write_text(
        build_repo_profile(repo_slug, repo_rows, generated_at),
        encoding="utf-8",
    )

    aggregate_lines = [
        "# Coding Standards Profile",
        "",
        f"Generated: {generated_at}",
        "",
        "This aggregate profile is generated from `sources/code_style.jsonl`.",
        "",
    ]
    repos = sorted({((row.get("raw_excerpt") or {}).get("repo") or {}).get("slug", "") for row in all_rows})
    for repo in [item for item in repos if item]:
        aggregate_lines.append(f"## {repo}")
        aggregate_lines.append("")
        aggregate_lines.append(build_repo_profile(repo, rows_for_repo(all_rows, repo), generated_at))
        aggregate_lines.append("")
    (ledger / "profiles" / "coding-standards-profile.md").write_text("\n".join(aggregate_lines), encoding="utf-8")
    (ledger / "profiles" / "agent-coding-instructions.md").write_text(
        build_agent_instructions(all_rows, generated_at),
        encoding="utf-8",
    )


def scan(repo: Path, ledger: Path, author: str | None, max_files: int, max_example_chars: int, max_commits: int) -> dict[str, Any]:
    if not repo.exists() or not repo.is_dir():
        raise SystemExit(f"repo does not exist or is not a directory: {repo}")
    repo = git_root(repo) if is_git_repo(repo) else repo.resolve()
    repo_info = repo_identity(repo)
    generated_at = now_iso()
    files = list_repo_files(repo)

    authored_counts, authored_commits = authored_path_counts(repo, author, max_commits)
    rows: list[dict[str, Any]] = []
    package = package_signal(repo, repo_info, generated_at)
    if package:
        rows.append(package)
    rows.extend(config_records(repo, repo_info, files, generated_at))
    code_rows, stats = representative_code_records(
        repo,
        repo_info,
        files,
        authored_counts,
        max_files=max_files,
        max_example_chars=max_example_chars,
        ingested_at=generated_at,
    )
    rows.append(architecture_record(repo, repo_info, files, stats, authored_counts, authored_commits, author, generated_at))
    rows.extend(code_rows)

    out = ledger / "sources" / "code_style.jsonl"
    replaced, total = merge_rows(out, repo_info["slug"], rows)
    all_rows = read_existing_jsonl(out)
    write_profiles(ledger, repo_info["slug"], all_rows, generated_at)
    return {
        "repo": repo_info,
        "ledger": str(ledger),
        "out": str(out),
        "records_written_for_repo": len(rows),
        "records_replaced_for_repo": replaced,
        "total_code_style_records": total,
        "profile": str(ledger / "profiles" / "coding-standards-profile.md"),
        "repo_profile": str(ledger / "profiles" / "code-style" / f"{repo_info['slug'].replace('/', '__')}.md"),
        "agent_instructions": str(ledger / "profiles" / "agent-coding-instructions.md"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Local repository path to scan.")
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--author", help="Optional git author filter used to boost user-authored examples.")
    parser.add_argument("--max-files", type=int, default=36, help="Maximum representative code files to store.")
    parser.add_argument("--max-example-chars", type=int, default=7000, help="Maximum characters per code excerpt.")
    parser.add_argument("--max-commits", type=int, default=1200, help="Maximum authored commits to inspect for path weighting.")
    parser.add_argument("--json", action="store_true", help="Print JSON result.")
    args = parser.parse_args()

    result = scan(
        Path(args.repo).expanduser().resolve(),
        resolve_ledger_path(args.ledger),
        args.author,
        max_files=args.max_files,
        max_example_chars=args.max_example_chars,
        max_commits=args.max_commits,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(
            " ".join(
                [
                    f"records_written_for_repo={result['records_written_for_repo']}",
                    f"records_replaced_for_repo={result['records_replaced_for_repo']}",
                    f"total_code_style_records={result['total_code_style_records']}",
                    f"out={result['out']}",
                ]
            )
        )


if __name__ == "__main__":
    main()
