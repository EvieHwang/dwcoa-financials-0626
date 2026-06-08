# Spec — Dues by unit (007)

Status: drafted for `/build`. Tests in `tests/` are the acceptance bar.

This feature derives each unit's dues obligation from the operating budget and
its ownership share, tracks payments recorded against that unit, carries last
year's balance forward, and presents per-unit outstanding balances. It adds a
*read aggregation* module, one *read endpoint*, and a *dues table embedded in the
dashboard view* — no schema change, no writes. It reuses foundation's auth guards
and the dashboard router's `as_of` validation pattern. It does **not** reuse the
proration engine: dues expected is the **full annual** amount, never prorated.

---

## Part 1 — Behavioral requirements

### Vocabulary & grounded facts (from the built code, not the legacy app)
- **Units.** `units(number TEXT, ownership_pct INTEGER)` where `ownership_pct` is
  exact **per-mille** (0.117 → `117`), `CHECK (>0 AND <=1000)` (`migrations.py`).
  The nine seeded units sum to **999‰** (117+104+112 per floor × 3), i.e. 99.9% —
  the missing 0.1% is the interest line, which this feature does **not** touch.
- **Baseline.** `unit_past_dues(unit_number, year, past_due_balance)` —
  `past_due_balance` is exact **integer cents**, `UNIQUE(unit_number, year)`
  (`migrations.py`). It is **not seeded** (`seed.py` writes no rows); it is
  populated only by the legacy migration (the 1/1/2025 baseline) and by tests
  directly. There is no in-app write path to it.
- **Operating budget.** The total annual operating budget for a year =
  `SUM(budgets.annual_amount)` over the year's budget rows joined to **`Expense`**
  categories that are **`active = 1`** (`categories.active`, default 1). This
  mirrors legacy `get_total_operating_budget` and is in integer cents.
- **Dues categories.** Each unit's payments are recorded as transactions
  categorized to the **income** category named exactly `Dues <number>` (e.g.
  `Dues 101`), seeded for all nine units (`seed.py`). A dues *payment* is a
  `credit` (income convention; matches the dashboard).
- **Money is integer cents end to end** (constitution: "Money"); ownership is
  integer per-mille. No floats in any returned amount.
- **`BASE_YEAR = 2025`** is the first year dues are computed. Pre-2025 dues are
  not computed (decision: pre-2025 history is reference-only, unreliable).

### Core definitions (the dues math)
For a requested **year `Y`** and **as-of date `D`** (with `Y = D.year`), for each
unit `u` with ownership `p` per-mille:

- **`operating_budget(Y)`** — integer cents, as defined above (0 if no budgets).
- **`annual_dues(u, Y)`** = `(operating_budget(Y) * p + 500) // 1000` — `u`'s
  ownership share of the operating budget, **full annual**, rounded to the
  nearest cent by integer arithmetic (round-half-up; no float). Computed
  independently per unit; the nine shares are **not** reconciled to sum exactly
  to `operating_budget(Y)` (a cent or two of drift is accepted — decision).
- **`paid(u, Y, D)`** = `SUM(credit)` over transactions whose category is
  `Dues <u.number>`, with `post_date` in calendar year `Y` and `post_date ≤ D`.
  Integer cents; 0 when none. Only the unit's own `Dues` category counts.
- **`carry_in(u, Y)`** — the balance carried into year `Y`:
  - `Y ≤ BASE_YEAR`: `past_due_balance(u, Y)` (0 if no row). This is the
    1/1/2025 baseline.
  - `Y > BASE_YEAR`: starting from 0, for each year `y` in `[BASE_YEAR, Y)`:
    `balance += past_due_balance(u, y) + annual_dues(u, y) − paid_full_year(u, y)`,
    where `paid_full_year(u, y)` is `paid(u, y, Dec-31 of y)` (prior years are
    complete, so payments are counted for the **whole** year, not capped at `D`).
    Can be **negative** (a credit) when a unit overpays.
- **`expected_total(u, Y)`** = `carry_in(u, Y) + annual_dues(u, Y)`.
- **`outstanding(u, Y, D)`** = `expected_total(u, Y) − paid(u, Y, D)`. Negative
  means a credit balance.

All six are integer cents. Only the **requested** year's `paid` is capped at `D`;
the carryover loop over prior years uses each prior year's full-year payments.

### User stories & acceptance criteria

**US1 — Board/treasurer reads per-unit dues as of a date.**
As an authenticated user (admin or view-only), I open the dues table, and for the
as-of date's year I see every unit's dues status.
- AC1.1 `GET /api/dues?as_of=YYYY-MM-DD` returns, for either role:
  `as_of_date`, `year` (= the as-of date's calendar year), `dues_tracked` (bool),
  `operating_budget` (cents), `units` (list, one per unit), and `totals`.
- AC1.2 An unauthenticated request is rejected `401`.
- AC1.3 `as_of` is optional; absent → **today**. Present but not a valid
  `YYYY-MM-DD` date → `400` (the project's manual edge-validation convention,
  matching `routers/dashboard.py`; not Pydantic 422, not a silent fallback).
- AC1.4 The endpoint is read-only: a `GET` writes nothing. Both roles may read;
  no CSRF guard (no state change).

**US2 — Each unit's expected dues is its ownership share of the operating budget.**
As the treasurer, I want each unit billed its ownership percentage of the
operating budget, in full for the year.
- AC2.1 Each `units[]` entry has: `unit` (the number string), `ownership_per_mille`
  (int), `carryover` (cents), `annual_dues` (cents), `expected_total` (cents),
  `paid` (cents), `outstanding` (cents).
- AC2.2 `annual_dues` = `(operating_budget * ownership_per_mille + 500) // 1000`
  (full annual; **not** prorated to the as-of date). Two units with different
  ownership get proportionally different annual dues from the same operating
  budget.
- AC2.3 `operating_budget` = sum of the year's **active Expense**-category
  budgets only. Income-category budgets and inactive/non-Expense categories never
  contribute. (No interest derivation, no income-budget coupling.)
- AC2.4 With no budgets for the year, `operating_budget` and every
  `annual_dues` are `0`; the endpoint still returns all nine units.

**US3 — Payments counted from the unit's dues category, through the as-of date.**
As the treasurer, I want a unit's recorded dues payments reflected, but only up to
the as-of date.
- AC3.1 `paid` = sum of `credit` on transactions categorized `Dues <unit>` within
  the year with `post_date ≤ as_of`. A payment dated after the as-of date is
  excluded; one in a different year is excluded.
- AC3.2 A credit on a **non-dues** income category (e.g. `Interest`) or on
  another unit's `Dues` category never counts toward this unit's `paid`.
- AC3.3 `outstanding` = `expected_total − paid`; it is negative when a unit has
  paid more than expected (a credit), and the response represents that faithfully
  (no clamping to zero).

**US4 — Carryover accumulates forward from the 2025 baseline.**
As the treasurer, I want last year's unpaid balance (or credit) to roll into this
year.
- AC4.1 For `year = 2025`, `carryover` = the unit's `unit_past_dues` row for 2025
  (`0` if none).
- AC4.2 For `year > 2025`, `carryover` = the accumulation defined above:
  baseline + each prior year's (`annual_dues − full-year paid`), so a prior-year
  shortfall increases this year's `expected_total` and a prior-year overpayment
  reduces it (can go negative).
- AC4.3 The carryover loop uses each prior year's **full-year** payments (capped
  at that year's Dec 31), independent of the requested as-of date.

**US5 — Pre-2025 reports not-tracked, never an error.**
As a board member who picks an early as-of date on the dashboard, I want the dues
table to degrade gracefully.
- AC5.1 For `year < 2025`, the response has `dues_tracked = false`,
  `operating_budget = 0`, `units = []`, and zeroed `totals`. It is **`200`**, not
  an error (so the embedded dashboard view doesn't break on an early date).
- AC5.2 For `year ≥ 2025`, `dues_tracked = true`.

**US6 — Association totals foot to the rows shown.**
As the treasurer, I want the column totals to equal the sum of the unit rows.
- AC6.1 `totals` has `carryover`, `annual_dues`, `expected_total`, `paid`,
  `outstanding`, each the exact integer-cent sum of the corresponding field over
  `units[]`.
- AC6.2 `totals.outstanding == totals.expected_total − totals.paid` and
  `totals.expected_total == totals.carryover + totals.annual_dues` (the row
  identities hold in aggregate).

**US7 — The dues table in the dashboard (frontend).**
As any logged-in user, I see a per-unit dues table within the dashboard, sharing
its as-of-date control, money formatted as USD, read-only for both roles.
- AC7.1 The dues table fetches `GET /api/dues?as_of=<date>` (the dashboard's
  current as-of date) and renders one row per unit with its ownership, carryover,
  annual dues, expected, paid, and outstanding as USD.
- AC7.2 Changing the dashboard's as-of-date control refetches `GET /api/dues`
  with the new `as_of`.
- AC7.3 Both `admin` and `viewer` see the table identically; it exposes no
  write/admin control.
- AC7.4 When `dues_tracked` is false, the table renders a clear "dues tracking
  begins 2025"-style note instead of unit rows (no crash, no empty silence).

### Edge cases & failure modes
- **Malformed `as_of`** → `400` (AC1.3). Missing → today.
- **`year < 2025`** → `dues_tracked=false`, empty units, zero totals, `200`
  (AC5.1) — not an error.
- **No budgets for the year** → operating budget `0`, all annual dues `0`; units
  still listed; outstanding driven by carryover and payments only (AC2.4).
- **Unit with no matching `Dues` category** (should not happen for the nine
  seeded units) → that unit's `paid` is `0`; the unit is still listed (the list
  drives off the `units` table, not off category presence).
- **Overpayment / credit** → `carryover` and/or `outstanding` negative, returned
  as-is, never clamped (AC3.3, AC4.2).
- **No `unit_past_dues` rows at all** (a freshly seeded dev DB) → every
  `carryover` for 2025 is `0`; the engine still returns all units (AC4.1).
- **`as_of` SQL safety** → the date is validated then passed only as a bound
  parameter; never string-interpolated into SQL.
- **Empty `units` table** (degenerate) → `units=[]`, zero totals; no error.

### Out of scope (this slice)
Per the feature declaration: My Account / per-unit homeowner statement &
self-select (008); income-budget or interest (0.1%) derivation; pre-2025 dues
computation; editing `unit_past_dues`; recording/collecting payments; PDF/print;
schema changes. Also out: a units/ownership management UI (units are seeded/
migrated), and any prorating of expected dues to the as-of date (expected is full
annual by design).

---

## Part 2 — Design

### Components & seams

**`app/dues.py` — dues aggregation logic (new, plain testable module).**
Business logic lives here, not in the route handler (constitution). Functions take
an open `sqlite3.Connection` and integer/`date` args and return integer-cent
Python structures — no floats. The function names below are `@scaffolding`
surface — `/build` may rename/refine them (logging it in `build-deviations.md`) as
long as the behaviors hold. Suggested seams:
- `operating_budget(con, year) -> int` — AC2.3 (sum of active-Expense budgets).
- `annual_dues(operating_budget_cents, ownership_per_mille) -> int` — AC2.2 (the
  rounding rule, pure/integer; reusable by 008).
- `unit_paid(con, unit_number, year, as_of) -> int` — AC3.1/3.2.
- `carry_in(con, unit, year) -> int` — AC4.* (the multi-year accumulation;
  reusable by 008).
- `build_dues(con, as_of) -> dict` — assembles the full payload (AC1.1, AC5.*,
  AC6.*).

Behavioral properties this module must hold:
- **Full-annual expected, never prorated.** `annual_dues` does not depend on the
  as-of date; only `paid` (for the requested year) is capped at it. This is the
  deliberate divergence from the dashboard's budget math — the proration engine
  is **not** used here.
- **Hard separation from income/interest.** The operating-budget basis is the
  Expense side only; nothing in this module reads, derives, or writes the income
  budget or an interest split.
- **Integer cents throughout**; every returned amount is a Python `int`. Totals
  are exact integer sums of the rows (AC6.1).
- **Carryover uses full-year prior payments** (AC4.3), the requested year's
  payments capped at `as_of`.

**`app/routers/dues.py` — HTTP surface (new).**
- `GET /api/dues` guarded by `require_auth` (reuses `app.dependencies.require_auth`;
  role read server-side only — both roles pass).
- Parses `as_of` from the query: absent → `date.today()`; present and invalid →
  `400`, using the same explicit-validation style as `routers/dashboard.py`
  (a strict `^\d{4}-\d{2}-\d{2}$` check then `date.fromisoformat`, raising
  `HTTPException(400)`), not Pydantic 422.
- Opens a connection via `get_connection(config.database_path)`, calls
  `build_dues`, returns the payload, closes the connection in `finally`.
  Read-only — no transaction, no `is_cross_origin` guard.
- Registered in `app/main.py` after the other API routers and before the SPA
  fallback.

**Frontend — a dues table embedded in the dashboard (`frontend/src/App.tsx`).**
- Inside the existing `Dashboard` component (the `region` labelled "Financial
  dashboard"), a per-unit dues section that fetches
  `GET /api/dues?as_of=<asOf>` with `credentials: "include"` using the
  dashboard's existing `asOf` state, so the existing "As of" date control drives
  both the dashboard payload and the dues table (one shared control).
- Renders one row per unit: unit number, ownership (per-mille shown as a
  percentage), carryover, annual dues, expected, paid, outstanding — money via the
  existing `centsToUsd` helper.
- When `dues_tracked` is false, renders a short note instead of rows.
- Identical for both roles; no write control in this view.

### The API contract (frozen shape)
`GET /api/dues?as_of=YYYY-MM-DD` → `200`:
```json
{
  "as_of_date": "2026-06-30",
  "year": 2026,
  "dues_tracked": true,
  "operating_budget": 12345600,
  "units": [
    {
      "unit": "101",
      "ownership_per_mille": 117,
      "carryover": 0,
      "annual_dues": 1444435,
      "expected_total": 1444435,
      "paid": 700000,
      "outstanding": 744435
    }
  ],
  "totals": {
    "carryover": 0,
    "annual_dues": 1444435,
    "expected_total": 1444435,
    "paid": 700000,
    "outstanding": 744435
  }
}
```
All amounts integer cents; `ownership_per_mille` integer per-mille. The endpoint
path, the top-level keys, the `units[]` entry keys, and the `totals` keys above
are the **`@frozen`** contract the frontend and tests bind to. Unit ordering is
not a contract (tests look up units by number, not position), but listing all
units when tracked is. The specific `annual_dues` value shown is *illustrative*
under the round-half-up rule above; because rounding is an accepted non-priority
(an owner decision), tests pin exact shares only for budgets that divide evenly,
and otherwise assert the share is within one cent — `/build` may use any
reasonable integer-cent rounding.

### Standards
- **Security (OWASP).** New surface is one authenticated read. Authz reuses
  foundation's `require_auth` (role server-side only); no write path, no CSRF
  surface. `as_of` is validated and parameterized (no SQL injection). The data
  exposed (per-unit dues balances) is the association-internal financial picture
  any authenticated user already sees on the dashboard; no new PII or secret is
  surfaced, and unit selection is not an authorization boundary (declaration).
- **Accessibility (WCAG 2.1 AA).** The dues table uses header cells (`<th
  scope="col">`) and shares the dashboard's already-labelled date control; the
  "not tracked" state is conveyed as text, not by an empty table alone.
- **API (OpenAPI).** One documented `GET` returning the shape above.

---

## Part 3 — Coverage

| Requirement / seam | Test(s) |
|---|---|
| AC1.1 payload keys, `year` = as-of year | `test_dues_api.py::test_payload_has_all_keys`, `::test_year_follows_as_of` |
| AC1.2 401 unauthenticated | `test_dues_api.py::test_requires_auth` |
| AC1.3 default-today / 400 malformed | `test_dues_api.py::test_omitted_as_of_defaults_today`, `::test_malformed_as_of_400` |
| AC1.4 both roles read; read-only (no write) | `test_dues_api.py::test_both_roles_can_read`, `::test_read_only_writes_nothing` |
| AC2.1 unit entry shape (keys, int types) | `test_dues_api.py::test_unit_entry_shape` |
| AC2.2 annual dues = ownership share, full annual, not prorated | `test_dues_engine.py::test_annual_dues_is_ownership_share`, `::test_annual_dues_not_prorated`, `::test_proportional_to_ownership` |
| AC2.3 operating budget = active Expense budgets only | `test_dues_engine.py::test_operating_budget_expense_only`, `::test_income_budget_does_not_affect_dues` |
| AC2.4 no budgets → zeros, units still listed | `test_dues_engine.py::test_no_budget_year_zero_dues` |
| AC3.1 paid through as-of, within year | `test_dues_engine.py::test_paid_capped_at_as_of`, `::test_paid_only_current_year` |
| AC3.2 only the unit's own Dues category counts | `test_dues_engine.py::test_paid_ignores_other_categories` |
| AC3.3 outstanding can be negative (credit), unclamped | `test_dues_engine.py::test_overpayment_is_credit` |
| AC4.1 2025 carryover = baseline row | `test_dues_engine.py::test_2025_carryover_is_baseline` |
| AC4.2/4.3 multi-year accumulation; full-year prior payments | `test_dues_engine.py::test_carryover_accumulates_forward`, `::test_carryover_three_years`, `::test_carryover_uses_full_prior_year_payments` |
| AC5.1/5.2 pre-2025 not tracked, 200; 2025+ tracked | `test_dues_api.py::test_pre_2025_not_tracked`, `::test_2025_is_tracked` |
| AC6.1/6.2 totals are exact sums; aggregate identities | `test_dues_engine.py::test_totals_are_sums`, `test_dues_api.py::test_totals_identities` |
| AC7.1 renders unit rows from endpoint as USD | `DuesByUnit.test.tsx::renders_dues_rows_from_endpoint` |
| AC7.2 as-of change refetches /api/dues | `DuesByUnit.test.tsx::as_of_change_refetches_dues` |
| AC7.3 both roles; no write control | `DuesByUnit.test.tsx::viewer_sees_same_readonly_dues` |
| AC7.4 not-tracked note when dues_tracked false | `DuesByUnit.test.tsx::shows_not_tracked_note` |

### Build-step note for `/build`
Beyond writing the module, router, and frontend changes, the new router must be
**registered in `app/main.py`** — added to the `from .routers import (...)` block
and to the `app.include_router(...)` sequence (after `dashboard.router`, before
`register_spa`). Without it every `test_dues_api.py` case 404s, so the suite
catches the omission, but call it out explicitly.

### Test wiring note for `/build`
These suites are **not** registered with the runners by this spec PR (project
convention — a spec PR stays green because its still-failing pre-build tests are
on no runner's path). When building, append
`"../features/dues-by-unit-007/tests/backend"` to `backend/pyproject.toml`
`[tool.pytest.ini_options].testpaths`, and add
`"../features/dues-by-unit-007/tests/frontend/**/*.test.{ts,tsx}"` to
`frontend/vite.config.ts` `test.include`. Backend test basenames
(`test_dues_engine.py`, `test_dues_api.py`) are unique across features; the
frontend file is `DuesByUnit.test.tsx`. Frontend tests import the app via the
`@/` alias and the external-dep aliases already configured in `vite.config.ts`.

---

## Adversarial gate
Mode: independent clean-context sub-agent (Stage 4), run once against the drafted
spec and tests. It also read the built code the feature depends on
(`migrations.py`, `seed.py`, `dashboard.py`, `routers/dashboard.py`,
`dependencies.py`, `main.py`, `App.tsx`) and the dashboard-006 spec to check the
spec against the real system.

**Confirmed sound** (no finding): the carryover math is hand-verified correct and
the seeded 2025 budgets are properly cleared in the multi-year examples; the
prior-year-full vs requested-year-capped distinction is genuinely tested; the
`dues_tracked=false` pre-2025 gate is verified to return `200`; the
income/interest separation is enforced and *negatively* tested
(`test_income_budget_does_not_affect_dues`); auth reuse is correctly scoped and
dropping CSRF for a GET is justified; `as_of` is regex-gated then parameterized
(no injection reachable); `@frozen`/`@scaffolding` tags are applied honestly. No
scope drift (My Account 008 and the income/interest derivation are walled off),
no document contradictions, no security regression.

**Findings & disposition** (all in spec/tests; none security → no re-gate needed):

| # | Sev | Finding | Disposition |
|---|-----|---------|-------------|
| 1 | MEDIUM | The wiring note listed only `pyproject.toml`/`vite.config.ts` edits and omitted registering the new router in `main.py` (caught by tests via 404s, but an easy omission for the build planner). | **Fixed.** Added an explicit "Build-step note for `/build`" calling out the `main.py` import + `include_router` registration. |
| 2 | MEDIUM | No test exercised a ≥3-year carryover, where the loop iterates two prior years; a loop off-by-one or per-iteration baseline double-count would pass the single-iteration (2026) examples — on the constitution's highest-value surface. | **Fixed.** Added `test_carryover_three_years` (Y=2027, baseline + 2025 + 2026 dues/payments, hand-verified `carryover=2,210,000`). |
| 3 | LOW | The rounding-tolerance test accepts floor or floor+1, so the exact round-half-up formula (and the contract example's `annual_dues`) is pinned nowhere. | **Proceed (sound by prior owner decision).** Rounding is an explicit non-priority; exact shares are pinned only for evenly-dividing budgets. Clarified the contract block to mark the `annual_dues` value illustrative. |
| 4 | LOW | (Self-withdrawn by the gate) the frozen API-contract example looked inconsistent. | **No action** — on recheck the gate confirmed the numbers foot. |
| 5 | LOW | (Self-withdrawn by the gate) `as_of` SQL-injection residual. | **No action** — the regex gate makes injection unreachable; parameterization documented. |
