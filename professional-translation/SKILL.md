---
name: professional-translation
description: Use this skill whenever the user asks for a reliable translation workflow, professional translation, localization, translation QA, glossary/style-guide alignment, codebase or document translation, source-language cleanup, bilingual review, or high-fidelity translation where meaning, terminology, formatting, placeholders, legal/technical requirements, or brand voice must be preserved. This skill should trigger for translation work across documents, code comments, UI copy, product strings, Markdown, websites, slide decks, spreadsheets, support content, compliance text, and mixed-content repositories, even when the user only says "translate this" but quality control or workflow discipline is needed.
---

# Professional Translation

Use this skill to run translation as a controlled workflow, not as a one-pass rewrite. The purpose is to preserve meaning, intent, constraints, terminology, audience fit, and technical structure while moving content from a source language into a target language.

This skill supports:

- Document translation: Markdown, Word, PDFs after extraction, slide decks, spreadsheets, policies, support docs, product docs.
- Product and software localization: UI strings, app copy, website content, release notes, metadata, onboarding flows, screenshots with embedded text, and in-context copy.
- Codebase translation: comments, docs, prompts, READMEs, configuration descriptions, non-locale user-facing strings, and source-language cleanup.
- High-stakes translation: legal, compliance, medical-adjacent, financial, security, architecture, safety, or contractual content where omissions are unacceptable.

## Core Principle

Translation quality comes from specifications, context, terminology control, review, and verification. Fluent target-language text is not enough if it changes obligations, drops edge cases, breaks placeholders, weakens warnings, or ignores the content's intended use.

## Workflow Map

```
┌────────────────────────────┐
│ Intake translation request  │
└──────────────┬─────────────┘
               ▼
┌────────────────────────────┐
│ Build scope inventory       │
│ and protected-content list  │
└──────────────┬─────────────┘
               ▼
┌────────────────────────────┐
│ Create translation brief    │
│ audience, locale, purpose   │
│ terminology, style, risk    │
└──────────────┬─────────────┘
               ▼
┌────────────────────────────┐
│ Translate one work unit     │
│ with source beside target   │
└──────────────┬─────────────┘
               ▼
┌────────────────────────────┐
│ Self-check: meaning, terms, │
│ formatting, placeholders    │
└──────────────┬─────────────┘
               ▼
┌────────────────────────────┐
│ Review and LQA scoring      │
└──────────────┬─────────────┘
               ▼
┌────────────────────────────┐
│ Quality gate satisfied?     │
└───────┬────────────────────┘
        │ no
        ▼
┌────────────────────────────┐
│ Fix current work unit and   │
│ repeat review loop          │
└───────┬────────────────────┘
        │ yes
        ▼
┌────────────────────────────┐
│ Final verification and      │
│ delivery report             │
└────────────────────────────┘
```

## Intake

Before translating, establish the minimum translation brief. Extract what is already known from the user request, files, repository conventions, existing translations, glossaries, style guides, and surrounding context.

Required brief fields:

```markdown
Source language: <language or detected language>
Target language and locale: <language + region when relevant>
Content type: <docs | UI | legal | marketing | technical | codebase | mixed>
Audience: <who will read or use it>
Purpose: <what the translated content must accomplish>
Tone/register: <formal, conversational, instructional, legal, brand-specific, etc.>
Terminology source: <existing glossary, prior translations, domain vocabulary, or "derive from corpus">
Protected content: <paths, strings, terms, placeholders, identifiers, or files that must not be translated>
Quality bar: <standard | high-stakes | publish-ready | exact 1:1>
Delivery format: <edit files in place, bilingual table, translated document, patch, report>
```

Ask only for missing information that would materially change the translation. If a safe assumption is available, state it and continue.

## Scope Inventory

Create an inventory before editing or delivering translated content.

For a single document, list sections, tables, figures, comments, footnotes, embedded text, and non-text assets that may contain translatable text.

For a codebase or folder, scan for source-language text and list eligible paths before updates. Use search tools for discovery, but do not bulk-translate by script. Treat the inventory as the control surface for the whole job.

For product localization, list translation units by feature, screen, namespace, file, or content system. Include screenshots, key descriptions, and character or layout constraints when available.

Inventory format:

```markdown
Translation inventory:
1. path/or/unit - content type - risk level - action
2. path/or/unit - content type - risk level - action

Protected or excluded content:
1. path/or/unit - reason
2. term/string/key - reason
```

Common protected content:

- Code identifiers, API names, enum values, keys, routes, import paths, environment variables, command names, package names, URLs, IDs, schema fields, and protocol literals.
- Placeholders and template syntax such as `{name}`, `${value}`, `%s`, `%{count}`, `{{token}}`, ICU arguments, HTML tags, Markdown links, XML tags, and component references.
- Locale catalogs, translation memory exports, or source-of-truth translation files unless the user explicitly includes them.
- Vendor, generated, build, dependency, archive, and hidden-agent directories unless explicitly in scope.
- Product names, brand terms, trademarks, regulated phrases, legal terms, and unresolved domain vocabulary.

## Work Unit Rule

Translate one coherent work unit at a time, then review that same unit before moving on.

Choose the work unit by content shape:

- Document: one section, page, table, slide, or heading subtree.
- Codebase: one file at a time unless the user explicitly defines a smaller unit.
- UI strings: one screen, flow, namespace, or group of context-linked strings.
- Spreadsheet: one sheet, column group, or labeled table.
- Mixed assets: one asset or asset group with all visible and embedded text.

High-stakes or architecture-sensitive work requires strict sequential processing: read one unit fully, translate it, review it, fix it, and only then continue. Deterministic scripts may help find text, validate placeholders, or count remaining source-language spans; they must not perform blind multi-file translation rewrites.

## Translation Method

For each work unit:

1. Read the full source unit and its surrounding context.
2. Identify translatable text, protected text, ambiguous terms, and formatting constraints.
3. Apply the brief, glossary, style guide, and project vocabulary.
4. Translate with full meaning preservation.
5. Keep source-target alignment clear enough for review.
6. Preserve structure, ordering, lists, tables, code fences, comments, links, placeholders, and syntactic markers.
7. Run self-checks before considering the unit done.

Keep the translated deliverable separate from process commentary. If the user needs a publishable file, patch, subtitle, JSON block, slide text, or document body, that artifact should contain only the translated content and required original structure. Put translation brief, LQA notes, glossary decisions, and verification evidence in a separate report section or file unless the user explicitly asks to embed them.

Meaning preservation requirements:

- Preserve every source idea, condition, dependency, warning, exception, limitation, contrast, requirement, and sequence.
- Preserve the force of obligation: requirements stay requirements, prohibitions stay prohibitions, recommendations stay recommendations.
- Preserve ambiguity when the source is intentionally ambiguous; resolve ambiguity only when context makes one meaning clearly correct.
- Preserve domain terms consistently. If a term is not in the glossary, infer from corpus evidence or ask when the choice affects correctness.
- Preserve paragraph, list, heading, table, and example structure unless target-language grammar or the requested output format requires a controlled adjustment.

Do not:

- Summarize, compress, omit, soften, embellish, or add new claims.
- Replace precise technical, legal, or product language with generic wording.
- Translate protected identifiers or literals as if they were prose.
- Convert localization into cultural adaptation unless the brief calls for localization or transcreation.

## Translation Modes

Use the mode implied by the content and brief.

| Mode | Use when | Quality focus |
|---|---|---|
| Exact translation | Requirements, legal, architecture, safety, policy, technical docs | Semantic fidelity and obligation preservation |
| Product localization | UI, support, onboarding, websites, release notes | Context fit, placeholders, tone, locale conventions, UX constraints |
| Technical translation | Code comments, API docs, engineering plans, runbooks | Terminology, code-adjacent syntax, factual precision |
| Marketing localization | Campaigns, landing pages, brand copy | Brand voice, intent, cultural fit, conversion meaning |
| Bilingual review | Existing translation needs checking | Error classification, source-target comparison, fix recommendations |

If modes conflict, choose the mode with the higher correctness risk. For example, legal or safety meaning takes priority over smoother marketing tone.

## Glossary and Style Control

Build or reuse a compact glossary before translating recurring terms.

Glossary format:

```markdown
| Source term | Target term | Rule | Evidence |
|---|---|---|---|
| <term> | <translation> | translate / do not translate / context-specific | <source path or prior usage> |
```

Style guide format:

```markdown
Audience:
Tone:
Formality:
Voice:
Locale conventions:
Do:
- <rule with example>
Do not:
- <rule with example>
```

Keep glossary terms separate from style rules. Glossaries control words and names; style guides control voice, formality, audience fit, and formatting behavior.

## Terminology Decision Blockers

When a term has multiple plausible target-language treatments and the choice affects legal, technical, brand, product, or UX correctness, block translation of the affected unit instead of guessing. Continue only with unaffected units.

Use the user's conversation language for the blocker note unless the user explicitly asks for the blocker to be written in the target language.

Blocker format:

```markdown
Translation blocked: terminology decision required

Source term: <term>
Affected contexts:
1. <context A> - <why it may require target term A>
2. <context B> - <why it may require target term B>

Recommended decision:
| Option | Target term | Use when | Risk |
|---|---|---|---|
| A | <term> | <context> | <risk if wrong> |
| B | <term> | <context> | <risk if wrong> |

Question: Which target term should be used for each context?
```

Do not produce a "best guess" translation for the blocked term unless the user approves the terminology decision.

## Technical Preservation Checklist

Verify these items before the quality score is assigned:

- Placeholders and variables are identical unless the target format explicitly requires reordering.
- HTML, XML, JSX, Markdown, ICU, YAML, JSON, SQL, regex, shell commands, and code fences remain syntactically valid.
- Links keep their original targets unless link localization is explicitly in scope.
- Locale conventions are correct for dates, numbers, currencies, units, names, addresses, honorifics, punctuation, directionality, and capitalization.
- Text expansion or contraction does not break UI constraints, table layout, slide layout, button labels, alt text, metadata, or screenshots.
- Embedded image text, captions, footnotes, comments, speaker notes, and accessibility text are included in the inventory.
- Existing tests, snapshots, checksums, or content IDs are not invalidated without a deliberate update.

## Quality Model

Score each work unit with this LQA-inspired 100-point gate.

| Category | Points | Full-credit requirement |
|---|---:|---|
| Accuracy | 30 | Target content preserves source meaning without mistranslation, omission, addition, under-translation, or over-translation. |
| Completeness | 15 | Every in-scope source segment is translated or intentionally marked as protected. |
| Terminology | 15 | Glossary, domain terms, product names, and non-translatables are handled consistently. |
| Fluency | 10 | Target language is grammatical, natural, and readable for the intended audience. |
| Style and register | 10 | Tone, formality, brand voice, and content type match the brief. |
| Locale and cultural fit | 10 | Locale conventions, cultural assumptions, legal/regional expectations, and UX context are appropriate. |
| Technical integrity | 10 | Formatting, placeholders, markup, links, layout constraints, and code-adjacent syntax are preserved. |

For high-stakes, publish-ready, or exact 1:1 requests, the work unit must reach 100/100. If it scores below 100, fix the current unit and repeat review before moving forward.

Automatic failure conditions:

- Any in-scope text is missing, untranslated, or replaced by a summary.
- A requirement, warning, exception, legal obligation, technical constraint, or product behavior changes meaning.
- A placeholder, identifier, key, tag, link, command, code literal, or schema field is accidentally changed.
- The translation is fluent but wrong in context.
- The work unit was edited without first reading the full source context.
- A multi-unit automated rewrite was used where the user required controlled sequential translation.

## Review Loop

Use this loop for every work unit:

```markdown
Work unit: <path, section, screen, sheet, or asset>
Source language:
Target language/locale:
Segments translated:
Protected segments:
Issues found:
- <category>: <issue and fix>
Score: <n>/100
Decision: pass / fix and re-review
```

When a unit fails, fix only that unit and re-score it. Do not move to later units until the current unit satisfies the requested quality bar.

For existing translations, review against the source text and classify issues using the quality model. Provide corrected target text, not only comments.

## Special Handling by Content Type

### Codebases

- Scan before editing and list eligible files.
- Exclude protected directories and locale catalogs unless explicitly in scope.
- Translate prose in comments, docs, prompts, and user-visible text only when requested.
- Preserve public APIs, identifiers, test fixtures, snapshots, routes, telemetry names, and string IDs.
- Run the repository's relevant checks after edits when available.

### UI and Product Strings

- Request or infer screen context, component purpose, variable meanings, max length, and audience.
- Preserve placeholders and pluralization logic.
- Check button labels, errors, empty states, tooltips, metadata, alt text, and accessibility strings.
- Verify that translated text works in context, not only as standalone sentences.

### Legal, Policy, Compliance, and Safety Text

- Use exact translation mode.
- Preserve obligations, exceptions, definitions, references, thresholds, time periods, actors, and jurisdictional qualifiers.
- Do not modernize, soften, or simplify legal force.
- Ask before resolving ambiguous regulated terms.

### Marketing and Brand Content

- Preserve the intended promise, emotion, audience, and conversion goal.
- Adapt idioms only when literal translation would fail the brief.
- Keep claims truthful and no stronger than the source.
- Preserve required brand terms and disclaimers.

### Documents, Slides, and Spreadsheets

- Inventory headings, body text, tables, charts, notes, comments, formulas-adjacent labels, captions, alt text, and embedded images.
- Preserve layout-sensitive structure.
- For spreadsheets, do not alter formulas or machine-readable values unless explicitly requested.
- For slides, verify text fit and visual hierarchy after translation.

## Final Verification

At the end, rerun discovery checks appropriate to the task:

- Source-language residue scan for in-scope files or documents.
- Placeholder and markup parity check.
- Glossary consistency check.
- Link, table, heading, and formatting spot checks.
- Product UI or layout check when visual context exists.
- Relevant tests, linters, build checks, document render checks, or file-open checks.

Final report format:

```markdown
Translation completed:
1. <unit> - <score>/100 - <mode>
2. <unit> - <score>/100 - <mode>

Protected or excluded:
1. <unit/term> - <reason>

Glossary decisions:
1. <source term> -> <target term> - <reason>

Verification:
- Scope scan: <result>
- Placeholder/markup parity: <result>
- Formatting/layout: <result>
- Tests or document checks: <result or reason not run>
```

If in-scope source-language text remains, or any requested quality gate has not passed, continue the workflow rather than reporting completion.

## When to Ask

Ask the user before translating when:

- The target language or locale is missing and cannot be inferred.
- A term has multiple plausible translations and affects legal, technical, brand, or product correctness.
- The source text is ambiguous and surrounding context does not resolve it.
- The user has not decided between exact translation and localization for content where the difference changes output.
- Protected content appears to conflict with the translation goal.

Ask the smallest question that unlocks the work, then continue.
