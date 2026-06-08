# Build deviations — Dashboard & reporting (006)

The build satisfied every `@frozen` contract and behavioral requirement as
written. The only divergences are refinements of `@scaffolding` interface
surfaces, which the spec (Part 2 § Components & seams) explicitly licenses
"`/build` may rename/refine … as long as the behaviors hold."

## 1. Aggregation function shape (`@scaffolding`)
- **Spec named:** `income_expense_summary(con, year, as_of) -> dict` (one function
  producing both summaries).
- **Built:** `category_summary(con, type_, year, as_of) -> dict`, called once per
  type (`Income`, `Expense`). A single parameterized function removes the
  income/expense duplication and makes the income-independence property (income
  budget summed only from income categories) structural rather than conventional.
- **Also added:** `build_dashboard(con, as_of) -> dict`, a thin assembler that the
  router calls, so the route handler holds no business logic (constitution:
  "business logic … not in route handlers"). Not a spec function; pure assembly.
- The other three scaffolding names (`account_balances`, `reserve_fund_status`,
  `monthly_cashflow`) were kept verbatim.
- **Why this is safe:** every behavior is exercised through `GET /api/dashboard`
  (the `@frozen` surface), never by importing these names, so the rename is
  invisible to the tests and to the frontend.

No `@frozen` test was modified. No behavioral assertion was weakened. No spec
requirement was contradicted, so there is nothing to kick back to `/spec`.
