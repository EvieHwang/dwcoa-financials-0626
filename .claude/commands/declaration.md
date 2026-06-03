---
description: Refines or extends the project-level declaration.md on an existing project — updates Shape, Roadmap, or scope as the project learns. For a fresh clone, use /setup instead, which handles both operational setup and the initial declaration in one session.
---

Read the current `declaration.md` before starting.

If `declaration.md` does not exist or contains only template placeholders, this is a new project — use `/setup` instead, which combines operational setup and the initial declaration in one session.

If `declaration.md` is populated, ask the user what they want to revisit:
- **Refine specific sections** — common when the project has learned something that changes Shape or Roadmap, when a feature revealed a scope boundary that wasn't explicit, or when the Roadmap sequence has shifted.
- **Rewrite from scratch** — uncommon; appropriate when the project's direction has substantially changed.

Surface which sections are changing and why before writing. If a Shape change removes a component that existing feature declarations touch, flag that tension — the feature declarations may need updating too.

Hold the conversation at the level of intent, not implementation. Redirect implementation discussion to constitution.md or feature artifacts.

**Shape and Roadmap are explicitly revisable.** The goal of revisiting them is to keep the declaration honest as the project learns, not to preserve original thinking. A Shape that no longer reflects the actual components, or a Roadmap that no longer reflects the actual sequence, is worse than a revision.

When the changes are clear, write the updated `declaration.md` with all seven sections: `## What`, `## Why`, `## For whom`, `## Out of scope`, `## Platform`, `## Shape (revisable)`, `## Roadmap (revisable)`. If the existing declaration predates the `## Platform` section, ask the user to fill it in during this pass — naming an Apple platform (iOS / macOS / iPadOS / visionOS / watchOS / tvOS) activates the HIG-native lens in `/spec`'s adversarial gate. Present it to the user for review. Revise until it says what they meant.

Commit `declaration.md` to the current branch with a message describing what changed and why.

Exit condition: `declaration.md` reflects current project intent, the user has confirmed it, and it is committed.
