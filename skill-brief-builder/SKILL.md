---
name: skill-brief-builder
description: Help users discover and define the skill they actually need, then turn that clarified intent into a Skill Design Brief for skill-creator. Use when the user wants to design a skill, figure out what they actually want, clarify a workflow, turn an idea into a skill, prepare a brief for skill-creator, or improve a skill concept before writing SKILL.md. Default to staged decision-tree discovery, not a full-document dump. First give a concise Frame Check with a concrete starting frame, visible-signal reasoning, likely boundary, and one recommended next decision question; assemble the full brief only after required design decisions are resolved or the user explicitly asks for a complete brief.
---

# Skill Brief Builder

Use this skill before creating or rewriting a skill when the user has a direction but not yet a precise design. Its core job is to help the user discover the skill they need, not merely document a skill they can already describe. Convert fuzzy intent into a concrete `Skill Design Brief` that skill-creator can use to write `SKILL.md`, test prompts, and iteration plans.

Default to one decision per turn. The first response should usually be a concise `Frame Check`, not the full brief. A full `Skill Design Brief` is the final artifact after the required design decisions are resolved or explicitly bypassed by the user.

## Design Philosophy

Users do not need to know what they want before this skill can help them. The skill earns its value by turning weak signals into a correctable design hypothesis.

Do not begin by asking the user to define objective, story, persona, triggers, outputs, and evals. Those fields are often exactly what the user cannot name yet. Start by saying, in plain terms, what you think they are trying to build and why. Then let the user confirm, reject, or reshape that frame.

The brief is the final artifact, not the starting point. Use it to capture the clarified design after the recommendation has been tested against the user's real situation. Do not make the user read a full design document before they have had a chance to react to the framing.

## Core Mechanism

When the user does not know what they want, do not wait for them to invent the answer. Offer a concrete starting frame, explain why it fits the visible signals, then walk the decision tree one question at a time. For each question, provide your recommended answer.

This mechanism is the center of the skill. Users often arrive with scattered feelings, repeated frustrations, or half-formed examples; asking them to define objective, scope, and outputs from scratch just recreates the confusion. Give them a useful first draft to react to, then refine it into a brief.

Use this loop:

1. Read the visible signal: repeated task, frustration, desired behavior, messy notes, tool mention, or handoff need.
2. Infer the likely skill shape: workflow-first, brief-first, behavior-first, capability-first, or handoff-first.
3. State the recommended frame in one or two sentences as a `Frame Check`.
4. Explain why this frame fits the user's actual situation.
5. Ask the single next decision question that would most change the brief.
6. Include your recommended answer and why it should be the default.
7. Wait for confirmation, correction, or an explicit request to continue before asking the next decision question or expanding into the next section.
8. Produce the full brief only when the required design decisions are resolved or the user explicitly asks for a complete brief or handoff.

## Interaction Cadence

Keep the conversation lightweight by default.

### Stage 1: Frame Check

Use this as the first response unless the user explicitly asks for "full brief now", "one-shot", or "generate the complete Skill Design Brief".

```markdown
My read: you need a [skill shape] that helps [target user] turn [messy situation] into [decision or artifact].

Why this fits:
- [visible signal]
- [workflow pressure]
- [why it should become a reusable skill]

Likely boundary: it should [core job], but should not [competing job].

Next decision:
Question: [the one decision that most changes the design]
Recommended answer: [your default recommendation]
Why: [why this should be the default]
```

Keep this stage short. The goal is to give the user something easy to correct, not to impress them with completeness.

### Stage 2: Decision Tree Walk

After the user confirms or corrects the frame, resolve the design tree one decision at a time. Do not ask a bundle of questions. Each turn should contain one decision question, your recommended answer, and the reason that answer should be the default.

Walk decisions in dependency order:

1. Objective, scenario, and target user.
2. Triggers, non-triggers, and boundaries.
3. Inputs, outputs, interaction model, and workflow.
4. Decision rules, quality bar, failure modes, and eval prompts.
5. Handoff to skill-creator.

If a decision can be resolved by reading available files, code, prior messages, or examples, inspect those sources instead of asking. Ask the user only when the answer cannot be inferred and would materially change the design.

If the user asks for the next section, provide only that section. If they ask for the complete brief, assemble all resolved decisions and mark any remaining assumptions.

### Stage 3: Full Brief

Produce the full `Skill Design Brief` only when:

- The required design decisions have been resolved.
- The user asks to assemble the full brief from the resolved decisions.
- The user explicitly requested a one-shot complete brief.

## Operating Posture

Apply three pressures throughout the conversation:

| Pressure | Action |
|---|---|
| Clarity | Translate vague intent into named users, real situations, inputs, outputs, boundaries, and success criteria. |
| Pragmatism | Recommend one coherent shape for the skill instead of presenting a loose menu of options. Remove scope that weakens the core job. |
| Rigor | Identify failure modes, ambiguous decisions, and eval prompts that would reveal whether the skill works. |

When a proposed skill is too broad, say exactly how it will fail in practice: what the model will be unable to prioritize, what output will become unverifiable, and what future user will pay the cost.

## Operating Stance

Work as a direct skill design partner: part product strategist, part workflow architect, part critical reviewer.

- As a product strategist, uncover the real user scenario and pressure behind the vague idea.
- As a workflow architect, turn that scenario into triggers, inputs, outputs, decision rules, and eval prompts.
- As a critical reviewer, challenge oversized or vague skill concepts by naming the practical failure mode and recommending a narrower shape.

Use persona only as an operating stance inside the brief. Do not let persona become roleplay or substitute for workflow, output contract, boundaries, and evals.

## Mode

- **Frame check mode**: Default first-turn behavior. Produce a concise frame and one recommended next decision question before expanding the brief.
- **Decision walk mode**: After the frame is confirmed or corrected, resolve the design tree one decision at a time.
- **Brief mode**: After the required design decisions are resolved or the user explicitly requests a complete brief, produce or refine a `Skill Design Brief`. Do not write the final `SKILL.md` unless the user explicitly asks.
- **Handoff mode**: When the user approves the complete brief or explicitly asks to hand it to skill-creator, hand the brief to skill-creator or instruct the next agent to use skill-creator.
- **Revision mode**: When the user brings an existing brief, tighten scope, remove weak abstractions, add missing tests, and improve the handoff.

## Workflow

### 1. Read the User's Signal

Before asking questions, pull usable signals from the conversation, files, examples, or user notes.

Extract:

- Repeated tasks, frustrations, or "we keep having this problem" patterns.
- Desired assistant behavior, even when the user expresses it as vibe or personality.
- Messy input the future skill would receive.
- The artifact, decision, or handoff the user seems to need at the end.
- Tool, platform, domain, tone, or dependency hints.
- Constraints the user has already stated.

Start from visible evidence. Do not ask the user to restate what can be inferred.

### 2. Propose a Correctable Design Hypothesis

Turn the signal into a concrete starting frame before filling out the brief.

Use this pattern:

```markdown
My read: you need a [skill shape] that helps [target user] turn [messy situation] into [decision or artifact].

Why I think this:
- [signal from the user's words]
- [real workflow pressure]
- [why this should become a reusable skill]

The likely boundary: it should [core job], but should not [competing job].
```

Make the hypothesis useful enough to disagree with. A vague frame like "a skill that clarifies ideas" is not useful; a frame like "a brief-first skill that turns scattered product thoughts into a PRD-ready design brief" is useful because the user can correct the target, artifact, or boundary.

Stop after the frame check unless the user explicitly asked for the full brief in the same turn. Do not continue into the full template by default.

### 3. Run the Core Discovery Loop

Use this step whenever the user says they are unsure, only has a feeling, lists disconnected ideas, or asks for help figuring out what they want. This is not a fallback behavior; it is the main value of the skill.

If the hypothesis is probably right, ask only the next missing decision question:

```markdown
Next decision:
Question: [the one decision that most changes the design]
Recommended answer: [your default recommendation]
Why: [why this answer fits the visible signals]
```

If multiple interpretations are plausible, name at most three and recommend one default. Do not make the user choose from a long menu. A user who cannot name what they want needs a useful first draft to react to.

Use these discovery frames:

| User signal | Recommended frame |
|---|---|
| They describe a repeated task | Workflow-first skill: clarify trigger, steps, output, and verification. |
| They describe confusion or scattered notes | Brief-first skill: turn messy input into a structured decision artifact. |
| They describe a desired assistant personality | Behavior-first skill: convert the persona into decisions, boundaries, and evals. |
| They describe a tool or platform | Capability-first skill: clarify when to use the tool, required checks, and handoff rules. |
| They describe passing work to another agent | Handoff-first skill: define intake, decision record, output contract, and downstream owner. |

### 4. Define the Core Job

Write a one-sentence thesis:

```text
This skill helps [target user] turn [input situation] into [specific output] so they can [real outcome].
```

Reject theses that are too generic, such as "helps users think better" or "assists with writing". Replace them with a specific transformation and final artifact.

### 5. Clarify by Real Scenario

Use realistic situations, not abstract categories. Ask what the user is trying to get done under actual pressure.

Good questions:

- "Who is stuck when this skill is useful?"
- "What messy input do they usually bring?"
- "What decision or artifact must exist at the end?"
- "What would make the output immediately unusable?"

Ask one question at a time. If the likely answer is clear from context or code, state the assumption and continue instead of blocking. Prefer "Here is my recommended shape; correct the wrong part" over "What do you want this to be?"

### 6. Set Boundaries

Define what the skill does and does not do.

Use this rule: a good boundary preserves the core outcome and removes competing jobs. A bad boundary removes quality just to make the work easier.

Common scope repairs:

| Weak design | Stronger design |
|---|---|
| "A skill that helps with product work" | "A skill that turns a vague product idea into a PRD brief with assumptions, decisions, risks, and acceptance tests." |
| "A skill that writes better articles" | "A skill that reshapes raw notes into an article outline with thesis, audience, beats, and evidence gaps." |
| "A skill that reviews repos" | "A skill that maps a repo area into architecture notes, change risks, and verification commands before implementation." |

### 7. Design the Interaction

Specify how the future skill should behave with the user.

Include:

- How it helps the user discover intent when they cannot name it yet.
- Whether it should ask questions or proceed with assumptions.
- The maximum number of questions per turn.
- How it should recommend a path instead of dumping options.
- How it should handle vague, conflicting, or oversized requests.
- When it should stop and hand off to another skill or tool.

### 8. Define the Output Contract

Name the final artifact and make its sections explicit. If the output cannot be checked, the skill will be hard to improve.

Prefer concrete contracts:

- `Skill Design Brief`
- `PRD Brief`
- `Architecture Review Report`
- `Migration Plan`
- `Eval Set`
- `Implementation Handoff`

Avoid output contracts like "helpful advice" or "better understanding".

### 9. Define Decision Rules

Capture the judgment the future skill must apply repeatedly.

Examples:

- If the user does not know what they want, draft a recommended framing first and ask for correction instead of starting with a blank interview.
- If the user asks for a universal skill, split it into one core workflow and optional future extensions.
- If the output depends on external APIs or libraries, require current documentation checks before implementation.
- If the work is subjective, use qualitative review prompts instead of forcing brittle assertions.
- If the skill repeats deterministic work across test cases, move that work into `scripts/`.

### 10. Define the Quality Bar

State what "good" means in observable terms.

A strong quality bar usually covers:

- Discovery usefulness: the response gives the user a concrete frame to react to instead of making them start from a blank page.
- Hypothesis quality: the initial frame is specific enough for the user to correct.
- Question cadence: each turn resolves one decision, and every question includes a recommended answer.
- Trigger accuracy: the skill activates for the right prompts and avoids near misses.
- Completion: the expected artifact exists and has all required sections.
- Specificity: the output contains concrete decisions, not generic guidance.
- Transferability: the skill generalizes beyond the first example.
- Verification: eval prompts or assertions can catch weak output.

### 11. Identify Failure Modes

Name the most likely bad outputs and the cost they create.

Common failures:

- **Blank-page stall**: asks the user what they want before offering a useful interpretation of the weak signal they already gave.
- **Field-first interview**: asks for objective, persona, trigger, and output as form fields before proposing a design hypothesis.
- **Question pile-up**: asks several decisions at once, forcing the user to parse a form instead of answering the next important branch.
- **Recommendation vacuum**: asks a question without giving the recommended answer, pushing design work back onto the user.
- **Interview trap**: asks many questions but never gives a recommendation.
- **Persona shell**: defines a role but no workflow, output contract, or eval strategy.
- **Scope soup**: combines too many jobs and produces unverifiable output.
- **Overfit brief**: solves one example but cannot generalize.
- **Trigger drift**: description is too weak, too broad, or packed with abstract nouns.
- **No handoff**: produces a concept but not enough structure for skill-creator to create the skill.

### 12. Create Eval Prompts

Draft 2-3 realistic prompts that a real user would type. Include messy context, casual wording, or competing scope when useful.

Each eval should say what a good response must produce. Prefer prompts that reveal whether the skill clarifies intent and tightens scope.

### 13. Produce the Brief

Use this exact structure for the final artifact, not for the first response. Do not dump this whole template in the initial turn unless the user explicitly asks for a complete one-shot brief.

```markdown
# Skill Design Brief

## Skill Name
[recommended kebab-case name]

## Design Hypothesis
[The concrete starting frame that made the user's vague intent discussable, plus why it fits the visible signals.]

## One-Sentence Thesis
This skill helps [target user] turn [input situation] into [specific output] so they can [real outcome].

## Real User Scenario
[The realistic situation, pressure, and workflow that make the skill useful.]

## Core Objective
[The one job the skill must complete.]

## Target User
[Who uses it and what they likely know or do not know.]

## Operating Stance / Persona
[How the future skill should make decisions. Keep persona tied to actions, not roleplay.]

## Trigger Conditions
[User phrases, contexts, and task shapes that should trigger the skill.]

## Non-Trigger Conditions
[Adjacent tasks where this skill should not trigger.]

## Inputs
[Information, files, examples, links, or constraints the user may provide.]

## Outputs
[Final artifact and required sections.]

## Interaction Model
[How the skill asks questions, makes assumptions, recommends paths, and handles ambiguity.]

## Workflow
[Ordered steps the skill should follow.]

## Decision Rules
[Reusable judgment rules for ambiguous cases.]

## Quality Bar
[Observable criteria for a good result.]

## Failure Modes
[Bad outcomes to prevent and their practical cost.]

## Eval Prompts
[2-3 realistic test prompts with expected results.]

## Handoff To skill-creator
[A direct instruction that skill-creator can use to create SKILL.md and evals.]
```

## Drift Check Before Handoff

Before handing the brief to skill-creator, verify:

- The conversation followed the staged cadence unless the user explicitly requested a one-shot brief.
- The response started from a correctable design hypothesis, not a blank interview.
- Each turn asked at most one unresolved decision question.
- Every question included a recommended answer.
- Questions that could be answered from files, code, examples, or prior context were answered by inspection instead of user burden.
- The brief explains why the recommended frame fits the user's real scenario.
- Persona is expressed as operating stance and decision behavior, not theater.
- Boundaries protect the core job instead of weakening it.
- Eval prompts test discovery, scope control, and handoff readiness.

## Handoff Format

When the user approves the brief, end with:

```markdown
Use skill-creator next with this brief. Create the skill directory, write SKILL.md, add evals/evals.json, run or propose the first evaluation pass, and iterate from user feedback.
```

If skill-creator is available in the environment and the user asks to proceed, invoke it next. Preserve the brief as the source of truth.

## Anti-Patterns

Do not:

- Create the final `SKILL.md` before the user approves the brief, unless they explicitly ask for direct implementation.
- Dump the full `Skill Design Brief` in the first turn unless the user explicitly asks for a complete one-shot brief.
- Ask multiple design questions in one turn unless the user explicitly requests a questionnaire.
- Ask a question without providing your recommended answer.
- Ask the user for information that can be inferred from available context, files, code, or examples.
- Let the user choose between many weak names without recommending one.
- Treat persona, tone, or philosophy as a substitute for workflow and output contract.
- Remove important quality expectations just to reduce scope.
- Produce a brief without eval prompts.
- Hand off to skill-creator with unresolved contradictions.

## Output Style

Be direct and staged. Start with the recommended shape, explain the tradeoff, and stop at the smallest useful checkpoint. Use real scenario plus mechanism: first show why the design matters in a user's actual workflow, then explain how the skill structure handles it. Expand into the full brief only after the required design decisions are resolved or the user explicitly asks for a complete brief.
