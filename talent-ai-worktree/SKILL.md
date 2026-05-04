---
name: talent-ai-worktree
description: Create and verify git worktrees for talent-platform-vibe and de-backoffice-cr swe_chat. Use paired worktrees only when a task impacts both repositories and requires synchronized frontend and backend worktrees with fixed localhost slots, worktree-local env files, dependency bootstrap, and boot verification. For backend-only changes, create only the backend worktree and use only a backend slot; do not create a frontend worktree or reserve a frontend slot. Do not use this skill for frontend-only changes. Always use sibling worktree roots named talent-platform-vibe.worktrees and de-backoffice-cr.worktrees. Never use repo-internal .worktrees layouts, repo-local git-worktree helper scripts, feat/ prefixes, or -fe/-be branch suffixes.
---

# Talent AI Worktree

Create one frontend worktree and one backend worktree as a matched pair only
when the task impacts both repos. If the request is backend-only, create only
the backend worktree and backend slot. If the request is frontend-only, stop
and do not create any frontend worktree with this skill. For BE-only or FE+BE
work, first resolve the required repo roots from the current workspace, then
pick a free fixed slot, keep env files local to each created worktree, install
dependencies inside each created worktree, and verify the required runtimes
before starting implementation.

This workflow is scope-dependent after the scope gate passes. `BE-only` may use
only the backend repo and backend slot. `FE+BE` must resolve both repos and use
the paired workflow. If only frontend code changes are needed, do not use this
skill.

For backend-only and paired cross-repo setup, this skill is the source of
truth. Do not fall back to repo-local worktree helper scripts,
`CLAUDE_PLUGIN_ROOT` helpers, or older single-repo conventions that prepend
`feat/` or add `-fe` / `-be` suffixes to branch names.

The skill folder itself is not a git repository and not the execution target.
Never run `git`, `pnpm`, or `uv` commands from the skill directory. Always
discover the actual repo roots first, then run commands inside those repos or
their worktrees.

Do not collapse `FE+BE` into a single-repo workflow. For `BE-only`, create only
the backend worktree under `de-backoffice-cr.worktrees`. Do not create both
frontend and backend worktrees under `talent-platform-vibe`, and do not create
both under `de-backoffice-cr`.

## Scope Gate

Classify the task before touching slots, branches, or worktrees.

```text
┌─ Task scope ───────────────────────────────────────────────────────────┐
│ FE only  -> stop; do not create any FE worktree with this skill      │
│ BE only  -> create only the BE worktree and only the BE slot         │
│ FE+BE    -> continue with the paired worktree workflow               │
└───────────────────────────────────────────────────────────────────────┘
```

Hard scope rules:

- do not create a frontend worktree when the requested code changes are only in
  `talent-platform-vibe`
- do not create a frontend worktree or reserve a frontend port when the
  requested code changes are only in `de-backoffice-cr`
- do not treat "frontend needs to call the backend" as enough by itself; the
  paired workflow starts only when backend code is also part of the task
- if scope is uncertain, stop and clarify whether the task is `FE-only`,
  `BE-only`, or `FE+BE`
- do not pick a slot, branch, or worktree path until the task is confirmed as
  `BE-only` or `FE+BE`

## Canonical Layout

Use exactly this shape:

```text
<workspace_root>/
├─ talent-platform-vibe
├─ talent-platform-vibe.worktrees/
│  └─ <feature_slug>
├─ de-backoffice-cr
└─ de-backoffice-cr.worktrees/
   └─ <feature_slug>
```

For `BE-only`, only `<backoffice_worktrees_root>/<feature_slug>` is created.
Do not create `<talent_worktrees_root>/<feature_slug>` and do not reserve any
frontend slot.

Reject these as wrong:

```text
talent-platform-vibe/.worktrees/...
de-backoffice-cr/.worktrees/...
.worktrees/feat/<feature_slug>-fe
.worktrees/feat/<feature_slug>-be
worktree-manager.sh create feat/<feature_slug>-fe
worktree-manager.sh create feat/<feature_slug>-be
```

## Git Worktree Integration

If the `git-worktree` skill is installed, prefer integrating with it for
per-repo worktree lifecycle handling only when its conventions are compatible
with the current workspace policy.

Compatibility rule:

- if `git-worktree` is present and the workspace policy also uses repo-internal
  `.worktrees/`, you may delegate repo-local create/list/cleanup mechanics to
  that skill
- if `git-worktree` is present but its repo-internal `.worktrees/` convention
  conflicts with this skill's sibling `*.worktrees` layout, do not delegate the
  layout decision to `git-worktree`; keep using this skill's direct workflow

Compatibility check algorithm:

1. Inspect the installed `git-worktree` skill instructions.
2. If it requires repo-internal `.worktrees/` paths, `worktree-manager.sh`, or
   branch-name-driven repo-local layouts, mark it incompatible.
3. If it can operate without changing this skill's canonical sibling
   `*.worktrees` layout, mark it compatible.
4. Only after a compatible result may you delegate helper mechanics to it.

Hard integration rule:

- installed `git-worktree` does not override this skill's canonical layout
- use `git-worktree` only as an implementation helper when there is no layout
  conflict
- if there is any conflict, fall back to the current workflow in this skill
- observed repo-local `.worktrees/...` directories do not count as evidence that
  the conflicting layout is allowed
- observed repo-local `feat/...` worktree names do not override this skill
- if compatibility is uncertain, treat `git-worktree` as incompatible

## Inputs

Resolve these inputs before creating anything:

- impact scope: `FE-only`, `BE-only`, or `FE+BE`
- `feature_slug`
- frontend base branch when scope is `FE+BE`
- backend base branch when scope is `BE-only` or `FE+BE`
- slot: `A`, `B`, or `C`

If the impact scope resolves to `FE-only`, stop immediately. Do not choose a
slot. Do not create a frontend worktree. Do not create a backend worktree.

If the impact scope resolves to `BE-only`, do not choose or reserve any
frontend port. Create only the backend worktree and select the slot from
backend port availability only.

Default to the current branch in each repo when the user did not specify base
branches.

Before creating worktrees, report which frontend and backend base branches you
selected for the active scope. If any default base branch is not the expected
mainline branch for the repo that will be used and the user did not specify it
explicitly, stop and ask for confirmation before creating worktrees.

## Repo Discovery

Resolve repo roots instead of hardcoding a workspace path.

1. Start from the current working directory.
2. Look for sibling directories named `talent-platform-vibe` and
   `de-backoffice-cr`.
3. If the required repos for the chosen scope are not present, look one parent
   level up and check again.
4. Use only those two search anchors: the current working directory and its
   immediate parent.
5. If scope is `BE-only`, `de-backoffice-cr` is required and
   `talent-platform-vibe` is optional.
6. If scope is `FE+BE`, both repos are required.
7. If the required repo set still cannot be found, stop and ask the user for
   the repo roots instead of guessing.
8. After repo discovery, verify that the sibling worktree roots needed for the
   chosen scope also exist or can be created:
   - `FE+BE`: `<workspace_root>/talent-platform-vibe.worktrees` and
     `<workspace_root>/de-backoffice-cr.worktrees`
   - `BE-only`: `<workspace_root>/de-backoffice-cr.worktrees`

Refer to the resolved paths below as:

- `<workspace_root>`
- `<talent_repo>`
- `<backoffice_repo>`
- `<talent_worktrees_root>`
- `<backoffice_worktrees_root>`

Use these fixed mappings when the repo is in scope:

- `<talent_repo>` = `<workspace_root>/talent-platform-vibe`
- `<backoffice_repo>` = `<workspace_root>/de-backoffice-cr`
- `<talent_worktrees_root>` = `<workspace_root>/talent-platform-vibe.worktrees`
- `<backoffice_worktrees_root>` = `<workspace_root>/de-backoffice-cr.worktrees`

Hard discovery rule:

- `de-backoffice-cr` is the correct backend repo name
- do not rewrite it to `de-backoffice`
- if there is any ambiguity about the current shell location, inspect or print
  the current working directory first and use that resolved path as the only
  discovery starting point
- do not scan the wider filesystem, home directory, or previously known
  workspace paths for matching repo names
- frontend and backend worktrees must live in the sibling `*.worktrees`
  directories, not inside the repo directories
- ignore any existing repo-internal `.worktrees` directories from older
  workflows
- ignore any repo-local `feat` slot directory conventions from older workflows

## Slot Map

```text
┌─ Backend-only Slot A ──────────────────────────────────────────────────┐
│ BE worktree: <backoffice_worktrees_root>/<feature_slug>              │
│ BE origin : http://localhost:8081                                    │
│ FE slot   : not reserved                                              │
└───────────────────────────────────────────────────────────────────────┘

┌─ Backend-only Slot B ──────────────────────────────────────────────────┐
│ BE worktree: <backoffice_worktrees_root>/<feature_slug>              │
│ BE origin : http://localhost:8082                                    │
│ FE slot   : not reserved                                              │
└───────────────────────────────────────────────────────────────────────┘

┌─ Backend-only Slot C ──────────────────────────────────────────────────┐
│ BE worktree: <backoffice_worktrees_root>/<feature_slug>              │
│ BE origin : http://localhost:8083                                    │
│ FE slot   : not reserved                                              │
└───────────────────────────────────────────────────────────────────────┘

┌─ Slot A ───────────────────────────────────────────────────────────────┐
│ FE worktree: <talent_worktrees_root>/<feature_slug>                  │
│ BE worktree: <backoffice_worktrees_root>/<feature_slug>              │
│ FE origin : http://localhost:3011                                    │
│ FE Vite   : http://localhost:9877                                    │
│ BE origin : http://localhost:8081                                    │
│ FE env    : PORT=3011 APP_URL=http://localhost:3011                  │
│ FE env    : VITE_DEV_PORT=9877                                      │
│ FE env    : APPS_WEB_UI_BASE_URL=http://localhost:3011               │
│ FE env    : AI_BACKEND_URL=http://localhost:8081                     │
│ Redirects : sign-in/out URLs on http://localhost:3011                │
│ SPA Vite  : http://localhost:9877 must belong to this FE worktree    │
└───────────────────────────────────────────────────────────────────────┘

┌─ Slot B ───────────────────────────────────────────────────────────────┐
│ FE worktree: <talent_worktrees_root>/<feature_slug>                  │
│ BE worktree: <backoffice_worktrees_root>/<feature_slug>              │
│ FE origin : http://localhost:3012                                    │
│ FE Vite   : http://localhost:9878                                    │
│ BE origin : http://localhost:8082                                    │
│ FE env    : PORT=3012 APP_URL=http://localhost:3012                  │
│ FE env    : VITE_DEV_PORT=9878                                      │
│ FE env    : APPS_WEB_UI_BASE_URL=http://localhost:3012               │
│ FE env    : AI_BACKEND_URL=http://localhost:8082                     │
│ Redirects : sign-in/out URLs on http://localhost:3012                │
│ SPA Vite  : http://localhost:9878 must belong to this FE worktree    │
└───────────────────────────────────────────────────────────────────────┘

┌─ Slot C ───────────────────────────────────────────────────────────────┐
│ FE worktree: <talent_worktrees_root>/<feature_slug>                  │
│ BE worktree: <backoffice_worktrees_root>/<feature_slug>              │
│ FE origin : http://localhost:3013                                    │
│ FE Vite   : http://localhost:9879                                    │
│ BE origin : http://localhost:8083                                    │
│ FE env    : PORT=3013 APP_URL=http://localhost:3013                  │
│ FE env    : VITE_DEV_PORT=9879                                      │
│ FE env    : APPS_WEB_UI_BASE_URL=http://localhost:3013               │
│ FE env    : AI_BACKEND_URL=http://localhost:8083                     │
│ Redirects : sign-in/out URLs on http://localhost:3013                │
│ SPA Vite  : http://localhost:9879 must belong to this FE worktree    │
└───────────────────────────────────────────────────────────────────────┘
```

## Naming

- frontend branch: `<feature_slug>` when scope is `FE+BE`
- backend branch: `<feature_slug>` when scope is `BE-only` or `FE+BE`
- frontend worktree path: `<talent_worktrees_root>/<feature_slug>` when scope
  is `FE+BE`
- backend worktree path: `<backoffice_worktrees_root>/<feature_slug>` when
  scope is `BE-only` or `FE+BE`

If the branch already exists, attach the new worktree to the existing branch
instead of inventing another name.

Hard naming rule:

- do not prepend `feat/`
- do not append `-fe`
- do not append `-be`
- both repos use the exact same `<feature_slug>` branch name
- commands containing `feat/<feature_slug>`, `<feature_slug>-fe`, or
  `<feature_slug>-be` are wrong for this skill
- commands that create worktrees under `<talent_repo>/.worktrees/...` are wrong
- commands that create worktrees under `<backoffice_repo>/.worktrees/...` are
  wrong

## Workflow

```text
┌─ FE-only task? ── yes ────────────────────────────────────────────────┐
│ Stop. Do not create any FE worktree with this skill.                  │
└───────────────────────────────────────────────────────────────────────┘

┌─ BE-only task? ── yes ────────────────────────────────────────────────┐
│                                                                       │
├─ 0. Confirm FE is out of scope before any slot selection              │
├─ 1. Resolve backend repo from current workspace                       │
├─ 2. Check backend ports and pick one free backend slot                │
├─ 3. Create BE worktree from BE base branch                            │
├─ 4. Copy BE env into the BE worktree                                  │
├─ 5. Install deps inside the BE worktree only                          │
├─ 6. Boot BE and verify /health                                        │
├─ 7. Start implementation only after BE boot passes                    │
└─ 8. Clean up the BE worktree when the task is finished                │
```

```text
┌─ FE+BE task? ── yes ──────────────────────────────────────────────────┐
│                                                                       │
├─ 0. Confirm backend impact before any slot or branch selection        │
├─ 1. Resolve repo roots from current workspace                         │
├─ 2. Check slot ports and pick one free slot                           │
├─ 3. Create FE worktree from FE base branch                            │
├─ 4. Create BE worktree from BE base branch                            │
├─ 5. Copy env files into each worktree                                 │
├─ 6. Rewrite FE env for the chosen FE/BE slot and scan stale ports     │
├─ 7. Install deps inside each worktree only                            │
├─ 8. Boot BE and verify /health                                        │
├─ 9. Boot FE and verify local response                                 │
├─ 10. Start implementation only after both pass                        │
└─ 11. Clean up paired worktrees when the task is finished              │
```

## Steps

### 0. Gate on scope before slot selection

Classify the requested change before doing anything else:

- if the task is `FE-only`, stop and report that this skill must not create a
  frontend worktree for frontend-only work
- if the task is `BE-only`, continue with a backend-only worktree and backend
  slot; do not reserve any frontend port
- only create the paired workflow when the planned implementation changes will
  land in both `talent-platform-vibe` and `de-backoffice-cr`
- do not check slot availability, create branches, or copy env files before
  that `BE-only` or `FE+BE` decision is explicit

### 1. Check slot availability first

Before taking a slot, test the ports required by the active scope.

- Main checkout default: `3010` and `9876`
- Slot A: `3011`, `9877`, and `8081`
- Slot B: `3012`, `9878`, and `8082`
- Slot C: `3013`, `9879`, and `8083`

Rules:

- for `FE+BE`, only take a slot when the Next.js port, Vite port, and backend
  port are all free
- for `BE-only`, only test `8081`, `8082`, or `8083` and ignore frontend port
  occupancy because no frontend slot is being reserved

If one or more candidate slots are occupied:

- try the next slot
- if all slots are occupied, stop and tell the user that no slot is available
- use the native port-check command for the current environment instead of
  assuming PowerShell, bash, or a specific platform tool

Hard slot rule:

- do not infer the slot from existing worktree names
- do not infer the slot from branch names
- do not assume Slot B or Slot C just because Slot A appears busy in docs
- choose the slot only from actual current port availability or explicit user
  instruction
- for `FE+BE`, a slot is not "free" just because a path or branch does not
  exist; it is free only when the Next.js port, Vite port, and backend port are
  all available
- for `BE-only`, a backend slot is free only when the backend port is available;
  frontend port occupancy is irrelevant
- existing repo-local `.worktrees` contents are irrelevant to slot selection for
  this skill

### 2. Create required worktrees

Decision rule before creation:

- first check whether the `git-worktree` skill is installed
- then check whether its active layout convention matches this workspace
- if both are true, you may use `git-worktree` as the repo-local creation
  helper
- otherwise, use the direct `git worktree add` commands below
- if the installed `git-worktree` skill mentions repo-internal `.worktrees/` or
  `worktree-manager.sh`, stop considering it compatible and use the direct
  commands below
- do not let current repo contents change this decision

For this skill's canonical sibling `*.worktrees` layout, the direct commands
below remain the default path.

Create the frontend worktree only for `FE+BE`:

```text
git -C <talent_repo> worktree add -b <feature_slug> <talent_worktrees_root>/<feature_slug> <frontend_base_branch>
```

Create the backend worktree for `BE-only` or `FE+BE`:

```text
git -C <backoffice_repo> worktree add -b <feature_slug> <backoffice_worktrees_root>/<feature_slug> <backend_base_branch>
```

If `git worktree add -b` fails because the branch already exists, retry without
`-b` and attach the worktree to that branch.

Track branch ownership for cleanup:

- if `git worktree add -b` succeeded, mark that repo branch as `created`
- if you retried without `-b`, mark that repo branch as `attached`
- use that branch mode later to decide whether branch deletion is automatic,
  forbidden, or requires confirmation

For `BE-only`, skip frontend worktree creation entirely.

Do not use repo-local worktree manager scripts for this setup.
Do not use paths such as `.codex/skills/git-worktree/scripts/worktree-manager.sh`
or similar repo-bundled wrappers here.
Do not reuse old `.worktrees/feat/...` naming or layout from older workflows.

### 3. Prepare env files

Frontend worktree for `FE+BE`:

- prefer copying `.env.local`
- fallback to `.env.example`
- rewrite:
  - `PORT`
  - `APP_URL`
  - `VITE_DEV_PORT`
  - `VITE_DEV_ORIGIN` if it exists in the copied env file
  - `APPS_WEB_UI_BASE_URL`
  - `AI_BACKEND_URL`
  - `NEXT_PUBLIC_AUTH_OAUTH_REDIRECT_SIGN_IN`
  - `NEXT_PUBLIC_AUTH_OAUTH_REDIRECT_SIGN_OUT`

Backend worktree for `BE-only` or `FE+BE`:

- prefer copying `.env`
- fallback to `.env.example`

For `BE-only`, do not create or rewrite any frontend env file.

Do not share one live env file across active worktrees.

Frontend env hard rule:

- set `PORT`, `APP_URL`, `APPS_WEB_UI_BASE_URL`, and both Cognito redirect URLs
  to the same chosen frontend origin
- set `VITE_DEV_PORT` to the slot's Vite port. If `VITE_DEV_ORIGIN` is present,
  set it to `http://localhost:<vite_port>` for the same slot
- do not only pass `--port <frontend_port>` to Next.js; the auth middleware
  builds redirects from `APP_URL`, and the UI validation harness reads
  `APPS_WEB_UI_BASE_URL`
- do not leave Vite on `9876` for every worktree; that makes Next.js load the
  wrong SPA bundle when multiple worktrees run together
- do not make a worktree safe by editing tracked `package.json` scripts to
  hardcode that worktree's slot ports. Keep scripts stable and route
  `dev:next` / `dev:spa` through tiny env-loading wrappers such as
  `tsx scripts/devNext.mts` and `tsx scripts/devVite.mts`; those wrappers read
  `PORT`, `VITE_DEV_PORT`, and `VITE_PORT` from the worktree-local env file
- keep `AI_BACKEND_URL` pointed at the paired backend slot
- after rewriting, scan the frontend worktree for stale runtime references to
  the default main-checkout origin:

```text
rg -n "localhost:3010|localhost:9876|APP_URL=http://localhost:3010|NEXT_PUBLIC_AUTH_OAUTH_REDIRECT_SIGN_IN=http://localhost:3010|APPS_WEB_UI_BASE_URL=http://localhost:3010|VITE_DEV_PORT=9876|VITE_DEV_ORIGIN=http://localhost:9876" <talent_worktrees_root>/<feature_slug>
```

Scan interpretation:

- fix stale matches in live env files and local agent instructions
- do not rewrite test fixtures, docs, or default fallbacks unless they affect
  the active worktree boot path
- if a local app instruction hardcodes `http://localhost:3010`, update it to
  read `APP_URL` / `PORT` from the worktree-local env file

### 4. Install dependencies inside each worktree

Frontend for `FE+BE`:

```text
# run from <talent_worktrees_root>/<feature_slug>
pnpm install --frozen-lockfile
```

Backend for `BE-only` or `FE+BE`:

```text
# run from <backoffice_worktrees_root>/<feature_slug>
uv sync --frozen --all-packages
```

Hard rules:

- never junction frontend `node_modules` to the main checkout
- never reuse the main checkout `.venv` as the backend worktree runtime
- do not install frontend dependencies for `BE-only`
- do not replace the backend command with bare `uv sync --frozen`; this repo is
  a `uv` workspace and `swe-chat` runtime boot depends on workspace-member
  packages being present before `uv run`

### 5. Verify runtime boot

Backend target:

```text
# run from <backoffice_worktrees_root>/<feature_slug>
uv run uvicorn de_backoffice.swe_chat.core:app --host 127.0.0.1 --port <backend_port> --reload
```

Pass condition:

- `http://127.0.0.1:<backend_port>/health` returns a non-5xx response

Required preconditions for the backend command:

- run it from the backend worktree root so `.env` is discoverable
- finish `uv sync --frozen --all-packages` first
- ensure a worktree-local `.env` exists

Notes:

- `de-backoffice-cr` is a `uv` workspace and `projects/swe_chat` is a workspace
  member; syncing all packages prevents missing runtime dependencies such as
  `e2b_code_interpreter`
- `--project projects/swe_chat` is optional when running from the repo root
  after `uv sync --frozen --all-packages`; the root workspace already exposes
  the package import path used by `de_backoffice.swe_chat.core:app`
- `--reload` is valid for local development, but not required for one-shot boot
  verification
- the minimum missing-step risk is not the `--reload` flag; it is forgetting
  repo-root cwd, dependency sync, or `.env`
- `uv run pytest` is not a substitute for boot verification; you must still
  start `uvicorn` and check `/health`

Frontend target for `FE+BE`:

```text
# run from <talent_worktrees_root>/<feature_slug>/apps/web
pnpm run dev
```

Pass condition:

- `http://127.0.0.1:<frontend_port>` responds
- there is no boot-time missing dependency error
- there is no invalid project-root failure
- the Vite SPA bundle on `http://localhost:<vite_port>` is served from the same
  frontend worktree, not from the main checkout or another worktree
- unauthenticated protected-route redirects stay on the selected frontend
  origin or use a relative `/signin?...` URL; they must not point back to
  `http://localhost:3010`
- browser verification with the worktree-local auth state reaches the target
  protected page and does not land on home

Important frontend boot detail:

- `talent-platform-vibe` is a SPA-inside-Next.js app in local development:
  Next.js serves the app shell on the selected frontend port while Vite serves
  the SPA bundle on the selected Vite port
- main checkout owns the default pair `3010/9876`; worktrees should use
  `3011/9877`, `3012/9878`, or `3013/9879`
- if the selected worktree points at another checkout's Vite port, the selected
  worktree can still
  return `200` from Next.js while loading the wrong router bundle; this can
  make new worktree routes redirect to home or disappear
- before accepting frontend boot, inspect the process command line for the
  selected Vite listener and verify it points at
  `<talent_worktrees_root>/<feature_slug>/apps/web`
- a direct module probe is a useful sanity check for route work:

```text
curl http://localhost:<vite_port>/src/routes/%28main%29/<route>/index.tsx
```

The returned module path should resolve to files inside the selected frontend
worktree. If it resolves to another checkout, stop the wrong Vite process and
restart `pnpm run dev` from the worktree.

### 6. Clean up created worktrees

Run cleanup only when the task is finished or explicitly abandoned.

Before removing anything:

- check each created worktree for uncommitted changes
- check whether any created worktree is still the current working directory
- stop and tell the user if there is uncommitted work that has not been
  committed, shelved, or intentionally discarded

Decision rule before cleanup:

- if `git-worktree` is installed and layout-compatible with the current
  workspace, you may use it for repo-local cleanup mechanics
- if `git-worktree` is not installed or its conventions conflict with this
  skill's sibling `*.worktrees` layout, use the direct cleanup commands below
- if the installed `git-worktree` skill mentions repo-internal `.worktrees/` or
  `worktree-manager.sh`, treat it as incompatible for cleanup too

Remove the frontend worktree only when it was created for `FE+BE`:

```text
git -C <talent_repo> worktree remove <talent_worktrees_root>/<feature_slug> --force
```

Remove the backend worktree when scope was `BE-only` or `FE+BE`:

```text
git -C <backoffice_repo> worktree remove <backoffice_worktrees_root>/<feature_slug> --force
```

If the worktree directory remains because local generated files kept it
non-empty, remove the leftover directory only after the git worktree metadata is
gone.

Branch cleanup rules:

- if branch mode is `attached`, do not auto-delete that branch; it existed
  before this workflow
- if branch mode is `created` and the branch still has zero commits beyond its
  selected base branch, delete it by default during cleanup
- if branch mode is `created` and the branch now has commits beyond its base
  branch, keep it unless the user explicitly asks to delete it
- determine "zero commits beyond base" with the repo-local base branch used for
  creation, for example:

```text
git -C <repo> rev-list --count <base_branch>..<feature_slug>
```

- a result of `0` means the created branch is still an empty setup branch and
  should be deleted by default
- a result greater than `0` means the branch contains work and must not be
  auto-deleted unless the user explicitly wants that

Delete the frontend branch only when safe and only if it exists:

```text
git -C <talent_repo> branch -D <feature_slug>
```

Delete the backend branch only when safe:

```text
git -C <backoffice_repo> branch -D <feature_slug>
```

Cleanup pass condition:

- every created worktree no longer appears in `git worktree list`
- leftover directories are removed
- every branch created only for empty setup validation is deleted
- branches with user work are either intentionally kept or intentionally deleted

## Report Back

When you finish, report:

- whether the task was classified as `FE-only` and skipped, `BE-only` and
  executed, or `FE+BE` and executed
- chosen slot
- whether a frontend slot was intentionally skipped for `BE-only`
- whether any slots were occupied and which one was selected next
- frontend worktree path and branch, or that none was created
- backend worktree path and branch, or that none was created
- branch mode in each created repo: `created` or `attached`
- whether install passed in each created worktree
- whether backend boot verification passed
- whether frontend boot verification passed, or that it was not run
- whether frontend `APP_URL`, `PORT`, OAuth redirect URLs, and
  `APPS_WEB_UI_BASE_URL` were rewritten to the selected frontend slot
- whether `VITE_DEV_PORT` / `VITE_DEV_ORIGIN` were rewritten to the selected
  Vite slot
- whether the selected Vite SPA listener belonged to the selected frontend
  worktree
- whether browser verification on a protected route stayed on the selected
  frontend origin
- whether cleanup was completed, skipped, or blocked
- whether each created branch was deleted by default, kept intentionally, or was
  protected because it was attached
- exact blocker if anything failed

## Failure Handling

- If scope resolves to `FE-only`, stop and report that no frontend worktree was
  created because backend impact was not in scope.
- If scope resolves to `BE-only`, do not reserve any frontend slot or create
  any frontend worktree.
- Switch to another free slot if the chosen ports are occupied.
- If all slots are occupied, stop and tell the user no slot is available.
- If frontend boot fails because of worktree-local dependency shape, fix the
  bootstrap in the worktree before touching app code.
- If a frontend route returns `200` from Next.js but lands on home, inspect
  `APP_URL` and the selected Vite port process before changing route code. A
  stale `APP_URL` can redirect auth back to the main checkout, and a stale
  Vite process can load another checkout's SPA router instead of the
  worktree's router.
- If backend boot fails with a missing workspace-member dependency, rerun the
  documented backend bootstrap with `uv sync --frozen --all-packages` before
  touching app code.
- If backend boot still fails because of env or runtime setup, report the exact
  missing variable, import path, or startup traceback.
- If multiple localhost callback URLs are not allowed by infra, stop and
  surface that as the architecture constraint.
- If cleanup finds uncommitted work, stop and ask the user whether to keep,
  commit, or discard it before removing the worktree.

## Verified Commands

These commands were verified in this workspace on 2026-04-10:

- `pnpm install --frozen-lockfile`
- `uv sync --frozen --all-packages`
- `uv run uvicorn de_backoffice.swe_chat.core:app --host 127.0.0.1 --port 8081 --reload`
- `pnpm run dev` from `apps/web` with `PORT=3011` and `VITE_DEV_PORT=9877`

Additional frontend worktree boot checks verified on 2026-05-04:

- `pnpm run dev` from `apps/web` after the worktree-local env sets `PORT`,
  `APP_URL`, `VITE_DEV_PORT`, `APPS_WEB_UI_BASE_URL`, and Cognito redirect
  URLs to the selected frontend origin and Vite origin
- `dev:next` / `dev:spa` package scripts kept port-neutral by using env-loading
  wrappers instead of hardcoded `next dev -p 3010` or `vite --port 9876`
- `curl` against a Vite route module on the selected Vite port to confirm the
  SPA bundle belongs to the selected frontend worktree
- `agent-browser` login and protected-route open against the selected
  frontend origin to confirm the route stays on that origin and does not land
  on home
