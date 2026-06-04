# Feature Declaration: Legacy Data Migration

**Feature:** legacy-migration-002
**Slice:** 2 of the DWCOA Financials rebuild

## What
A one-time, offline importer that reads the legacy production SQLite database (`dwcoa.db`, pulled from S3 in a local session with AWS access) and writes its data into the new app's schema, producing a ready-to-deploy SQLite file for the Fly volume. The importer is a pure, tested transform-and-load: it copies every row of real data — 6 years of transactions, multi-year budgets, categories, accounts, units, per-unit past dues, categorize-rules, app config, and budget locks — converting the legacy representation into the new one and preserving primary keys so all foreign-key references stay intact.

Two changes ride along because the migration exposed them:
- **Foundation seed gating.** The legacy DB has drifted from foundation's hardcoded seed (e.g. category `Interest` vs the seed's `Interest income`, `Reserve Fund` vs `Reserve Expenses`, `Reserve Contribution` typed Expense not Transfer, plus five categories the treasurer added). The seed must become an empty-DB bootstrap only, so it never injects conflicting phantom rows on top of migrated production data. The dev/test seed is also corrected to match production's canonical names and types.
- **`budget_locks` schema restoration.** Foundation declared it established the full schema but omitted the `budget_locks` table, which the legacy app uses as an in-year safeguard against accidental budget edits (2025 and 2026 are currently locked). A new migration adds the table so the lock state can be carried over; enforcement behavior is restored later in the Budgets feature.

## Why
The rebuild replaces a live, in-use system. The treasurer's real history — categorized transactions back to 2021, the budgets and dues balances the board relies on, the rules that make categorization work, and the locked-budget safeguards — must arrive in the new app intact and to-the-cent, or the rebuild is a regression rather than a replacement. Doing this as a tested offline transform (rather than a permanent in-app import endpoint) keeps the cutover auditable and adds zero ongoing surface to operate. Getting the money conversion provably correct is the whole point: this is the feature that proves the new schema can hold the old reality without losing or corrupting a cent.

## Success
- Running the importer against the legacy `dwcoa.db` produces a new-schema SQLite file whose transactions, budgets, past-dues, categories, accounts, units, rules, app config, and budget locks all match the source, with monetary amounts converted exactly to integer cents and ownership converted exactly to integer per-mille.
- Every foreign-key reference in the output resolves (transactions → categories, budgets → categories, rules → categories, past-dues → units) — verified, no dangling ids.
- Per-year transaction counts and per-year budget totals in the output equal the legacy source to the cent.
- The locked-budget state (2025, 2026 locked; 2024 open) is preserved.
- The foundation seed, run against the migrated DB, is a no-op — it adds no rows and changes no values; run against an empty DB it still bootstraps a complete dev/test dataset whose category names and types match production.
- The importer is idempotent and refuses to overwrite a target that already holds real transaction data unless explicitly forced, so dry-runs and re-runs are safe.
- A documented runbook covers the parts that only run locally: the S3 pull, the import command, landing the file on the Fly volume, and verifying counts post-cutover.

## Shape touched
- **Persistence & deploy substrate** — a `budget_locks` migration; the seed-gating change; the importer's output is the production DB that lands on the Fly volume.
- **Transaction ingestion & store** — the transactions table is populated from legacy history (this feature loads it directly; CSV ingestion is a later slice).
- **Budget, dues & units model** — budgets (multi-year), per-unit past dues, units (ownership), categories, and rules are migrated; budget-lock state is carried.

## Out of scope
- **The actual S3 pull and Fly deploy of the migrated DB.** Those run from a local session with AWS access, following the runbook this feature ships. The feature delivers the importer and runbook, not the live cutover.
- **CSV ingestion, dedup, and account-number mapping** — the next slice. This feature loads the already-clean legacy rows directly, not via the CSV path.
- **Budget-lock enforcement** (rejecting edits to locked years) — the table and data land here; the lock/unlock endpoint and edit-blocking logic are restored in the Budgets feature.
- **A permanent in-app import/upload endpoint** — deliberately not built; the importer is an offline one-time script with no runtime surface.
- **The `v_*` reporting views and the deprecated `units.past_due_balance` column** — intentionally dropped; the new app computes reporting in code and uses `unit_past_dues`.
- **Any change to categorization, budget proration, or dues math** — this feature moves data, it does not compute over it.
