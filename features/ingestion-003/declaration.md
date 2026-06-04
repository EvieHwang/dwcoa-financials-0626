# Feature Declaration: Ingestion

**Feature:** ingestion-003
**Slice:** 3 of the DWCOA Financials rebuild

## What
The in-app path by which transaction data enters the running system: the
treasurer uploads a bank-export CSV of the **full transaction history**, and the
server parses it, maps each masked account number to its account, converts every
dollar amount to exact integer cents, **dedups** against what is already stored,
and inserts only the genuinely new rows — never duplicating a row and never
clobbering a category already assigned to an existing one. The treasurer sees a
plain summary of what happened (how many rows added, how many skipped as
already-present, which rows referenced an unknown account). The feature also
exposes the stored transactions as a **paginated, filterable table** (by year and
account) that any logged-in user can read, while only an admin may upload.

This is the runtime complement to legacy-migration-002: that slice loaded six
years of clean history directly; this slice is how every subsequent month's data
arrives, safely and repeatably.

## Why
The treasurer's real monthly workflow is "export everything from the bank, upload
the whole file." That only works if re-uploading an overlapping history is
*safe* — idempotent to the row, and non-destructive to the manual categorization
work that accumulates between uploads. Getting dedup provably right is the whole
point of the slice: a duplicated transaction silently corrupts every balance,
budget-vs-actual, and dues figure downstream, and a clobbered category throws
away the treasurer's review work. Making the full-history upload the supported
(and only) ingestion mode keeps the mental model simple and the data trustworthy.

## Success
- Uploading a bank CSV adds every new transaction with its amounts stored as
  exact integer cents (`$371.40 → 37140`), maps each masked account number to its
  account name, and reports a clear summary of added / skipped-as-duplicate /
  unknown-account rows.
- **Re-uploading the same file is a no-op**: zero rows added, all skipped as
  duplicates. Uploading an overlapping file adds only the new rows.
- **Existing categories survive re-upload.** A transaction the treasurer has
  categorized is recognized as a duplicate and left untouched — its category is
  never reset.
- A row whose account number isn't one of the mapped accounts is still imported
  (tagged as an unknown account) and surfaced in the summary, never silently
  dropped and never blocking the rest of the file.
- A structurally invalid file (missing required columns) or a row with
  unparseable money/date is rejected as a whole — nothing is partially inserted —
  with an error the treasurer can act on.
- The stored transactions are viewable as a paginated table filterable by year
  and account; any authenticated user can read it, only an admin can upload, and
  the upload endpoint rejects view-only and cross-origin requests.

## Shape touched
- **Transaction ingestion & store** — the CSV parser, the dedup rule, account
  mapping, and the writes into the existing `transactions` table.
- **API layer** — an admin-only upload endpoint and an authenticated
  list/filter endpoint, reusing foundation's auth guards and same-origin/CSRF
  defense.
- **Dashboard & reporting UI** — an admin upload control with a result summary
  and a paginated, filterable transactions table in the existing dashboard shell.

## Out of scope
- **Categorization.** New rows land uncategorized; the rules engine, review
  queue, and rule-suggestion-on-fix are slice 4 (Rules categorization). This
  slice neither categorizes on ingest nor builds any categorizer.
- **CSV export.** Originally named in the slice scope, transaction CSV export is
  **cut** for this slice — a deliberate, recorded deviation from the
  constitution's "all data exportable as CSV" portability principle (portability
  is met by the copyable SQLite file plus the documented schema). It may return
  with the reporting slice if a real need emerges.
- **Re-mapping already-ingested "unknown account" rows.** If a row is imported as
  `Unknown` and the account is added afterward, re-uploading does **not** rewrite
  the stored name (the row is already a recognized duplicate). Correcting
  historical account names is not handled here.
- **Dashboard charts, balances, budget-vs-actual, transfers-excluded reporting** —
  the table here is the raw transaction store, not the dashboard (slice 6). The
  list shows all transactions regardless of category type.
- **Editing or deleting transactions** through this UI (category edits arrive
  with the review queue in slice 4).
- **Any change to the schema, migrations, or seed** — the `transactions` and
  `accounts` tables already exist from foundation + legacy-migration.
