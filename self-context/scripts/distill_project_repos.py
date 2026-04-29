#!/usr/bin/env python3
"""Distill local project repositories into project-level self-context sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ledger_paths import resolve_ledger_path


EXCLUDED_DIRS = {
    ".angular",
    ".git",
    ".next",
    ".turbo",
    ".umi",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "tmp",
}

CODE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".html", ".less", ".scss", ".css"}
SYMBOL_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
DOC_SUFFIXES = {".md", ".mdx"}

GENERIC_PATH_PARTS = {
    "__tests__",
    "app",
    "assets",
    "common",
    "components",
    "constants",
    "containers",
    "core",
    "helpers",
    "hooks",
    "index",
    "lib",
    "libs",
    "models",
    "modules",
    "pages",
    "packages",
    "services",
    "shared",
    "src",
    "store",
    "stores",
    "styles",
    "types",
    "utils",
}

STACK_DEPENDENCIES = {
    "angular": ["@angular/core", "@angular/cli", "@angular/forms", "@angular/router"],
    "react": ["react", "react-dom"],
    "nextjs": ["next"],
    "umi": ["@umijs/max", "umi", "umi-presets-pro"],
    "typescript": ["typescript"],
    "rxjs": ["rxjs", "rxjs-etc"],
    "akita": ["@datorama/akita"],
    "tanstack_query": ["@tanstack/angular-query-experimental", "@tanstack/react-query"],
    "antd": ["antd", "ng-zorro-antd", "@ant-design/pro-components"],
    "auth": ["@auth0/auth0-spa-js", "oidc-client-ts", "aws-amplify"],
    "feature_flags": ["unleash-proxy-client", "@unleash/proxy-client-react"],
    "observability": ["@sentry/angular", "@sentry/react", "@sentry/cli"],
    "analytics_reporting": ["@antv/g2", "@antv/data-set", "xlsx", "@looker/embed-sdk"],
    "rich_text": ["@tiptap/starter-kit", "ngx-quill", "quill"],
    "turbo_changesets": ["turbo", "@changesets/cli", "@changesets/changelog-github"],
    "quality_tooling": ["eslint", "prettier", "husky", "lint-staged", "commitlint"],
    "semantic_release": ["semantic-release", "@semantic-release/git", "@semantic-release/npm"],
}

DOMAIN_HINTS = {
    "recruiting_candidate": ["candidate", "talent", "job", "hiring", "assessment", "role-fit", "role_fit", "profile"],
    "employee_learning": ["employee", "learner", "learning", "goal", "action-item", "action_item"],
    "analytics_reporting": ["analytics", "report", "reporting", "dashboard", "chart", "insight", "export", "looker"],
    "admin_operations": ["admin", "console", "framework", "email", "template", "company", "user-details"],
    "auth_permissions": ["auth", "auth0", "cognito", "rbac", "permission", "access-control", "guard"],
    "localization": ["i18n", "transloco", "locale", "translation", "sync-i18n"],
    "web_infra": ["workflow", "gh-actions", "deploy", "semantic-release", "environment", "sentry", "artifact"],
    "ai_agent": ["ai", "agent", "mcp", "prompt", "openai", "gpt"],
}

PATTERN_REGEXES = {
    "angular_component": re.compile(r"@Component\s*\("),
    "angular_service": re.compile(r"@Injectable\s*\("),
    "react_component": re.compile(r"\bfunction\s+[A-Z][A-Za-z0-9_]*\s*\(|\bconst\s+[A-Z][A-Za-z0-9_]*\s*[:=][^\n]*=>"),
    "rxjs_stream": re.compile(r"\bObservable\b|\bpipe\s*\(|\bswitchMap\b|\bcombineLatest\b|\bBehaviorSubject\b"),
    "api_service": re.compile(r"\bHttpClient\b|\baxios\b|\bfetch\s*\("),
    "feature_flag": re.compile(r"\bunleash\b|feature[-_]?flag", re.IGNORECASE),
    "auth_permission": re.compile(r"\bauth0\b|\bcognito\b|\brbac\b|\bpermission\b|\bguard\b", re.IGNORECASE),
    "test_quality": re.compile(r"\bdescribe\s*\(|\bit\s*\(|\btest\s*\("),
}

CLASS_RE = re.compile(r"\bexport\s+(?:abstract\s+)?class\s+([A-Z][A-Za-z0-9_]*)")
FUNCTION_RE = re.compile(r"\bexport\s+(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
CONST_RE = re.compile(r"\bexport\s+const\s+([A-Za-z_][A-Za-z0-9_]*)\s*[:=]")
TYPE_RE = re.compile(r"\bexport\s+(?:interface|type)\s+([A-Z][A-Za-z0-9_]*)")
ROUTE_RE = re.compile(r"\b(?:Routes|RouteObject|createBrowserRouter|path\s*:|redirectTo\s*:)")
STATE_RE = re.compile(r"\b(?:Store|Query|BehaviorSubject|createSlice|createReducer|useReducer|atom|zustand|setState)\b")
IMPORT_RE = re.compile(
    r"(?:import\s+(?:type\s+)?(?:[^'\"]+\s+from\s+)?|export\s+[^'\"]+\s+from\s+|import\s*\()\s*['\"]([^'\"]+)['\"]"
)
REQUIRE_RE = re.compile(r"\brequire\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")
API_METHOD_RE = re.compile(
    r"(?:\b(?:axios|request|http|client|this\.http|httpClient|HttpClient)\s*\.\s*)?"
    r"\b(get|post|put|patch|delete)\s*\(\s*[`'\"]([^`'\"]*)[`'\"]",
    re.IGNORECASE,
)
REQUEST_METHOD_RE = re.compile(r"\bmethod\s*:\s*[`'\"]([A-Z]+)[`'\"]")
ROUTE_PATH_RE = re.compile(r"\bpath\s*:\s*[`'\"]([^`'\"]*)[`'\"]")
ROUTE_COMPONENT_RE = re.compile(r"\bcomponent\s*:\s*([A-Za-z_][A-Za-z0-9_.]*)")
ROUTE_LAZY_RE = re.compile(r"\b(?:loadChildren|loadComponent)\s*:")
ROUTE_GUARD_RE = re.compile(r"\b(?:canActivate|canActivateChild|canLoad|canMatch|access)\s*:")
ROUTE_REDIRECT_RE = re.compile(r"\bredirectTo\s*:")
ROUTER_NAVIGATION_RE = re.compile(r"\b(?:navigate|navigateByUrl|routerLink|useParams|useSearchParams|history\.push)\b")
MENU_NAV_RE = re.compile(r"\b(?:menu|sider|sidebar|breadcrumb|navigation|navItem|NzMenuItem)\b", re.IGNORECASE)
MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,3}\s+(.+?)\s*$", re.MULTILINE)
TEST_SUFFIXES = {".spec.ts", ".spec.tsx", ".test.ts", ".test.tsx", ".spec.js", ".test.js", ".spec.jsx", ".test.jsx"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


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


def git_root(repo: Path) -> Path:
    root = run_git(repo, ["rev-parse", "--show-toplevel"])
    return Path(root).resolve() if root else repo.resolve()


def normalize_remote(remote: str) -> str:
    remote = remote.strip().removesuffix(".git")
    match = re.search(r"[:/]([^/:]+/[^/]+)$", remote)
    if match:
        return match.group(1).lower()
    return ""


def repo_identity(repo: Path) -> dict[str, str]:
    remote = run_git(repo, ["config", "--get", "remote.origin.url"])
    slug = normalize_remote(remote) or f"{repo.name.lower()}-{stable_hash(str(repo), 8)}"
    return {
        "slug": slug.replace("\\", "/"),
        "name": repo.name,
        "remote": remote,
        "branch": run_git(repo, ["branch", "--show-current"]),
        "head": run_git(repo, ["rev-parse", "--short=12", "HEAD"]),
    }


def should_skip(relative_path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in relative_path.parts)


def list_repo_files(repo: Path) -> list[Path]:
    tracked = run_git(repo, ["ls-files", "--cached", "--others", "--exclude-standard"])
    files: list[Path] = []
    if tracked:
        for line in tracked.splitlines():
            relative = Path(line.strip())
            path = repo / relative
            if line.strip() and path.is_file() and not should_skip(relative):
                files.append(path)
        return files

    for path in repo.rglob("*"):
        if path.is_file():
            relative = path.relative_to(repo)
            if not should_skip(relative):
                files.append(path)
    return files


def read_text(path: Path, max_chars: int = 80_000) -> str:
    if not path.exists() or not path.is_file() or path.stat().st_size > max_chars:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(read_text(path, 300_000))
    except json.JSONDecodeError:
        return {}


def package_dependencies(package_json: dict[str, Any]) -> dict[str, str]:
    deps: dict[str, str] = {}
    for key in ["dependencies", "devDependencies", "optionalDependencies", "peerDependencies"]:
        values = package_json.get(key)
        if isinstance(values, dict):
            deps.update({str(name): str(version) for name, version in values.items()})
    return deps


def package_scripts(package_json: dict[str, Any]) -> dict[str, str]:
    scripts = package_json.get("scripts")
    if not isinstance(scripts, dict):
        return {}
    return {str(name): str(value) for name, value in scripts.items()}


def detect_stack(repo: Path, files: list[Path], package_json: dict[str, Any]) -> list[str]:
    deps = package_dependencies(package_json)
    stack: set[str] = set()
    for name, dependency_names in STACK_DEPENDENCIES.items():
        if any(dependency in deps for dependency in dependency_names):
            stack.add(name)

    relative_names = {path.relative_to(repo).as_posix().lower() for path in files}
    if "angular.json" in relative_names:
        stack.add("angular")
    if "turbo.json" in relative_names:
        stack.add("turbo_changesets")
    if any(name.startswith("gh-actions/") or ".github/workflows/" in name for name in relative_names):
        stack.add("github_actions")
    if any(name.startswith("environments/") for name in relative_names):
        stack.add("environment_config")
    if any(name.startswith("cdk/") for name in relative_names):
        stack.add("cdk")
    if any(name.endswith(".tsx") or name.endswith(".jsx") for name in relative_names):
        stack.add("react")
    if any(name.endswith(".ts") for name in relative_names):
        stack.add("typescript")
    return sorted(stack)


def detect_domains(files: list[Path], deps: dict[str, str]) -> list[str]:
    text = " ".join([path.as_posix().lower() for path in files] + list(deps)).lower()
    domains = []
    for domain, hints in DOMAIN_HINTS.items():
        if any(hint in text for hint in hints):
            domains.append(domain)
    return sorted(domains)


def top_level_counts(repo: Path, files: list[Path], limit: int = 12) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for path in files:
        relative = path.relative_to(repo)
        key = relative.parts[0] if relative.parts else relative.as_posix()
        counter[key] += 1
    return [{"name": name, "files": count} for name, count in counter.most_common(limit)]


def extension_counts(files: list[Path], limit: int = 16) -> dict[str, int]:
    counter = Counter(path.suffix.lower() or "<none>" for path in files)
    return dict(counter.most_common(limit))


def important_files(repo: Path, files: list[Path], limit: int = 40) -> list[str]:
    names = []
    for path in files:
        relative = path.relative_to(repo).as_posix()
        lowered = relative.lower()
        if (
            lowered in {"package.json", "angular.json", "turbo.json", "pnpm-workspace.yaml", "readme.md", "contributing.md"}
            or lowered.startswith(".github/workflows/")
            or lowered.startswith("gh-actions/")
            or lowered.startswith("environments/")
            or "auth" in lowered
            or "rbac" in lowered
            or "report" in lowered
            or "candidate" in lowered
            or "framework" in lowered
            or "lookup" in lowered
            or "mcp" in lowered
        ):
            names.append(relative)
        if len(names) >= limit:
            break
    return names


def detected_patterns(repo: Path, files: list[Path]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for path in files:
        relative = path.relative_to(repo)
        lowered = relative.as_posix().lower()
        if relative.suffix.lower() in CODE_SUFFIXES:
            text = read_text(path, 120_000)
            for pattern_name, pattern in PATTERN_REGEXES.items():
                matches = pattern.findall(text)
                if matches:
                    counts[pattern_name] += len(matches)
        if "service" in lowered:
            counts["service_layer_files"] += 1
        if "component" in lowered:
            counts["component_files"] += 1
        if "api" in lowered or "apis" in lowered:
            counts["api_files"] += 1
        if "store" in lowered or "state" in lowered:
            counts["state_files"] += 1
        if "workflow" in lowered or "gh-actions" in lowered or ".github/workflows" in lowered:
            counts["workflow_files"] += 1
        if "environment" in lowered:
            counts["environment_files"] += 1
    return dict(counts.most_common())


def symbol_kind(path: Path, text: str, name: str) -> str:
    lowered = path.as_posix().lower()
    prefix = text[max(0, text.find(name) - 500) : text.find(name) + 500]
    if "@Component" in prefix or lowered.endswith(".component.ts") or ".component." in lowered:
        return "angular_component"
    if "@Injectable" in prefix or lowered.endswith(".service.ts") or ".service." in lowered:
        return "service_layer"
    if name.startswith("use") and len(name) > 3 and name[3:4].isupper():
        return "react_hook"
    if name[:1].isupper() and path.suffix.lower() in {".tsx", ".jsx"}:
        return "react_component"
    if lowered.endswith((".types.ts", ".type.ts", ".interface.ts")):
        return "type_contract"
    if "guard" in lowered or "permission" in lowered or "auth" in lowered:
        return "auth_permission_surface"
    if "api" in lowered or "service" in lowered:
        return "api_service"
    return "exported_symbol"


def symbol_signals(path: Path, text: str) -> list[str]:
    lowered = path.as_posix().lower()
    signals: list[str] = []
    if ROUTE_RE.search(text) or "route" in lowered:
        signals.append("routing")
    if "HttpClient" in text or "axios" in text or "fetch(" in text:
        signals.append("api_boundary")
    if STATE_RE.search(text) or "store" in lowered or "state" in lowered:
        signals.append("state_management")
    if "Observable" in text or ".pipe(" in text or "switchMap" in text:
        signals.append("async_stream")
    if "permission" in lowered or "auth" in lowered or "guard" in lowered or "rbac" in lowered:
        signals.append("auth_permission")
    if ".spec." in lowered or ".test." in lowered:
        signals.append("test")
    if "i18n" in lowered or "locale" in lowered or "translation" in lowered:
        signals.append("localization")
    return signals


def extract_symbols(repo: Path, files: list[Path], limit: int = 120) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    for path in files:
        if path.suffix.lower() not in SYMBOL_SUFFIXES or path.name.endswith(".d.ts"):
            continue
        text = read_text(path, 180_000)
        if not text:
            continue
        relative = path.relative_to(repo).as_posix()
        names = []
        for pattern in [CLASS_RE, FUNCTION_RE, CONST_RE, TYPE_RE]:
            names.extend(match.group(1) for match in pattern.finditer(text))
        if not names and path.suffix.lower() in {".tsx", ".jsx"}:
            names.append(path.stem)
        signals = symbol_signals(Path(relative), text)
        for name in names[:8]:
            kind = symbol_kind(Path(relative), text, name)
            symbols.append(
                {
                    "name": name,
                    "kind": kind,
                    "path": relative,
                    "signals": signals,
                }
            )
            if len(symbols) >= limit:
                return symbols
    return symbols


def symbol_summary(symbols: list[dict[str, Any]], limit: int = 50) -> dict[str, Any]:
    kinds = Counter(str(symbol.get("kind", "")) for symbol in symbols)
    signals = Counter(signal for symbol in symbols for signal in symbol.get("signals", []))
    representative = []
    seen_kinds: Counter[str] = Counter()
    for symbol in symbols:
        kind = str(symbol.get("kind", ""))
        if seen_kinds[kind] >= 8:
            continue
        representative.append(symbol)
        seen_kinds[kind] += 1
        if len(representative) >= limit:
            break
    return {
        "symbol_counts": dict(kinds.most_common()),
        "signal_counts": dict(signals.most_common()),
        "representative_symbols": representative,
    }


def path_domain_tags(text: str) -> list[str]:
    lowered = text.lower()
    tags = []
    for domain, hints in DOMAIN_HINTS.items():
        if any(hint in lowered for hint in hints):
            tags.append(domain)
    return tags


def feature_key(relative: Path) -> str:
    parts = [part.lower() for part in relative.parts[:-1]]
    if not parts:
        return relative.stem.lower()
    for index, part in enumerate(parts):
        if part in {"src", "app", "pages", "modules", "features", "packages", "libs", "environments", "gh-actions"}:
            for candidate in parts[index + 1 : index + 4]:
                normalized = candidate.replace("_", "-")
                if normalized and normalized not in GENERIC_PATH_PARTS:
                    return normalized
    for part in reversed(parts):
        normalized = part.replace("_", "-")
        if normalized and normalized not in GENERIC_PATH_PARTS:
            return normalized
    return parts[-1]


def feature_surfaces(repo: Path, files: list[Path], limit: int = 20) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for path in files:
        relative = path.relative_to(repo)
        if should_skip(relative):
            continue
        lowered = relative.as_posix().lower()
        if path.suffix.lower() not in CODE_SUFFIXES and not lowered.startswith(("environments/", "gh-actions/", ".github/workflows/")):
            continue
        key = feature_key(relative)
        surface = grouped.setdefault(
            key,
            {
                "name": key,
                "files": 0,
                "signals": Counter(),
                "domains": Counter(),
                "representative_paths": [],
            },
        )
        surface["files"] += 1
        for tag in path_domain_tags(lowered):
            surface["domains"][tag] += 1
        if "api" in lowered or "service" in lowered:
            surface["signals"]["api_service"] += 1
        if "component" in lowered or path.suffix.lower() in {".tsx", ".jsx", ".html"}:
            surface["signals"]["ui_surface"] += 1
        if "store" in lowered or "state" in lowered or "query" in lowered:
            surface["signals"]["state_data_flow"] += 1
        if "guard" in lowered or "permission" in lowered or "auth" in lowered:
            surface["signals"]["auth_permission"] += 1
        if ".spec." in lowered or ".test." in lowered:
            surface["signals"]["test_coverage"] += 1
        if "workflow" in lowered or "gh-actions" in lowered or ".github/workflows" in lowered:
            surface["signals"]["ci_cd_workflow"] += 1
        if "environment" in lowered or lowered.startswith("environments/"):
            surface["signals"]["environment_config"] += 1
        if len(surface["representative_paths"]) < 8:
            surface["representative_paths"].append(relative.as_posix())

    output = []
    for surface in sorted(grouped.values(), key=lambda item: item["files"], reverse=True)[:limit]:
        output.append(
            {
                "name": surface["name"],
                "files": surface["files"],
                "signals": dict(surface["signals"].most_common()),
                "domains": dict(surface["domains"].most_common()),
                "representative_paths": surface["representative_paths"],
            }
        )
    return output


def dependency_root(import_path: str) -> str:
    if import_path.startswith("."):
        return "internal_relative"
    if import_path.startswith("@"):
        parts = import_path.split("/")
        return "/".join(parts[:2]) if len(parts) >= 2 else import_path
    return import_path.split("/")[0]


def import_feature(import_path: str) -> str:
    clean = import_path.strip().replace("\\", "/")
    if clean.startswith("."):
        parts = [part for part in clean.split("/") if part not in {".", "..", ""}]
        if not parts:
            return "internal"
        for part in parts:
            normalized = part.lower().replace("_", "-")
            if normalized not in GENERIC_PATH_PARTS:
                return normalized
        return "internal"
    return dependency_root(clean).lower().replace("_", "-").replace("/", "__")


def dependency_graph(repo: Path, files: list[Path], deps: dict[str, str], limit: int = 40) -> dict[str, Any]:
    external_counts: Counter[str] = Counter()
    internal_edges: Counter[tuple[str, str]] = Counter()
    surface_external: dict[str, Counter[str]] = {}
    import_file_count = 0

    for path in files:
        if path.suffix.lower() not in SYMBOL_SUFFIXES:
            continue
        text = read_text(path, 160_000)
        if not text:
            continue
        imports = [*IMPORT_RE.findall(text), *REQUIRE_RE.findall(text)]
        if not imports:
            continue
        import_file_count += 1
        source = feature_key(path.relative_to(repo))
        surface_external.setdefault(source, Counter())
        for imported in imports[:80]:
            root = dependency_root(imported)
            if imported.startswith("."):
                target = import_feature(imported)
                if target and target != source:
                    internal_edges[(source, target)] += 1
            else:
                external_counts[root] += 1
                surface_external[source][root] += 1

    edge_rows = [
        {"from": source, "to": target, "imports": count}
        for (source, target), count in internal_edges.most_common(limit)
        if source and target
    ]
    surface_rows = []
    for surface, counter in sorted(surface_external.items(), key=lambda item: sum(item[1].values()), reverse=True)[:20]:
        surface_rows.append(
            {
                "surface": surface,
                "external_dependencies": dict(counter.most_common(10)),
                "import_count": sum(counter.values()),
            }
        )
    return {
        "import_file_count": import_file_count,
        "external_dependency_counts": dict(external_counts.most_common(limit)),
        "internal_dependency_edges": edge_rows,
        "surface_dependency_summary": surface_rows,
        "declared_dependency_count": len(deps),
    }


def api_contract_surfaces(repo: Path, files: list[Path], limit: int = 24) -> dict[str, Any]:
    method_counts: Counter[str] = Counter()
    grouped: dict[str, dict[str, Any]] = {}
    for path in files:
        if path.suffix.lower() not in SYMBOL_SUFFIXES:
            continue
        relative = path.relative_to(repo)
        lowered = relative.as_posix().lower()
        if not any(part in lowered for part in ["api", "apis", "service", "request", "client", "interface"]):
            continue
        text = read_text(path, 180_000)
        if not text:
            continue
        methods = [match.group(1).upper() for match in API_METHOD_RE.finditer(text)]
        methods.extend(match.group(1).upper() for match in REQUEST_METHOD_RE.finditer(text))
        exported_types = [match.group(1) for match in TYPE_RE.finditer(text)]
        if not methods and not exported_types and "interface" not in lowered:
            continue
        surface = feature_key(relative)
        row = grouped.setdefault(
            surface,
            {
                "surface": surface,
                "api_files": 0,
                "method_counts": Counter(),
                "type_contracts": 0,
                "representative_contracts": [],
            },
        )
        row["api_files"] += 1
        for method in methods:
            row["method_counts"][method] += 1
            method_counts[method] += 1
        row["type_contracts"] += len(exported_types)
        if len(row["representative_contracts"]) < 8:
            row["representative_contracts"].append(
                {
                    "path": relative.as_posix(),
                    "methods": sorted(set(methods))[:6],
                    "exported_types": exported_types[:8],
                }
            )

    surfaces = []
    for row in sorted(grouped.values(), key=lambda item: (item["api_files"], item["type_contracts"]), reverse=True)[:limit]:
        surfaces.append(
            {
                "surface": row["surface"],
                "api_files": row["api_files"],
                "method_counts": dict(row["method_counts"].most_common()),
                "type_contracts": row["type_contracts"],
                "representative_contracts": row["representative_contracts"],
            }
        )
    return {
        "method_counts": dict(method_counts.most_common()),
        "api_contract_surfaces": surfaces,
    }


def quality_surfaces(repo: Path, files: list[Path], scripts: dict[str, str], limit: int = 24) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    workflow_files = []
    quality_files = []
    quality_script_names = [
        name
        for name in sorted(scripts)
        if any(keyword in name.lower() for keyword in ["test", "lint", "type", "tsc", "format", "build", "check"])
    ]

    for path in files:
        relative = path.relative_to(repo)
        lowered = relative.as_posix().lower()
        suffix_name = path.name.lower()
        is_test = any(suffix_name.endswith(suffix) for suffix in TEST_SUFFIXES) or "__tests__" in lowered
        is_workflow = lowered.startswith(".github/workflows/") or lowered.startswith("gh-actions/")
        is_quality_config = any(
            marker in lowered
            for marker in [
                "eslint",
                "prettier",
                "commitlint",
                "lint-staged",
                "tsconfig",
                "vitest",
                "jest",
                "playwright",
                "cypress",
                "karma",
            ]
        )
        if is_workflow:
            workflow_files.append(relative.as_posix())
        if is_quality_config:
            quality_files.append(relative.as_posix())
        if not (is_test or is_workflow or is_quality_config):
            continue
        surface = "ci-cd" if is_workflow else feature_key(relative)
        row = grouped.setdefault(
            surface,
            {
                "surface": surface,
                "test_files": 0,
                "workflow_files": 0,
                "quality_config_files": 0,
                "representative_paths": [],
            },
        )
        if is_test:
            row["test_files"] += 1
        if is_workflow:
            row["workflow_files"] += 1
        if is_quality_config:
            row["quality_config_files"] += 1
        if len(row["representative_paths"]) < 8:
            row["representative_paths"].append(relative.as_posix())

    surfaces = sorted(
        grouped.values(),
        key=lambda item: (item["test_files"] + item["workflow_files"] + item["quality_config_files"], item["surface"]),
        reverse=True,
    )[:limit]
    return {
        "quality_scripts": quality_script_names,
        "workflow_files": workflow_files[:24],
        "quality_config_files": quality_files[:24],
        "quality_surfaces": surfaces,
    }


def is_documentation_candidate(relative: Path) -> bool:
    lowered = relative.as_posix().lower()
    if relative.suffix.lower() not in DOC_SUFFIXES:
        return False
    if "changelog" in lowered or "changeset" in lowered:
        return False
    if relative.name.lower() in {"readme.md", "contributing.md"}:
        return True
    return any(
        marker in lowered
        for marker in [
            "guideline",
            "guidelines",
            "docs",
            "architecture",
            "rfc",
            "standard",
            "migration",
            "mcp",
            "frontend",
            "component",
            "form",
            "http",
            "typescript",
        ]
    )


def documentation_surfaces(repo: Path, files: list[Path], limit: int = 24) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    doc_file_count = 0
    heading_count = 0
    for path in files:
        relative = path.relative_to(repo)
        if not is_documentation_candidate(relative):
            continue
        text = read_text(path, 180_000)
        if not text:
            continue
        headings = [re.sub(r"\s+", " ", match.group(1)).strip(" #`") for match in MARKDOWN_HEADING_RE.finditer(text)]
        headings = [heading for heading in headings if heading][:12]
        if not headings and relative.name.lower() not in {"readme.md", "contributing.md"}:
            continue
        surface = feature_key(relative)
        row = grouped.setdefault(
            surface,
            {
                "surface": surface,
                "doc_files": 0,
                "heading_count": 0,
                "domains": Counter(),
                "representative_docs": [],
            },
        )
        doc_file_count += 1
        heading_count += len(headings)
        row["doc_files"] += 1
        row["heading_count"] += len(headings)
        for tag in path_domain_tags(relative.as_posix() + " " + " ".join(headings)):
            row["domains"][tag] += 1
        if len(row["representative_docs"]) < 10:
            row["representative_docs"].append(
                {
                    "path": relative.as_posix(),
                    "headings": headings[:8] or [relative.stem],
                }
            )

    surfaces = []
    for row in sorted(grouped.values(), key=lambda item: (item["doc_files"], item["heading_count"]), reverse=True)[:limit]:
        surfaces.append(
            {
                "surface": row["surface"],
                "doc_files": row["doc_files"],
                "heading_count": row["heading_count"],
                "domains": dict(row["domains"].most_common()),
                "representative_docs": row["representative_docs"],
            }
        )
    return {
        "doc_file_count": doc_file_count,
        "heading_count": heading_count,
        "documentation_surfaces": surfaces,
    }


def route_navigation_surfaces(repo: Path, files: list[Path], limit: int = 24) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    route_file_count = 0
    navigation_file_count = 0
    guard_file_count = 0
    route_count = 0
    guard_count = 0
    lazy_boundary_count = 0
    redirect_count = 0

    for path in files:
        if path.suffix.lower() not in CODE_SUFFIXES:
            continue
        relative = path.relative_to(repo)
        lowered = relative.as_posix().lower()
        text = read_text(path, 180_000)
        if not text:
            continue

        has_router_context = any(
            marker in text
            for marker in [
                "@angular/router",
                "RouterModule",
                "createBrowserRouter",
                "createHashRouter",
                "ConfigType['routes']",
                "react-router",
            ]
        ) or any(marker in lowered for marker in ["routes", "routing", "router"])
        path_matches = [match.group(1) for match in ROUTE_PATH_RE.finditer(text)]
        has_navigation = bool(ROUTER_NAVIGATION_RE.search(text))
        has_menu_nav = bool(MENU_NAV_RE.search(text)) and ("router" in text.lower() or "route" in lowered)
        file_guard_count = len(ROUTE_GUARD_RE.findall(text))
        file_lazy_count = len(ROUTE_LAZY_RE.findall(text))
        file_redirect_count = len(ROUTE_REDIRECT_RE.findall(text))
        has_router_guard = file_guard_count > 0 or file_lazy_count > 0 or file_redirect_count > 0
        if not has_router_context and not has_navigation and not has_menu_nav and not has_router_guard:
            continue
        if not path_matches and not has_navigation and not has_menu_nav and not has_router_guard:
            continue

        surface = feature_key(relative)
        row = grouped.setdefault(
            surface,
            {
                "surface": surface,
                "route_files": 0,
                "navigation_files": 0,
                "guard_files": 0,
                "route_count": 0,
                "guard_count": 0,
                "lazy_boundary_count": 0,
                "redirect_count": 0,
                "representative_routes": [],
                "representative_paths": [],
            },
        )
        route_file_count += 1 if path_matches else 0
        navigation_file_count += 1 if has_navigation or has_menu_nav else 0
        guard_file_count += 1 if file_guard_count else 0
        route_count += len(path_matches)
        guard_count += file_guard_count
        lazy_boundary_count += file_lazy_count
        redirect_count += file_redirect_count

        row["route_files"] += 1 if path_matches else 0
        row["navigation_files"] += 1 if has_navigation or has_menu_nav else 0
        row["guard_files"] += 1 if file_guard_count else 0
        row["route_count"] += len(path_matches)
        row["guard_count"] += file_guard_count
        row["lazy_boundary_count"] += file_lazy_count
        row["redirect_count"] += file_redirect_count
        if len(row["representative_paths"]) < 8:
            row["representative_paths"].append(relative.as_posix())

        components = [match.group(1) for match in ROUTE_COMPONENT_RE.finditer(text)]
        for route_path in path_matches[:10]:
            if len(row["representative_routes"]) >= 12:
                break
            row["representative_routes"].append(
                {
                    "path_pattern": re.sub(r":[A-Za-z0-9_]+", ":param", route_path or "/"),
                    "file": relative.as_posix(),
                    "has_guard": file_guard_count > 0,
                    "has_lazy_boundary": file_lazy_count > 0,
                    "has_redirect": file_redirect_count > 0,
                    "components": components[:5],
                }
            )

    surfaces = sorted(
        grouped.values(),
        key=lambda item: (item["route_count"] + item["navigation_files"], item["surface"]),
        reverse=True,
    )[:limit]
    return {
        "route_file_count": route_file_count,
        "navigation_file_count": navigation_file_count,
        "guard_file_count": guard_file_count,
        "route_count": route_count,
        "guard_count": guard_count,
        "lazy_boundary_count": lazy_boundary_count,
        "redirect_count": redirect_count,
        "route_navigation_surfaces": surfaces,
    }


def repo_kind(repo_name: str, stack: list[str], domains: list[str]) -> str:
    if repo_name == "web-app-infra" or "environment_config" in stack or "cdk" in stack:
        return "web delivery infrastructure"
    if repo_name == "web-foundation":
        return "shared frontend foundation"
    if "angular" in stack:
        return "angular product application"
    if "react" in stack or "umi" in stack:
        return "react admin product application"
    return "frontend project"


def domains_text(domains: Iterable[str]) -> str:
    return " ".join(domains)


def project_summary(repo_info: dict[str, str], kind: str, stack: list[str], domains: list[str]) -> str:
    stack_text = ", ".join(stack[:8]) or "project files"
    domain_text = ", ".join(domains[:6]) or "frontend product workflows"
    return f"{repo_info['name']} is a {kind} covering {domain_text}, with stack signals around {stack_text}."


def architecture_guidance(kind: str, stack: list[str], domains: list[str]) -> list[str]:
    guidance = [
        "Treat this project as product architecture, not isolated file knowledge.",
        "Preserve typed contracts, workflow state, environment boundaries, and release safety when using this context.",
    ]
    if "angular" in stack:
        guidance.append("For Angular work, keep module/service/component boundaries explicit and preserve RxJS or query-state behavior.")
    if "react" in stack or "umi" in stack:
        guidance.append("For React/Umi work, keep API service boundaries, route permissions, and page-level state clear.")
    if "github_actions" in stack or "environment_config" in stack:
        guidance.append("For infrastructure work, treat GitHub Actions, environment config, deploy actions, and release automation as delivery-critical.")
    if "analytics_reporting" in domains:
        guidance.append("For reporting or analytics surfaces, protect filter semantics, export correctness, and user-visible data accuracy.")
    if "auth_permissions" in domains:
        guidance.append("For auth or permission surfaces, avoid local-only conditionals that weaken access-control semantics.")
    return guidance


def project_guardrails(stack: list[str], domains: list[str]) -> list[str]:
    guardrails = [
        "Do not expose local paths, private environment values, workflow run ids, or private customer data by default.",
        "Do not claim sole project ownership from static repo structure alone.",
    ]
    if "environment_config" in stack:
        guardrails.append("Do not copy environment config values into default answers.")
    if "portfolio_cases" in domains:
        guardrails.append("Keep public case-study language sanitized unless the user provides public screenshots or explicit approval.")
    return guardrails


def source_url(repo_info: dict[str, str]) -> str:
    return repo_info.get("remote") or repo_info.get("slug") or repo_info.get("name", "")


def source_row(
    row_id: str,
    source_type: str,
    title: str,
    summary: str,
    generated_at: str,
    topics: list[str],
    repo_info: dict[str, str],
    raw_excerpt: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": row_id,
        "source_id": row_id,
        "source_type": source_type,
        "title": title,
        "summary": summary,
        "occurred_at": generated_at,
        "ingested_at": generated_at,
        "url_or_path": source_url(repo_info),
        "tags": topics,
        "topics": topics,
        "confidence": "evidenced",
        "raw_excerpt": raw_excerpt,
    }


def build_rows(repo: Path, generated_at: str) -> dict[str, list[dict[str, Any]]]:
    repo = git_root(repo)
    files = list_repo_files(repo)
    repo_info = repo_identity(repo)
    slug_key = repo_info["slug"].replace("/", "__")
    package_json = read_json(repo / "package.json")
    deps = package_dependencies(package_json)
    scripts = package_scripts(package_json)
    stack = detect_stack(repo, files, package_json)
    domains = detect_domains([path.relative_to(repo) for path in files], deps)
    kind = repo_kind(repo_info["name"], stack, domains)
    summary = project_summary(repo_info, kind, stack, domains)
    patterns = detected_patterns(repo, files)
    important = important_files(repo, files)
    top_levels = top_level_counts(repo, files)
    ext_counts = extension_counts(files)
    symbols = symbol_summary(extract_symbols(repo, files))
    surfaces = feature_surfaces(repo, files)
    dependencies = dependency_graph(repo, files, deps)
    api_contracts = api_contract_surfaces(repo, files)
    quality = quality_surfaces(repo, files, scripts)
    documentation = documentation_surfaces(repo, files)
    route_navigation = route_navigation_surfaces(repo, files)
    guidance = architecture_guidance(kind, stack, domains)
    guardrails = project_guardrails(stack, domains)
    common_raw = {
        "repo": repo_info,
        "project_kind": kind,
        "stack": stack,
        "domains": domains,
        "scripts": scripts,
        "dependencies": sorted(deps)[:80],
        "top_level_areas": top_levels,
        "extension_counts": ext_counts,
        "detected_patterns": patterns,
        "important_files": important,
        "file_count": len(files),
    }
    topics = sorted({"project_context", "architecture_material", *stack, *domains})
    symbol_counts = symbols["symbol_counts"]
    symbol_kinds = ", ".join(list(symbol_counts)[:6]) or "project symbols"
    surface_names = ", ".join(surface["name"] for surface in surfaces[:6]) or "project feature surfaces"
    dependency_names = ", ".join(list(dependencies["external_dependency_counts"])[:6]) or "internal imports"
    api_surface_names = ", ".join(surface["surface"] for surface in api_contracts["api_contract_surfaces"][:6]) or "API contracts"
    quality_surface_names = ", ".join(surface["surface"] for surface in quality["quality_surfaces"][:6]) or "quality surfaces"
    documentation_surface_names = (
        ", ".join(surface["surface"] for surface in documentation["documentation_surfaces"][:6])
        or "documentation surfaces"
    )
    route_surface_names = (
        ", ".join(surface["surface"] for surface in route_navigation["route_navigation_surfaces"][:6])
        or "route/navigation surfaces"
    )

    architecture_rows = [
        source_row(
            f"project_architecture:{slug_key}",
            "project_architecture",
            f"Project architecture: {repo_info['name']}",
            summary,
            generated_at,
            topics,
            repo_info,
            {
                **common_raw,
                "practical_guidance": guidance,
                "guardrails": guardrails,
            },
        ),
        source_row(
            f"project_coding_contract:{slug_key}",
            "project_architecture",
            f"Project coding contract: {repo_info['name']}",
            f"{repo_info['name']} coding context should follow its detected stack, module boundaries, package scripts, and product-domain workflows.",
            generated_at,
            sorted({"coding_style", "technical_stack", *stack, *domains}),
            repo_info,
            {
                **common_raw,
                "coding_contract": guidance,
                "guardrails": guardrails,
            },
        ),
        source_row(
            f"project_symbol_graph:{slug_key}",
            "project_symbol_graph",
            f"Project symbol graph: {repo_info['name']}",
            f"{repo_info['name']} exposes project code structure around {symbol_kinds}.",
            generated_at,
            sorted({"symbol_graph", "code_structure", "coding_style", "technical_stack", *stack, *domains}),
            repo_info,
            {
                **common_raw,
                **symbols,
                "symbol_guidance": [
                    "Look for existing component, service, hook, API, state, and route boundaries before proposing new code.",
                    "Prefer extending nearby symbols that already own the same product behavior over creating isolated helpers.",
                    "Use symbol kind and signal counts to infer where code belongs, not as proof of personal ownership.",
                ],
                "guardrails": [
                    *guardrails,
                    "Do not expose raw source code by default; use symbol names and relative paths only as navigation hints.",
                ],
            },
        ),
        source_row(
            f"project_feature_surface:{slug_key}",
            "project_feature_surface",
            f"Project feature surfaces: {repo_info['name']}",
            f"{repo_info['name']} feature surfaces cluster around {surface_names}.",
            generated_at,
            sorted({"feature_surface", "project_context", "domain_knowledge", *stack, *domains}),
            repo_info,
            {
                **common_raw,
                "feature_surfaces": surfaces,
                "feature_guidance": [
                    "Use feature surfaces to understand where product workflows, UI, API, state, and release concerns meet.",
                    "When changing a feature, inspect neighboring representative paths before deciding the implementation boundary.",
                    "Treat high-file-count surfaces as higher-risk areas that need focused validation.",
                ],
                "guardrails": [
                    *guardrails,
                    "Do not treat a feature surface as public portfolio material until names and screenshots are sanitized.",
                ],
            },
        ),
        source_row(
            f"project_dependency_graph:{slug_key}",
            "project_dependency_graph",
            f"Project dependency graph: {repo_info['name']}",
            f"{repo_info['name']} dependency context centers on {dependency_names}.",
            generated_at,
            sorted({"dependency_graph", "code_structure", "architecture_material", "technical_stack", *stack, *domains}),
            repo_info,
            {
                **common_raw,
                **dependencies,
                "dependency_guidance": [
                    "Use dependency graph context to preserve package and feature boundaries before changing shared code.",
                    "Prefer local feature dependencies over adding broad cross-surface coupling.",
                    "Check high-import shared surfaces for regression risk before changing exports or shared services.",
                ],
                "guardrails": [
                    *guardrails,
                    "Do not infer runtime behavior from static imports alone.",
                    "Do not expose private package names as public portfolio claims unless explicitly sanitized.",
                ],
            },
        ),
        source_row(
            f"project_api_contract_surface:{slug_key}",
            "project_api_contract_surface",
            f"Project API contract surface: {repo_info['name']}",
            f"{repo_info['name']} API contract surfaces cluster around {api_surface_names}.",
            generated_at,
            sorted({"api_contract", "service_layer", "technical_stack", "project_context", *stack, *domains}),
            repo_info,
            {
                **common_raw,
                **api_contracts,
                "api_contract_guidance": [
                    "Use API contract context before changing request payloads, response types, or service boundaries.",
                    "Preserve exported type names and service responsibilities unless a migration updates all callers.",
                    "Treat API and interface files as contract surfaces that need focused validation.",
                ],
                "guardrails": [
                    *guardrails,
                    "Do not expose endpoint paths or private API details in default answers.",
                    "Do not claim backend ownership from frontend API client contracts alone.",
                ],
            },
        ),
        source_row(
            f"project_quality_surface:{slug_key}",
            "project_quality_surface",
            f"Project quality surface: {repo_info['name']}",
            f"{repo_info['name']} quality and validation surfaces cluster around {quality_surface_names}.",
            generated_at,
            sorted({"quality_surface", "testing", "ci_cd", "delivery", *stack, *domains}),
            repo_info,
            {
                **common_raw,
                **quality,
                "quality_guidance": [
                    "Use quality surface context to decide the minimum validation before changing a feature or shared package.",
                    "Prefer existing lint, typecheck, test, build, and workflow contracts over ad hoc verification.",
                    "Treat CI/CD and quality config files as production-safety surfaces.",
                ],
                "guardrails": [
                    *guardrails,
                    "Do not overstate test coverage from test file names alone.",
                    "Do not treat a passing static quality scan as proof that product behavior is correct.",
                ],
            },
        ),
    ]

    if route_navigation["route_file_count"] or route_navigation["navigation_file_count"] or route_navigation["guard_file_count"]:
        architecture_rows.append(
            source_row(
                f"project_route_navigation:{slug_key}",
                "project_route_navigation",
                f"Project route and navigation surface: {repo_info['name']}",
                f"{repo_info['name']} route and navigation surfaces cluster around {route_surface_names}.",
                generated_at,
                sorted({"route_navigation", "project_context", "architecture_material", "auth_permissions", *stack, *domains}),
                repo_info,
                {
                    **common_raw,
                    **route_navigation,
                    "route_navigation_guidance": [
                        "Use route and navigation context before changing page boundaries, guards, redirects, or menu behavior.",
                        "Keep route-level permission, feature-flag, and redirect behavior aligned with existing route ownership.",
                        "Validate navigation changes through the page entry points and guard paths they affect.",
                    ],
                    "guardrails": [
                        *guardrails,
                        "Do not expose private route paths or permission names in public-facing answers unless explicitly requested.",
                        "Do not infer product ownership from route presence alone.",
                    ],
                },
            )
        )

    if documentation["doc_file_count"]:
        architecture_rows.append(
            source_row(
                f"project_documentation_surface:{slug_key}",
                "project_documentation_surface",
                f"Project documentation surface: {repo_info['name']}",
                f"{repo_info['name']} documentation surfaces cluster around {documentation_surface_names}.",
                generated_at,
                sorted({"documentation_surface", "architecture_material", "project_context", "coding_style", *stack, *domains}),
                repo_info,
                {
                    **common_raw,
                    **documentation,
                    "documentation_guidance": [
                        "Use documentation surface context before changing standards, shared package behavior, or onboarding guidance.",
                        "Prefer documented project conventions over inferred style when both are available.",
                        "Treat README, contributing notes, and guidelines as durable project contracts, not casual comments.",
                    ],
                    "guardrails": [
                        *guardrails,
                        "Do not quote long private documentation by default; summarize the convention instead.",
                        "Do not treat documentation headings as proof of shipped behavior without code or release evidence.",
                    ],
                },
            )
        )

    release_rows: list[dict[str, Any]] = []
    if {"github_actions", "environment_config", "semantic_release", "turbo_changesets"} & set(stack) or any(
        key in scripts for key in ["release", "build", "deploy"]
    ):
        release_rows.append(
            source_row(
                f"project_release:{slug_key}",
                "release_activity",
                f"Release and delivery context: {repo_info['name']}",
                f"{repo_info['name']} contains release-sensitive project material around builds, workflows, environment config, package release, or deploy automation.",
                generated_at,
                sorted({"release_ownership", "ci_cd", "delivery", "web_infra", *stack}),
                repo_info,
                {
                    **common_raw,
                    "release_guidance": [
                        "Treat build, environment, deploy, and package-release changes as delivery-risk changes.",
                        "Keep rollout, QA, and rollback implications visible when using this project context.",
                    ],
                    "guardrails": guardrails,
                },
            )
        )

    portfolio_rows = [
        source_row(
            f"portfolio_case:{slug_key}",
            "portfolio_case",
            f"Sanitized project case: {repo_info['name']}",
            f"Public-safe case material can describe {repo_info['name']} as {kind} work across {', '.join(domains[:5]) or 'frontend product workflows'} without exposing private source paths or customer data.",
            generated_at,
            sorted({"portfolio_cases", "case_study", *domains, *stack}),
            repo_info,
            {
                **common_raw,
                "case_study_angles": [
                    "Explain the product or platform problem in sanitized terms.",
                    "Describe architecture, workflow, quality, and delivery decisions rather than private implementation details.",
                    "Use as interview or portfolio material only after removing private names, paths, and screenshots.",
                ],
                "guardrails": guardrails,
            },
        )
    ]

    return {
        "architecture_material.jsonl": architecture_rows,
        "release_activity.jsonl": release_rows,
        "portfolio_cases.jsonl": portfolio_rows,
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def row_repo_slug(row: dict[str, Any]) -> str:
    raw = row.get("raw_excerpt") if isinstance(row.get("raw_excerpt"), dict) else {}
    repo = raw.get("repo") if isinstance(raw.get("repo"), dict) else {}
    return str(repo.get("slug", ""))


def merge_rows(path: Path, repo_slugs: set[str], new_rows: list[dict[str, Any]]) -> dict[str, int]:
    existing = read_jsonl(path)
    kept = [row for row in existing if row_repo_slug(row) not in repo_slugs]
    write_jsonl(path, [*kept, *new_rows])
    return {
        "previous_rows": len(existing),
        "replaced_rows": len(existing) - len(kept),
        "added_rows": len(new_rows),
        "total_rows": len(kept) + len(new_rows),
    }


def distill(repos: list[Path], ledger: Path) -> dict[str, Any]:
    generated_at = now_iso()
    all_rows_by_file: dict[str, list[dict[str, Any]]] = {
        "architecture_material.jsonl": [],
        "release_activity.jsonl": [],
        "portfolio_cases.jsonl": [],
    }
    repo_summaries = []
    repo_slugs: set[str] = set()

    for repo in repos:
        if not repo.exists() or not repo.is_dir():
            raise SystemExit(f"repo does not exist or is not a directory: {repo}")
        rows_by_file = build_rows(repo.resolve(), generated_at)
        for file_name, rows in rows_by_file.items():
            all_rows_by_file[file_name].extend(rows)
        first_row = next(iter(rows_by_file["architecture_material.jsonl"]))
        raw = first_row["raw_excerpt"]
        repo_info = raw["repo"]
        repo_slugs.add(str(repo_info["slug"]))
        repo_summaries.append(
            {
                "repo": repo_info,
                "project_kind": raw["project_kind"],
                "stack": raw["stack"],
                "domains": raw["domains"],
                "architecture_rows": len(rows_by_file["architecture_material.jsonl"]),
                "release_rows": len(rows_by_file["release_activity.jsonl"]),
                "portfolio_rows": len(rows_by_file["portfolio_cases.jsonl"]),
            }
        )

    sources = ledger / "sources"
    merge_results = {
        file_name: merge_rows(sources / file_name, repo_slugs, rows)
        for file_name, rows in all_rows_by_file.items()
    }

    return {
        "generated_at": generated_at,
        "ledger": str(ledger),
        "repos": repo_summaries,
        "merge_results": merge_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", action="append", required=True, help="Local repository path. May be provided multiple times.")
    parser.add_argument("--ledger", help="Ledger path. Defaults to SELF_CONTEXT_HOME or the user profile directory.")
    parser.add_argument("--json", action="store_true", help="Print JSON result.")
    args = parser.parse_args()

    result = distill([Path(item).expanduser() for item in args.repo], resolve_ledger_path(args.ledger))
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for repo in result["repos"]:
            print(f"distilled {repo['repo']['slug']} stack={','.join(repo['stack'])}")


if __name__ == "__main__":
    main()
