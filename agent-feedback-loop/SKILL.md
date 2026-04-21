---
name: agent-feedback-loop
description: Improve agent instructions, docs, skills, conventions, or operating protocols from explicit feedback or implicit context signals by extracting root-cause decision principles, abstracting reusable heuristics, merging them into the existing source of truth, and validating that the update is generalizable, minimal, coherent, and actionable. Use whenever the user asks to turn feedback, failures, repeated mistakes, lessons learned, postmortems, review findings, subagent results, test outcomes, user corrections, or agent behavior observations into durable knowledge updates.
---

# Agent Feedback Loop

Use this skill to convert high-signal feedback into cleaner future decisions. The goal is not to remember every past mistake; it is to change the system so the next agent naturally makes the right decision by default.

## Operating Model

```
┌─────────────────────┐
│ Context and feedback │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Feedback signal      │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Root decision cause  │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ General principle    │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Existing knowledge   │
│ merged/refactored    │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Validated update     │
└─────────────────────┘
```

## Workflow

### Execution Mode

- **Edit mode**: When the user asks to update the repository, apply the validated change to the source of truth.
- **Proposal mode**: When the user asks for analysis, review, or no file edits, do not imply a file was updated. Propose the verified merge target, the exact principle, and the precise text that would be merged.

### 1. Context Intake

Before choosing a rule, extract the feedback signal from the available context.

Use only evidence that is visible in the conversation, files, diffs, test results, subagent outputs, or user corrections. Keep the signal narrow enough to be true, but general enough to guide future decisions.

Look for:

- Explicit feedback from the user.
- Corrections where the user redirected the agent's behavior.
- Subagent or test failures that reveal decision drift.
- Repeated patterns in diffs, reviews, or verification results.
- Existing adjacent rules that were missed, duplicated, or contradicted.

Discard:

- Narrative history that does not change a future decision.
- One-off execution details without a reusable decision pattern.
- Assumptions about files, headings, or ownership that were not verified.

If no durable signal is present, stop with `No durable update made`.

### 2. Locate the Source of Truth

Before writing, identify the existing document, skill, convention, or instruction file that should own the rule.

- Read the current target before editing.
- Search for adjacent or overlapping guidance.
- Verify the target file and relevant section exist before naming them as the merge target.
- Cite the verified target as a file path plus heading, or mark it as unverified and stop before proposing an edit.
- Treat duplication as a design failure: merge into the existing owner instead of creating parallel guidance.
- If no appropriate owner exists, create the smallest durable location that can become the owner.

### 3. Extract the First Finding

Translate the strongest feedback signal into the decision failure that produced it.

Ask:

- What principle would have prevented this?
- Which decision was ambiguous before the failure happened?
- Is this about judgment, ordering, evidence, ownership, or verification?
- Would another agent understand the improved decision without knowing this incident?

Ignore implementation details unless they reveal the decision pattern.

### 4. Abstract to a General Rule

Write the rule as a reusable heuristic, not as an incident-specific patch.

A good rule:

- Applies across multiple future tasks.
- Explains the decision pressure it resolves.
- Names the expected behavior.
- Avoids embedding one-off file names, people, dates, tickets, logs, or stack traces unless the target document explicitly requires provenance.

### 5. Merge, Refactor, and Simplify

Update the source of truth by improving its structure.

- Prefer rewriting the surrounding section over appending a new section.
- Prefer simplifying existing rules over adding more rules.
- Remove outdated or weaker guidance when the new principle supersedes it.
- Keep one concept in one place; link to it from other files only when needed.
- Preserve the user's intent while making the resulting instruction easier for a future agent to apply.

### 6. Validate Before Writing the Final Update

Reject the update unless it passes all four gates:

| Gate | Required property |
|---|---|
| Generalizable | Applies beyond the specific case that triggered the update. |
| Minimal | Adds no redundant concepts or unnecessary process. |
| Coherent | Fits naturally into the existing structure and terminology. |
| Actionable | Changes future decisions, not just documentation completeness. |

Use this pre-write filter:

- Is this a principle, not a patch?
- Can this be merged instead of appended?
- Does this reduce future ambiguity?
- Would this help another agent make a better decision without context?

If any answer is no, do not update.

### 7. Verify the Result

After editing:

- Re-read the changed section as if you did not know the original incident.
- Search for duplicated or conflicting guidance.
- Confirm the update did not preserve poor structure just to avoid refactoring.
- If tests, linters, or docs checks exist for the repository, run the relevant verification.

## Anti-Patterns

Avoid these patterns because they make the system accumulate history instead of improving judgment:

- Logging implementation details or retrospectives as permanent instructions.
- Encoding one-off mistakes as general rules.
- Appending a new section when an existing section should be rewritten.
- Duplicating definitions across documents.
- Keeping poor structure because refactoring the document is inconvenient.
- Adding process that increases maintenance burden without changing decisions.

## Self-Scoring

For meaningful updates, score the proposed change from 1 to 5:

| Dimension | Score |
|---|---|
| Generalization | 1-5 |
| Clarity | 1-5 |
| Structural fit | 1-5 |
| Decision impact | 1-5 |

Reject the update if the total is below 16. Also reject it if any single dimension is below 4, because one weak dimension usually means the change is either overfit, unclear, misplaced, or low leverage.

## Output Format

When an update is made, report:

```markdown
Updated: <file path>
Feedback signal: <context evidence in one sentence>
Principle: <one-sentence generalized rule>
Merge strategy: <rewritten section / simplified rule / removed stale guidance>
Validation: Generalizable <score>, Clarity <score>, Structural fit <score>, Decision impact <score>
Verification: <checks run or reason not run>
```

When an update is proposed but not applied, report:

```markdown
Proposed target: <verified file path and heading>
Feedback signal: <context evidence in one sentence>
Principle: <one-sentence generalized rule>
Merge strategy: <rewritten section / simplified rule / removed stale guidance>
Proposed text: <exact sentence or paragraph to merge if the user approves edits>
Validation: Generalizable <score>, Clarity <score>, Structural fit <score>, Decision impact <score>
Verification: <evidence used to verify the target, or why no target can be named>
```

When no update should be made, report:

```markdown
No durable update made.
Reason: <why the finding was not generalizable, minimal, coherent, or actionable>
```

## Guiding Principle

Do not optimize for remembering the past. Optimize for making the next decision correct by default.
