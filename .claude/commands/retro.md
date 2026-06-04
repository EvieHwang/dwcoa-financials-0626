---
description: Coached retro at the end of a feature build. Produces features/[feature-name]-[number]/retro.md capturing what was learned and proposed template/constitution/CLAUDE.md changes.
---

Run after `/build` to capture what was learned during the feature build, and to propose changes to the template, constitution, or CLAUDE.md before the lessons evaporate.

Read in order: constitution.md, declaration.md, features/[feature-name]-[number]/declaration.md, features/[feature-name]-[number]/spec.md, and features/[feature-name]-[number]/build-deviations.md if it exists. Skim the feature branch's git log for the build phase.

This is a coached conversation. Walk the user through:

- **What went well.** Specific things — name the artifacts and decisions, not vague praise.
- **What went badly.** Tie each item to evidence: things the adversarial gate should have caught but didn't, spec gaps that only surfaced during the build, build deviations that point to a weak spec or a brittle test.
- **Spec vs. reality.** Where did the build diverge from the spec (see build-deviations.md), and what does that say about the spec or the tests? Did the adversarial gate earn its keep, or did it miss the things that actually bit?
- **Spec-authoring lessons (the feedback loop).** Read `build-deviations.md` as the signal from execution back to authoring — this is the one route that closes the loop, so do not skip it when the file exists. For each deviation ask: was this a one-off, or a *recurring* spec-authoring mistake (a premature/over-constrained test, a behavioral requirement stated as implementation, a missing seam, a frozen-too-early surface that should have been `@scaffolding`)? Turn the recurring ones into concrete entries for constitution.md's `## Spec-authoring lessons` — each phrased as a rule the next `/spec` can apply, tagged with this feature. Without this, `build-deviations.md` stays a local note and the same mistakes recur silently across features.
- **Recommended additions to constitution.md.** Patterns, principles, quality gates, acknowledged-risk rows, and the `## Spec-authoring lessons` entries from the loop above.
- **Recommended additions to CLAUDE.md.** Precedent repos, one-time setup steps, deploy-target nuances surfaced during this build.
- **Recommended changes to skill prompts.** Specific edits to specific skills (e.g., "`/spec` should …", "`/build` should …"). Frame as proposed diffs, not vague feedback.

Write features/[feature-name]-[number]/retro.md with these sections (including a `## Spec-authoring lessons` block holding the proposed constitution.md entries from the feedback loop). The "Recommended additions" sections should be formatted so they can be lifted directly into a template-update PR — concrete blocks of markdown rather than narrative observations. The `## Spec-authoring lessons` entries are project-level by default (they land in this repo's constitution.md); mark any that are genuinely template-level so they propagate to the framework.

Distinguish project-specific learnings (which stay in this repo's constitution.md / CLAUDE.md) from template-level learnings (which should propagate to the framework template). Mark each recommendation accordingly.

Present the retro to the user for review. Revise until it is sound.

Commit the completed retro.md to the current branch.

Exit condition: features/[feature-name]-[number]/retro.md exists with all sections populated, project-vs-template recommendations are clearly marked, the user has confirmed it, and the file is committed.
