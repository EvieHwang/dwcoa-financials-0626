# Feature declaration — Dues by unit (007)

## What
The association-wide, per-unit dues table: for a chosen year (driven by an as-of
date) it shows, for each of the nine units, its ownership share, the balance
carried in from prior years, this year's expected dues, what it has paid through
the as-of date, and what it still owes. This is the board/treasurer view of who
owes what — the per-unit dues status that Dashboard (006) deliberately left out.
A read API (`GET /api/dues`) plus a dues table embedded in the dashboard view.
No schema change — `units`, `unit_past_dues`, `budgets`, and the `Dues <unit>`
income categories all already exist.

## Why
Collecting dues is the association's core recurring task, and the treasurer needs
a single trustworthy answer to "is each unit current, and if not, by how much?"
Dashboard (006) gives the association-level picture but says nothing per unit.
This feature derives each unit's obligation from the operating budget and its
ownership percentage, tracks payments already recorded against that unit, carries
forward last year's balance (or credit), and presents outstanding balances the
board can act on. Getting the carryover and outstanding math provably correct —
in integer cents, against hand-verified examples — is the whole point; the
constitution names per-unit carryover and dues expected/paid/outstanding as
required test surfaces.

## Success
- For a year ≥ 2025 and an as-of date, `GET /api/dues` returns, per unit:
  ownership share, carry-in balance, this year's expected dues
  (`operating budget × ownership`, full annual — not prorated), amount paid
  through the as-of date, and outstanding (expected_total − paid). All integer
  cents; row figures and totals foot exactly as shown.
- Each unit's annual dues is its ownership share of the **total operating
  budget** (sum of the year's active Expense-category budgets); the nine shares
  naturally sum to ~99.9% of the operating budget (ownership sums to 999‰) and
  this feature does **not** gross that up, derive interest, or touch the income
  budget — it stays fully separate from the dues/interest derivation.
- Carryover accumulates forward from a 1/1/2025 baseline (`unit_past_dues`):
  for each prior year, `carry-in + annual dues − payments`, and can go negative
  (a credit) when a unit overpays. Pre-2025 dues are not computed (the legacy
  per-unit-category path is dropped); a pre-2025 as-of date reports
  dues-not-tracked rather than an error.
- Payments are the credits on a unit's `Dues <number>` income category within the
  year, counted through the as-of date; non-dues income never counts.
- View-only and admin sessions both read the table; role is enforced server-side
  and never taken from client input. The view is read-only — no write path.

## Shape touched
- **Budget, dues & units model** — the dues engine (operating-budget basis,
  per-unit annual share, multi-year carryover, paid/outstanding) as a plain,
  testable, integer-cent module; reusable by My Account (008).
- **API layer** — one authenticated read endpoint, `GET /api/dues?as_of=…`.
- **Dashboard & reporting UI** — a per-unit dues table embedded in the dashboard
  view, sharing the dashboard's as-of-date control.

## Out of scope
- **My Account (008).** The per-unit homeowner statement, self-select-your-unit,
  and payment guidance are the next slice. This feature is the association-wide
  table only. The carryover engine is built here so 008 can reuse it.
- **Income-budget / interest derivation.** Deriving the income budget from the
  operating budget, or the dues-99.9% / interest-0.1% split, is explicitly not
  done here. Dues and income budgets stay separate processes (the prototype
  linked them out of convenience; we don't).
- **Pre-2025 dues.** Historical pre-2025 data stays in the DB as untouched
  reference; this feature neither computes dues from it nor tries to make it
  accurate.
- **Editing `unit_past_dues`.** The 1/1/2025 baseline is read-only and computed
  forward; there is no in-app edit surface for it.
- **Recording or collecting payments.** Payments enter via categorized
  transactions (ingestion + categorization); this feature reads them, it does not
  add a payment-entry or online-payment path.
- **PDF / print export** and **schema changes.**
