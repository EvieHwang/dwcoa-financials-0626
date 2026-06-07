# Feature declaration — Budgets (005)

## What
Budget management for DWCOA: per-year, per-category annual budget amounts with
timing patterns and per-line timing overrides, copy-a-year-forward, year
locking, and a centralized YTD-proration engine. A treasurer-facing budget
editor plus a read API, built on the existing `budgets` and `budget_locks`
tables (no schema change).

## Why
The treasurer sets and finalizes each year's operating budget by category. Two
things make that workflow trustworthy:

- **Timing-aware proration.** Comparing budget-to-date against actual-to-date
  mid-year is only honest if each line is paced by how it is actually spent. An
  annual insurance bill paid once in March should not show as "half-budgeted,
  fully-spent, over budget" in June. Proration is stepped by timing pattern so
  annual lines count their full amount upfront, quarterly lines step at quarter
  boundaries, and monthly lines accrue month by month — never a naive
  months÷12 across every line.
- **Locking.** Once a year's budget is approved it must be protected from
  accidental edits. Lock enforcement is the piece migration 2 explicitly
  deferred to this feature.

A per-line timing override gives the treasurer flexibility: an irregular expense
gets an `annual` line for that year (full-upfront treatment) without changing
the category's default timing.

## Success
- The treasurer can set/adjust each category's annual budget for a year,
  override an individual line's timing, copy a prior year forward as a starting
  point (with confirmation before overwriting a non-empty target year), and
  lock/unlock a year.
- Writes to a locked year — upsert, copy-into, delete — are rejected (403).
- The centralized proration engine returns hand-verified YTD numbers for
  monthly, quarterly, and annual lines, in integer cents, for any as-of date
  (including dates before/after the budget year).
- View-only sessions can read budgets but cannot write; role is enforced
  server-side and never taken from client input.

## Shape touched
- **Budget, dues & units model** — budget read/write logic, lock enforcement,
  and the proration engine (plain, testable modules).
- **API layer** — budget list/upsert/copy/lock endpoints.
- **Dashboard & reporting UI** — the budget editor (per-year grid, copy-year,
  lock toggle).

## Out of scope
- **Budget-vs-actual.** Joining budgets to transaction actuals for a
  budget-vs-actual summary is Dashboard (006). This feature provides the
  proration engine that the dashboard will consume; it does not compute actuals.
- **Calculated-dues / interest derivation.** The 2025+ "income budget = total
  operating budget, dues 99.9% + interest 0.1%" logic is Dues (007) / Dashboard.
- **Category management.** Creating/renaming/retyping categories, toggling
  active, and editing a category's *default* timing is a separate feature.
  Budgets edits only annual amounts and per-line timing overrides on existing
  (migrated) categories.
- **Account balances, reserve-fund status, monthly cashflow, charts, PDF/print**
  — all Dashboard (006).
- **Schema changes.** The `budgets` and `budget_locks` tables already exist from
  foundation + legacy-migration; this feature adds behavior, not tables.
