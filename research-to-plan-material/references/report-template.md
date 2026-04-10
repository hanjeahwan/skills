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
┌──────────────────────────┐
│ [User / Caller / Input]  │
└─────────────┬────────────┘
              │ request / event / artifact
              ▼
┌──────────────────────────┐
│ [Entry Boundary]         │
│ API / UI / Worker        │
└─────────────┬────────────┘
              │ orchestrates
              ▼
┌──────────────────────────┐
│ [Coordinator / Runtime]  │
└───────┬─────────┬────────┘
        │         │
        │         ├──────────────────────┐
        │         │                      │
        ▼         ▼                      ▼
┌────────────┐ ┌──────────────┐  ┌──────────────┐
│ [State]    │ │ [Execution]  │  │ [Artifacts]  │
│ DB / Cache │ │ Jobs / Tools │  │ Files / Blob │
└─────┬──────┘ └──────┬───────┘  └──────┬───────┘
      │               │                 │
      └───────────────┴────────┬────────┘
                               ▼
                    ┌────────────────────┐
                    │ [Replay / Output]  │
                    │ UI / API / Export  │
                    └────────────────────┘
```

- [Explain the main components]
- [Explain the critical boundaries]
- [Explain where state is persisted]
- [Explain how outputs are replayed or consumed]

### Request / Data Flow

```text
┌──────────────────────────┐
│ [Trigger / Request]      │
└─────────────┬────────────┘
              │
              ▼
┌──────────────────────────┐
│ [Ingress / Validation]   │
└─────────────┬────────────┘
              │ accepted input
              ▼
┌──────────────────────────┐
│ [Coordinator / Router]   │
└───────┬─────────┬────────┘
        │         │
        ▼         ▼
┌────────────┐ ┌──────────────┐
│ [Read]     │ │ [Work]       │
│ state/data │ │ transform/run│
└─────┬──────┘ └──────┬───────┘
      │               │
      └───────────────┴────────┐
                               ▼
                    ┌────────────────────┐
                    │ [Persist / Publish]│
                    └────────────┬───────┘
                                 │
                                 ▼
                    ┌────────────────────┐
                    │ [Replay / Response]│
                    └────────────────────┘
```

- [Explain the input boundary]
- [Explain the critical transformations]
- [Explain what gets persisted and when]
- [Explain how the final result is replayed, returned, or consumed]

## GitHub Research

- [Finding with inline citation]
- [If using GitHub API metrics or recency claims, pair them with a stable GitHub page when possible, or note `sampled YYYY-MM-DD via GitHub API`]

## External Research

- [Finding with inline citation]

## Key Findings

1. [Finding]
2. [Finding]

## Recommendations

- [Recommendation and rationale]

## Open Questions

- [Unresolved question or contradiction, or `None`]

## Downstream Use

- [How later work might use this report, or `Not needed for this topic`]

## Sources

### Local Repo Evidence

- Repo: `path/to/file`

### GitHub / External Sources

- [citation:Title](URL)

## Methodology

- Local grounding: [How repo evidence was gathered]
- GitHub research: `$github-deep-research` was invoked literally
- External research: `$deep-research` was invoked literally
- GitHub metric provenance: [If GitHub API metrics were used, note sampled date and whether a stable GitHub page was paired]
