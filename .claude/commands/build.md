---
description: Builds a feature against its finalized spec and test suite — plans, decomposes, and implements until the suite passes, using parallel subagents where the work warrants it, then opens a PR. Assumes /spec has already run and its adversarial gate has cleared. Does not re-open spec questions.
---

Read constitution.md, declaration.md, `features/[feature-name]-[number]/declaration.md`, `features/[feature-name]-[number]/spec.md`, and every file in `features/[feature-name]-[number]/tests/`. Note **every** runner in constitution.md's `## Testing` section — a polyglot repo has more than one (e.g. pytest and Vitest), each with its own run command and test root, and the bar is all of them green.

`/build` assumes the spec and tests are final: they have already cleared `/spec`'s independent adversarial gate, and `/spec`'s handoff PR has been merged to `main`. Your job is to make the test suite pass without re-litigating the spec. Plan, decompose, and implement — the runtime owns the orchestration; you are not walking a hand-built DAG.

Confirm the inputs are present:
- `spec.md` exists and `tests/` is non-empty.
- The `## Testing` section names at least one runner and run command (and, for a polyglot repo, the test root for each).

If either is missing, stop and tell the user — `/build` runs after `/spec`, not before it.

## Build

1. **Plan and decompose.** Read the spec and tests, and lay out the work the suite implies. Where the work has independent parts that can proceed in parallel, dispatch them to parallel subagents (Dynamic Workflows); where it is inherently sequential or small, do it directly. Use judgment about which shape fits — you are not required to parallelize, only to not serialize work that needn't be.
2. **Implement against the tests.** The tests are the bar. Before writing code for a slice of behavior, run its tests and confirm they fail in the expected way (right module, right reason) — a test that passes before its behavior exists is mistagged or wrong; investigate it rather than building past it.
3. **Iterate until green.** Run the suite, fix what fails, repeat. Commit as logical units of work land.
4. **Final full-suite run.** When you believe the feature is complete, run every runner in the constitution's `## Testing` section with its own run command. All tests across all runners must pass — a green Python suite with an unrun frontend suite is not done.

There is no wave loop, no `state.md`, and no per-wave checkpoint-and-push choreography — the runtime keeps its own working state. Commit and push as you would for any branch; you do not need to push after every unit to keep state durable.

## The contract

**Tests are the source of truth.** When a test fails, assume the implementation is wrong. If, after genuine investigation, the test itself contains a clear error (a wrong assertion, a constraint built on a false assumption about the library or the requirement), you may correct it — but record the change in `features/[feature-name]-[number]/build-deviations.md` (create it if absent): which test changed, the original assertion, why it was wrong, what was corrected.

**Frozen vs. scaffolding tests.** A test tagged `@frozen` (or untagged) is a hard contract — satisfy it as written. A test tagged `@scaffolding` named an interface surface ahead of the implementation (a seam name, a call shape, an env-var name) only to make the behavior testable; if implementation reality makes that surface wrong, you may refine the surface so long as the behavior the test asserts still holds, logging it in `build-deviations.md` (which test, what surface changed, why). This is latitude over provisional interface detail, not license to weaken a behavioral assertion. If a `@scaffolding` test turns out to be guarding real behavior you cannot satisfy, treat it like any frozen requirement problem and kick back to `/spec`.

**The spec's requirements are immutable.** If a requirement looks wrong — not just hard, but actually wrong — stop. Do not edit `spec.md`. Surface the problem and kick back to `/spec`: requirements are revised there, against a fresh adversarial gate, not patched mid-build. This is the one case where `/build` hands control back instead of pushing through.

**Design is a recommendation, not a contract.** If implementation reality contradicts the design — a call shape doesn't exist, a library behaves differently, an API has changed — satisfy the behavioral requirement a different way and record the deviation in `build-deviations.md`: the design section contradicted, what was done instead, and why. Do not silently rewrite `spec.md` in place. Deviations are the honest record of where the build diverged from the plan.

`build-deviations.md` is the feedback channel back to spec-writing, not just a local note: `/retro` mines it for recurring spec-authoring mistakes and routes them to constitution.md's `## Spec-authoring lessons`, where the next `/spec` reads them. Write each deviation to be legible to a future spec author — name the spec/test mistake it exposes (a premature `@scaffolding`-worthy assertion frozen too early, a behavioral requirement stated as implementation, a missing seam), not just the local fix.

## Open the PR

Open a PR against `main` with:
- **Feature** — what was built and why, from the feature declaration.
- **Spec** — link to `spec.md` and summarize the behavior and architecture.
- **Build summary** — what was implemented, and the final test results (the full suite passing is the headline).
- **Deviations** — link to `build-deviations.md` if it exists, and note anything that diverged from the design or any test that was corrected.
- **Risk** — anything to watch in subsequent work.

Ready for review (not draft). No reviewers or assignees (the owner is the PR author).

Exit condition: the full test suite passes, all changes are committed and pushed, and the PR is open against `main`.
