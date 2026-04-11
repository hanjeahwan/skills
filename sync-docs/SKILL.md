---
name: sync-docs
description: Use when codebase has changed and docs/* may be stale, when adding new features or services, after refactoring module boundaries, or when asked to "update docs", "sync docs", or "check docs freshness". Also triggers for verifying doc consistency after architectural changes, when check:foundations fails, when promoting TECH_DEBT items to CONVENTIONS, or after creating new design-docs/solutions/plans that require upstream doc updates.
---

# Sync Docs

Keep `docs/` in sync with the living codebase. Each doc has a defined purpose, format, and update trigger — this skill enforces all three.

## Doc Ecosystem

```
CLAUDE.md (root)              ← Entry point for AI agents
  references ↓
docs/ARCHITECTURE.md          ← System structure, data flow, invariants, dependency rules
docs/CONVENTIONS.md           ← Enforceable coding rules with rationale and source
docs/TECH_DEBT.md             ← Tracked issues with occurrence counts and severity
docs/QUALITY_SCORE.md         ← Per-module health grades (A-D)
docs/SECURITY.md              ← Auth, secrets, validation, PII boundaries
docs/FRONTEND.md              ← Component patterns, state management, provider tree
docs/DESIGN.md                ← Design tokens, layout patterns, theming, motion
docs/design-docs/             ← Architecture Decision Records (ADRs)
docs/solutions/               ← Resolved incident solutions with root cause and prevention
docs/plans/                   ← Implementation plans with execution state
docs/brainstorms/             ← Exploration and requirements documents
```

### Dependency Graph

```
CLAUDE.md
  └─ summarizes and links to all docs/*

ARCHITECTURE.md
  └─ defines invariants and dependency rules that CONVENTIONS.md enforces
  └─ defines module boundaries that QUALITY_SCORE.md grades

CONVENTIONS.md
  └─ rules promoted from TECH_DEBT.md (3+ occurrences)
  └─ references ARCHITECTURE.md for structural rationale

TECH_DEBT.md
  └─ feeds into CONVENTIONS.md (promotion rule)
  └─ feeds into QUALITY_SCORE.md (known issues column)

QUALITY_SCORE.md
  └─ grades modules defined in ARCHITECTURE.md codemap
  └─ references TECH_DEBT.md issues

FRONTEND.md + DESIGN.md
  └─ detail the frontend subset of ARCHITECTURE.md
  └─ follow patterns declared in CONVENTIONS.md

design-docs/
  └─ ADRs referenced as Source links from CONVENTIONS.md

solutions/
  └─ resolved incidents referenced from TECH_DEBT.md and CONVENTIONS.md

plans/
  └─ implementation plans; status tracked per Plans as Artifacts principle

brainstorms/
  └─ exploration docs that feed into plans/ and design-docs/
```

**Key rule:** Information flows downward. `CLAUDE.md` summarizes; `docs/*` contains detail. Never duplicate — reference instead.

**Note:** `CLAUDE.md` has a compact `Maintenance > Doc Update Triggers` table — that is the agent-facing quick reference. This skill's change-type table (in Sync Process) is the detailed version with specific file-level guidance.

## Format Specifications

### CLAUDE.md

Commands section format:

```markdown
- **Label:** `exact command` — optional description after em dash
```

Sections required: Commands, Docs (with subsections: Architecture, Conventions, Tech Debt, Quality Score, Frontend, Design System, Security, Directories), Boundaries, Git, Maintenance (Doc Update Triggers + Promotion Rule), Troubleshooting.

### ARCHITECTURE.md

Sections: Bird's Eye Overview, Codemap, Data Flow (with ASCII diagrams), Invariants, Cross-Cutting Concerns.

Invariant format:

```markdown
- Must always: [rule]
- Must never: [rule]
```

Codemap format:

```markdown
- `path/to/module/` — One-line purpose
```

### CONVENTIONS.md

Entry format (strict — every entry must have all three fields):

```markdown
- Rule: [single enforceable sentence]
- Rationale: [why this rule exists]
- Source: [link to ADR, solution doc, or "Project convention"]
```

Grouped by category: File Naming, Imports, Components, External API Integration, Error Handling, State Management, Styling, Code Quality, i18n, Git, Environment Variables, Testing.

### TECH_DEBT.md

Table format:

```markdown
| Issue | Occurrences | Severity | Status | Source |
```

- Severity: `critical`, `high`, `medium`, `low`
- Status: `active`, `scheduled`, `resolved`
- When Occurrences >= 3: suggest promotion to CONVENTIONS.md

### QUALITY_SCORE.md

Table format:

```markdown
| Module | Tests | Last Reviewed | Grade | Known Issues |
```

- Grades: A (strong), B (mostly healthy), C (drift), D (high risk)
- Module paths must match ARCHITECTURE.md codemap

### SECURITY.md

Sections: Scope, Authentication and Authorization, Input Validation Boundaries, Secrets Management, API Security, Dependency Auditing, Logging and PII, Incident Response.

### FRONTEND.md

Sections: Component Conventions, State Management (with Provider Tree ASCII), API Integration Patterns, Accessibility Baseline, Performance, Testing.

### DESIGN.md

Sections: Design Tokens (Color, Typography, Spacing, Border Radius), Component Library, Layout Patterns (with ASCII diagram), Responsive Strategy, Direction Support, Motion Guidelines, Theming, Design QA.

## Sync Process

### Step 1: Detect What Changed

Determine scope of changes since docs were last updated:

```bash
# Files changed since last doc update
git log --oneline --name-only docs/ | head -1  # last doc commit
git diff --name-only <last-doc-commit>..HEAD -- src/ backend/ package.json tsconfig.json
```

Categorize changes:

| Change Type               | Docs to Update                                               |
| ------------------------- | ------------------------------------------------------------ |
| New/moved files in `src/` | ARCHITECTURE.md codemap, QUALITY_SCORE.md                    |
| New external service      | ARCHITECTURE.md codemap + data flow, SECURITY.md             |
| New dependency            | CONVENTIONS.md (if pattern change), FRONTEND.md or DESIGN.md |
| New component pattern     | FRONTEND.md, DESIGN.md                                       |
| New context/provider      | FRONTEND.md provider tree, ARCHITECTURE.md state management  |
| Auth changes              | SECURITY.md, ARCHITECTURE.md auth section                    |
| Config/tooling changes    | CLAUDE.md commands, CONVENTIONS.md code quality              |
| New feature module        | ARCHITECTURE.md codemap, QUALITY_SCORE.md new row            |
| Bug fix pattern           | TECH_DEBT.md (track), possibly CONVENTIONS.md (promote)      |
| New design decision       | docs/design-docs/ new ADR                                    |
| Resolved incident         | docs/solutions/ new solution doc                             |
| New implementation plan   | docs/plans/ new plan file                                    |

### Step 2: Audit Current Docs

For each affected doc, use an Explore agent to:

1. Read the current doc
2. Read the relevant source code
3. Identify stale content, missing content, and format violations

### Step 3: Update with Format Enforcement

Apply updates following strict format rules. For each doc:

1. **Never add free-form text** outside defined sections
2. **Never duplicate** information that belongs in another doc — add a reference
3. **Preserve existing valid content** — only add/modify what changed
4. **Match the established format** exactly (see Format Specifications above)

### Step 4: Cross-Reference Check

After all updates, verify consistency:

- [ ] ARCHITECTURE.md codemap paths all exist on disk
- [ ] QUALITY_SCORE.md module list matches ARCHITECTURE.md codemap
- [ ] CONVENTIONS.md rules don't contradict ARCHITECTURE.md invariants
- [ ] TECH_DEBT.md issues with 3+ occurrences have promotion suggestion
- [ ] FRONTEND.md provider tree matches actual `src/app/providers.tsx`
- [ ] DESIGN.md tokens match actual `src/styles/theme.css`
- [ ] CLAUDE.md Conventions Summary reflects current `docs/CONVENTIONS.md`
- [ ] CLAUDE.md Auth section reflects current `docs/SECURITY.md`
- [ ] No information duplicated across docs — only references
- [ ] CONVENTIONS.md Source links to `docs/design-docs/` resolve to existing files
- [ ] `docs/plans/` completed work has `status: completed` in frontmatter
- [ ] CLAUDE.md `Maintenance > Doc Update Triggers` table covers all `docs/*` entries

### Step 5: Verify

Run mechanical checks first, then manual verification:

```bash
pnpm run check:foundations
```

Fix any failures before proceeding. Then for each updated doc, confirm:

1. **Format compliance** — every section header, entry format, and table column matches the Format Specifications above
2. **Codebase accuracy** — spot-check 3+ claims per doc against actual source files (read the file, not from memory)
3. **Cross-doc consistency** — any entity mentioned in two docs uses the same name and path
4. **No stale references** — no paths to deleted files, no mentions of removed features or renamed modules
5. **No orphan content** — every QUALITY_SCORE.md module has a codemap entry; every CONVENTIONS.md rule has a rationale and source

## Common Mistakes

| Mistake                                                            | Fix                                                            |
| ------------------------------------------------------------------ | -------------------------------------------------------------- |
| Adding a convention without all 3 fields (Rule/Rationale/Source)   | Every entry needs all three — no exceptions                    |
| Putting implementation detail in CLAUDE.md                         | CLAUDE.md summarizes; detail goes in docs/\*                   |
| Duplicating invariants between ARCHITECTURE.md and CONVENTIONS.md  | Invariants in ARCHITECTURE.md; CONVENTIONS.md references them  |
| Adding a module to QUALITY_SCORE.md not in ARCHITECTURE.md codemap | Add to codemap first                                           |
| Forgetting to update CLAUDE.md summary after docs/\* change        | CLAUDE.md Conventions Summary must reflect docs/CONVENTIONS.md |
| TECH_DEBT resolved but still marked active                         | Update status to `resolved` when fixed                         |
| Format drift (missing table columns, wrong section headers)        | Follow Format Specifications exactly                           |
