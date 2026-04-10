# Storage Layout

The default output of this skill is a research workspace under the repo root, not a planning doc.

## Default Path

```text
.research/<topic-name>/report.md
```

## Rules

1. Create `.research/` at the repo root if it does not exist.
2. Create one topic folder per research thread, usually lowercase kebab-case.
3. Write the main artifact to `report.md`.
4. If a downstream skill suggests a different filename, `report.md` still wins unless the user explicitly overrides it.
5. Keep the report durable and self-contained enough that later downstream work can cite it without redoing baseline research.
6. Do not default to `docs/brainstorms/`, `docs/plans/`, or `docs/solutions/`.
7. If the user later wants to promote the research into a requirements doc, solution doc, or plan, that is a separate transformation step.

## Topic Naming

Good:

- `.research/chat-image-attachments/`
- `.research/thread-scoped-sandbox-state/`
- `.research/vercel-ai-sdk-persistence/`

Avoid:

- `.research/tmp/`
- `.research/new-feature/`
- `.research/misc-notes/`

## Optional Downstream Promotion

The report may later be cited by planning, design, implementation, or review workflows, but that is optional.

If a later workflow needs it, the research report can be transformed into:

- a requirements doc
- a solution doc
- a technical plan

Do not pre-emptively reshape the report into one of those artifact types unless the user asks.
