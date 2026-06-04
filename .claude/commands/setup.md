---
description: Coached repository setup after cloning the Evie tiered-build template. Fills CLAUDE.md (project name, one-liner, run/test/deps block, deployment target) and declaration.md (what / why / for whom / out of scope / shape / roadmap) in one session, then commits both. This is the single command to run on a fresh clone before any feature work begins.
---

This command runs once per freshly-cloned template. It does not touch `constitution.md`; those edits happen as the project develops (see `user-guide.md` §"New project setup").

Before starting, read `CLAUDE.md`, `README.md`, `declaration.md`, and `user-guide.md` §"New project setup". If `CLAUDE.md` no longer contains `# [Project Name]` (the placeholder), the repo has already been set up — confirm with the user whether to re-run before making any edits.

Verify the working branch matches `claude/<short-task-name>-<suffix>` (the sandbox provisions it). If not, surface the discrepancy and stop.

---

## Phase 1 — Operational setup

These four fields are low-stakes and usually pre-decided in planning, so **default to expert mode**: propose a complete draft of all four at once — inferring sensible defaults from the repo contents and the conversation that led here — and ask the user to confirm or hand back diffs. Walk them one-topic-per-turn only if the user is undecided, asks to be coached through it, or the repo gives you nothing to infer from. (Save the slow, one-question-per-turn cadence for the genuine forks: Phase 2's Shape and Roadmap, and the product/scope stops in `/spec`. Cadence should scale with stakes, not be uniform.)

The four fields, in order:

1. **Project name** — short, human-readable. Used to replace `# [Project Name]` in CLAUDE.md and as the `#` heading in the new README.
2. **One-line description** — what the app is, in a sentence. Becomes the README subtitle and a comment line in CLAUDE.md.
3. **Stack / runtime** — pick the run/test/deps block. Offer the common shapes (Node + pnpm/npm, Python + pyproject, Swift/Xcode, static site, "skip — fill later"). If the user names a stack not on the list, accept it and synthesize a reasonable block.
4. **Deployment target** — Eviebot (self-hosted Mac mini, launchd), AWS (us-east-1, account 070840362692), Apple/Xcode (App Store / TestFlight), or "none yet". Pull the canonical coordinates from CLAUDE.md's `## User globals` block when writing Eviebot/AWS targets.

Hold answers at the level the template expects — names and commands, not architecture. If the user starts describing features or behavior, note it and redirect: that will come out in the declaration conversation that follows.

Confirm the four answers back to the user before writing anything.

**Write and commit:**

`README.md` — overwrite with:

```
# <Project name>

<One-line description>
```

`CLAUDE.md` — make these edits, preserving the rest of the file verbatim (especially the `## User globals — Evie Hwang` section at the bottom):
- Replace `# [Project Name]` with `# <Project name>`.
- Replace the bracketed one-line-description placeholder with the user's one-liner.
- Under `## Run, test, deps`: replace the instruction text with a single uncommented block for the chosen stack (install, run/dev, test commands). If the user picked "skip", leave a single-line TODO comment.
- Under `## Deployment target`: replace the instruction text with a single uncommented block for the chosen target. For Eviebot: reference `/Users/eviebot/services/<repo-name>/` and `launchd`. For AWS: reference account `070840362692`, region `us-east-1`, secrets from the repo's GitHub Actions secrets. For Apple/Xcode: reference Xcode build + signing. For "none yet": leave a single-line TODO.

Do not modify `declaration.md`, `constitution.md`, or anything under `features/`.

Present the diff of the two changed files to the user. Revise until confirmed.

Commit `README.md` and `CLAUDE.md` together:

```
chore: initialize <project name> from template

- README stub
- CLAUDE.md: project name, one-liner, <stack> run/test, <target> deploy
```

Do not push yet — the declaration commit follows on the same branch.

---

## Phase 2 — Declaration

Tell the user: "Operational setup is committed. Now let's write the project declaration — this captures intent, scope, the app's Shape, and the Roadmap so every feature build starts from a shared understanding."

The project name and one-liner from Phase 1 seed this conversation — do not re-ask for them. Use them as the starting point for the What section and refine from there.

Ask in this order; one topic per turn, do not batch:

1. **What** — what this project is. The one-liner is the seed; ask the user to expand if needed. One or two sentences, no implementation detail.
2. **Why** — the problem it solves or the need it serves.
3. **For whom** — who uses it and what they need from it.
4. **Out of scope** — what this project explicitly does not do.
5. **Platform** — where this runs. One of: iOS, macOS, iPadOS, visionOS, watchOS, tvOS, web, CLI, server, cross-platform (name the platforms), or other (describe). Apple-platform answers (iOS / macOS / iPadOS / visionOS / watchOS / tvOS, alone or in combination) trigger the HIG-native lens in `/spec`'s adversarial gate, which pushes back on custom-built controls, gestures, navigation, or settings surfaces that Apple's Human Interface Guidelines already solve. Note this to the user when they pick an Apple platform.
6. **Shape** — once the above is settled, ask the user to name 3–7 components or seams the app will eventually have. One line each, no diagrams, no contracts, no data models. This is not architecture — it is a map of the parts that exist so the first feature has something to slice against. Tell the user explicitly: this is revisable as the project learns; the goal is to make implicit decomposition explicit, not to commit to a system design.
7. **Roadmap** — after the Shape, ask the user to name the next 3–7 features they anticipate building, in rough order. One line each. Tag each with the Shape seams it touches. This is **not a commitment** — it is memory. The thinking the user does now about "what comes next" otherwise evaporates and has to be reconstructed when feature 2 starts. Tell the user explicitly: the Roadmap is revisable as reality diverges; anything beyond the horizon is fiction. Do not solicit acceptance criteria, effort estimates, or specs — those belong in the per-feature declaration when the feature is actually about to be built.

Hold the conversation at the level of intent, not implementation. If the user starts describing how something works rather than what it is, redirect — that content belongs in constitution.md or feature artifacts.

Continue until the declaration is clearly formed. Do not proceed to writing until the user confirms.

**Write and commit:**

Write `declaration.md` (at the repo root) with sections labeled `## What`, `## Why`, `## For whom`, `## Out of scope`, `## Platform`, `## Shape (revisable)`, and `## Roadmap (revisable)`. The Shape section is a bulleted list, one line per component/seam. The Roadmap section is a numbered list, one line per anticipated feature, each tagged with the Shape seams it touches (e.g., `1. Auth — adds login/logout. Touches: API gateway, user store.`).

Present the written declaration to the user for review. Revise until it says what they meant.

Commit `declaration.md`:

```
docs: add project declaration

What / Why / For whom / Out of scope / Shape / Roadmap
```

---

## Exit condition

- `README.md` is an app stub (name + one-liner), no template framework text remains.
- `CLAUDE.md` has the project name, one-liner, an uncommented run/test/deps block, and an uncommented deployment-target block. `## User globals` is preserved untouched.
- `declaration.md` is populated with all six sections, confirmed by the user.
- Both commits are on the current branch.
- **Handoff.** In a cloud sandbox each session re-clones from `main`, so setup must reach `main` before feature work can build on it: push the branch (`git push -u origin <current-branch>`) and ensure exactly one setup PR is open against `main` (the harness may have auto-created one on first push — update it rather than opening a second). The owner merges it before the first `/feature`. Working locally instead, you may leave the commits unpushed and continue straight into `/feature` in the same session.
- Tell the user: "Setup complete. Once this PR is merged, the next step is `/feature` (in a fresh session, from `main`) when you're ready to define the first feature. You can also refine `constitution.md`'s app-specific sections (architectural principles, patterns, quality gates, out-of-scope) before starting feature work."
