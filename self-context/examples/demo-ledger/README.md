# Demo Ledger

This directory is intentionally kept free of committed private data.

Use the synthetic benchmark seed to generate a local demo ledger when you want to show the project without exposing real Git, Jira, PR, or personal material:

```bash
python scripts/run_retrieval_benchmarks.py --suite synthetic --json
```

For a persistent local demo, create a ledger outside the repository:

```bash
python scripts/init_ledger.py --ledger "../self-context-demo-ledger"
python scripts/run_retrieval_benchmarks.py --suite synthetic --json
```

The public repository should contain code, docs, schemas, and synthetic examples only. Real ledger folders such as `sources/`, `derived/`, `events/`, `exports/`, `profiles/`, and `reports/` must stay outside Git.
