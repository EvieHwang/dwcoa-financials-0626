# Build deviations — legacy-migration-002

Honest record of where the build diverged from the spec's design or corrected a
test. Written to be legible to a future spec author (`/retro` mines this).

## 1. Corrected two foundation-001 tests pinned to a pre-drift category name

**Tests changed:** `features/foundation-001/tests/backend/test_seed.py`
- `test_reference_data_seeded` — assertion set contained `"Interest income"`.
- `test_budget_amounts_in_cents` — `EXPECTED_BUDGET_CENTS` keyed `"Interest income": 2600`.

**Original assertion:** both required the seeded category to be named
`Interest income`.

**Why it was wrong:** legacy-migration-002 R10 establishes that production's
canonical category name is `Interest`, not `Interest income` (the live treasurer
DB had drifted from foundation's hardcoded seed). R10 *requires* the seed to use
`Interest`, so foundation's assertions on the old name became a direct
contradiction with the current feature's spec — not a behavior this build could
satisfy without changing them. Satisfying R10 necessarily breaks them.

**What was corrected:** both assertions now use `Interest` (and `"Interest": 2600`),
matching the corrected seed. No behavioral assertion was weakened — the budget
cents, counts, and idempotency checks are unchanged; only the category *name*
literal moved to production's real value.

**Spec-authoring lesson:** foundation-001 froze reference-data *content* (a
specific category name) into a test as if it were a stable contract, when it was
really a snapshot of seed data that the live system had already diverged from.
Reference-data names/types that mirror an external, drifting source are a poor
thing to pin with an equality literal in a foundational test — a later
data-migration feature is exactly when they get corrected. Prefer asserting
structural invariants (counts, money-is-cents, FK integrity) over specific
seed-content strings, or localize seed-content assertions so a downstream
correction touches one place.

## 2. Backend test command changed from a single `pytest` to a per-feature loop

**Design/convention contradicted:** the constitution's `## Testing` run command
was `cd backend && .venv/bin/pytest`, with `testpaths` pointing at a single
feature's `tests/backend`. The implicit assumption was that adding a feature's
suite is just appending its dir to `testpaths` and running one `pytest`.

**What was found:** every feature's `tests/backend/` ships its own
`conftest.py`, and the test files import shared data/helpers with a bare
`from conftest import ...` (foundation: `COOKIE`, `do_login`, ...; legacy:
`LEGACY_BUDGETS`, `connect`, ...). Python can hold only one top-level module
named `conftest` per process, so collecting both dirs in one `pytest` run leaves
`sys.modules["conftest"]` pointing at whichever loaded last and the other
suite's `from conftest import ...` fails at collection. `--import-mode=importlib`
does not help — it breaks the bare `from conftest import` in *both* suites.

**What was done instead:** the canonical backend command now runs one feature
directory per pytest process —
`for d in ../features/*/tests/backend; do .venv/bin/pytest "$d" || exit 1; done` —
which isolates each suite's `conftest` and scales automatically as features are
added. `testpaths` still lists both dirs (documents the full suite; a bare
`pytest` over it collides and is explicitly not the blessed invocation, noted in
`pyproject.toml` and `constitution.md`).

**Spec-authoring lesson:** the per-feature `tests/backend/conftest.py` +
`sys.path.insert(BACKEND)` + bare `from conftest import` pattern (inherited from
foundation) does not compose across features in a single pytest process. A
future spec that adds a backend test suite should either (a) expect the
per-directory loop runner, or (b) move shared importable test data into a
uniquely-named module (e.g. `_legacy_fixtures.py`) and keep `conftest.py` for
pytest fixtures only, so a single combined `pytest` invocation could work.
