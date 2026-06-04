# Spec: Legacy Data Migration

**Feature:** legacy-migration-002
**Declaration:** `features/legacy-migration-002/declaration.md`

This feature delivers an offline, one-time importer that transforms the legacy
production SQLite database into the new app's schema, plus two schema/seed
changes the migration exposed. It is backend-only (Python, pytest). It computes
no business logic over the data — it moves data and proves the move is exact.

---

## Part 1 — Behavioral requirements

### R1 — Monetary values convert to exact integer cents
**As** the treasurer, **I need** every dollar amount to survive the migration to
the cent, **so that** balances, budgets, and past-dues in the new app match the
old system exactly.

- The legacy DB stores money as SQLite `REAL` (floating-point dollars):
  `transactions.debit/credit/balance`, `budgets.annual_amount`,
  `unit_past_dues.past_due_balance`. The new schema stores integer cents.
- **Acceptance:** for any source value `v` (a number with at most two decimal
  places), the output is the integer number of cents equal to `v` rounded to the
  nearest cent, half rounded away from zero, computed so that binary
  float artifacts never shift the result (`371.4 → 37140`, `625.44 → 62544`,
  `3981.85 → 398185`, `122489.78 → 12248978`).
- **Acceptance:** a `NULL` source value (e.g. `debit` on a credit-only row)
  converts to `NULL`, not `0`. Negative values (e.g. an overdrawn `balance`)
  convert with sign preserved.

### R2 — Ownership converts to exact integer per-mille
**As** the treasurer, **I need** each unit's ownership share preserved exactly,
**so that** dues and proration math is unchanged.

- Legacy `units.ownership_pct` is a `REAL` fraction (`0.117`); the new schema
  uses integer per-mille (`117`).
- **Acceptance:** `0.117 → 117`, `0.104 → 104`, `0.112 → 112`, computed without
  float-artifact drift, and the result satisfies the new schema's bound
  (`0 < pct <= 1000`).

### R3 — All rows migrate with primary keys preserved and foreign keys intact
**As** the treasurer, **I need** every record carried over with its
relationships, **so that** each transaction keeps its category, each budget its
category, each rule its category, and each past-due its unit.

- Tables migrated: `accounts`, `categories`, `units`, `unit_past_dues`,
  `budgets`, `transactions`, `categorize_rules`, `app_config`, `budget_locks`.
- **Acceptance:** every output row retains the source row's primary-key `id`
  (so existing foreign-key references remain valid without remapping).
- **Acceptance:** in the output, every `transactions.category_id` and
  `transactions.auto_category_id` (when non-NULL), every
  `budgets.category_id`, every `categorize_rules.category_id`, and every
  `unit_past_dues.unit_number` resolves to an existing parent row. No dangling
  references.
- **Acceptance:** row counts per migrated table equal the source; per-year
  transaction counts and per-year budget cent-totals equal the source.

### R4 — `timing`, status, review, and config fields carry over verbatim
- `categories.timing`, `budgets.timing` (which may be `NULL`),
  `transactions.status/needs_review/confidence/check_number`,
  `categories.type/default_account/active`, `categorize_rules.*`, and all
  `app_config` rows (including `current_year` and `last_upload_at`) carry over
  unchanged.
- **Acceptance:** `app_config['current_year']` in the output equals the source
  (e.g. `2026`); a `budgets.timing` that is `NULL` in the source remains `NULL`.

### R5 — Budget-lock state is preserved (without the unused `locked_by`)
**As** the treasurer, **I need** the locked-budget safeguard carried over, **so
that** prior/current-year budgets stay protected after cutover.

- The new schema gains a `budget_locks` table via migration (R8). It holds
  `year`, `locked`, `locked_at` — it does **not** carry the legacy `locked_by`
  column (there are no per-user identities in this app).
- **Acceptance:** every legacy `budget_locks` row appears in the output with the
  same `year`, `locked`, and `locked_at`; the locked set is preserved (in the
  current production data: `2025` and `2026` locked, `2024` absent/open).

### R6 — Legacy-only artifacts are dropped
- The legacy `v_transaction_summary`, `v_budget_summary`, `v_unit_summary`
  views and the deprecated `units.past_due_balance` column are **not** carried
  into the output. The output uses the new schema verbatim (the new schema has
  no such views or column).
- **Acceptance:** the output DB contains no views, and `units` has no
  `past_due_balance` column.

### R7 — The importer is safe to re-run and refuses to clobber real data
**As** the operator, **I need** dry-runs and re-runs to be safe, **so that** I
can rehearse the cutover without risk.

- The importer takes a source path and a target path. Running it twice against
  the same source produces an equivalent target (deterministic rebuild).
- **Acceptance:** if the target path already exists and already contains
  transaction rows, the importer aborts with a clear error and makes no changes,
  unless an explicit `--force` flag is given; with `--force` it rebuilds the
  target from the source.
- **Acceptance:** a missing or unreadable source aborts with a clear error and
  produces no partial target.

### R8 — The new schema gains a `budget_locks` table via migration
- A new versioned migration (after foundation's version 1) creates
  `budget_locks (year PRIMARY KEY, locked, locked_at)`, applied idempotently on
  startup like all foundation migrations.
- **Acceptance:** running migrations on a fresh DB creates `budget_locks`;
  running them again is a no-op; the `schema_migrations` table records the new
  version.
- This feature adds the **table only**. Lock *enforcement* (rejecting edits to a
  locked year) is out of scope (Budgets feature).

### R9 — The reference seed becomes an empty-DB bootstrap that never conflicts with migrated data
**As** the operator, **I need** the startup seed to leave migrated production
data untouched, **so that** deploying the migrated DB doesn't inject phantom or
contradictory rows.

- Foundation's `seed_reference_data` currently inserts per-row with
  `INSERT OR IGNORE`. Against a migrated DB whose categories differ in name from
  the seed (`Interest` vs `Interest income`, `Reserve Fund` vs
  `Reserve Expenses`), that would add conflicting rows.
- **Acceptance:** run against a DB that already contains category rows, the seed
  adds no rows and changes no values to any table (true no-op).
- **Acceptance:** run against an empty DB, the seed still produces a complete
  dev/test dataset.

### R10 — The dev/test seed matches production canonical names and types
**As** a developer, **I need** the seed to reflect production reality, **so
that** dev/test data doesn't diverge from what the app actually holds.

- **Acceptance:** the seeded categories contain no category named
  `Interest income` (it is `Interest`) and none named `Reserve Expenses` (it is
  `Reserve Fund`); `Reserve Contribution` has type `Expense` (not `Transfer`).
- **Acceptance:** the seeded category set (by name) equals the production set,
  including the five treasurer-added categories — `Membership & License`,
  `Reserve Income`, `202 & 302 Balcony Repairs`, `102 & 103 Leak Repairs`,
  `PB Replacement` — and any seed rule or budget that referenced a renamed
  category now references the corrected name.

### R11 — A runbook documents the local-only cutover
**As** the operator, **I need** written steps for the parts that only run
locally with AWS access, **so that** the cutover is repeatable and auditable.

- **Acceptance:** a committed runbook describes, in order: pulling `dwcoa.db`
  from S3 (`s3://dwcoa-data-070840362692/dwcoa.db`), running the importer to
  produce the new-schema DB, landing that file on the Fly volume
  (`fly ssh sftp`, replacing the seeded skeleton DB), and verifying post-cutover
  (row/lock counts match expectations). It names the importer command and flags.

### Out of scope (restated from declaration)
- The live S3 pull and Fly deploy (runbook only, not executed by this feature).
- CSV ingestion / dedup / account mapping.
- Budget-lock enforcement behavior.
- Any permanent in-app import endpoint.
- Any calculation over the data (categorization, proration, dues).

---

## Part 2 — Design

### D1 — Importer module (new)
`backend/app/legacy_import.py` — a plain, testable module, not a route handler
(per constitution: business logic lives in modules). It exposes:

Its public interface is the contract this feature's tests pin (named here
because the call shape *is* the contract):
- `to_cents(value: float | None) -> int | None` — maps a legacy dollar `REAL`
  (or `None`) to integer cents (or `None`).
- `to_permille(value: float) -> int` — maps a fraction `REAL` to integer
  per-mille.
  Both compute via decimal arithmetic on the value's exact decimal string so
  binary-float artifacts cannot shift the result, rounding half away from zero.
  **These functions are the highest-value test surface (R1, R2).**
- `build_target(source_path: str, target_path: str, force: bool = False) -> None`
  — (a) creates the target with the new schema by running the foundation
  migrations, (b) does **not** seed, and (c) reads each source table and writes
  the transformed rows into the target preserving primary keys, inside a single
  transaction so a failure leaves no partial target. Raises on a missing source
  or an occupied target without `force` (R7).
- A `__main__` CLI: `python -m app.legacy_import --source <legacy.db>
  --target <out.db> [--force]`, wrapping `build_target` with the clobber
  guard (R7).

**Behavioral properties:**
- Output money/ownership exact per R1/R2; NULLs and signs preserved.
- Output primary keys equal source; all foreign keys resolve (R3).
- Per-table counts, per-year transaction counts, and per-year budget cent-totals
  equal source (R3).
- `timing`/status/config carried verbatim (R4); lock rows carried minus
  `locked_by` (R5).
- No views or `units.past_due_balance` in output (R6).
- Source-missing or target-occupied (without `--force`) aborts cleanly with no
  partial write (R7).

**Reuses pattern:** foundation's DB access (`app.db.get_connection`) and
migration runner (`app.migrations.run_migrations`). The importer creates the
target schema *through* the existing migration path, not via hand-written DDL.

### D2 — `budget_locks` migration (extends foundation)
Append a version-2 entry to `app.migrations.MIGRATIONS` creating
`budget_locks (year INTEGER PRIMARY KEY, locked INTEGER NOT NULL DEFAULT 0,
locked_at TEXT)`. The existing version-tracking machinery applies it once and
idempotently (R8). No change to the version-1 migration.

**Reuses pattern:** foundation's `run_migrations` / `schema_migrations`
versioning — this is a new entry in the existing list, not a new mechanism.

### D3 — Seed gating + correction (modifies foundation)
`app.seed.seed_reference_data` changes in two ways:
- **Gate:** before seeding, if the DB already holds reference data (categories
  present), return without writing — making the seed a true no-op on any
  migrated or already-seeded DB (R9). This supersedes per-row `INSERT OR IGNORE`
  as the idempotency mechanism.
- **Correct:** the seeded category list, and any budget/rule keyed on a category
  name, are updated to production's canonical names and types (R10): `Interest`
  (not `Interest income`), `Reserve Fund` (not `Reserve Expenses`),
  `Reserve Contribution` typed `Expense`, plus the five treasurer-added
  categories. Newly added categories with no known timing/account use the schema
  defaults (`timing='monthly'`, `default_account` NULL), matching how they
  appear in production.

**Behavioral properties:** no-op on populated DB (R9); complete on empty DB
(R9); seeded names/types match production (R10). The gate must not depend on
seeding order across tables — presence of categories is the single guard.

### D4 — Runbook (new doc)
`backend/docs/legacy-import.md` — the operator runbook (R11). Plain prose: S3
pull command, importer invocation with flags, `fly ssh sftp` file-landing on the
volume, app restart, and a post-cutover verification checklist (expected row
counts, per-year transaction counts, locked years `2025`/`2026`).

### Test fixtures
Because the real `dwcoa.db` contains private financial data and is never
committed, the suite builds a **synthetic legacy-schema fixture DB** in a temp
dir, populated with rows that exercise the edge cases: credit-only and
debit-only transactions across multiple years, a negative balance, a `NULL`
`budgets.timing`, the real ownership fractions, the real past-due values
(including the unit-302 correction), multi-year budgets, locked and unlocked
years, and a category whose legacy name differs from the foundation seed. The
importer runs against this fixture; assertions check the output DB.

---

## Coverage

| Requirement / seam | Test(s) |
|---|---|
| R1 money → cents (incl. float-artifact values, NULL, negative) | `test_converters.py::test_to_cents_*` |
| R2 ownership → per-mille | `test_converters.py::test_to_permille_*` |
| R3 PK preservation | `test_import.py::test_primary_keys_preserved` |
| R3 FK integrity (no dangling refs) | `test_import.py::test_foreign_keys_resolve` |
| R3 counts + per-year aggregates equal source | `test_import.py::test_counts_and_year_aggregates_match` |
| R4 timing/status/config carried verbatim | `test_import.py::test_passthrough_fields_preserved` |
| R5 lock rows carried, `locked_by` dropped | `test_import.py::test_budget_locks_migrated` |
| R6 no views / no deprecated column in output | `test_import.py::test_legacy_artifacts_dropped` |
| R7 clobber guard + force + missing source | `test_import.py::test_refuses_existing_target`, `test_force_rebuilds`, `test_missing_source_aborts` |
| R8 budget_locks migration idempotent | `test_budget_locks_migration.py` |
| R9 seed no-op on populated DB; full on empty | `test_seed_gating.py::test_seed_noop_when_populated`, `::test_seed_complete_when_empty` |
| R10 seed names/types match production | `test_seed_gating.py::test_seed_canonical_names_and_types` |
| R11 runbook exists and covers the four steps | `test_runbook.py::test_runbook_documents_cutover` |

---

## Adversarial gate
[populated after the clean-context gate runs]
