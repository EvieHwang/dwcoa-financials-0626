---
description: Upgrade a downstream project's framework-owned files to the latest version from evie-dev-framework. Replaces all skill commands, user-guide.md, features/README.md, and FRAMEWORK_VERSION wholesale; semantically merges CLAUDE.md and constitution.md framework-owned sections behind per-edit in-session approval, preserving project-specific content.
---

Upgrade this project's framework files to the latest version from the canonical framework repo.

## Source of truth

The framework source repo is declared once here and used for **every** fetch below — never inline another repo slug:

```
SOURCE_REPO = EvieHwang/evie-dev-framework
```

`evie-dev-framework` is the authoritative, actively-developed framework repo. The non-suffixed `evie-dev-framework` is an older snapshot — do not fetch from it. If this constant ever needs to change, change it here only; the single declaration is what keeps the canonical-vs-snapshot split from drifting across the seven fetches below.

All framework files are fetched using `curl` via the Bash tool against raw GitHub URLs (`https://raw.githubusercontent.com/<SOURCE_REPO>/main/<path>`, i.e. `https://raw.githubusercontent.com/EvieHwang/evie-dev-framework/main/<path>`). Do not use `mcp__github__get_file_contents` for the framework repo (MCP is scoped to the current project only) and do not use WebFetch (blocked by sandbox network policy).

## Pre-flight checks

Run these before touching any files. Stop and report if any check fails.

1. **Uncommitted changes.** Run `git status --porcelain`. If any output appears, stop — tell the user to commit or stash changes before upgrading.

2. **Project is set up.** Read `CLAUDE.md`. If it still contains `# [Project Name]` (the template placeholder), stop — this project has not been initialized. Run `/setup` first.

3. **Current version.** Read `FRAMEWORK_VERSION` locally. Record as `from_version`. If the file does not exist, `from_version` is `(pre-versioning)`.

4. **Target version.** Run:
   ```bash
   curl -sf https://raw.githubusercontent.com/EvieHwang/evie-dev-framework/main/FRAMEWORK_VERSION
   ```
   Strip whitespace from the output. Record as `to_version`. If curl fails (non-zero exit), stop and report the error.

5. **Already current.** If `from_version == to_version`, report "Already up to date at framework version `<to_version>`." and exit without making any changes.

## Replace framework-owned files

For each file in the list below, run:
```bash
curl -sf https://raw.githubusercontent.com/EvieHwang/evie-dev-framework/main/<path> -o <path>
```

If the file does not yet exist locally, create any missing parent directories first (`mkdir -p`). Write the fetched content verbatim — do not merge or selectively apply.

```
FRAMEWORK_VERSION
user-guide.md
features/README.md
.claude/commands/build.md
.claude/commands/declaration.md
.claude/commands/feature.md
.claude/commands/patch.md
.claude/commands/retro.md
.claude/commands/setup.md
.claude/commands/spec.md
.claude/commands/upgrade.md
```

If any `curl` call fails, stop and report which file failed before making any commits.

**Removing stale commands.** A project upgrading across the V2 boundary may still have the V1 command files (`requirements.md`, `architecture.md`, `adversarial.md`, `tests.md`, `dag.md`, `next.md`) under `.claude/commands/`. If any exist, `git rm` them — they were collapsed into `/spec` and `/build` and a lingering file would shadow the new flow. Note in the PR which were removed.

## Structural merge — CLAUDE.md and constitution.md

These files mix framework-template sections with project-specific content (project name, run/test/deps block, deployment target, the user-globals block at the bottom of `CLAUDE.md`; the decision log and acknowledged-risks table in `constitution.md`), so they are **never replaced wholesale**. Instead, work **section by section** and apply each framework-owned change as a separate, individually approved edit. Project-specific sections are never touched.

Fetch the framework versions once:
```bash
curl -sf https://raw.githubusercontent.com/EvieHwang/evie-dev-framework/main/CLAUDE.md
curl -sf https://raw.githubusercontent.com/EvieHwang/evie-dev-framework/main/constitution.md
```

There are two classes of edit. Build the full list of proposed edits across both classes first, then walk them one at a time through the approval step below.

### Class 1 — framework-owned section merges

For each section below, take the text from the section heading up to the next `##` heading and compare framework vs. local:

**CLAUDE.md:** `## Repo map`, `## Development environment`, `## Secrets`
**constitution.md:** `## Standards`, `## Spec-authoring lessons`

If a section is byte-identical, skip it. **If a section is absent locally** — one the framework has newly introduced (e.g. `## Spec-authoring lessons`) — propose adding the framework version verbatim at the position it occupies in the framework file, as its own approval-gated edit. If it differs, produce a **semantic merge**, not a blind overwrite: adopt the framework's new structure, wording, and any new directives, while **preserving any project-specific lines the local copy added** to that section (e.g. repo-specific entries under Repo map, project-added standards, accumulated spec-authoring lessons). When in doubt about whether a local line is a project addition or stale framework text, keep it and call it out in the approval prompt so the user decides.

### Class 2 — stale-section deletions

The framework has *deleted* some sections a downstream repo may still carry in its always-loaded files; a lingering one keeps dead rules in context. Propose a deletion for each that is still present locally:
- `CLAUDE.md` — `## Build flow note` (the DAG / `state.md` / `verify.md` build flow it describes no longer exists).
- `constitution.md` — `## Artifact formats` (the `state.md` state-file spec).

These are pure removals — no project content lives in them.

### Approval step — one prompt per edit

Present each proposed edit individually and apply only what the user approves. Use the `AskUserQuestion` tool, one question per edit, with options **Apply**, **Skip**, and **Show full** (when "Show full" is chosen, print the complete before/after for that section, then ask again). The question must include enough of the diff that the user can decide without scrolling back — for a merge, show the local section and the proposed merged result; for a deletion, show the section being removed and name what made it obsolete.

Apply each approved edit to the file with the `Edit` tool immediately after its approval. Leave skipped edits untouched. If no sections differ and no stale sections are present, report "No CLAUDE.md / constitution.md changes to apply." and make no edits to these files.

Keep a record of which edits were **applied** and which were **skipped** — this goes in the PR body.

## Commit

Stage the framework-owned files listed above, plus `CLAUDE.md` and/or `constitution.md` **only if** the structural-merge step applied at least one approved edit to them. Never stage other project-specific files (`declaration.md`, feature artifacts, the project's run/test/deps or deployment blocks). If the user skipped every CLAUDE.md / constitution.md edit, leave both files unstaged.

```
chore: upgrade framework to <to_version>

Updated from <from_version>. Skill commands, user-guide.md,
features/README.md, and FRAMEWORK_VERSION replaced wholesale.
CLAUDE.md / constitution.md framework-owned sections merged with
approval (see PR for which edits were applied vs. skipped).
```

Push the branch: `git push -u origin <current-branch>`.

## Open PR

Open a pull request against `main` using `mcp__github__create_pull_request`:

- **Title:** `chore: upgrade framework to <to_version>`
- **Body:**

```
## Upgraded files

`.claude/commands/*.md`, `user-guide.md`, `features/README.md`, `FRAMEWORK_VERSION`
upgraded from `<from_version>` to `<to_version>`.

## CLAUDE.md / constitution.md edits

**Applied (approved in-session):**
<for each applied edit: section name, and merge vs. deletion>

**Skipped (declined in-session):**
<for each skipped edit: section name, and what it would have changed — so the
reviewer can revisit it manually if desired>

If no sections differed, write "No structural changes — both files already current."

## Verification

Run the test suite to confirm no regressions. Project-specific configuration
(CLAUDE.md / constitution.md project sections, run/test/deps, deployment target,
declaration.md, feature artifacts) is unchanged — only the approved framework-owned
sections above were touched.
```

- Ready for review (not draft). No reviewers or assignees, per CLAUDE.md (the owner is the PR author).

Present the PR URL to the user.
