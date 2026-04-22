# Git Scanning

Use this reference when the user gives a repository path and wants the skill to scan commit history.

## Data Flow

```text
repo path
  ▼
git log export
  ▼
sources/git.jsonl
  ▼
capability event distillation
  ▼
baseline or snapshot
```

## Recommended Command

Use the bundled script from the skill directory:

```bash
python scripts/export_git_commits.py --repo "<repo-path>" --out "<ledger-path>/sources/git.jsonl" --author "<author-filter>"
```

Use `--since`, `--until`, or `--max-count` for scoped imports.

## No-Clone GitHub Mode

When the user does not want to clone repositories, use GitHub API mode. This requires the GitHub CLI (`gh`) to be authenticated with access to the target repositories.

```bash
python scripts/export_github_commits.py --author "<github-login>" --since "<YYYY-MM-DD>" --until "<YYYY-MM-DD>" --out "<ledger-path>/sources/git.jsonl"
```

Scope the search when possible:

```bash
python scripts/export_github_commits.py --author "<github-login>" --org "<org>" --since "<YYYY-MM-DD>" --until "<YYYY-MM-DD>" --out "<ledger-path>/sources/git.jsonl"
```

No-clone mode stores:

- Commit message and GitHub URL.
- Repository full name.
- Author name/email/date.
- File list.
- Additions/deletions.
- Patch excerpts.

No-clone mode cannot:

- Run local tests or code analysis.
- Inspect full surrounding source context unless the patch includes it.
- See data outside the authenticated GitHub account's permissions.
- Reliably pull more than GitHub search can return in one broad query.

For large histories, split imports by month or quarter.

## Full History Without Clone

When the user wants to scan from their first GitHub contribution to today, use the long-range exporter. It searches by date windows, splits dense windows, fetches commit details, and writes a coverage report.

```bash
python scripts/export_github_history.py --author "<github-login>" --org "<org>" --user "<github-login>" --since "<YYYY-MM-DD>" --out "<ledger-path>/sources/git.jsonl"
```

Use `--author-mode author-email --author "<email>"` when commits are not reliably linked to the GitHub login.

Use `--replace` for a clean baseline import. Omit `--replace` for append-only refreshes.

The coverage report is written next to the output as `<name>.coverage.json` unless `--coverage-out` is provided. Review this file before claiming the import is complete. Any window marked `truncated` or with a warning needs a smaller date range or narrower scope.

Recommended first full import:

```bash
python scripts/export_github_history.py --author "<github-login>" --org "Pulsifi" --user "<github-login>" --since "2016-01-01" --replace --out "<ledger-path>/sources/git.jsonl"
```

## Reruns and Deduplication

Commit import is resumable. Both GitHub API exporters read existing `sources/git.jsonl` ids before writing new records. If a commit already exists, it is skipped.

Stable raw evidence ids use:

```text
git_commit:<owner/repo>:<sha>
```

Use this behavior:

- Initial baseline: run with `--replace` only when the user wants a clean rebuild.
- Incremental refresh: omit `--replace`; the exporter appends only new commits.
- After any import: run `scripts/validate_ledger.py` to catch duplicate ids or malformed records.
- If manual edits created duplicates: run `scripts/dedupe_sources.py` on the affected JSONL file.

Import status and distillation status are different:

- Imported: the commit exists in `sources/git.jsonl`.
- Distilled: at least one event in `derived/capability_events.jsonl` references that commit id via `evidence_id`.

Do not infer that an imported commit has already been used in the profile unless a capability event references it.

## GitHub PR Activity

For ownership, code review, mentoring, promotion, or resume work, import PR activity as raw evidence before writing conclusions. Use:

```bash
python scripts/export_github_pr_activity.py --repos-from-git-source --github-user "<github-login>"
```

After the first scan, use the incremental path:

```bash
python scripts/export_github_pr_activity.py --repos-from-git-source --github-user "<github-login>" --incremental
```

This writes to `sources/github_pr_activity.jsonl` and stores:

- PRs authored by the user.
- PR discussion comments authored by the user.
- PR review comments authored by the user.
- A coverage file: `sources/github_pr_activity.jsonl.coverage.json`.

Stable ids use:

```text
pull_request:<owner/repo>#<number>
pull_request_discussion_comment:<owner/repo>#<number>:<comment-id>
pull_request_review_comment:<owner/repo>#<number>:<comment-id>
```

If an earlier scan report exists, convert it without network calls:

```bash
python scripts/export_github_pr_activity.py --from-scan-json "<ledger-path>/reports/github-pr-review-leadership-scan-YYYY-MM-DD.json"
```

Treat `reports/` as generated views only. Do not rely on a report JSON as the persistent database. Future runs should read `sources/github_pr_activity.jsonl` first and append only missing ids.

`--incremental` uses the prior coverage `generated_at` timestamp to fetch only PR and comment activity updated after the last scan when supported by GitHub endpoints. Use a full scan only for the first baseline or when coverage is missing or suspected incomplete.

Interpretation limits:

- Authored and merged PRs support delivery ownership.
- Code review comments support review participation.
- Mentoring requires content-level evidence of guidance or coaching.
- Architecture leadership requires PR/Jira/design text showing decision rationale, not just PR size.

## Author Filtering

If the repository has multiple contributors, identify the user's author identity before importing. Prefer an email address because names can vary.

If the user does not know the author string, inspect recent commits with:

```bash
git -C "<repo-path>" log --format="%an <%ae>" --max-count=30
```

## Distillation Signals

Commit messages alone are weak evidence. Combine:

- Commit title and body.
- Changed files and directories.
- Test changes.
- Repeated work in the same subsystem.
- Jira keys or PR references in commit text.
- Large related commit series.

## Limits

Do not claim business impact from Git data alone. Business impact needs Jira outcomes, metrics, release notes, incident records, or user-supplied context.
