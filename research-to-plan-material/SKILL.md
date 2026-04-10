---
name: research-to-plan-material
description: Combine $deep-research and $github-deep-research to investigate a technical topic, repository, feature direction, architecture choice, library decision, or open-source dependency, then save a durable research report under `.research/topic-name/`. Use this when the user wants a stored research artifact and the topic needs both local repo grounding and external or GitHub research. Do not use it for chat-only answers, pure repo archaeology, or pure external research without a durable artifact.
---

# Research To Plan Material

## Overview

Turn research into a durable workspace artifact. Gather local repo evidence, GitHub-native evidence, and broader external evidence, then write a full report under the repo root at `.research/<topic-name>/report.md`.

## Use This Skill Only When

Use this skill when all of these are true:

- the user explicitly wants the research saved or stored on disk, or wants a durable report that later work can cite
- the topic materially touches the current workspace or a sibling repo enough to justify local grounding
- the topic also needs external research, GitHub research, or both

If the topic is mostly external but still needs a durable artifact for the current workspace, you may use this skill only when you can still ground it with meaningful local evidence or explicitly state why local evidence is thin.

Use-case examples:

- Use this skill: "Research how our AI chat replay should evolve, compare it to canonical OSS repos, and save the findings under `.research/`."
- Use this skill: "Investigate artifact publication patterns that touch this workspace, compare them against industry repos, and store a durable report."
- Do not use this skill: "Explain LangGraph checkpoints to me in chat."
- Do not use this skill: "Read this repo and tell me how the current thread service works."
- Do not use this skill: "Plan the implementation for thread persistence."

Do not use this skill when:

- the user only wants a direct answer in chat
- the question can be handled by `$deep-research` or `$github-deep-research` alone without a durable artifact
- the topic is pure local repo archaeology or implementation analysis with no real external / GitHub research need
- the topic does not need local repo grounding
- the user wants a plan, implementation, or code change rather than a research report

## Workflow Map

```text
┌───────────────────┐
│ User research ask │
└─────────┬─────────┘
          ▼
┌─────────────────────────────┐
│ Normalize topic folder name │
│ .research/<topic-name>/     │
└─────────┬───────────────────┘
          ▼
┌─────────────────────────────┐
│ Local repo grounding        │
│ + GitHub deep research      │
│ + external deep research    │
└─────────┬───────────────────┘
          ▼
┌─────────────────────────────┐
│ Write durable report        │
│ .research/<topic>/report.md │
└─────────────────────────────┘
```

## 1. Preflight Availability Check

Before doing any research, verify that both `$deep-research` and `$github-deep-research` are available for literal use in the current environment.

Rules:

- If both are available, continue.
- If either one is unavailable for literal use, tell the user exactly which one is unavailable and stop.
- Do not manually reproduce either skill's workflow as a fallback.
- Do not continue into local grounding, GitHub research, external research, or report writing after a failed preflight.

Use this stop message pattern when preflight fails:

```text
Stop: this research workflow requires literal availability of both $deep-research and $github-deep-research.

Unavailable:
- [list the missing skill or skills]

Install:
- $deep-research: https://skillsmp.com/skills/bytedance-deer-flow-skills-public-deep-research-skill-md
- $github-deep-research: https://skillsmp.com/skills/bytedance-deer-flow-skills-public-github-deep-research-skill-md

No report was generated.
```

## 2. Create The Research Workspace

Read `references/storage-layout.md` first.

Default output location:

```text
.research/<topic-name>/report.md
```

Rules:

- Create the topic folder at the repo root.
- Normalize the topic name to lowercase kebab-case unless the repo already has a clearer local naming convention.
- Treat the report as the primary artifact. Do not default to `docs/brainstorms/`, `docs/plans/`, or `docs/solutions/`.
- If the user later wants to turn the report into a requirements doc or solution doc, do that as a separate follow-up step.

## 3. Ground The Topic In The Local Repo

Inspect the local workspace directly before running external research.

Capture at least:

- relevant packages, services, modules, and entry points
- current implementation patterns and constraints
- existing documents, ADRs, TODOs, or prior reports related to the topic
- exact file paths that support or contradict the proposed direction

Minimum local grounding floor:

- cite at least 4 concrete local repo paths when the topic materially touches the workspace
- if the topic is mostly external and fewer than 4 local paths are relevant, say that explicitly in the report
- do not summarize the repo in generic prose without anchored file evidence

When sibling repos are relevant, treat one repo as the artifact home and the others as supporting evidence. Keep in-report file references repo-relative within their own repo and label cross-repo evidence explicitly, for example:

- `web-app: src/features/chat/message-schema.ts`
- `api-service: services/agent/sandbox_tools.py`

If local dependency or installed package evidence matters, label it explicitly as local implementation evidence rather than project-owned code.

## 4. Run GitHub-Native Research

Run `$github-deep-research` when the topic involves:

- a GitHub repository
- an open-source framework or dependency
- release history, roadmap, issue trends, PR history, or contributor activity
- architecture or timeline questions that benefit from GitHub API evidence

Default target quality bar:

- Prefer industry-grade, widely adopted, or otherwise notable open-source repositories.
- When using GitHub research for comparison or pattern extraction, favor canonical repos maintained by the framework, vendor, or an ecosystem-defining project.
- Do not fill the report with low-signal small repos when stronger reference implementations exist.
- If the user's topic is not itself a GitHub repo, use GitHub research to inspect well-known repos that represent the pattern, architecture, or dependency under study.

Selection rubric:

1. Prefer an official vendor or framework repo first.
2. Add ecosystem-defining repos next when they represent the real production pattern better than the official repo alone.
3. Add focused reference implementations only when they teach something the canonical repos do not.
4. Use small or niche repos only if no stronger reference exists, and explain why they were included.

Minimum GitHub evidence floor when GitHub research is warranted:

- inspect at least 2 GitHub repositories
- include at least 1 official or canonical repository
- explain in the report why each selected repository met the quality bar

Mandatory deeper GitHub investigation:

- inspect releases when the topic involves churn, migration, or recency
- inspect issues or discussions when the topic involves pain points, adoption friction, or roadmap uncertainty
- inspect PRs or commit history when the topic involves architectural evolution or timeline claims

Keep inline external citations in the final report whenever claims come from GitHub or web sources.

When using GitHub API URLs for dynamic metrics or recency-sensitive claims:

- pair them with a stable GitHub HTML page when possible
- if the metric only comes from the API, stamp the sentence with the sampled date and say it was sampled via the GitHub API

## 5. Run Broader External Research

Run `$deep-research` for multi-angle external research around the same topic.

Also enforce these rules:

- When the topic touches a specific package, framework, SDK, or API, verify best practices with Context7 or official documentation first.
- If documentation is incomplete, inspect local source, lockfiles, manifests, `.d.ts`, or implementation files instead of guessing.
- Use the actual current date when "latest", "recent", "today", or version-sensitive guidance matters.
- Gather both recommended patterns and failure modes, tradeoffs, or limitations.
- Keep direct source links so the final report can cite them.

Minimum external evidence floor:

- include at least 3 high-signal external citations when the topic depends on external guidance
- use official docs as the anchor whenever they exist
- if high-signal sources disagree, surface the disagreement instead of flattening it away

## 6. Synthesize Into A Research Report

Read `references/report-structure.md` before writing.
If useful, start from `references/report-template.md` and fill it rather than inventing your own section layout.

Separate clearly:

- local repo findings
- GitHub research findings
- broader external findings
- inferred recommendations
- unresolved questions

Do not write the report like a plan. It is a research artifact first.

The report may include a short section such as `Downstream Use` or `Questions For Follow-up`, but only as optional downstream guidance. Do not write implementation units, task breakdowns, or rollout choreography.

Treat the report headings in `references/report-structure.md` as mandatory unless a section is truly not applicable. When a mandatory section does not apply, keep the heading and state `Not needed for this topic`.
Use the mandatory headings verbatim in English and in the documented order. Do not localize, rename, merge, or reorder them.
When the topic involves components, boundaries, or sequential stages, include the `High-Level Architecture / Data Flow` section with an ANSI box-drawing diagram inside a fenced `text` block.
Choose `System Architecture`, `Request / Data Flow`, or both based on the topic shape, following the rules in `references/report-structure.md`.

## 7. Quality Bar

The artifact is complete only when `.research/<topic-name>/report.md` contains:

- a clear research question or problem frame
- local repo grounding with repo-relative evidence
- GitHub-native findings when the topic warrants it
- broader external findings with inline citations
- synthesized recommendations with rationale
- explicit open questions or contradictions
- a source list or evidence section

If any API, contract, or library behavior is still uncertain, do not guess. Research it or mark it as unresolved.

## 8. Finish Checklist

Before considering the report complete, verify all of these:

- the report uses the required output path `.research/<topic-name>/report.md`
- every nontrivial GitHub-derived or web-derived claim has an inline citation
- dynamic GitHub API claims are paired with a stable GitHub page or explicitly stamped with sampled date + GitHub API provenance
- findings and recommendations are clearly separated
- at least one section explicitly names unresolved questions, contradictions, or `None`
- the GitHub repositories chosen are explained, not just listed
- repo evidence uses consistent path labeling
- the mandatory headings appear verbatim and in order
- the `Sources` section contains the exact subsection labels `Local Repo Evidence` and `GitHub / External Sources`
- the `Methodology` section explicitly states that `$github-deep-research` and `$deep-research` were invoked literally
- the report does not drift into implementation planning
