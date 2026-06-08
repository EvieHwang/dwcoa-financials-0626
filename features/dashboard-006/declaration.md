# Feature declaration — Dashboard & reporting (006)

## What
The association-level financial dashboard: the at-a-glance view the board and
homeowners open to understand DWCOA's finances for a chosen point in time. For a
user-selected **as-of date**, it shows account balances (with beginning-of-year
context), income and expense summaries that compare actual-to-date against
**timing-aware prorated budget-to-date**, reserve-fund status, and one simple
monthly income-vs-expense chart. It joins the tables and engines built by earlier
slices (transactions, categories, budgets + the proration engine, accounts) into
a single read-only report view. Read API + dashboard UI; no schema change.

## Why
This is the payoff slice. Every prior feature — ingestion, categorization,
budgets — exists so the treasurer and board can see a trustworthy current picture
of the association's money. Until now the data is in tables but there is no
synthesized view. The dashboard turns it into the report the board actually looks
at in meetings: where the money is, how spending tracks against budget *honestly*
mid-year (which is why budgets-005 built a proration engine — comparing
actual-to-date against a full annual budget makes every front-loaded line look
over budget), and how the reserve fund stands. The as-of date matters because the
board reviews finances "as of" a specific meeting date, not only "today."

## Success
- A logged-in user (admin or view-only) selects an as-of date and sees, for that
  date and its year: account balances as of the date, beginning-of-year balances,
  total cash, income & expense summaries by category, reserve-fund status, and a
  monthly income-vs-expense chart.
- Income and expense summaries compare **actual-to-date** against **prorated
  budget-to-date** (from the budgets-005 proration engine, stepped by each line's
  timing pattern) and show remaining — not full annual budget vs. YTD actual.
- **Transfers are excluded** from all income/expense totals; they affect account
  balances only. Inter-account movement never counts as income or expense.
- All monetary math is in **integer cents** end to end; the displayed totals foot
  exactly (income − expense, budget − actual, reserve net) and are verified
  against hand-worked examples.
- The income side reflects **entered/migrated income-category budgets directly** —
  it does not derive income budget from the operating-budget total, nor compute
  the dues-99.9% / interest-0.1% split. That derivation is Dues (007)'s concern.
- View-only and admin sessions can both read the dashboard; role is enforced
  server-side. The dashboard is read-only (no writes).

## Shape touched
- **Dashboard & reporting UI** — the dashboard page: as-of date control, balance
  cards, income/expense summary tables with prorated budget + remaining,
  reserve-fund block, monthly income/expense chart.
- **Budget, dues & units model** — dashboard aggregation logic (balances,
  transfers-excluded actuals, budget-vs-actual using the existing proration
  engine, reserve-fund status, monthly cashflow) as plain, testable modules in
  integer cents.
- **API layer** — a read endpoint returning the dashboard payload for an as-of
  date.

## Out of scope
- **PDF / print export.** Cut entirely (deliberate deviation from the
  constitution's "the dashboard is the report → print-clean + matching PDF" gate;
  recorded as a decision). The dashboard is a clean on-screen view only.
- **Per-unit dues table.** The legacy dashboard embedded per-unit dues status;
  that is Dues by unit (Roadmap 7). This slice is association-level only.
- **Calculated-dues / interest derivation.** Deriving income budget from the
  operating budget (dues 99.9% + interest 0.1%) belongs to Dues (007); the
  dashboard shows income-category budgets as entered, independently.
- **Richer cashflow / multi-year trend views.** Only the one simple monthly
  income-vs-expense bar for the selected year. No reserve-trend, no
  year-over-year, no multi-year analytics (also a project-level out-of-scope).
- **Category / budget editing.** The dashboard is read-only; budget edits live in
  Budgets (005), category management is its own feature.
- **Schema changes.** All tables (transactions, categories, budgets,
  budget_locks, accounts, units) already exist from foundation + earlier slices.
  This feature adds read aggregation and UI, not tables.
