# Privacy

Use this reference whenever importing workplace data, communication logs, or private career material.

## Storage Boundary

Never store private user data inside the installed skill directory. Store it in the selected ledger path only.

## Data Minimization

Keep only what supports future capability analysis:

- Small excerpts instead of full private threads.
- Source ids and links instead of full duplicated records when links are enough.
- Summaries of sensitive conversations instead of raw chat logs.

## Redaction

Redact:

- Secrets, tokens, credentials, and API keys.
- Customer personal data.
- Private HR information unrelated to the user's capability evidence.
- Sensitive internal names when a report is intended for external use.

Run the bundled redaction helper after importing raw source data and before generating resume, promotion, portfolio, or recruiter-facing assets:

```bash
python scripts/redact_ledger_secrets.py --ledger "<ledger-path>" --write-report
python scripts/redact_ledger_secrets.py --ledger "<ledger-path>" --dry-run
```

The first command applies redaction and writes `reports/secret-redaction-report-YYYY-MM-DD.md/json`. The second command verifies no pending secret-like values remain. Treat `total_changed_rows=0` as the expected clean state.

The report must be count-only. It may include rule names, changed row counts, file names, and evidence ids. It must never include the original token, secret, DSN, credential, API key, bucket access detail, or private config value.

Redaction should preserve career evidence context by replacing only secret-like values with placeholders such as `<REDACTED_SECRET>`, while keeping source ids, titles, URLs, changed file names, and surrounding non-sensitive technical context.

## Publication

Before generating resume, portfolio, or public reports, remove confidential project names, customer names, internal URLs, and unreleased product details unless the user explicitly confirms they are public.
