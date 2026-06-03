# Migration: V1 → V2 (2026-05-30)

## The thesis

V1 was built against a model that had to be forced into self-consistency and hand-walked through execution — convergence loops, stability markers, a DAG, wave sequencing, and a state file did that walking. That assumption no longer holds (Opus 4.8 + Claude Code Dynamic Workflows), so V2 keeps everything that encodes human judgment the model can't derive and hands everything that merely supervised the model's process back to the runtime.

The single test applied to every element: it survives if it carries *intent or constraint only the owner has*; it is cut if it exists to *supervise the model's process*. Tests are the deliberate exception — the executable half of "what done means" — so V2 makes them more central, not less.

## What was kept

- **`/setup`, `/declaration`, `/feature`, `/patch`, `/retro`, `/upgrade`** — upstream intent and utility. `/feature`'s walking-skeleton coaching and Roadmap-aware start are preserved verbatim as pure judgment.
- The **independent adversarial review**, now the final clean-context stage of `/spec` rather than a standalone command.
- The contracts that make autonomous execution trustworthy: **tests are the source of truth, requirements are immutable, design is a recommendation**, the **deviation-logging** discipline (`build-deviations.md`), the **"a weak test is worse than no test"** stance, and **acknowledged-risk propagation** to `constitution.md`.
- All non-derivable always-loaded content: the user-globals / Eviebot coordinates, the standards registry, the decision log, the acknowledged-risks table, the post-deploy-health-check rule, and the no-reviewers/no-assignees PR constraint.

## What was collapsed

- **`/requirements` + `/architecture` + `/adversarial` + `/tests` → `/spec`.** One forward pass produces a single `spec.md` (requirements and design written together) and an executable `tests/` suite, then runs an independent adversarial gate in clean context. The gate is a single pass, not a loop: no requirements↔architecture round-trips, no stability markers, no convergence counters, no multi-round bounce-back. It surfaces findings to the user — the only stops `/spec` makes, alongside genuine product-judgment stops — and the user fixes, acknowledges, or proceeds.
- **`/dag` + `/next` + the wave loop → `/build`'s native planning.** `/build` now assumes a finalized, gate-cleared spec, plans and decomposes the work itself (parallel subagents / Dynamic Workflows where warranted), and iterates against the tests until the suite passes. If it hits a genuine spec problem it kicks back to `/spec` instead of editing the spec.

## What was deleted

- Commands: `/requirements`, `/architecture`, `/adversarial`, `/tests`, `/dag`, `/next`.
- Machinery: the `state.md` artifact and its format spec, the per-wave push-for-durability hack, the one-DAG-per-session sizing apparatus, `verify.md`'s task→test mapping, and the artifact-existence-detection that drove loop re-entry.
- Always-loaded clutter the model now does unprompted: the `## Build flow note` in `CLAUDE.md`, the "read the constitution first" directives, and the conventional-commits convention in `constitution.md`.

## Artifact changes

A feature folder now holds `declaration.md`, `spec.md`, `tests/`, optionally `build-deviations.md`, and optionally `retro.md`. Gone: `requirements.md`, `design.md`, `adversarial-review.md`, `verify.md`, `dag.md`, `state.md`, `spec-summary.md` (the PM summary now lives in the spec PR body).

## Judgment calls

- **No standalone test-refinement command.** Tests stay central, but a separate `/tests` wasn't kept: `/spec` regenerates the suite (it detects existing artifacts and re-runs the gate), and `/patch` can refine tests directly. Re-running the whole `/spec` pass to adjust tests is cheap now that there's no loop around it.
- **`spec.md` folds requirements and design into one file.** A single capable pass writes them together; splitting them existed mainly to feed the req↔arch loop, which is gone. The behavioral-constraint discipline that kept design honest is preserved as a section within `spec.md`.
- **The PM summary became the spec PR body** rather than a committed `spec-summary.md` artifact — the PR is already the handoff surface between the `/spec` session and the `/build` session.
- **The adversarial gate's record lives in a section of `spec.md`**, not a separate living `adversarial-review.md` with stable IDs and re-verification — that bookkeeping only made sense for the multi-round loop.

## What to watch in practice

- **The single-pass spec.** The gate is the only safety net now that the req↔arch loop is gone. If specs start shipping with contradictions the gate misses, that's the signal the one-pass assumption is too aggressive for some feature shapes.
- **`/build` planning without a DAG.** Large features used to be force-split by the one-DAG-per-session sizing check. With that gone, `/build` is trusted to decompose and parallelize on its own; watch for builds that sprawl past a session or lose the thread on big features — that's where a lightweight sizing nudge might need to come back.
- **Gate independence.** The gate is only as good as its clean context. If it drifts toward defending or rewriting the spec instead of attacking it, the independence that justifies the whole stage is lost.
