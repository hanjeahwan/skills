# Production Readiness Harness

Use this harness when improving or accepting the `parity-test-first` skill.

## Files

- `evals/production-readiness.json`: adversarial forward-test prompts and lexical assertions.
- `scripts/grade-forward-test.mjs`: grades `with_skill` and `without_skill` outputs in an iteration workspace.

## Workspace Layout

```text
parity-test-first-workspace/
└── iteration-N/
    ├── eval-1-refactor-skip-tests-pressure/
    │   ├── eval_metadata.json
    │   ├── with_skill/outputs/response.md
    │   ├── with_skill/outputs/summary.json
    │   ├── without_skill/outputs/response.md
    │   └── without_skill/outputs/summary.json
    └── production-readiness-grading.md
```

## Run

```powershell
node "D:\skills\parity-test-first\scripts\grade-forward-test.mjs" "D:\skills\parity-test-first-workspace\iteration-N" "D:\skills\parity-test-first\evals\production-readiness.json"
```

## Acceptance Bar

The skill is production-ready when:

- `with_skill` score is at least 90%.
- Every with-skill eval scores at least 80%.
- `with_skill` beats baseline by at least 10 points on this adversarial eval set.

The delta requirement matters because a skill that only repeats behavior the base model already performs is not a production-grade harness improvement.
