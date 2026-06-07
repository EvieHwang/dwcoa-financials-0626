# Spec — Budgets (005)

Budget management on the existing `budgets` and `budget_locks` tables: per-year /
per-category annual amounts with timing patterns and per-line timing overrides,
copy-a-year-forward, year locking with write enforcement, and a centralized
YTD-proration engine. Treasurer-facing editor plus a read API. No schema change.

Money is integer cents end to end (constitution: "Money"); the API boundary
carries integer cents, never dollars or floats. Reuses foundation's auth/role
guards and CSRF (same-origin) defense and ingestion's `get_connection` access.

---

## Behavioral requirements

### R1 — Read a year's budget (any authenticated role)
**As** a board member or treasurer, **I want** to see a year's budget by
category **so that** I can review what was planned.

`GET /api/budgets?year=YYYY` returns, for that year:
- `year`, `locked` (bool), `locked_at` (ISO string or null),
- `budgets`: one entry per **budgetable** category — every active category of
  type `Income` or `Expense`, **plus** any category that already has a budget
  row for that year (so migrated/now-inactive lines stay visible). Each entry
  has: `category_id`, `category_name`, `category_type`, `annual_amount`
  (integer cents; `0` when no row exists for the year), `timing` (the per-line
  override, or `null` when none), `category_default_timing`, and
  `effective_timing` (= `timing` if set, else `category_default_timing`).

**Acceptance:**
- A category with no budget row for the year appears with `annual_amount = 0`,
  `timing = null`, `effective_timing = category_default_timing`.
- A category with a row returns its stored cents and override.
- `Transfer`/`Internal` categories are excluded unless they have a row for the
  year.
- An unauthenticated request → 401. A `viewer` role → 200 (read allowed).
- A missing/invalid `year` (non-integer, or outside 2000–2100) → 400.

### R2 — Set or update a budget line (admin only)
**As** the treasurer, **I want** to set a category's annual budget for a year,
optionally overriding its timing, **so that** I can build the year's plan.

`POST /api/budgets` with body `{year, category_id, annual_amount, timing?}`
upserts the unique `(year, category_id)` line and returns the stored line in the
R1 entry shape.
- `annual_amount` is a **non-negative integer (cents)**.
- `timing`, when present and non-null, must be one of `monthly`/`quarterly`/
  `annual` and is stored as the line's override. When omitted **or** explicitly
  `null`, the stored override is cleared (the line inherits the category
  default). Re-upserting is the way to change either field.

**Acceptance:**
- Upserting a new `(year, category_id)` creates the row; upserting an existing
  one replaces `annual_amount` and the override, leaving no duplicate (the
  `UNIQUE(year, category_id)` invariant holds).
- `annual_amount` of `1234` stores and returns `1234` cents exactly (no float
  drift).
- Negative `annual_amount`, non-integer `annual_amount`, unknown `category_id`,
  invalid `timing`, or missing required field → 400, and **nothing is written**.
- A `viewer` → 403; unauthenticated → 401; a cross-origin request → 403
  (CSRF), and nothing is written.

### R3 — Copy a year forward (admin only)
**As** the treasurer, **I want** to copy a prior year's budgets into a new year
**so that** I have a starting point instead of re-entering every line.

`POST /api/budgets/copy` with body `{from_year, to_year, overwrite?}` copies
every budget line from `from_year` into `to_year`, carrying **both**
`annual_amount` and the `timing` override verbatim. Returns `{from_year,
to_year, count}`.

**Acceptance:**
- Copy carries the timing override, not just the amount (a `from_year` line with
  `timing='annual'` lands in `to_year` with `timing='annual'`).
- `from_year == to_year` → 400. `from_year` with no budgets → 400.
- If `to_year` already has **any** budget row and `overwrite` is absent/false →
  **409** with a clear message, and `to_year` is left unchanged (no silent
  clobber).
- With `overwrite: true`, `to_year`'s budget set is **replaced** to match
  `from_year` (the operation is atomic — on any failure `to_year` is unchanged).
- If `to_year` is locked → 403, regardless of `overwrite`. (`from_year` being
  locked does not block — it is only read.)
- `viewer` → 403; unauthenticated → 401; cross-origin → 403.

### R4 — Lock / unlock a year (admin only)
**As** the treasurer, **I want** to lock a finalized year **so that** its budget
can't be changed by accident.

`POST /api/budgets/lock` with body `{year, locked}` sets the lock state and
returns `{year, locked, locked_at}`. `locked_at` is set when locking and may be
cleared/ignored when unlocking. Lock/unlock is always available to admin (it is
the meta-control, not budget content).

**Acceptance:**
- Locking then reading (R1) reflects `locked: true` and a `locked_at`.
- Unlocking restores writeability.
- `viewer` → 403; unauthenticated → 401; cross-origin → 403.

### R5 — Locked-year write enforcement (admin only)
**As** the treasurer, **I want** writes to a locked year refused **so that** a
finalized budget is protected.

When a year is locked, `POST /api/budgets` (upsert), `POST /api/budgets/copy`
into that year, and `DELETE /api/budgets` (R6) each return **403** and make **no
change** to stored budgets. This is the enforcement migration 2 deferred here.

**Acceptance:**
- Upsert into a locked year → 403 and the prior stored value is unchanged.
- Copy into a locked year → 403 and `to_year` is unchanged.
- Delete in a locked year → 403 and the line still exists.

### R6 — Delete a budget line (admin only)
**As** the treasurer, **I want** to remove a line I added by mistake.

`DELETE /api/budgets?year=YYYY&category_id=ID` removes the `(year, category_id)`
row and returns the count deleted (`0` if none existed — idempotent).
- `viewer` → 403; unauthenticated → 401; cross-origin → 403; locked year → 403
  (R5).

### R7 — Centralized YTD proration engine
**As** the system (and, later, the dashboard), **I need** one tested function
that prorates an annual budget to a given as-of date by timing pattern, **so
that** mid-year budget-vs-actual is honest and computed in exactly one place.

The engine maps `(annual_cents, effective_timing, as_of_date, budget_year)` →
**integer cents** of budget expected through `as_of_date`, **stepped by period
reached** (a period contributes its full share the moment the as-of date enters
it):

- `as_of.year < budget_year` → `0` (year hasn't started), for every timing.
- `as_of.year > budget_year` → `annual_cents` (year fully elapsed), for every
  timing.
- `as_of.year == budget_year`, with `m = as_of.month` (1–12):
  - **monthly** → `round(annual_cents × m / 12)`
  - **quarterly** → `round(annual_cents × ceil(m/3) / 4)`
  - **annual** → `annual_cents` (full amount from January 1)
- Rounding is half-up to the nearest cent, computed with exact decimal
  arithmetic on integers (no binary float) so results never drift.

Worked examples (all `budget_year = 2025`, `annual_cents = 120000` = $1,200):

| timing | as_of | expected cents |
|---|---|---|
| monthly | 2025-01-15 | 10000 |
| monthly | 2025-06-01 | 60000 |
| monthly | 2025-06-30 | 60000 |
| monthly | 2025-12-31 | 120000 |
| quarterly | 2025-01-10 | 30000 |
| quarterly | 2025-04-30 | 60000 |
| quarterly | 2025-07-01 | 90000 |
| quarterly | 2025-12-31 | 120000 |
| annual | 2025-01-01 | 120000 |
| annual | 2025-12-31 | 120000 |
| any | 2026-02-01 | 120000 |
| any | 2024-12-31 | 0 |

Rounding examples: `annual_cents=100`, monthly, month 1 → `round(100/12)=8`;
month 2 → `round(200/12)=17`. `annual_cents=150`, monthly, month 1 →
`round(150/12)=13` (half rounds up).

**Effective timing resolution** is a single rule used by R1 and the engine's
callers: `effective_timing = budget.timing if not null else category.timing`.

### R8 — Budget editor UI
**As** the treasurer, **I want** a screen to read and edit a year's budget,
copy a year forward, and lock/unlock **so that** I can run the workflow without
the API directly. View-only users see the budget but no edit controls.

**Acceptance:**
- The editor renders the selected year's lines (amounts shown in USD) from R1.
- For an admin, editing a line's amount and saving issues an R2 upsert carrying
  **integer cents** (dollars converted at the boundary).
- Copy-year issues an R3 request; when the target is non-empty the UI surfaces
  the 409 and offers to confirm, re-issuing with `overwrite: true`.
- The lock toggle issues an R4 request; a locked year disables the edit/save
  controls.
- A `viewer` sees the budget read-only — no save, copy, or lock controls.

### Out of scope (this feature)
- Budget-vs-**actual** (joining budgets to transaction actuals), the 2025+
  calculated-dues/interest income derivation, account balances, reserve-fund
  status, cashflow, charts, PDF/print — all Dashboard (006) / Dues (007). The
  proration engine (R7) is delivered and tested here; its **HTTP exposure and
  the actuals join are 006**, so no endpoint in this feature returns prorated
  values.
- Category management (create/rename/retype/activate, editing a category's
  *default* timing) — a separate feature. This feature edits only amounts and
  per-line timing overrides on existing categories.
- Schema migrations — the tables already exist.

---

## Design

### Components & seams
- **Proration engine** — a pure module (e.g. `app.proration`) exposing the R7
  function and the effective-timing rule. No I/O, no DB; deterministic given its
  arguments. This is the constitution's "centralized, unit-tested" budget-timing
  logic. Dashboard (006) will import it; Budgets (005) owns and tests it.
- **Budget read/write logic** — plain functions (not in the route handler;
  constitution: "business logic lives in modules") that read a year's lines in
  the R1 shape, upsert/delete a line, copy a year, and read/set lock state.
- **Budgets router** — `/api/budgets` HTTP surface (list, upsert, copy, lock,
  delete) wiring guards to the logic. Registered in `create_app()` after the
  existing routers and before the SPA fallback.
- **Budget editor UI** — a section of the authenticated React shell consuming
  the R1 read and issuing R2–R4/R6 writes.

### Seam properties (behavioral)
- **Auth/role (Reuses pattern: foundation auth).** Reads use `require_auth`,
  writes use `require_admin`; role is derived server-side from the session token
  and never from client input. A `viewer` reaches reads (200) but not writes
  (403); an anonymous request gets 401.
- **CSRF (Reuses pattern: foundation same-origin guard).** Every unsafe method
  (POST upsert/copy/lock, DELETE) rejects a cross-origin request with 403 before
  any write, identical to the ingestion upload guard.
- **DB access (Reuses pattern: ingestion `get_connection`).** Writes run with FK
  enforcement on; copy-overwrite and any multi-statement write are atomic
  (single transaction; rollback on error) — a failed write never leaves a
  partial year. Single-writer assumption holds (constitution).
- **Money boundary.** Amounts cross the API as integer cents and are stored as
  integer cents; the engine returns integer cents. No dollars or floats appear
  in storage, request, or response. Decimal/integer arithmetic only.
- **Validation boundary.** Out-of-range year, negative/non-integer amount,
  unknown category, and invalid timing are rejected at the edge (400) with no
  write; lock violations are 403 with no write; copy-into-non-empty without
  overwrite is 409 with no write. These are returned as **400** via explicit
  validation (the project's ingestion/foundation manual-validation convention),
  **not** FastAPI/Pydantic's default 422 — so handlers read the year query and
  the JSON body loosely (e.g. as a mapping) and validate the documented cases
  themselves. `annual_amount` must be a JSON integer (a float such as `100.5`
  fails); `year` must parse to an integer in 2000–2100.

### Constraints
- The `UNIQUE(year, category_id)` invariant is never violated by upsert or copy.
- Proration is the **only** place YTD budget timing math lives (no second
  implementation in the router or UI).
- No new tables, columns, or migrations; `budgets.timing` (nullable override)
  and `budget_locks` are used as-is.
- The proration function name/signature is `@scaffolding` (named so tests can
  call it); its **behavior** (the R7 table) is the frozen contract. The HTTP
  surface and response field names in R1–R6 are `@frozen` (the frontend and the
  dashboard consume them).

---

## Coverage

| Requirement / seam | Test(s) |
|---|---|
| R1 read shape, zero-fill, type filter, default/effective timing | `test_budgets_crud.py::test_list_*` |
| R1 auth (viewer reads, anon 401), bad year 400 | `test_budgets_authz.py::test_read_*`, `test_budgets_crud.py::test_list_rejects_bad_year` |
| R2 upsert create/replace, uniqueness, exact cents | `test_budgets_crud.py::test_upsert_*` |
| R2 timing override set/clear | `test_budgets_crud.py::test_upsert_timing_override*` |
| R2 validation (negative/non-int/unknown cat/bad timing) → 400, no write | `test_budgets_crud.py::test_upsert_rejects_*` |
| R2/R3/R4/R6 admin-only, CSRF | `test_budgets_authz.py::*` |
| R3 copy carries amount+timing, count | `test_budgets_copy_lock.py::test_copy_*` |
| R3 same-year/empty-source 400; non-empty target 409 no-clobber; overwrite replaces atomically | `test_budgets_copy_lock.py::test_copy_rejects_*`, `::test_copy_overwrite*` |
| R4 lock/unlock round-trips, reflected in read | `test_budgets_copy_lock.py::test_lock_*` |
| R5 locked upsert/copy/delete → 403, no change | `test_budgets_copy_lock.py::test_locked_*` |
| R6 delete removes line, idempotent | `test_budgets_crud.py::test_delete_*` |
| R7 proration worked examples (all timings, year boundaries, rounding) | `test_proration.py::*` |
| R7 effective-timing resolution (override beats default) | `test_proration.py::test_effective_timing*` |
| R8 editor renders, edit→upsert cents, copy→confirm/overwrite, lock toggle, viewer read-only, locked disables | `BudgetEditor.test.tsx` |

---

## Adversarial gate
[populated after Stage 4]
