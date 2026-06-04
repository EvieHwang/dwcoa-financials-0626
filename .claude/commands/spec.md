---
description: Produces a feature's spec and its executable test suite in one pass, then runs an independent adversarial gate in clean context. Stops only for findings and product-judgment decisions the owner must make; finalizes, commits, and opens a handoff PR for /build. Replaces the old requirements → architecture → adversarial → tests → DAG pipeline.
---

Read constitution.md and declaration.md. Apply constitution.md's `## Spec-authoring lessons` as you go — those are concrete mistakes prior builds revealed about writing specs and tests here; don't repeat them.

`/spec` produces two things for a feature:
- **`spec.md`** — the behavioral spec: what to build, the seams it touches, and the constraints it must hold. This is the contract.
- **`tests/`** — an executable test suite that is the acceptance bar. The suite is the deliverable, not a sketch: a weak test is worse than no test because it creates false confidence.

It runs as a single forward pass — declaration → spec → tests → independent adversarial gate — not a loop. There are no convergence counters, stability markers, or requirements↔architecture round-trips. The model is trusted to write a self-consistent spec in one pass; the gate exists to catch what a single pass cannot see about itself, not to iterate the author against themselves.

`/spec` stops only for decisions the owner must make (see **When to stop**). Everything else proceeds autonomously.

## Resuming

Check which artifacts exist in `features/[feature-name]-[number]/`:
- No populated `declaration.md` → start at Stage 1.
- `declaration.md` populated, no `spec.md` → start at Stage 2.
- `spec.md` and `tests/` exist → re-running to refine. Regenerate from the current declaration and conversation, then re-run the gate (Stage 4). Prior tests are tied to the prior spec; do not preserve them blindly.

---

## Stage 1 — Feature declaration

Skip if `features/[feature-name]-[number]/declaration.md` already exists and is populated (a prior `/feature` run).

Otherwise produce it inline from the preceding conversation by running the `/feature` procedure — that skill is the source of truth for the walking-skeleton coaching (first feature) and the Roadmap-aware start (feature 2+). Do not restate it here. The declaration must hold five sections — **What**, **Why**, **Success**, **Shape touched**, **Out of scope** — at the level of intent, not implementation. Confirm it with the user before continuing; a mis-sized or mis-scoped declaration is far cheaper to fix here than after the spec and tests are written.

Commit `declaration.md`.

---

## Stage 2 — Spec

Write `features/[feature-name]-[number]/spec.md`. It folds what were once separate requirements and design documents into one artifact, because a single capable pass writes them together. It has three parts:

**Behavioral requirements** — in testable terms:
- User stories with acceptance criteria — each names a user, a need, and the criteria that confirm it works.
- Edge cases and failure modes — boundaries, and what happens when things go wrong.
- Out of scope — what this feature explicitly does not address.

**Design** — the architecture that satisfies those requirements:
- Components, the seams between them, and the behavioral properties each must hold.
- **Constraint discipline.** Every constraint must be behavioral — a property the user or system cares about ("requests time out within 5 s"), not a call signature, attribute name, or code shape. If a draft constraint names a library API detail, restate it as the property it protects and leave the implementation to `/build`. The single exception: when the call shape itself is the contract (a public interface this project exposes to callers), name it and say why.
- **Pattern reuse.** If a component or attack surface reuses a pattern already in constitution.md's registry (existing auth module, Eviebot launchd template, an established DB access layer), say so explicitly. Only mark genuine, complete reuse — partial reuse is not reuse.
- When a deploy step mutates an asynchronously-updating cloud resource (Lambda, CloudFront, RDS), sequence the wait/poll between dependent mutations and name any value shared between bootstrap and deploy scripts (e.g. the handler path) as an explicit contract.

**Ground-truth check before drafting the design.** Identify the CLAUDE.md sections you intend to lean on — precedent repos, deployment shape, gateway/auth patterns, the User globals block — list them back to the user, and ask whether each is current. If CLAUDE.md names a precedent repo, attempt to read it; if access is scoped out, ask the user to confirm the precedent before assuming it. If the precedent is **in-repo reference material** (e.g. a `reference/` folder of prior artifacts to rebuild from, listed under CLAUDE.md's precedent section), read it directly — it is the same kind of ground truth, just local. A wasted design built on a stale section costs more than one short exchange.

**Standards-creep check.** Standards in constitution.md apply by default, but when a thin feature would absorb a heavy cross-cutting set (e.g. full WCAG sign-off for a one-page admin tool), surface the tension rather than silently absorbing the cost. The user decides whether to absorb, scope down, or defer.

---

## Stage 3 — Tests

Check constitution.md's `## Testing` section. If it names a runner, use it. If empty, choose the framework that best fits the stack and any existing tests, surface the choice and run command to the user, confirm, then populate `## Testing`. This is a one-time decision per project.

**Multi-runner repos.** A polyglot repo has more than one test runner (e.g. pytest for a Python API, Vitest for a JS/TS frontend), each with its own root, import resolution, and config. constitution.md's `## Testing` holds one block per runner. On first use, establish — and record there — the **wiring** that makes feature-folder tests executable by each runner: where each runner's feature tests physically live (default: `features/[feature-name]-[number]/tests/<runner>/`, e.g. `.../tests/api/` and `.../tests/web/`) and the config that discovers them (a `testpaths`/rootdir entry, a Vitest `include` glob, an import alias). Decide this once, write it into `## Testing`, and confirm it with the user; do **not** improvise per-feature path hacks and hand them to `/build` — the wiring is a project-level decision every feature and `/build` inherit. Name any cross-runner convention the tests depend on (an import alias like `@/`, a test base-URL the framework needs). With a single runner this collapses to the simple case.

Derive two categories of tests, both from `spec.md`:
1. **Behavioral tests** — does it do what the requirements specify?
2. **Seam tests** — do the design's seams hold? Timeouts fire at the right boundaries, errors map to the right taxonomy, interfaces between components behave as designed. Do not assert that a specific constructor was called with specific arguments, that a private attribute holds a specific value, or that an internal call signature matches the design — those test the implementation, not the seam. Rewrite any such candidate to assert the observable behavior instead.

Tests that read a repo-relative file must resolve the path from the test file's own location (`Path(__file__).resolve().parents[N]` or the language equivalent), never an absolute sandbox path.

**Minimum contract surface.** Writing tests before the code exists forces you to name some interface surface (an app factory, a cookie name, an env var, a UI test-id). Name only what a test genuinely needs to observe behavior, and reach for the most stable surface available. Naming an internal detail *only so a test can be written* is the same implementation-locking the gate flags — a **premature** test that over-constrains `/build` is as much a failure as a weak one. A weak test creates false confidence; a premature test forecloses valid implementations. Both are findings, and they pull in opposite directions: the fix for one is not to commit the other.

**Tag each test file's contract strength** with a one-line marker at the top, one of:
- `@frozen` — a real public contract (an interface this project exposes to callers, or an externally-observable behavior). `/build` must satisfy it as written.
- `@scaffolding` — an interface named only to make the behavior testable now; `/build` may refine the surface (rename the seam, change the call shape) as long as the *behavior* the test asserts still holds, logging the change in `build-deviations.md`.

Default behavioral assertions to `@frozen`; use `@scaffolding` only for interface details you are naming ahead of the implementation. An untagged test is treated as `@frozen`. The tag tells `/build` how much latitude it has and tells the gate which surfaces to scrutinize for over-constraint.

Tests written before `/build` implements against them are expected to fail (ImportError, skip, or red assertion) until the code exists — that is the point. The contract is that the suite, once green, means the feature is done.

If a requirement cannot be tested as written, do not paper over it with a weak test. Surface the gap and fix it by revising `spec.md`, then continue.

Write `features/[feature-name]-[number]/tests/`. Add a short **Coverage** section to `spec.md` mapping each requirement and each design seam to the test(s) that verify it, so the human can see the acceptance bar at a glance without reading the test files.

---

## Stage 4 — Independent adversarial gate

This is the one stage that must run in clean context. Spawn a fresh sub-agent (Agent tool, `general-purpose`) whose **only** job is to attack the spec and tests — not to build, not to defend, not to rewrite. A review folded into the pass that wrote the spec inherits that pass's blind spots no matter how capable the model is; an independent pass catches what the author cannot see itself missing. That is why this is a separate agent and not a self-review step.

Spawn prompt, in substance:

> You are an independent reviewer in clean context. Read constitution.md, declaration.md, `features/[feature-name]-[number]/declaration.md`, `features/[feature-name]-[number]/spec.md`, and every file in `features/[feature-name]-[number]/tests/`. Your only job is to find problems. Do not edit anything. Do not build. Zero findings is a valid outcome when the spec is sound — only surface a finding if you can name a concrete failure mode it would cause; drop generic concerns ("add more error handling", "think about scale").
>
> Review through these lenses:
> - **Scope drift** — what has been added beyond the feature declaration, or beyond the project declaration?
> - **Integrity** — do the documents contradict each other? Does the design implement the requirements? Do the tests actually verify the requirements, or do they assert implementation shape (constructor calls, private state, exact call signatures) instead of behavior? A test that locks in implementation detail is itself a finding. Honor the `@frozen` / `@scaffolding` tags: an `@frozen` test that pins a non-contract internal detail is a finding (it will over-constrain `/build`); a `@scaffolding` test gets latitude on its named surface, but flag any `@scaffolding` tag hiding a real behavioral assertion that should be `@frozen`.
> - **Coverage** — what behaviors or edge cases are unspecified or untested? Is any requirement covered only by a weak test?
> - **Security** — what attack surface does the design expose? Name the specific component and the requirement/design section where it lands; drop findings that only restate a pattern without a location. Honor `Reuses pattern:` markers by scoping those surfaces to HIGH severity only.
> - **Standards compliance** — does the design respect the applicable items in constitution.md's standards registry?
> - **Failure modes** — what breaks silently vs. visibly? What recovery is missing?
> - **HIG-native (Apple platforms only).** Run only if declaration.md's `## Platform` names an Apple platform. For each custom-built control, gesture, navigation pattern, settings/sharing surface, or system-integration touchpoint, ask whether Apple's HIG or a standard UIKit/AppKit/SwiftUI component already solves it. If yes, file a finding naming the custom thing, the platform pattern it duplicates, and what is lost by deferring — default recommendation is to delete the custom path. Skip entirely on web/CLI/server.
>
> Return your findings as a list. For each: a severity (HIGH / MEDIUM / LOW), the lens, the concrete failure mode, and whether it lands in the spec or the tests. A LOW finding must name a specific location or it is dropped. If nothing survives the bar, say so.

The gate does not loop. It runs once against the drafted spec and tests and returns its findings to the orchestrator.

---

## Resolving the gate and finalizing

Present the gate's findings to the user. These are the **only** stops `/spec` makes, alongside the product-judgment stops below. For each finding the user decides: **fix** it (you edit `spec.md` and/or `tests/` directly — you are the author now, not the gate), **acknowledge** the risk, or **proceed**. The author may fix as many findings as the user directs in this single resolution pass; there is no second gate run and no bounce-back loop.

**Re-gate security fixes.** When the user chooses to **fix** a HIGH or MEDIUM *security* finding, that fix is written by the same author who wrote the spec — reintroducing, one level up, the single-author blind spot the gate exists to remove. After applying such a fix, spawn one fresh clean-context sub-agent (Agent tool, `general-purpose`) scoped to **only the fix**: hand it the finding and the diff of what changed in `spec.md`/`tests/`, and ask whether the fix actually closes the named failure mode or merely relocates it. This is cheap and bounded — one finding, one diff, no full re-review — and runs once per fixed HIGH/MEDIUM security finding, never in a loop. Fold its verdict into the `## Adversarial gate` record. LOW findings and non-security fixes do not trigger a re-gate.

Record the outcome in an `## Adversarial gate` section at the bottom of `spec.md`: the mode (clean-context gate), what was found, and the disposition of each finding (fixed / acknowledged / proceeded). For every finding the user **acknowledges**, append one row to constitution.md's `## Acknowledged risks` table: feature name, severity (the *unmitigated* severity — an acknowledged HIGH stays HIGH), one-line risk, one-line rationale, mitigation (or "none"). This is the project's cumulative-risk surface and it must stay honest.

### When to stop

Stop and ask the user — using the exact product or scope question that needs judgment, not a list of technical options — when:
- The gate surfaces findings to disposition (above).
- The spec drifts in scope from the feature declaration, or the feature tensions with the project or feature declaration. Declaration tension usually means the feature is mis-scoped.
- A risk needs an explicit acknowledgment only the owner can make.

Everything else — writing the spec, writing tests, fixing findings the user has told you to fix — proceeds without pausing.

### Finalize

Once the gate is resolved and any product stops are settled:
1. Commit `spec.md`, the test files, `declaration.md`, and (if changed) constitution.md.
2. Push the branch (`git push -u origin <current-branch>`).
3. Ensure exactly one handoff PR exists against `main` (check `mcp__github__list_pull_requests` for the branch first; the cloud harness may have auto-created one on first push — update it rather than opening a second). The PR is the handoff: `/build` always runs in a separate session off a fresh `main`, so the spec must be merged before `/build` can begin.
   - Title: `spec: [feature-name]`
   - Body: a plain-language summary of what the feature does (written for someone who hasn't read the spec), the acknowledged risks in product terms, what is out of scope, and a closing line — "Merge this, then start a new session and run `/build feature-name: [name]` from `main`."
   - Ready for review (not draft). No reviewers or assignees (the owner is the PR author).

Do not merge. Give the user the PR URL and the next step.

Exit condition: `spec.md` and `tests/` exist, the adversarial gate has run in clean context and its findings are dispositioned, acknowledged risks are in constitution.md, and a handoff PR is open against `main`.
