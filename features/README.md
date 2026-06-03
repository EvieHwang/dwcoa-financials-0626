# Features

Artifacts for each feature live in their own folder.

**Naming convention:** `[feature-name]-[number]`
- Numbers are sequential per feature name, used for both ordering and disambiguation.
- Do not overwrite a previous version — create a new numbered folder.

Each folder is populated at runtime by `/spec` and `/build`:
- `declaration.md` — the feature's statement of intent (What / Why / Success / Shape touched / Out of scope).
- `spec.md` — the behavioral spec: requirements, design, coverage map, and the record of the adversarial gate.
- `tests/` — the executable acceptance suite. Once green, the feature is done.
- `build-deviations.md` — created by `/build` only if implementation diverged from the design or a test was corrected.
- `retro.md` — created by `/retro` if you run one.

Do not pre-create empty placeholder files. The folder and its contents are produced by the commands as they run.
