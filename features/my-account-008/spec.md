# Spec — My Account (008)

Status: drafted for `/build`. Tests in `tests/` are the acceptance bar.

The per-unit homeowner statement. It adds a *read aggregation* that **reuses the
007 dues engine** (`app/dues.py`), one *read endpoint* (`GET /api/account`), and a
*"My Account" section on the existing dashboard page* — no schema change, no
writes. It reuses foundation's `require_auth` and `get_connection`, and the
`as_of` validation pattern from `routers/dashboard.py` / `routers/dues.py`.

The whole point of this slice's math is to be **provably equal to the board's
view** for a single unit, plus a new *payment-guidance* layer. So the current-year
figures are not re-derived — they come from the same functions Dues by Unit (007)
uses — and the only new integer-cent math is payment guidance and the
recent-payments window.

---

## Part 1 — Behavioral requirements

### Vocabulary & grounded facts (from the built code, not the legacy app)
- **The dues engine already exists** (`app/dues.py`, slice 7), integer cents
  throughout, and was written to be reused here:
  - `operating_budget(con, year) -> int` — sum of the year's **active Expense**
    budgets.
  - `annual_dues(operating_budget_cents, ownership_per_mille) -> int` — a unit's
    **full-annual** ownership share, round-half-up, never prorated.
  - `unit_paid(con, unit_number, year, as_of) -> int` — sum of `credit` on
    transactions categorized `Dues <number>` with `post_date` in `year` and
    `post_date <= as_of`.
  - `carry_in(con, unit_number, ownership_per_mille, year) -> int` — the balance
    carried into `year` from the 1/1/2025 baseline (`unit_past_dues`),
    accumulating forward; can be negative (a credit).
  This feature **calls these**; it does not reimplement carryover, the
  operating-budget basis, or the income/interest separation.
- **`BASE_YEAR = 2025`** (from `app/dues.py`) is the first tracked year. A pre-2025
  as-of date is *not tracked* (mirrors `GET /api/dues`).
- **Units.** `units(number TEXT, ownership_pct INTEGER per-mille)`; the nine seeded
  units are `101 102 103 201 202 203 301 302 303` (`seed.py`). Ownership is integer
  per-mille (0.117 → 117).
- **Money is integer cents end to end** (constitution: "Money"); ownership is
  integer per-mille. No floats in any returned amount.
- **Auth.** `require_auth` (foundation) admits both roles; role is read
  server-side only and **never** from client input. Unit selection is a
  convenience, not an authorization boundary (declaration) — so any authenticated
  caller may read any unit.

### Core definitions (the new math)
For a requested **unit `u`** (ownership `p` per-mille) and **as-of date `D`** with
year `Y = D.year` and `Y >= BASE_YEAR`:

**Current year** (all reuse 007 and must equal the `GET /api/dues` row for `u`,`D`):
- `carryover` = `carry_in(con, u, p, Y)`.
- `annual_dues` = `annual_dues(operating_budget(con, Y), p)` (full annual).
- `total_due` = `carryover + annual_dues` (the dues row's `expected_total`).
- `paid_ytd` = `unit_paid(con, u, Y, D)` (the dues row's `paid`).
- `remaining_balance` = `total_due − paid_ytd` (the dues row's `outstanding`); may
  be negative (a credit).

**Prior year** (`Y − 1`):
- `data_available` = `(Y − 1) >= BASE_YEAR`.
- When available: `annual_dues_budgeted` = `annual_dues(operating_budget(con, Y−1), p)`;
  `total_paid` = `unit_paid(con, u, Y−1, Dec-31 of Y−1)` (the prior year is
  complete, so its full year counts). When not available, both are `null`.
- `balance_carried_forward` = `carryover` (the current year's carryover **is** the
  balance carried forward from prior years; the two are the same number, surfaced
  in both blocks). It is present even when `data_available` is false (it is then
  the 2025 baseline). Note: `annual_dues_budgeted` and `total_paid` are the prior
  year's *standalone* figures shown for context; they foot to
  `balance_carried_forward` only in the two-year case (`Y = 2026`) — the
  authoritative accumulation lives in `carry_in` (and is tested there), not in
  this display breakdown.

**Payment guidance** (the genuinely new integer-cent math):
- `standard_monthly` = round-half-up(`annual_dues / 12`), integer cents, always
  present (0 when `annual_dues` is 0).
- `months_remaining` = `(12 − D.month + 1)` if `D.day <= 15`, else `(12 − D.month)`.
  Worked: Jan 1 → 12, Jan 15 → 12, Jan 16 → 11, Mar 1 → 10, Mar 16 → 9,
  Dec 15 → 1, Dec 16 → 0. Driven by the as-of date.
- `status` and `suggested_monthly`, resolved in this order:
  1. `remaining_balance < 0` → `status = "credit"`, `suggested_monthly = null`.
  2. `remaining_balance == 0` → `status = "paid_in_full"`, `suggested_monthly = null`.
  3. `remaining_balance > 0` and `months_remaining == 0` →
     `status = "due_by_year_end"`, `suggested_monthly = null` (the whole remaining
     is due by Dec 31 — **never** a divide by zero).
  4. `remaining_balance > 0` and `months_remaining > 0` → `status = "owes"`,
     `suggested_monthly = round-half-up(remaining_balance / months_remaining)`.

**Recent payments**: the unit's own `Dues <u>` credits with `post_date` in the
calendar years `Y−1` or `Y` **and** `post_date <= D`, newest first by `post_date`
descending. The relative order of multiple payments on the **same** date is
unspecified (both must appear; their order is not a contract). Each entry is
`{ "date": "YYYY-MM-DD", "amount": <cents> }`. No other unit's or category's
credits; no count cap beyond the two-year window.

When `Y < BASE_YEAR` the statement is **not tracked**: `dues_tracked = false`,
`current_year = null`, `prior_year = null`, `payment_guidance = null`,
`recent_payments = []`, returned `200` (mirrors `GET /api/dues`).

### User stories & acceptance criteria

**US1 — A homeowner picks their unit and sees their statement.**
As an authenticated user, I select a unit and read its current-year statement.
- AC1.1 `GET /api/account?unit=<n>&as_of=YYYY-MM-DD` returns, for either role:
  `unit`, `ownership_per_mille`, `as_of_date`, `year` (= the as-of year),
  `dues_tracked`, `current_year`, `prior_year`, `payment_guidance`,
  `recent_payments`.
- AC1.2 An unauthenticated request is rejected `401`.
- AC1.3 `as_of` is optional; absent → **today**. Present but not a valid
  `YYYY-MM-DD` → `400` (the project's manual edge-validation convention, matching
  `routers/dues.py`; not Pydantic 422, not a silent fallback).
- AC1.4 `unit` is **required**; absent → `400`. A `unit` not among the seeded units
  → `400` (`"Unknown unit"`). The unit value is parameterized into SQL, never
  interpolated.
- AC1.5 The endpoint is read-only: a `GET` writes nothing. Both roles may read; no
  CSRF guard (no state change).

**US2 — The current-year figures equal the board's dues row (engine reuse).**
As a homeowner, I want my numbers to match what the board sees, so the statement
is trustworthy.
- AC2.1 `current_year` has integer-cent `carryover`, `annual_dues`, `total_due`,
  `paid_ytd`, `remaining_balance`, and `year` (= the as-of year).
- AC2.2 For the same unit and as-of date, `current_year.carryover`,
  `annual_dues`, `total_due`, `paid_ytd`, `remaining_balance` equal the unit's
  `GET /api/dues` row fields `carryover`, `annual_dues`, `expected_total`, `paid`,
  `outstanding` respectively. (Proves the 007 engine is reused, not re-derived.)
- AC2.3 `annual_dues` is the **full annual** amount: it does not change with the
  as-of date within a year (early vs. late as-of in the same year are equal), and
  `remaining_balance == total_due − paid_ytd` exactly.
- AC2.4 `remaining_balance` is negative (a credit) when the unit has overpaid;
  returned as-is, never clamped to zero.

**US3 — The prior-year wrap-up shows where the carryover came from.**
As a homeowner, I want last year's budgeted/paid and the balance that rolled in.
- AC3.1 For `Y >= 2026`, `prior_year` has `year` (= `Y−1`), `data_available = true`,
  integer-cent `annual_dues_budgeted` (= `annual_dues` of the prior year's
  operating budget) and `total_paid` (prior year's **full-year** dues payments),
  and `balance_carried_forward`.
- AC3.2 `prior_year.balance_carried_forward == current_year.carryover` (the same
  number in both blocks).
- AC3.3 For `Y == 2025`, `prior_year.year == 2024`, `data_available == false`,
  `annual_dues_budgeted == null`, `total_paid == null`, and
  `balance_carried_forward == current_year.carryover` (the 2025 baseline).

**US4 — Payment guidance turns the balance into a monthly target.**
As a homeowner, I want a concrete monthly amount to stay current, with sensible
handling at the year boundary and when I'm paid up.
- AC4.1 `payment_guidance.standard_monthly` = round-half-up(`annual_dues / 12`),
  integer cents (worked example pinned for a divisible annual dues).
- AC4.2 `payment_guidance.months_remaining` follows the 15th rule above
  (parametrized across Jan/Mar/Dec boundary dates).
- AC4.3 When the unit owes and months remain, `status == "owes"` and
  `suggested_monthly` = round-half-up(`remaining_balance / months_remaining`)
  (worked example pinned for a divisible case; a non-divisible case is asserted
  within one cent — rounding mode is not a priority, matching 007's `annual_dues`).
- AC4.4 `remaining_balance == 0` → `status == "paid_in_full"`,
  `suggested_monthly == null`. `remaining_balance < 0` → `status == "credit"`,
  `suggested_monthly == null`. `standard_monthly` is still present in both.
- AC4.5 `remaining_balance > 0` with `months_remaining == 0` (as-of after Dec 15)
  → `status == "due_by_year_end"`, `suggested_monthly == null`, HTTP `200` (no
  divide-by-zero, no error).

**US5 — Recent payments confirm checks landed.**
As a homeowner, I want to see my own recent dues payments.
- AC5.1 `recent_payments` lists the unit's `Dues <n>` credits in years `Y−1` and
  `Y` with `post_date <= as_of`, newest first by date; each entry has `date` and
  integer `amount`. Payments sharing a date both appear (their relative order is
  not a contract).
- AC5.2 A credit on another unit's `Dues` category, on a non-dues category (e.g.
  `Interest`), outside the two-year window, or after the as-of date is **excluded**.
- AC5.3 No payments in the window → `recent_payments == []` (not an error).

**US6 — Pre-2025 reports not-tracked, never an error.**
- AC6.1 For `Y < 2025`, `dues_tracked == false`, `current_year == null`,
  `prior_year == null`, `payment_guidance == null`, `recent_payments == []`,
  HTTP `200`.
- AC6.2 For `Y >= 2025`, `dues_tracked == true`.

**US7 — The "My Account" section on the dashboard (frontend).**
As any logged-in user, I see a "My Account" section on the dashboard page, pick my
unit once, and read my statement; the choice is remembered and the section shares
the dashboard's as-of control.
- AC7.1 The section shows a **unit selector** listing all nine units. Until a unit
  is chosen it shows a prompt (e.g. "Select your unit to view your statement") and
  does **not** call `GET /api/account`.
- AC7.2 Selecting a unit fetches `GET /api/account?unit=<n>&as_of=<dashboard as-of>`
  and renders the current-year figures, payment guidance, and recent payments as
  USD.
- AC7.3 The selected unit **persists across visits**: after selecting a unit and
  remounting the app, that unit is pre-selected and its statement is fetched
  without re-selecting (localStorage).
- AC7.4 Changing the dashboard's as-of-date control refetches `GET /api/account`
  for the selected unit with the new `as_of`.
- AC7.5 Both `admin` and `viewer` see the section and the selector identically
  (selection is not an authorization boundary); the section exposes no
  write/admin control.
- AC7.6 A `dues_tracked == false` payload renders a clear "tracking begins
  2025"-style note instead of statement figures (no crash).

### Edge cases & failure modes
- **Malformed `as_of`** → `400` (AC1.3); missing → today.
- **Missing or unknown `unit`** → `400` (AC1.4) — not a 500, not a silent empty
  statement.
- **`Y < 2025`** → not tracked, `200` (AC6.1) — not an error, so an early as-of on
  the shared dashboard control doesn't break the section.
- **Divide-by-zero at the year boundary** — after Dec 15, `months_remaining == 0`;
  guidance must not divide (AC4.5).
- **Overpayment / credit** — `remaining_balance` negative, `status == "credit"`,
  unclamped (AC2.4, AC4.4).
- **No budgets for the year** — `annual_dues == 0`, `standard_monthly == 0`;
  statement still returns; `status` driven by carryover and payments.
- **Unit with no `Dues` category or no payments** — `paid_ytd == 0`,
  `recent_payments == []`; statement still returns.
- **`unit` / `as_of` SQL safety** — both validated then passed only as bound
  parameters; never string-interpolated.

### Out of scope (this slice)
Per the feature declaration: recording/collecting payments; editing
`unit_past_dues`; income-budget / interest derivation; pre-2025 dues computation;
a budget-lock / "preliminary" notice; per-unit login or any authz tied to unit
selection; print/PDF; a separate page/route/tab; multi-year analytics; schema
changes.

---

## Part 2 — Design

### Components & seams

**`app/account.py` — per-unit statement assembler (new, plain testable module).**
Business logic lives here, not in the route handler (constitution). It **imports
and calls** `app.dues` (`operating_budget`, `annual_dues`, `unit_paid`,
`carry_in`) for everything the board view already computes, and adds only the new
logic. Function names below are `@scaffolding` — `/build` may rename/refine them
(logging in `build-deviations.md`) as long as the behaviors hold. Suggested seams:
- `months_remaining(as_of) -> int` — pure; the 15th rule (AC4.2).
- `payment_guidance(annual_dues_cents, remaining_cents, as_of) -> dict` — pure;
  `standard_monthly`, `months_remaining`, `suggested_monthly`, `status`
  (AC4.1–4.5). No DB access; integer arithmetic only.
- `recent_payments(con, unit_number, year, as_of) -> list[dict]` — AC5.* (the new
  two-year, capped-at-as-of, this-unit-only query).
- `build_account(con, unit_number, ownership_per_mille, as_of) -> dict` —
  assembles the full payload (AC1.1, AC2.*, AC3.*, AC6.*), delegating current-year
  and prior-year amounts to `app.dues`.

Behavioral properties this module must hold:
- **Engine reuse, not re-derivation.** Current-year `carryover`, `annual_dues`,
  `paid_ytd`, and prior-year `annual_dues_budgeted` / `total_paid` come from
  `app.dues` functions; the module adds no second carryover or operating-budget
  implementation. (AC2.2 is the cross-endpoint check that enforces this.)
- **Round-half-up, integer cents, no floats** in `standard_monthly` /
  `suggested_monthly`; every returned amount is a Python `int` (or `null` where
  the contract says so).
- **No divide-by-zero**: `suggested_monthly` is computed only in the
  `months_remaining > 0` owe branch (AC4.5).
- **Prior-year full-year payments** (capped at that year's Dec 31), current-year
  payments and recent-payments capped at `as_of`.

**`app/routers/account.py` — HTTP surface (new).**
- `GET /api/account` guarded by `require_auth` (reuses
  `app.dependencies.require_auth`; both roles pass; role server-side only).
- Parses `as_of` exactly as `routers/dues.py` does (absent → `date.today()`;
  present and invalid → `400`; strict `^\d{4}-\d{2}-\d{2}$` then
  `date.fromisoformat`). Reuse that established validation shape.
- Reads `unit` from the query: absent → `400`; looks the unit up in `units`
  (parameterized) and `400` (`"Unknown unit"`) if not found, otherwise uses the
  row's `ownership_pct`.
- Opens a connection via `get_connection(config.database_path)`, calls
  `build_account`, returns the payload, closes the connection in `finally`.
  Read-only — no transaction, no cross-origin/CSRF guard.
- Registered in `app/main.py`: added to the `from .routers import (...)` block and
  to the `app.include_router(...)` sequence **after** `dues.router` and **before**
  `register_spa` (the SPA fallback). Without this every `test_account_api.py` case
  404s.

**Frontend — a "My Account" section in the dashboard (`frontend/src/App.tsx`).**
- Inside the existing `Dashboard` component (the region labelled "Financial
  dashboard", which owns the `asOf` state and the "As of" control), a new "My
  Account" section with a `<label>`ed unit `<select>` listing the nine units.
- The selected unit is persisted to and restored from `localStorage` (key is a
  `@scaffolding` detail). On mount, a previously chosen unit is pre-selected and
  its statement fetched; with no stored unit, a prompt renders and no
  `GET /api/account` is issued.
- When a unit is selected, fetch `GET /api/account?unit=<n>&as_of=<asOf>` with
  `credentials: "include"`, using the dashboard's existing `asOf` so the one "As
  of" control drives the dashboard payload, the dues table, **and** this section.
- Render the current-year figures, payment guidance (standard monthly; suggested
  monthly *or* the paid-in-full / credit / due-by-Dec-31 status text), and the
  recent-payments list — money via the existing `centsToUsd` helper.
- When `dues_tracked` is false, render a short "tracking begins 2025" note instead
  of figures. Identical for both roles; no write control.

### The API contract (frozen shape)
`GET /api/account?unit=101&as_of=YYYY-MM-DD` → `200`:
```json
{
  "unit": "101",
  "ownership_per_mille": 117,
  "as_of_date": "2026-06-30",
  "year": 2026,
  "dues_tracked": true,
  "current_year": {
    "year": 2026,
    "carryover": 770000,
    "annual_dues": 2340000,
    "total_due": 3110000,
    "paid_ytd": 1000000,
    "remaining_balance": 2110000
  },
  "prior_year": {
    "year": 2025,
    "data_available": true,
    "annual_dues_budgeted": 1170000,
    "total_paid": 500000,
    "balance_carried_forward": 770000
  },
  "payment_guidance": {
    "standard_monthly": 195000,
    "months_remaining": 6,
    "suggested_monthly": 351667,
    "status": "owes"
  },
  "recent_payments": [
    { "date": "2026-05-01", "amount": 1000000 }
  ]
}
```
The endpoint path, the top-level keys, the `current_year` / `prior_year` /
`payment_guidance` keys, the `status` enum
(`owes` | `paid_in_full` | `credit` | `due_by_year_end`), and each
`recent_payments` entry's `date` / `amount` keys are the **`@frozen`** contract the
frontend and tests bind to. `suggested_monthly` is `null` for every non-`owes`
status. The `suggested_monthly` value shown is *illustrative* under round-half-up
(2,110,000 / 6); tests pin exact monthly values only for divisible cases and
otherwise assert within one cent. The not-tracked shape (`dues_tracked: false`
with the four null/empty members) is also `@frozen`.

### Standards
- **Security (OWASP).** New surface is one authenticated read. Authz reuses
  foundation's `require_auth` (role server-side only; both roles read). No write
  path, no CSRF surface. Both `unit` and `as_of` are validated at the edge and
  parameterized (no SQL injection). The data exposed (one unit's dues balances) is
  the same association-internal financial picture any authenticated user already
  sees on the dashboard's dues table; **unit selection is explicitly not an
  authorization boundary** (declaration), so serving any unit to any authenticated
  caller is by design, not a broken-access-control finding. No new PII or secret.
- **Accessibility (WCAG 2.1 AA).** The unit selector is a labelled `<select>`; any
  figures table uses header cells; the not-tracked and "select your unit" states
  are conveyed as text, not by an empty region alone. (Thin feature — no heavy
  cross-cutting standards absorption beyond these.)
- **API (OpenAPI).** One documented `GET` returning the shape above.

### Pattern reuse
- **Auth guard:** reuses `app.dependencies.require_auth` (foundation) — complete
  reuse, no new auth code.
- **`as_of` edge-validation:** reuses the exact regex-then-`fromisoformat`/`400`
  shape already in `routers/dues.py` and `routers/dashboard.py`.
- **Dues math:** reuses `app/dues.py` (007) in full for current/prior-year
  amounts — the central reason this slice is small.

---

## Part 3 — Coverage

| Requirement / seam | Test(s) |
|---|---|
| AC1.1 payload keys, `year` = as-of year | `test_account_api.py::test_payload_has_all_keys`, `::test_year_follows_as_of` |
| AC1.2 401 unauthenticated | `test_account_api.py::test_requires_auth` |
| AC1.3 default-today / 400 malformed as_of | `test_account_api.py::test_omitted_as_of_defaults_today`, `::test_malformed_as_of_400` |
| AC1.4 unit required / unknown → 400; parameterized | `test_account_api.py::test_missing_unit_400`, `::test_unknown_unit_400`, `::test_unit_sql_injection_safe` |
| AC1.5 both roles read; read-only (no write) | `test_account_api.py::test_both_roles_can_read`, `::test_read_only_writes_nothing` |
| AC2.1 current_year shape (keys, int types) | `test_account_api.py::test_current_year_shape` |
| AC2.2 current_year equals the /api/dues row (engine reuse) | `test_account_engine.py::test_current_year_matches_dues_row` |
| AC2.3 annual_dues full-annual (as-of invariant); remaining identity | `test_account_engine.py::test_annual_dues_not_prorated`, `::test_remaining_is_total_minus_paid` |
| AC2.4 remaining negative (credit), unclamped | `test_account_engine.py::test_overpayment_is_credit` |
| AC3.1/3.2 prior-year block; carried-forward == carryover | `test_account_engine.py::test_prior_year_block`, `::test_carried_forward_equals_carryover` |
| AC3.3 Y=2025 prior year not available, baseline carried | `test_account_engine.py::test_2025_prior_year_not_available` |
| AC4.1 standard_monthly = annual/12 (divisible) | `test_account_guidance.py::test_standard_monthly_divisible` |
| AC4.2 months_remaining 15th rule | `test_account_guidance.py::test_months_remaining_15th_rule` (parametrized) |
| AC4.3 suggested_monthly owe case (divisible + within-cent) | `test_account_guidance.py::test_suggested_monthly_divisible`, `::test_suggested_monthly_rounds_within_cent` |
| AC4.4 paid-in-full / credit statuses, suggested null | `test_account_guidance.py::test_paid_in_full_status`, `::test_credit_status` |
| AC4.5 Dec-16 months_remaining 0 → due_by_year_end, no div0, 200 | `test_account_guidance.py::test_due_by_year_end_no_divzero` |
| AC5.1 recent payments newest-first, two-year window, capped; same-date both appear | `test_account_engine.py::test_recent_payments_window_and_order`, `::test_recent_payments_same_date_both_appear` |
| AC5.2 other unit / category / out-of-window / after-as_of excluded | `test_account_engine.py::test_recent_payments_excludes_others` |
| AC5.3 empty window → [] | `test_account_engine.py::test_recent_payments_empty` |
| AC6.1/6.2 pre-2025 not tracked (nulls/empty, 200); 2025+ tracked | `test_account_api.py::test_pre_2025_not_tracked`, `::test_2025_is_tracked` |
| AC7.1 selector + prompt; no fetch before selection | `MyAccount.test.tsx::shows_prompt_and_selector_before_selection` |
| AC7.2 selecting a unit fetches /api/account and renders USD | `MyAccount.test.tsx::selecting_unit_fetches_and_renders` |
| AC7.3 selection persists across remount (localStorage) | `MyAccount.test.tsx::selection_persists_across_remount` |
| AC7.4 as-of change refetches /api/account with new as_of | `MyAccount.test.tsx::as_of_change_refetches_account` |
| AC7.5 both roles; no write control | `MyAccount.test.tsx::viewer_sees_same_readonly_account` |
| AC7.6 not-tracked note | `MyAccount.test.tsx::shows_not_tracked_note` |

### Build-step note for `/build`
Register the new router in `app/main.py` — add it to the `from .routers import
(...)` block and the `app.include_router(...)` sequence (after `dues.router`,
before `register_spa`). Without it every `test_account_api.py` case 404s.

### Test wiring note for `/build`
These suites are **not** registered with the runners by this spec PR (project
convention — a spec PR stays green because its still-failing pre-build tests are on
no runner's path). When building, append
`"../features/my-account-008/tests/backend"` to `backend/pyproject.toml`
`[tool.pytest.ini_options].testpaths`, and add
`"../features/my-account-008/tests/frontend/**/*.test.{ts,tsx}"` to
`frontend/vite.config.ts` `test.include`. Backend test basenames
(`test_account_api.py`, `test_account_engine.py`, `test_account_guidance.py`) are
unique across features; the frontend file is `MyAccount.test.tsx`. Frontend tests
import the app via the `@/` alias and the external-dep aliases already configured in
`vite.config.ts`.

---

## Adversarial gate
Mode: independent clean-context sub-agent (Stage 4), run once against the drafted
spec and tests. It also read the built code this feature reuses/depends on
(`dues.py`, `routers/dues.py`, `routers/dashboard.py`, `dependencies.py`,
`migrations.py`, `seed.py`, `App.tsx`) and the 007 spec/tests, and **recomputed
every hand-verified number** on the financial test surface.

**Confirmed sound** (no finding): all worked-example arithmetic is correct
(carry_in 770,000; annual_dues 2,340,000; standard_monthly 97,500; the 15th-rule
months; suggested 100,000 / illustrative 351,667; overpayment −330,000;
prior-year 1,170,000 / 500,000 / 770,000; 2025 baseline 250,000). No scope drift
(carryover/operating-budget/income-interest delegated to `dues.py`; no pre-2025
dues, no budget-lock notice, no print/PDF, no per-unit authz). The four-way
guidance status ordering is unambiguous and each branch pinned; the December
divide-by-zero is covered directly; `unit`/`as_of` are validated-then-parameterized
with an injection test; serving any unit to any authenticated caller is by design
(declaration), not broken access control; `@frozen`/`@scaffolding` tags applied
honestly (math via the endpoint, frontend pins behavior not markup).

**Findings & disposition** (both LOW, both in tests, none security → no re-gate):

| # | Sev | Finding | Disposition |
|---|-----|---------|-------------|
| 1 | LOW | The engine-reuse equality test pinned only unit 101 against its `/api/dues` row; a re-derivation reproducing 101's simple single-prior-year accumulation could pass. | **Fixed.** `test_current_year_matches_dues_row` now cross-checks **two** units with different ownership and distinct histories (101 @ 117 owing; 102 @ 104 carrying a credit / negative remaining), in addition to 101's hand-verified absolutes. |
| 2 | LOW | The spec promised "ties broken stably" for `recent_payments`, but no test exercised two payments on the same `post_date`. | **Fixed.** Spec softened to "same-date relative order unspecified (both must appear)"; added `test_recent_payments_same_date_both_appear` asserting both same-date entries appear in the correct newest-first position. |
