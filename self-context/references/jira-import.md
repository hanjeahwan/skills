# Jira Import

Use this reference when the user wants to import Jira tickets.

## Required User Inputs

Ask for:

- Jira base URL.
- Project key or JQL query.
- Authentication method available in the current environment.
- Whether to include comments, changelog, and linked issues.

## Recommended Command

Use the bundled script when Jira Cloud credentials are available through environment variables:

```bash
python scripts/export_jira_issues.py --jql "<JQL>" --out "<ledger-path>/sources/jira.jsonl"
```

Required environment variables:

```text
JIRA_BASE_URL
JIRA_EMAIL
JIRA_API_TOKEN
```

Use append-only mode by default. The exporter reads existing `sources/jira.jsonl` ids and skips duplicate issue keys. Use `--replace` only when the user explicitly wants to rebuild Jira evidence from scratch.

Recommended initial JQL:

```text
(assignee = currentUser() OR reporter = currentUser()) AND created >= "2016-01-01" ORDER BY updated DESC
```

## Recommended Fields

Store each ticket as raw evidence with:

- Key.
- Summary.
- Description summary.
- Status and resolution.
- Created, updated, resolved dates.
- Assignee, reporter, and user role when available.
- Labels, components, fix versions.
- Links to PRs, incidents, or design docs.
- Small excerpts from comments that show decisions, ownership, or outcomes.

## Distillation Signals

Jira can support stronger claims than Git when it includes:

- Clear problem statement.
- Acceptance criteria.
- Resolution or shipped outcome.
- Priority or severity.
- Cross-team coordination in comments.
- Metrics or incident references.

## Privacy

Do not import full comments by default when they contain unrelated personal discussion. Prefer short, relevant excerpts.
