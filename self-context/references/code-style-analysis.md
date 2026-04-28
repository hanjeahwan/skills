# Code Style Analysis

Use this reference when turning repositories, commit patches, and local source scans into self-context memory about how the user writes code.

## Goal

The output is not a code-style report. The output is coding memory:

- what the user tends to build,
- how they structure frontend/backend work,
- what quality practices they repeat,
- what an agent should do when coding in the user's style,
- what is uncertain or should not be assumed.

## Source Import

Local repo scan:

```bash
python scripts/scan_code_style.py --ledger "<ledger-path>" --repo "<repo-path>" --author "<author-filter>" --json
```

GitHub commit patch analysis:

```bash
python scripts/analyze_github_commit_patterns.py --ledger "<ledger-path>" --json
```

Then refresh self-context:

```bash
python scripts/build_memory_atoms.py --ledger "<ledger-path>"
python scripts/build_context_packs.py --ledger "<ledger-path>"
python scripts/build_sqlite_index.py --ledger "<ledger-path>"
uv run --with sentence-transformers python scripts/build_memory_index.py --ledger "<ledger-path>"
```

MCP tools:

```text
scan_code_style_from_repo
analyze_github_commit_code_patterns
rebuild_self_context
query_self_context
```

## Distillation Rules

Turn code evidence into memory atoms such as:

- `coding_style`: React/Next, Angular, TypeScript, state management, components, services, tests, linting.
- `decision_pattern`: maintainability, API contracts, release safety, performance, auth/security boundaries.
- `capability`: product frontend, CI/CD, shared libraries, AI product UI, observability.
- `unknown_gap`: missing examples, weak proof, stale stack evidence.

Default answers must explain coding behavior, not source counts.

Good answer shape:

```text
Example User tends to write product-oriented frontend code with explicit TypeScript boundaries,
component/state separation, and attention to data contracts and release quality.
When coding for him, prefer clear reusable components, predictable state flow,
lint/type safety, and production checks before clever abstractions.
```

Proof mode may expose source ids, but normal mode must not.

## Guardrails

- Do not infer mastery from counts alone.
- Do not treat generated reports as the database.
- Do not expose private repo names or source ids unless proof is requested.
- Separate historical stack depth from current preference.
- Keep exact code examples for proof/debug or authorized portfolio work.
