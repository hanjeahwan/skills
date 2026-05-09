# Source Alignment

Use this reference when checking whether the skill still aligns with the user's source PDF, or when updating the skill after another audit pass.

The source PDF is *Dive Into Design Patterns* by Alexander Shvets. Do not copy long passages from it. Use this file as a coverage map, not as a replacement for the source.

## PDF-To-Skill Coverage

| Source area | PDF pages from outline | Skill coverage | Status |
|---|---:|---|---|
| Copyright, dedication, reading notes | 3-7 | Not skill content except copyright caution in `SKILL.md` | Intentionally excluded |
| OOP basics and pillars | 8-20 | `references/design-foundations.md` object relationship and SOLID grounding | Covered at applied level |
| Relations between objects | 21-26 | `references/design-foundations.md` relationship vocabulary; `references/pattern-catalog.md` relation vocabulary | Covered |
| What patterns are and why they matter | 27-32 | `SKILL.md` operating model; `references/source-alignment.md` and `references/pattern-anatomy.md` | Covered at workflow level |
| Good design: reuse and extensibility | 33-37 | `references/design-foundations.md` good design pressure | Covered |
| Design principles | 38-51 | `references/design-foundations.md` core design principles | Covered |
| SOLID principles | 52-71 | `references/design-foundations.md` SOLID pressure tests | Covered |
| Catalog overview | 72 | `references/selection-guide.md`; `references/pattern-catalog.md` | Covered |
| Creational patterns | 73-147 | `references/pattern-catalog.md`; `references/pattern-anatomy.md`; `references/code-reference.md` for common enterprise cases | Covered |
| Structural patterns | 148-246 | `references/pattern-catalog.md`; `references/pattern-anatomy.md`; `references/code-reference.md` for common enterprise cases | Covered |
| Behavioral patterns | 247-409 | `references/pattern-catalog.md`; `references/pattern-anatomy.md`; `references/code-reference.md` for common enterprise cases | Covered |
| Conclusion | 410 | Skill quality bar and practical workflow | Covered indirectly |

## Pattern Chapter Structure Coverage

The PDF pattern chapters consistently use a structure like this:

| Source chapter element | Skill equivalent |
|---|---|
| Intent / aliases | `references/pattern-catalog.md` and `references/pattern-anatomy.md` |
| Problem | `references/pattern-anatomy.md` `Problem Pressure` |
| Solution | `references/pattern-anatomy.md` `Solution Mechanism` |
| Structure | `references/pattern-anatomy.md` `Structure`; code roles in `references/code-reference.md` |
| Pseudocode | `references/code-reference.md` implementation skeletons; `references/pattern-code-sketches.md` compact sketches |
| Applicability | `references/selection-guide.md`; `references/pattern-anatomy.md` |
| How to implement | `references/refactor-playbooks.md`; `references/pattern-anatomy.md` |
| Pros and cons | `references/pattern-catalog.md`; `references/enterprise-review-checklist.md`; `references/pattern-anatomy.md` |
| Relations with other patterns | `references/pattern-catalog.md`; `references/selection-guide.md`; `references/pattern-anatomy.md` |

## Known Scope Choices

- The skill intentionally avoids copying book prose or examples verbatim.
- The skill prioritizes enterprise codebase usage over tutorial completeness.
- The code reference gives full skeletons for common enterprise combinations, while `pattern-code-sketches.md` provides compact code references for every GoF pattern.
- Language-specific syntax is intentionally secondary. When editing a repo, follow the repo's language, framework, and test conventions.

## Re-Audit Checklist

Run this checklist after future edits:

1. Extract the PDF outline and confirm the same source areas are represented above.
2. Confirm all 22 GoF patterns appear in `pattern-catalog.md`, `selection-guide.md`, and `pattern-anatomy.md`.
3. Confirm foundation terms are present: variation encapsulation, program to interface, composition over inheritance, SOLID, object relationships.
4. Confirm implementation references still include code boundary, wiring boundary, verification shape, and a code sketch route for every GoF pattern.
5. Confirm no private purchase markers, emails, or long source excerpts were copied.
6. Confirm `SKILL.md` remains under 500 lines and references over 100 lines have a table of contents.

Deterministic check:

```bash
python scripts/verify_skill.py --pdf /path/to/dive-into-design-patterns.pdf
```

Run without `--pdf` when the source PDF is unavailable; the script still verifies skill structure, coverage, privacy markers, evals, and TypeScript sketch safety.

When the user asks to audit or verify this skill, run the deterministic check if tools are available. Do not treat audit as read-only unless the user explicitly says not to run commands.

If the task context forbids reading `evals/evals.json`, run:

```bash
python scripts/verify_skill.py --skip-evals
```

Report that eval coverage was not checked. This is a degraded verification mode, not a full pass.
