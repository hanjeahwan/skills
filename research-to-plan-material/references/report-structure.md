# Report Structure

Use this when writing `.research/<topic-name>/report.md`.

## First Rule

Prefer repo-local conventions only when they do not remove the mandatory sections below. This structure defines the minimum stable contract for the report.

## Mandatory Sections

These headings are mandatory unless truly not applicable:

- `Research Question`
- `Executive Summary`
- `Local Repo Grounding`
- `High-Level Architecture / Data Flow`
- `GitHub Research`
- `External Research`
- `Key Findings`
- `Recommendations`
- `Open Questions`
- `Sources`
- `Methodology`

If a section does not apply, keep the heading and write `Not needed for this topic`.
Use these headings verbatim, in English, and in this exact order. Do not localize them, rename them, or merge them into other sections.

## Baseline Structure

```markdown
# [Topic Title]

**Date:** YYYY-MM-DD
**Topic Folder:** `.research/<topic-name>/`
**Status:** Draft

## Research Question

[What is being investigated and why]

## Executive Summary

[2-4 short paragraphs summarizing the answer]

## Local Repo Grounding

- [Finding with repo-relative evidence]

## High-Level Architecture / Data Flow

### System Architecture

```text
┌────────────────────┐
│ [Producer / Input] │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ [Coordinator]      │
└──────┬─────┬───────┘
       │     │
       ▼     ▼
┌──────────┐ ┌──────────┐
│ [State]  │ │ [Work]   │
└────┬─────┘ └────┬─────┘
     │            │
     └──────┬─────┘
            ▼
     ┌──────────────┐
     │ [Output]     │
     └──────────────┘
```

- [Explain the diagram in 2-5 bullets]

### Request / Data Flow

```text
┌────────────────────┐
│ [Trigger / Input]  │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ [Ingress]          │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ [Coordinator]      │
└──────┬─────┬───────┘
       │     │
       ▼     ▼
┌──────────┐ ┌──────────┐
│ [Read]   │ │ [Work]   │
└────┬─────┘ └────┬─────┘
     │            │
     └──────┬─────┘
            ▼
     ┌──────────────┐
     │ [Persist]    │
     └──────┬───────┘
            ▼
     ┌──────────────┐
     │ [Output]     │
     └──────────────┘
```

- [Explain the flow in 2-5 bullets]

## GitHub Research

- [Finding with inline citation]
- [If using a dynamic GitHub API metric, pair it with a stable GitHub page when possible, or stamp the sampled date and API provenance in the sentence]

## External Research

- [Finding with inline citation]

## Key Findings

1. [Finding]
2. [Finding]

## Recommendations

- [Recommendation and rationale]

## Open Questions

- [Unresolved question or contradiction]

## Downstream Use (Optional)

- [How later work might use this report]

## Sources

### Local Repo Evidence

- Repo: `path/to/file`

### GitHub / External Sources

- [citation:Title](URL)

## Methodology

- Local grounding: [How local grounding was done]
- GitHub research: `$github-deep-research` was invoked literally
- External research: `$deep-research` was invoked literally
- GitHub metric provenance: [If GitHub API metrics were used, note sampled date and whether a stable GitHub page was paired]
```

## Authoring Rules

1. Keep the report evidence-first. Recommendations should be downstream of findings.
2. Use repo-relative paths for repo evidence.
3. When supporting evidence comes from sibling repos, keep the path repo-relative within that repo and label it explicitly.
4. When supporting evidence comes from local installed packages or vendor code, label it as local implementation evidence.
5. Use inline citations for GitHub and web-derived claims.
6. Keep planning references optional. The report is valid even if no plan is ever written.
7. Do not write implementation units, sprint tasks, rollout choreography, or code patches in this document.
8. Use stable source subsection names: `Local Repo Evidence` and `GitHub / External Sources`.
9. In the `Sources` section, list repo evidence as bullets starting with `- Repo:` and external evidence as bullets using `[citation:Title](URL)`.
10. In the `Methodology` section, explicitly say that `$github-deep-research` and `$deep-research` were invoked literally.
11. Do not translate the mandatory section headings even if the report body is written in another language.
12. When the topic has multiple components, boundaries, or sequential stages, the `High-Level Architecture / Data Flow` section must include an ANSI box-drawing diagram inside a fenced `text` block.
13. Use `System Architecture` when the report needs to explain stable components and boundaries.
14. Use `Request / Data Flow` when the report needs to explain sequencing, transformations, persistence timing, or replay.
15. For complex topics, include both subsections in the same order shown above.
16. When using GitHub API URLs for dynamic metrics or recency claims, pair them with a stable GitHub HTML page when possible; otherwise stamp the sampled date and GitHub API provenance in the finding text or methodology.
