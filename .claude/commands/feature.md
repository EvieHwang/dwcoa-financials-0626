---
description: Coached conversation that produces features/[feature-name]-[number]/declaration.md — the feature-level statement of intent anchored to the project declaration. Optional — `/spec` produces the declaration inline from the preceding conversation when run cold. Reach for `/feature` when scope is genuinely fuzzy and you want a coached scoping pass before the rest of the pipeline runs.
---

Read declaration.md and constitution.md before starting. Note the Shape section of declaration.md — the named components/seams are the parts this feature can slice against. Note the Roadmap section too — it captures the user's anticipated feature sequence and is the starting point for this conversation.

Check whether any prior feature folders exist under `features/`. If none exist, this is the project's first feature — run in **first-feature mode** (see below). If prior features exist, run in normal mode.

**Roadmap-aware start.** Before asking the user "what is this feature?", look at declaration.md's Roadmap and identify the next unbuilt entry (the first Roadmap entry whose work has not yet been done as a feature folder). Propose it as the default starting point: "Based on the Roadmap, the next feature looks like *[Roadmap entry]*. Is that what you want to build now, or has the plan shifted?" If the user confirms, use the Roadmap line as the seed for the conversation. If the user picks something different, ask whether the Roadmap should be updated to reflect the new sequence — divergence is fine, but it should be made explicit so feature 3 doesn't start from a stale plan. If declaration.md has no Roadmap section (older project), proceed without and recommend running `/declaration` to add one before the next feature.

If features/[feature-name]-[number]/declaration.md already exists (beyond template placeholders), ask whether the user wants to refine specific sections or rewrite from scratch.

**First-feature mode (walking skeleton).** When no prior features exist, coach the user toward a walking skeleton rather than the most valuable feature.

*Skip-the-prelude branch.* If the user has already articulated a thin cross-cutting slice — either in the conversation immediately preceding this skill, or as a Roadmap entry explicitly labeled walking-skeleton/skeleton/spine — validate the framing in one sentence ("Confirmed — that's a walking-skeleton shape: thin across the seams.") and proceed to Phase 1. Do not re-deliver the coaching prelude below. The prelude is for cases where the user is reaching for the highest-value feature first.

Otherwise, deliver the coaching prelude:

> "The first feature is not the most valuable feature — it is the thinnest vertical slice that exercises the seams in declaration.md's Shape end-to-end. Most behaviors will be stubbed, hardcoded, or minimal. The success criterion is *all the seams meet*; the value comes from feature 2 onward, which iterates against the skeleton. Picking the highest-value feature first usually means building a system without a spine — feature 2 then has to retrofit one."

In first-feature mode, the **Success** section should describe end-to-end reachability across the named seams, not depth on any one seam. If the user's first instinct is a deep slice through one component, surface the tension and ask whether a thinner cross-cutting slice would serve better. The user can still choose depth-first, but the choice should be deliberate.

If declaration.md has no Shape section (older project predating the Shape convention), surface this and recommend running `/declaration` to add one before continuing — first-feature mode depends on knowing the seams.

**Normal mode (feature 2+).** Coach toward depth on a coherent slice. Reference declaration.md's Shape to ask which components this feature touches; a feature that touches every seam is either a second walking skeleton (legitimate if the Shape has grown) or a feature that's trying to do too much (split it).

Phase 1 — coached conversation:
Ask the user to articulate this specific feature:
- **What** — what is this feature and what does it do?
- **Why** — why does it exist at this point in the project, and how does it serve the purpose in declaration.md?
- **Success** — what does success look like for this feature specifically? (First-feature mode: end-to-end reachability across seams. Normal mode: depth on the touched components.)
- **Shape touched** — which components from declaration.md's Shape does this feature touch? List them explicitly.
- **Out of scope** — what is explicitly not part of this feature?

The feature declaration must be consistent with the project declaration. Surface any tension between them before proceeding — that tension is either a feature mis-scoped or a project declaration that needs revising. If a feature requires a component not listed in the Shape, surface that too — either the Shape was incomplete (update declaration.md) or the feature is straying out of scope.

Hold the conversation at the level of intent, not implementation. If the user starts describing how it works, redirect — that content belongs in requirements or design.

**Feature-size sanity check.** Before confirming the declaration, check the size signals:
- Can the value be described in one sentence without "and" doing heavy lifting? Multiple "ands" usually means multiple features.
- If first-feature mode: shallow across many seams is correct.
- If normal mode: deep on a coherent slice is correct; broad and shallow across many seams (outside the skeleton case) usually means the feature should be split.
- Surface mis-sizing before Phase 2. Re-doing the declaration is much cheaper than re-doing the spec and tests.

Continue until the feature declaration is clearly formed. Do not proceed to Phase 2 until the user confirms.

Phase 2 — structured output:
Write features/[feature-name]-[number]/declaration.md with sections labeled `## What`, `## Why`, `## Success`, `## Shape touched`, `## Out of scope`. If this is a walking skeleton, note that explicitly at the top of the file (e.g., `*Walking skeleton — first feature.*`).

Present the written declaration back to the user for review. Revise until it says what they meant.

Commit the completed declaration.md to the current branch and push it. Do not open a PR — `/spec` opens the spec PR at the end of its pipeline. If the cloud harness auto-creates one on first push, leave it as-is; `/spec` will update it.

Exit condition: features/[feature-name]-[number]/declaration.md is populated with all five sections, the user has confirmed it, the feature declaration is consistent with the project declaration, and it is committed and pushed.
