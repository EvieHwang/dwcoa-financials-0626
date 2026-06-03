# User Guide

A build framework for Claude Code, distributed as a template repository. It provides slash commands (in `.claude/commands/`) that produce a per-feature spec and test suite in `features/[name]-[number]/`, then build against them. The spec and tests are the contract between what you wanted and what got built.

This guide is the human's map: which command to reach for, and how the pieces fit. Each command's exact procedure lives in its own file in `.claude/commands/` — that file is the source of truth, and you can read it if you want the mechanics.

---

## The division of labor

The framework draws one line and holds it:

- **You own intent and the definition of done.** What to build, why, what's out of scope, the standards that apply, the risks you knowingly accept. The model can't derive these — they live in `declaration.md`, `constitution.md`, the per-feature declaration, and above all in the **tests**, which are the executable statement of "done."
- **The runtime owns orchestration and execution.** Planning the work, decomposing it, running pieces in parallel, iterating until the tests pass. You don't manage waves, state files, or convergence loops — the runtime does that natively, and the framework stays out of its way.

The one place the framework still inserts itself into execution is the **adversarial gate**: an independent, clean-context attack on the spec and tests before any code is written. That isn't process supervision — it catches blind spots the authoring pass can't see in itself, no matter how capable the model is.

---

## Choosing your approach

**Quick change — `/patch`.** Bug fixes, tweaks, polish, small features where the intent is clear and the work fits one session. No feature artifacts; the PR body is the documentation. Use when you know what correct looks like and the change is contained.

**Feature build — `/spec` → `/build`.** Real features built from a written spec and a test suite. `/spec` produces both and runs them past an independent adversarial gate; `/build`, in a later session, implements against the tests until they pass. Use when the work is deliberate, spans multiple components, or carries hard-to-reverse decisions.

---

## Core documents

- **`declaration.md`** — the project's statement of intent: what it is, why, for whom, what it explicitly doesn't do, plus **Shape** (3–7 named components/seams) and **Roadmap** (3–7 anticipated features in rough order). Shape and Roadmap are revisable as the project learns.
- **`constitution.md`** — the project's accumulated judgment: standards registry, architectural principles, patterns in use, quality gates, testing framework, decision log, acknowledged risks.
- **`CLAUDE.md`** — the app's operational map: repo layout, run/test/deploy context, and user-global identity coordinates.

The model reads these before acting; you don't have to remind it to.

---

## Running a quick change

```
/patch
```

Identifies the minimal change, presents a plan with breakage risk surfaced, waits for approval, implements only that, runs existing tests, and opens a PR. The PR body (Intent / Change / Verification / Risk) is the record.

---

## Running a feature build

The path is `/spec` → merge the spec PR → `/build` in a fresh session. The two commands run in separate sessions because the cloud sandbox re-clones from `main` each time — so the spec has to be merged before the build can start from it.

### Optionally scope first — `/feature`

```
/feature   feature-name: [name]
```

Reach for `/feature` only when a feature's scope is genuinely fuzzy and you want a coached scoping pass — including the walking-skeleton coaching on a project's first feature. It produces `features/[name]-[number]/declaration.md`. If you skip it, `/spec` produces the declaration inline from the conversation that led up to it.

### Spec — `/spec`

```
... chat about the next feature ...
/spec   feature-name: [name]
```

`/spec` runs one forward pass:

1. **Declaration** — the feature's intent, from the prior conversation (or from a `/feature` run if you did one).
2. **Spec** — `spec.md`: behavioral requirements *and* the design that satisfies them, written together in one pass. Constraints are behavioral, not implementation prescriptions.
3. **Tests** — an executable suite in `tests/` that is the acceptance bar. A weak test is worse than no test, so the suite is the real deliverable, not a sketch.
4. **Adversarial gate** — a fresh sub-agent in clean context whose only job is to attack the spec and tests. Independence is the point: a review folded into the authoring pass inherits that pass's blind spots.

This is a single gate, not a loop — no requirements↔architecture round-trips, no stability markers, no convergence counters. `/spec` stops only for decisions you must make: the gate's findings (you choose to fix, acknowledge, or proceed for each), scope drift, tension with the declaration, or a risk that needs your explicit acknowledgment. Acknowledged risks are recorded in `constitution.md`. When the gate is resolved, `/spec` commits and opens a handoff PR against `main`.

**Merge that PR**, then start a new session.

### Build — `/build`

```
/build   feature-name: [name]
```

`/build` assumes the spec and tests are final and merged. It plans the work, decomposes it (parallel subagents / Dynamic Workflows where the work warrants it), and implements against the tests, iterating until the full suite passes. Then it opens a PR.

During build:
- **Tests are the source of truth.** A failing test means the implementation is wrong — unless the test itself is genuinely in error, in which case the correction is logged in `build-deviations.md`.
- **Requirements are immutable.** If a requirement looks actually wrong, `/build` stops and kicks back to `/spec` rather than editing the spec — requirements get revised against a fresh adversarial gate, not patched mid-build.
- **Design is a recommendation.** When reality contradicts the design, `/build` satisfies the behavioral requirement a different way and logs the deviation in `build-deviations.md`.

### Retro

```
/retro   feature-name: [name]
```

Optional but recommended. A coached conversation producing `retro.md` — what went well, what didn't (with build deviations as evidence), whether the adversarial gate earned its keep, and concrete proposed changes to `constitution.md`, `CLAUDE.md`, and skill prompts. Template-level lessons are marked separately so they lift directly into a framework-update PR.

---

## New project setup

After cloning the template:

1. `/setup` — coached fill of `CLAUDE.md` (name, description, run/test/deps, deployment target) and a README stub, then `/declaration` as its second phase. Both happen in one session.
2. Edit `constitution.md`'s app-specific sections as the project develops; the template ships with universal defaults already filled in (prune anything that doesn't apply).
3. Pick an approach for your first piece of work.

---

## Keeping the framework up to date

```
/upgrade
```

Fetches the latest framework-owned files and writes them into the current project, then opens a PR.

- **Replaced wholesale** (projects have no reason to customize these): `FRAMEWORK_VERSION`, `user-guide.md`, `features/README.md`, `.claude/commands/*.md`.
- **Never replaced wholesale** (mix framework template sections with project-specific content): `CLAUDE.md` and `constitution.md`. `/upgrade` works these section by section — it semantically merges each framework-owned section (preserving any project-specific lines you added) and proposes deletions for sections the framework has retired, then prompts you per edit in-session (apply / skip / show full). Only the edits you approve are written; project-specific sections are never touched. The PR body lists which edits were applied vs. skipped.

`FRAMEWORK_VERSION` holds the date the framework was last fetched; `/upgrade` reads it to detect whether an upgrade is needed. To force a same-day re-upgrade, delete the file locally first.

A project crossing the V1→V2 boundary will have stale command files (`requirements`, `architecture`, `adversarial`, `tests`, `dag`, `next`); `/upgrade` removes them as part of the upgrade.

**Bootstrapping a pre-`/upgrade` project:** open a session on the old project and ask Claude to `curl` the upgrade command into place:

```
curl -sf https://raw.githubusercontent.com/EvieHwang/evie-dev-framework/main/.claude/commands/upgrade.md -o .claude/commands/upgrade.md
```

Then run `/upgrade` to pull in the rest.
