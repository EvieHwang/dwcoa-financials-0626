# Spec — Dashboard & reporting (006)

Status: drafted for `/build`. Tests in `tests/` are the acceptance bar.

This feature joins the tables and engines built by earlier slices into one
read-only, association-level financial picture for a user-selected **as-of date**.
It adds *read aggregation* and *UI* — no schema change, no writes. It reuses the
budgets-005 proration engine verbatim (it does not reimplement timing math) and
foundation's auth guards.

---

## Part 1 — Behavioral requirements

### Vocabulary & grounded facts (from the built code)
These are facts the design depends on, taken from the current schema/seed, not
the stale legacy app:

- **Category types** are `Income`, `Expense`, `Transfer`, `Internal`
  (`migrations.py`). Income/expense aggregation includes **only `Income` and
  `Expense`** categories; `Transfer`/`Internal` are the "transfers" that are
  excluded from income/expense totals and the cashflow chart. In the current
  seed the only transfer-like category is `Transfers` (type `Internal`).
- **`Reserve Contribution` is type `Expense`** and **`Reserve Fund` is type
  `Expense`** (`seed.py`). So a reserve contribution *does* count in the expense
  summary — that matches how the operating budget treats it. The separate
  reserve-fund block (R5) reports reserve cash movement on top of that.
- **Accounts** are seeded as `Savings`, `Checking`, `Reserve Fund` (`seed.py`),
  and `transactions.account_name` carries the friendly name.
- **`transactions.balance`** is the bank-supplied running balance (integer
  cents). Account balance as of a date = the `balance` of that account's latest
  transaction on or before the date — *not* a recomputed sum (so transfers,
  which move money between accounts, are already reflected).
- **`transactions.debit` / `transactions.credit`** are integer cents, nullable.
  Income actual draws from `credit`; expense actual draws from `debit` (matches
  the legacy convention and the sign of the data).
- **Money is integer cents end to end** (constitution: "Money"). Every amount in
  this feature's API payload is an integer number of cents. No floats.
- **Proration** is `app.proration.prorated_ytd(annual_cents, timing, as_of,
  budget_year)` with `effective_timing(override, default)` (budgets-005, R7).
  The dashboard *consumes* these; it must not re-derive the stepping.

### User stories & acceptance criteria

**US1 — Board member reads the finances as of a date.**
As a board member (admin or view-only), I open the dashboard, pick an as-of date,
and see the association's financial picture for that date and its year.
- AC1.1 `GET /api/dashboard?as_of=YYYY-MM-DD` returns, for an authenticated
  session of **either** role: `as_of_date`, `year` (= the as-of date's calendar
  year), `accounts`, `total_cash`, `income_summary`, `expense_summary`,
  `reserve_fund`, and `monthly_cashflow`.
- AC1.2 An unauthenticated request is rejected `401`.
- AC1.3 `as_of` is optional; when omitted it defaults to **today**. When present
  but not a valid `YYYY-MM-DD` date, the request is rejected `400` (the project's
  manual edge-validation convention; not a silent fallback).
- AC1.4 The endpoint is read-only: a `GET` never writes. No CSRF guard is needed
  (no state change); both roles may read.

**US2 — Honest budget-vs-actual, prorated to the date.**
As the treasurer, I want each category's spend compared against what *should* have
been budgeted by this date, so a front-loaded annual line doesn't read as over
budget mid-year.
- AC2.1 `income_summary` and `expense_summary` each contain per-category lines and
  rolled-up totals. Each category line has: `category_id`, `name`,
  `annual_budget` (cents), `prorated_budget` (cents), `actual` (cents),
  `remaining` (cents).
- AC2.2 `prorated_budget` for a line = `prorated_ytd(annual_budget,
  effective_timing(line.timing, category.timing), as_of, year)`. The line's
  **effective timing** (per-line override beating the category default) drives the
  stepping — never the raw category default when an override exists.
- AC2.3 `remaining` = `prorated_budget − actual` (for expenses, money still
  expected to be spent by now; for income, expected-to-date not yet received).
- AC2.4 `actual` for an `Income` line = sum of `credit` over that category's
  transactions in `year` with `post_date ≤ as_of`. For an `Expense` line = sum of
  `debit`, same filter. Uncategorized transactions (`category_id IS NULL`) are
  excluded from all actuals.
- AC2.5 Summary totals (`annual_budget`, `prorated_budget`, `actual`,
  `remaining`) are the exact integer-cent sums of their category lines.

**US3 — Income budget shown independently (decision #4).**
As the owner, I want the dashboard's income budget to reflect the entered income
budgets directly, with no built-in dependency on the dues/interest derivation.
- AC3.1 `income_summary.annual_budget` = the exact sum of the **entered/migrated
  income-category budget rows** for the year. The dashboard does **not** derive
  income from the total operating (expense) budget, and does **not** compute the
  "dues 99.9% / interest 0.1%" split. (That derivation is Dues-007's concern.)
- AC3.2 Concretely: with income budgets summing to X and expense budgets summing
  to a different Y, `income_summary.annual_budget == X` (and `!= Y`).

**US4 — Account balances with year context.**
As a board member, I want each account's balance as of the date and where it
started the year, plus total cash.
- AC4.1 `accounts` lists every seeded account (`Savings`, `Checking`,
  `Reserve Fund`) with `name`, `balance` (cents), and `beginning_balance` (cents).
- AC4.2 `balance` = the `balance` of that account's latest transaction with
  `post_date ≤ as_of`; an account with no such transaction reports `0`.
- AC4.3 `beginning_balance` = the same rule evaluated at `Dec 31` of the prior
  year (the account's balance entering `year`); `0` when none.
- AC4.4 `total_cash` = the exact integer-cent sum of the accounts' `balance`.

**US5 — Reserve fund status.**
As a board member, I want to see reserve-fund activity for the year against its
contribution budget.
- AC5.1 `reserve_fund` has: `budget` (cents), `contributions` (cents),
  `expenses` (cents), `net` (cents), `beginning_balance` (cents).
- AC5.2 `contributions` = sum of `credit` on transactions in the `Reserve Fund`
  account for `year` with `post_date ≤ as_of`. `expenses` = sum of `debit` on the
  `Reserve Fund` account, same filter. `net = contributions − expenses`.
- AC5.3 `budget` = the prorated-to-date `Reserve Contribution` budget
  (`prorated_ytd` with that category's effective timing), or `0` if unbudgeted.
- AC5.4 `beginning_balance` = the `Reserve Fund` account balance at `Dec 31` of
  the prior year (per AC4.3).

**US6 — One simple monthly cashflow chart.**
As a board member, I want a simple month-by-month income-vs-expense view for the
year.
- AC6.1 `monthly_cashflow` is a list of `{month, income, expenses}` (cents),
  ordered by month, one entry per month from January through the as-of month.
  (`year` always equals the as-of date's year per AC1.1, so the as-of date is
  always within `year`; viewing a full past year means picking its Dec 31, which
  yields all twelve months.) Months with no activity report `0`/`0`, never gaps.
- AC6.2 `income` = sum of `credit` over `Income` categories that month; `expenses`
  = sum of `debit` over `Expense` categories that month. **Transfers excluded**
  (`Transfer`/`Internal` never contribute); uncategorized excluded.

**US7 — The dashboard view (frontend).**
As any logged-in user, I see the dashboard rendered from the endpoint, with money
formatted as USD, an as-of date control, and the budget/actual/remaining,
balances, reserve, and chart sections — read-only, for both roles.
- AC7.1 The dashboard fetches `GET /api/dashboard` (with the chosen `as_of`) and
  renders account balances and total cash as USD.
- AC7.2 It renders income & expense summary rows showing each category's budget,
  prorated budget, actual, and remaining (USD).
- AC7.3 Changing the as-of date control refetches `GET /api/dashboard` with the
  new `as_of`.
- AC7.4 The reserve-fund block and the monthly chart render from the payload.
- AC7.5 Both `admin` and `viewer` see the dashboard identically — it exposes no
  admin-only control and issues no writes. (Transfer/Internal categories never
  appear as income/expense rows because the API excludes them.)

### Edge cases & failure modes
- **Malformed `as_of`** → `400` (AC1.3). Missing `as_of` → today (not an error).
- **Year with no budgets** → every `annual_budget`/`prorated_budget` is `0`;
  actuals still computed and shown. No divide-by-zero anywhere (no ratios are
  computed server-side).
- **No transactions at all** → all balances and `total_cash` `0`; all actuals
  `0`; `monthly_cashflow` still lists months 1…as-of-month with zeros.
- **Account with no transactions on/before the date** → `balance` and
  `beginning_balance` `0`, but the account is still listed (AC4.1 drives off the
  `accounts` table, not off transaction presence).
- **Uncategorized backlog** (`category_id IS NULL`, common right after a
  migration) → excluded from income/expense actuals and cashflow, but still
  reflected in account balances via the `balance` column. This can make actuals
  understate until the review queue is worked — correct, not a bug.
- **Future as-of year** → prorating returns the full annual for that year's
  budgets (typically none); balances use the latest transaction on/before the
  date. No error.
- **`as_of` SQL safety** → the date is validated then passed only as a bound
  parameter; never string-interpolated into SQL.

### Out of scope (this slice)
Per the feature declaration: PDF/print export (cut entirely — recorded
deviation); per-unit dues table (Dues-007); operating-budget→income/interest
derivation (Dues-007); richer cashflow/reserve-trend/multi-year views; any
editing; schema changes. Also out: a "needs review" badge and "last updated"
stamp (kept off this slice to hold the surface tight; they belong to the
rules/ingestion surfaces).

---

## Part 2 — Design

### Components & seams

**`app/dashboard.py` — aggregation logic (new, plain testable module).**
Business logic lives here, not in the route handler (constitution). Functions take
an open `sqlite3.Connection` and an `as_of: date`, return integer-cent Python
structures. Names below are the `@scaffolding` surface — `/build` may rename/refine
them (logging it in `build-deviations.md`) as long as the behaviors hold:
- `account_balances(con, as_of) -> list[dict]` — AC4.1–4.4 (drives off the
  `accounts` table; latest-balance-on-or-before per account; beginning-of-year).
- `income_expense_summary(con, year, as_of) -> dict` — AC2.*, AC3.* (per-category
  prorated budget vs. actual, totals; income budget summed independently).
- `reserve_fund_status(con, year, as_of) -> dict` — AC5.*.
- `monthly_cashflow(con, year, as_of) -> list[dict]` — AC6.*.

Behavioral properties this module must hold:
- **Reuses pattern: proration engine (budgets-005).** It calls
  `app.proration.prorated_ytd` / `effective_timing`; it must not re-implement the
  stepping. Seam property: a line whose category default is `monthly` but whose
  per-line override is `annual` prorates *full-from-January*, not `m/12`.
- **Transfers excluded** from every income/expense/cashflow figure; only
  `Income`/`Expense` typed, categorized rows contribute.
- **Integer cents throughout**; every returned amount is a Python `int`. Sums are
  exact (no float accumulation).

**`app/routers/dashboard.py` — HTTP surface (new).**
- `GET /api/dashboard` guarded by `require_auth` (reuses
  `app.dependencies.require_auth`; role read server-side only — both roles pass).
- Parses `as_of` from the query: absent → `date.today()`; present and invalid →
  `400` via the same explicit-validation style as `routers/budgets.py`
  (`HTTPException(400)`), not Pydantic's `422`.
- Opens a connection via `get_connection(config.database_path)`, calls the four
  aggregation functions, assembles and returns the payload, closes the connection
  in `finally`. Read-only — no transaction, no `is_cross_origin` guard.
- Registered in `app/main.py` after the other API routers and before the SPA
  fallback.

**Frontend — a Dashboard view in `frontend/src` (extends the existing SPA).**
- Fetches `GET /api/dashboard?as_of=<date>` with `credentials: "include"`, renders
  balances/total cash, income & expense summary tables (budget / prorated /
  actual / remaining), the reserve block, and a simple monthly income-vs-expense
  bar chart. Money formatted with the existing `centsToUsd` helper.
- An as-of date `<input type="date">` (default today) drives a refetch on change.
- Identical for both roles; no admin-only control in this view.

### The API contract (frozen shape)
`GET /api/dashboard?as_of=YYYY-MM-DD` → `200`:
```json
{
  "as_of_date": "2030-06-30",
  "year": 2030,
  "accounts": [
    {"name": "Checking", "balance": 1234567, "beginning_balance": 1000000}
  ],
  "total_cash": 1234567,
  "income_summary": {
    "annual_budget": 0, "prorated_budget": 0, "actual": 0, "remaining": 0,
    "categories": [
      {"category_id": 1, "name": "Dues 101", "annual_budget": 0,
       "prorated_budget": 0, "actual": 0, "remaining": 0}
    ]
  },
  "expense_summary": { "annual_budget": 0, "prorated_budget": 0, "actual": 0,
                       "remaining": 0, "categories": [] },
  "reserve_fund": {"budget": 0, "contributions": 0, "expenses": 0, "net": 0,
                   "beginning_balance": 0},
  "monthly_cashflow": [{"month": 1, "income": 0, "expenses": 0}]
}
```
All amounts integer cents. The endpoint path, the top-level keys, and the
nested keys above are the **`@frozen`** contract the frontend and tests bind to.
Which categories appear as lines (an active Income/Expense category, or any
category with a budget row, or any category with actual activity in the year;
zero-budget-and-zero-actual lines suppressed) is a behavioral detail tests pin by
totals and presence, not an ordering contract.

### Standards
- **Security (OWASP).** New surface is one authenticated read. Authz reuses
  foundation's `require_auth` (role server-side only); no new write path, no CSRF
  surface. `as_of` is validated and parameterized (no injection). No secret or PII
  is exposed beyond the aggregate finances any authenticated user already sees.
- **Accessibility (WCAG 2.1 AA).** The view is tables + labeled controls + a
  chart; the date control has a label, summary tables use header cells, and the
  chart is not the sole carrier of any datum (the same numbers appear in the
  summary/reserve sections). No full-report print styling is in scope (PDF cut).
- **API (OpenAPI).** One documented `GET` returning the shape above.

---

## Part 3 — Coverage

| Requirement / seam | Test(s) |
|---|---|
| AC1.1 payload keys, `year`=as-of year | `test_dashboard_api.py::test_payload_has_all_sections`, `::test_year_follows_as_of` |
| AC1.2 401 unauthenticated | `test_dashboard_api.py::test_requires_auth` |
| AC1.3 default-today / 400 malformed | `test_dashboard_api.py::test_omitted_as_of_defaults_today`, `::test_malformed_as_of_400` |
| AC1.4 both roles read; read-only (no write) | `test_dashboard_api.py::test_both_roles_can_read`, `::test_read_only_writes_nothing` |
| AC2.2 prorated uses effective timing (override) | `test_dashboard_summary.py::test_prorated_uses_effective_timing_override` |
| AC2.3 remaining = prorated − actual | `test_dashboard_summary.py::test_remaining_is_prorated_minus_actual` |
| AC2.4 income←credit / expense←debit; uncategorized excluded | `test_dashboard_summary.py::test_actuals_by_type`, `::test_uncategorized_excluded` |
| AC2.5 totals are exact sums | `test_dashboard_summary.py::test_totals_are_sum_of_lines` |
| AC2.1 line carries integer category_id | `test_dashboard_summary.py::test_line_includes_category_id` |
| AC3.1/3.2 income budget independent of operating budget | `test_dashboard_summary.py::test_income_budget_is_independent_sum` |
| Transfers excluded from income/expense | `test_dashboard_summary.py::test_transfers_excluded_from_totals` |
| AC4.2 balance = latest ≤ as_of | `test_dashboard_balances.py::test_balance_is_latest_on_or_before` |
| AC4.3 beginning balance = prior Dec 31 | `test_dashboard_balances.py::test_beginning_balance_prior_year_end` |
| AC4.1/4.4 all accounts listed; total cash | `test_dashboard_balances.py::test_all_accounts_listed_and_total`, `::test_account_without_txns_is_zero` |
| AC5.2/5.3/5.4 reserve in/out/net/budget/beginning | `test_dashboard_reserve.py::test_reserve_contributions_expenses_net`, `::test_reserve_budget_is_prorated` |
| AC6.1/6.2 monthly cashflow, transfers excluded, months filled, full-year via year-end | `test_dashboard_cashflow.py::test_monthly_income_expense`, `::test_cashflow_excludes_transfers`, `::test_months_filled_through_as_of`, `::test_full_year_via_year_end_as_of` |
| AC7.1/7.2 renders balances + summary as USD | `Dashboard.test.tsx::renders_balances_and_summary_from_endpoint` |
| AC7.3 date control refetches with as_of | `Dashboard.test.tsx::as_of_change_refetches` |
| AC7.4 reserve + chart render | `Dashboard.test.tsx::renders_reserve_and_chart` |
| AC7.5 both roles; no admin control; transfers absent | `Dashboard.test.tsx::viewer_sees_same_readonly_dashboard` |

### Test wiring note for `/build`
These suites are **not** registered with the runners by this spec PR (per the
project convention — a spec PR stays green because its still-failing pre-build
tests are on no runner's path). When building, append
`"../features/dashboard-006/tests/backend"` to `backend/pyproject.toml`
`[tool.pytest.ini_options].testpaths`, and add
`"../features/dashboard-006/tests/frontend/**/*.test.{ts,tsx}"` to
`frontend/vite.config.ts` `test.include`. Backend test basenames (`test_dashboard_*`)
are unique across features; the frontend file is `Dashboard.test.tsx`.

---

## Adversarial gate
Mode: independent clean-context sub-agent (Stage 4), run once against the drafted
spec and tests. It also read the built code the feature depends on (`proration.py`,
`migrations.py`, `seed.py`, the budgets/transactions routers, `dependencies.py`,
`auth.py`) to check the spec against the real system.

**Confirmed sound** (no finding): the `Reserve Contribution`/`Reserve Fund`
both-`Expense` "double count" is intentional and documented; income-independence
is correctly enforced and tested (no smuggled dues/interest derivation); the
proration signature matches the built engine; auth reuse is correctly scoped and
dropping CSRF for a GET is justified; seed facts (account names, category types,
timings) all match the code; `@frozen`/`@scaffolding` tags are honestly applied.
No scope drift, no integrity contradictions, no security regression. (The gate
raised then withdrew its own HIGH on the reserve beginning-balance after
confirming it is covered.)

**Findings & disposition** (all in the tests; none security → no re-gate needed):

| # | Sev | Finding | Disposition |
|---|-----|---------|-------------|
| 1 | MEDIUM | The `monthly_cashflow` "later-year → through December" branch (old AC6.1) was untested. | **Fixed — by correcting the spec.** Investigation showed the branch is *unreachable*: the endpoint always sets `year = as_of.year` (AC1.1), so `as_of` is always within `year`. Removed the contradictory clause from AC6.1 and added `test_full_year_via_year_end_as_of` (Dec-31 as-of → all twelve months), the real "view a full past year" path. |
| 2 | MEDIUM | No test asserted the GET is read-only — yet the spec leans on read-only-ness to justify omitting the CSRF guard. | **Fixed.** Added `test_read_only_writes_nothing` (table row counts unchanged across a GET, run as admin). |
| 3 | LOW | `category_id` is in the frozen line contract but no backend test asserted a line contains it. | **Fixed.** Added `test_line_includes_category_id`. |
