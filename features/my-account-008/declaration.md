# Feature declaration — My Account (008)

## What
The per-unit homeowner statement: a homeowner picks their unit (once, remembered)
and sees a personal financial picture for an as-of date — last year's wrap-up,
this year's running balance (carryover + dues − paid = what's left), a
"pay about $X/month to stay current" guidance line, and a list of their recent
dues payments so they can confirm a check landed. A dedicated read API
(`GET /api/account?unit=…&as_of=…`) plus a "My Account" section on the existing
single dashboard page. No schema change; it reuses the dues engine built in 007.

## Why
The nine homeowners are view-only users who today have to ask the treasurer
"what do I owe?" This slice answers that question for them directly and
trustworthily: it derives each unit's obligation from the same operating-budget
math the board sees in Dues by Unit (007), shows where this year's carryover came
from, and turns the remaining balance into a concrete monthly target so a
homeowner can self-manage their payments without treasurer intervention. The
*new* surface — payment guidance (standard monthly, a "snap at the 15th"
suggested monthly, and the year-end / paid-in-full / credit edge states) — is
integer-cent financial math, so it lands on the constitution's highest-value test
surface and is pinned to hand-verified worked examples.

## Success
- For a chosen `unit` and as-of date in a year ≥ 2025, `GET /api/account` returns
  that unit's ownership share, a **current-year** block (carryover, annual dues,
  total due, paid YTD, remaining balance), a **prior-year** block (last year's
  budgeted dues, paid, and the balance carried forward), **payment guidance**, and
  a **recent-payments** list. All money is integer cents and the current-year
  figures match the unit's row in `GET /api/dues` for the same date exactly (it
  reuses the 007 engine; it does not re-derive carryover).
- Payment guidance, in integer cents, hand-verified:
  - `standard_monthly` = annual dues ÷ 12.
  - `months_remaining` = `(12 − month + 1)` when the as-of day ≤ 15, else
    `(12 − month)` (e.g. Mar 1 → 10, Mar 16 → 9; driven by the as-of date).
  - `suggested_monthly` = remaining balance ÷ months_remaining when the unit owes
    and months remain; otherwise it is absent and a status conveys the situation:
    **paid in full** (remaining 0), **credit** (remaining < 0), or **due by Dec 31**
    (remaining > 0 but months_remaining is 0, i.e. after Dec 15 — never a divide
    by zero).
- Recent payments are the unit's own `Dues <number>` credits in the current and
  prior calendar year, newest first, each through the as-of date — no other unit's
  or category's credits, no separate "load more".
- A homeowner self-selects their unit from a dropdown; the choice persists across
  visits (localStorage). Selection is a **convenience, not an authorization
  boundary**: any authenticated session (view-only or admin) may read any unit,
  role enforced server-side, never taken from client input. The view is read-only.
- A pre-2025 as-of date reports dues-not-tracked (mirrors 007) rather than an error.

## Shape touched
- **Budget, dues & units model** — a per-unit statement assembler that *reuses*
  `app/dues.py` (`operating_budget`, `annual_dues`, `unit_paid`, `carry_in`) and
  adds only the new payment-guidance and recent-payments logic, as a plain,
  integer-cent testable module.
- **API layer** — one authenticated read endpoint, `GET /api/account?unit=…&as_of=…`.
- **Dashboard & reporting UI** — a "My Account" section on the existing dashboard
  page with a unit selector (localStorage-persisted) that shares the dashboard's
  as-of-date control.

## Out of scope
- **Recording or collecting payments.** Payments enter via categorized
  transactions (ingestion + categorization); this feature reads them.
- **Editing `unit_past_dues` / the 2025 baseline**, the income-budget / interest
  (0.1%) derivation, and **pre-2025 dues computation** — all walled off in 007 and
  unchanged here.
- **A budget-lock / "amounts are preliminary" notice.** The homeowner does not see
  lock state; whatever budget exists is shown.
- **Per-unit login or any authorization tied to unit selection.** Unit selection
  is a convenience only (declaration-level decision).
- **Print / PDF export.** Removed project-wide; the single scrollable dashboard
  page is the report. Not a gap.
- **A separate page, route, or tab**, multi-year trend analytics, and any schema
  change.
