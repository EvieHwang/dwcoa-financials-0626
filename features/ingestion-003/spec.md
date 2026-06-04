# Spec: Ingestion

**Feature:** ingestion-003
**Declaration:** `features/ingestion-003/declaration.md`

This feature delivers the runtime CSV-upload path: an admin-only ingestion
endpoint that parses a bank-export CSV, maps accounts, converts money to exact
integer cents, dedups idempotently against the stored history (preserving
existing categories), and inserts new rows; an authenticated list/filter
endpoint; and the dashboard UI (admin upload control + paginated transactions
table). It builds on foundation's auth, CSRF guard, DB access, and the
`transactions`/`accounts` tables. It computes no categorization, budget, or dues
logic.

The business logic (parsing, conversion, dedup) lives in a plain testable module,
not in the route handler (constitution: "business logic lives in modules").

---

## Part 1 — Behavioral requirements

### R1 — Bank CSV is parsed; structural problems reject the whole file
**As** the treasurer, **I need** my bank export to be read correctly, **so that**
the right transactions land in the system.

- The bank export has a header row with these columns (the contract this feature
  reads): `Account Number, Post Date, Check, Description, Debit, Credit, Status,
  Balance`. (The real export's first data rows look like
  `"****9226",2/6/2026,,"Overdraft Protection Withdraw",538.07,,Posted,120730.25`.)
- **Acceptance:** a file missing any of the required columns
  (`Account Number, Post Date, Description, Debit, Credit, Balance`) is rejected
  with HTTP 400 and an error naming the missing column(s); **no rows are
  inserted**. (`Check` and `Status` are tolerated-absent: treated as empty /
  `Posted`.)
- **Acceptance:** an empty upload, or content that is not parseable as CSV with a
  header, is rejected 400 with no rows inserted.
- **Acceptance:** extra/unrecognized columns beyond the expected set are ignored,
  not an error.

### R2 — Money converts to exact integer cents (never binary float)
**As** the treasurer, **I need** every amount stored to the cent, **so that**
balances and downstream budget/dues math are exact.

- `Debit`, `Credit`, `Balance` are dollar strings that may carry `$`, thousands
  commas, and surrounding whitespace. The store holds integer cents
  (`transactions.debit/credit` nullable, `balance NOT NULL`).
- **Acceptance:** for any value with at most two decimal places, the stored value
  is the integer number of cents equal to the amount rounded to the nearest cent,
  half away from zero, computed so binary-float artifacts never shift the result
  (`371.4 → 37140`, `625.44 → 62544`, `3981.85 → 398185`, `122489.78 →
  12248978`, `"$1,234.56" → 123456`).
- **Acceptance:** an empty `Debit` or `Credit` cell stores `NULL` (not `0`) — a
  credit-only row has `debit IS NULL`, a debit-only row has `credit IS NULL`. A
  negative value (e.g. an overdrawn `Balance`) is stored with sign preserved.
- **Acceptance:** a row whose `Balance` is empty/unparseable, or whose `Debit`/
  `Credit` is non-empty but unparseable, is a row-level data error → the whole
  upload is rejected 400 with no rows inserted (R6 atomicity). `Balance` is
  required because it is `NOT NULL` and part of the dedup identity (R4).

### R3 — Dates normalize to ISO; unparseable dates reject the file
- `Post Date` arrives in US bank format (`M/D/YYYY`, e.g. `2/6/2026`; two-digit
  years `M/D/YY` also accepted). It is stored as `YYYY-MM-DD`.
- **Acceptance:** `2/6/2026 → 2026-02-06`, `12/31/2025 → 2025-12-31`,
  `1/2/26 → 2026-01-02`. ISO `YYYY-MM-DD` input is accepted unchanged
  (idempotent re-ingest of an already-normalized value).
- **Acceptance:** ambiguous day-first formats are **not** silently accepted — the
  parser does not guess `D/M/Y`; an unparseable date is a row-level error that
  rejects the whole upload (R6) rather than storing a wrong date.

### R4 — Ingestion is idempotent: dedup on the full bank-row identity
**As** the treasurer, **I need** re-uploading the full history to be safe, **so
that** I never create duplicate transactions.

- A transaction's dedup identity is the tuple
  **`(account_number, post_date, description, debit, credit, balance)`** — all
  bank-provided, immutable values (`balance` is included deliberately: it is the
  bank's own per-row running balance, not a computed field, and anchors row
  identity). Matching is **NULL-aware**: a `NULL` debit matches only a `NULL`
  debit (so two credit-only rows are not falsely distinguished).
- **Acceptance:** uploading a file, then uploading the **same file** again, adds
  zero rows the second time and reports all rows as skipped-duplicate. The total
  row count is unchanged.
- **Acceptance:** uploading an **overlapping** file (some rows already present,
  some new) inserts only the new rows; the already-present rows are skipped.
- **Acceptance:** if the same row appears **twice within one file**, it is
  inserted once and the repeat is counted as a duplicate.
- **Acceptance:** two distinct transactions that share date + amount + description
  but differ in `account_number` (or in `balance`) are both kept — the identity
  includes account and balance, so they do not collide.
- **Design note (rationale, not a test):** dedup is enforced in application code
  (load existing identities, compare, insert misses) within a single
  transaction, **not** via a DB `UNIQUE` constraint — SQLite treats `NULL`s as
  distinct in a unique index, which would wrongly admit duplicate credit-only /
  debit-only rows.

### R5 — Re-upload preserves existing categories and other server-side fields
**As** the treasurer, **I need** my categorization work to survive re-uploads,
**so that** I don't redo it every month.

- **Acceptance:** given a stored transaction that the treasurer has categorized
  (`category_id` set), re-uploading a file containing that same transaction
  leaves the stored row **completely unchanged** — `category_id`,
  `auto_category_id`, `needs_review`, and `id` are all untouched, and no new row
  is added. (Follows directly from R4: a duplicate is skipped, never updated.)

### R6 — An upload is atomic: all valid rows or nothing
**As** the treasurer, **I need** a bad file to fail cleanly, **so that** I'm never
left with a half-imported history I can't trust.

- **Acceptance:** when any structural error (R1) or row-level data error (R2/R3)
  is present, the response is 400, the body lists the error(s), and the
  transactions table is byte-for-byte unchanged from before the request
  (no partial insert).
- **Acceptance:** on success the response is 200 and **all** new rows are present.
- There is **no** destructive "replace all" mode. Dedup-append is the only
  ingestion behavior; an upload never deletes or overwrites stored rows.

### R7 — Unknown accounts are imported and surfaced, not dropped
**As** the treasurer, **I need** a row for an unmapped account to still import and
be flagged, **so that** I notice it and add the account, without losing data or
having the whole file rejected.

- Accounts are mapped masked-number → name via the existing `accounts` table
  (seeded/migrated; currently `****7145 Savings`, `****9242 Checking`,
  `****9226 Reserve Fund`). The set is small and changes rarely.
- **Acceptance:** a row whose `Account Number` is not in `accounts` is **still
  inserted**, with `account_number` stored verbatim and `account_name` set to
  `Unknown`; it counts toward "added", and the summary reports the count (and the
  distinct unknown account numbers seen). It is **not** a hard error and does not
  block other rows.
- **Acceptance:** a mapped row stores the correct `account_name` for its masked
  number.

### R8 — Upload returns an actionable summary
**As** the treasurer, **I need** to see what the upload did, **so that** I can
trust it and spot problems.

- **Acceptance:** a successful upload returns counts for **added**,
  **skipped-as-duplicate**, and **unknown-account** rows, plus the total rows
  read. (`added` includes unknown-account rows; they are added *and* flagged.)
- **Acceptance:** the summary surfaces the distinct unknown account number(s)
  encountered so the treasurer can act on them.

### R9 — Transactions are listable, filterable, and paginated
**As** any logged-in user, **I need** to see the stored transactions, **so that**
I can verify an upload and review the history.

- **Acceptance:** an authenticated `GET` returns transactions ordered newest-first
  (`post_date` desc, then `id` desc), each carrying its account name/number, post
  date, check number, description, debit, credit (as integer cents or null),
  status, balance, and its category name (null until categorized in slice 4).
- **Acceptance:** results are paginated — the response carries the page of rows
  plus the total count matching the active filters, and the page size is bounded
  (a caller cannot request an unbounded page).
- **Acceptance:** filtering by `year` returns only transactions whose `post_date`
  falls in that calendar year; filtering by `account` (account name) returns only
  that account's rows; the two filters compose. The total count reflects the
  filters.
- **Acceptance:** the list includes **all** transactions regardless of category
  type (no Transfer/Internal exclusion — that is dashboard logic in slice 6).

### R10 — Authorization and CSRF are enforced server-side
**As** the association, **I need** only the admin to mutate data and only from the
app itself, **so that** the financial record can't be tampered with.

- **Acceptance:** the upload endpoint requires the **admin** role: a view-only
  session gets 403, an unauthenticated request gets 401, and in both cases no
  rows are inserted. Role is taken only from the verified session, never from
  client input (reuses foundation's `require_admin`).
- **Acceptance:** a cross-origin upload (foreign `Origin`/`Referer`) is rejected
  403 and inserts nothing (reuses foundation's same-origin guard).
- **Acceptance:** the list endpoint requires authentication (any role); an
  unauthenticated request gets 401. View-only sessions **can** read it.
- **Acceptance (observable):** an upload above a sane size bound is rejected
  (413 or 400) and inserts nothing. The bound comfortably exceeds a multi-year
  history (which is well under 1 MB).
- **Design intent (OWASP, not directly observable at this test layer):** the
  size check should short-circuit before the file is fully read into memory —
  e.g. reject on a declared `Content-Length` over the bound, or stream-count
  bytes and abort. FastAPI's `UploadFile` spools large bodies to a temp file
  rather than RAM, so the memory-bounding property is a `/build` responsibility
  the suite cannot assert directly; the test pins only the reject-and-no-insert
  outcome.

### R11 — The dashboard gains an upload control and a transactions table
**As** the treasurer, **I need** to upload and review transactions in the app,
**so that** ingestion is a real workflow, not just an API.

- **Acceptance:** an **admin** sees an upload control (a labeled file input + a
  submit action); a **view-only** user does not (parallel to the existing
  admin-only gating). The control posts the file to the upload endpoint and, on
  completion, shows the result summary (added / skipped / unknown-account) in a
  region announced to assistive tech (`aria-live`). An error response shows the
  error message rather than a silent failure.
- **Acceptance:** all authenticated users see a **transactions table** populated
  from the list endpoint, with controls to filter by year and by account and to
  page through results; changing a filter re-queries with that filter applied.
- **Acceptance (a11y, WCAG 2.1 AA, scoped):** the table uses real header cells
  (`<th scope="col">`), the file input has an associated label, and filter
  controls are labeled. (Scope note under Standards.)

### Out of scope (restated from declaration)
- Categorization on ingest, the rules engine, and the review queue (slice 4).
- CSV export (cut; recorded deviation in the decision log).
- Re-mapping already-ingested `Unknown` rows when an account is later added.
- Dashboard charts / balances / budget-vs-actual / transfers-excluded reporting
  (slice 6); editing or deleting transactions through this UI.
- Any schema, migration, or seed change.

---

## Part 2 — Design

### D1 — Ingestion module (new, pure logic) — `backend/app/ingest.py`
A plain, testable module (no FastAPI imports). Public surface the tests pin
(names are scaffolding; the **behavior** is the contract):

- `to_cents(value: str | None) -> int | None` — parse a dollar string (tolerating
  `$`, commas, whitespace; empty/`None` → `None`) to exact integer cents via
  decimal arithmetic on the value's exact decimal string, half away from zero.
  **Reuse:** this is the same conversion legacy-migration-002 introduces
  (`app.legacy_import.to_cents`, which takes a float); `/build` should converge on
  a single shared exact-cents converter (e.g. an `app.money` helper or by reusing
  the existing one) rather than writing a second rounding implementation. The
  string-input variant here additionally strips currency formatting. **This and
  dedup are the highest-value test surface.**
- `normalize_date(value: str) -> str | None` — `M/D/YYYY` / `M/D/YY` / ISO →
  `YYYY-MM-DD`; returns `None` (not a guess) for anything else. Does not accept
  day-first formats.
- `dedup_key(account_number, post_date, description, debit, credit, balance)` —
  the canonical identity tuple used both for in-file dedup and against-store
  dedup. NULL-aware by construction (the tuple carries `None` for empty
  debit/credit).
- `parse_csv(content: str, account_map: dict[str, str]) -> ParseResult` — parse,
  validate the header, map accounts (unmapped → `account_name="Unknown"` +
  recorded), convert money/date, and collapse in-file duplicates. Returns parsed
  rows plus structured outcomes: `errors` (structural + row-level; non-empty ⇒
  the caller must reject the whole upload), `unknown_accounts` (distinct masked
  numbers seen unmapped), and an in-file duplicate count. Pure: the account map
  is passed in, no DB access here.

**Behavioral properties:** R1 (header validation, no insert on structural error),
R2 (exact cents, NULL/sign), R3 (date normalization, no day-first guess), R7
(unknown → `Unknown` + recorded), in-file dedup (R4).

### D2 — Transactions router (new) — `backend/app/routers/transactions.py`
Registered in `app.main.create_app` after the existing routers, before the SPA
fallback. Two endpoints; both reuse foundation patterns.

- **`POST /api/transactions/upload`** — `require_admin` (reuses
  `app.dependencies.require_admin`) and the same-origin guard (reuses
  `app.auth.is_cross_origin`, rejecting cross-origin 403 exactly as the auth
  router does). Accepts the CSV as a multipart file upload, bounded in size
  before full processing (R10) — the bound is a config knob
  (`INGEST_MAX_UPLOAD_BYTES`, default comfortably above a multi-year history; the
  env-var name is a scaffolding detail `/build` may rename). It:
  1. reads the account map from `accounts`;
  2. calls `ingest.parse_csv`;
  3. if `errors` is non-empty → 400 with the errors, **no writes**;
  4. else, in a **single DB transaction**: load the set of existing dedup
     identities (one query), insert each parsed row whose identity is not already
     present (and not already inserted earlier in this file), set
     `category_id/auto_category_id/confidence = NULL` and `needs_review =` schema
     default, and update `app_config['last_upload_at']`; commit. Any error rolls
     back so nothing is inserted (R6).
  5. returns the summary: `added`, `skipped_duplicate`, `unknown_account_count`,
     `unknown_accounts`, `total`.

  Reuses foundation's `get_connection` (FK enforcement on). Inserted columns:
  `account_number, account_name, post_date, check_number, description, debit,
  credit, status, balance` (+ NULL category fields). New rows are uncategorized
  (D — categorization is slice 4).

- **`GET /api/transactions`** — `require_auth` (any role). Query params: `year`,
  `account`, `limit` (bounded; rejects/clamps over-large values), `offset`.
  Returns `{ transactions: [...], total, limit, offset }`, ordered `post_date`
  desc, `id` desc, joining `categories.name` for display. No category-type
  exclusion (R9). The response shape and the two routes are a **public contract**
  the frontend consumes (`@frozen`).

**Reuses pattern:** foundation auth guards (`require_admin`/`require_auth`),
`is_cross_origin` CSRF defense, `get_connection` DB access, and the existing
`transactions`/`accounts` schema and indexes (`idx_transactions_date`,
`idx_transactions_account`). No new migration.

**New dependency:** multipart upload requires `python-multipart` — FastAPI raises
at request time if it is absent, which would error the entire upload test suite.
`/build` must add it to `backend/pyproject.toml` (it is the one new runtime
dependency this feature introduces).

### D3 — Dashboard UI (extends `frontend/src/App.tsx`)
The app is a single `App.tsx` with inline components (foundation pattern). Extend
`DashboardShell`:
- An **admin-only** upload section (rendered only when `role === "admin"`, under
  the existing admin gating) with a labeled file input and submit; on response it
  renders the summary in an `aria-live` region, or the error text on failure;
  after a successful upload it refreshes the transactions table.
- A **transactions table** for all roles, fed by `GET /api/transactions`, with
  labeled year and account filter controls and pagination; changing a filter
  re-queries. Real `<th scope="col">` headers.

Reuses the existing `fetch(..., { credentials: "include" })` convention and the
role plumbing already in `App.tsx`. The endpoint paths, query params, and JSON
shape are the seam to the backend; the DOM/test-ids are named for testability
(`@scaffolding`) — `/build` may refine markup as long as the behaviors hold.

### D4 — Test wiring (project-level convention; applied by `/build`, recorded here)
Feature tests live in `features/<feature>/tests/{backend,frontend}/` and are
discovered by each runner via a **per-feature registration that the feature's
`/build` adds** — not the spec PR (that is why prior spec PRs stayed green: the
spec only deposits the test files):
- **pytest:** `/build` appends `"../features/ingestion-003/tests/backend"` to
  `backend/pyproject.toml`'s `tool.pytest.ini_options.testpaths`. Test-module
  basenames are unique across features (this feature uses `test_ingest_*.py` /
  `test_transactions_list.py`, avoiding collision with legacy-migration's
  `test_import.py` under pytest's default import mode). Each backend test dir
  resolves the repo root from its own location (`parents[4]`) and puts `backend/`
  on `sys.path`, never an absolute sandbox path.
- **Vitest:** `/build` extends `frontend/vite.config.ts`'s `test.include` to cover
  `../features/ingestion-003/tests/frontend/**`. Frontend tests import the app via
  the `@/` alias and pull React/testing-library through the external-dep aliases
  already configured in `vite.config.ts`.

This convention is recorded in `constitution.md` `## Testing` so every feature and
`/build` inherit it.

---

## Coverage

| Requirement / seam | Test(s) |
|---|---|
| R1 header validation, structural reject, no insert | `test_ingest_parse.py::test_missing_columns_*`, `test_ingest_upload.py::test_structural_error_inserts_nothing` |
| R2 exact cents (artifact values, `$`/commas), NULL, negative | `test_ingest_parse.py::test_to_cents_*`; end-to-end exactness `test_ingest_upload.py::test_amounts_stored_as_exact_cents` |
| R2 unparseable amount/balance rejects file | `test_ingest_upload.py::test_bad_amount_rejects_whole_file` |
| R3 date normalization; no day-first guess; bad date rejects | `test_ingest_parse.py::test_normalize_date_*`, `test_ingest_upload.py::test_bad_date_rejects_whole_file` |
| R4 idempotent re-upload (0 added) | `test_ingest_upload.py::test_reupload_is_noop` |
| R4 overlapping upload adds only new | `test_ingest_upload.py::test_overlapping_upload_adds_only_new` |
| R4 in-file duplicate inserted once | `test_ingest_upload.py::test_in_file_duplicate_inserted_once` |
| R4 account/balance distinguish near-identical rows; NULL-aware | `test_ingest_upload.py::test_distinct_account_or_balance_not_deduped`, `test_ingest_parse.py::test_dedup_key_null_aware` |
| R5 existing category preserved on re-upload | `test_ingest_upload.py::test_reupload_preserves_category` |
| R6 atomic — nothing inserted on any error | `test_ingest_upload.py::test_structural_error_inserts_nothing`, `::test_bad_amount_rejects_whole_file` |
| R7 unknown account imported as `Unknown` + surfaced | `test_ingest_upload.py::test_unknown_account_imported_and_flagged` |
| R7 mapped account stores correct name | `test_ingest_upload.py::test_mapped_account_name` |
| R8 summary counts (added/skipped/unknown/total) | `test_ingest_upload.py::test_summary_counts` |
| R9 list ordering, fields, category null | `test_transactions_list.py::test_list_orders_and_fields` |
| R9 pagination + bounded page + total | `test_transactions_list.py::test_pagination_and_total`, `::test_limit_is_bounded` |
| R9 year + account filters compose | `test_transactions_list.py::test_filters_year_account` |
| R9 all category types included | `test_transactions_list.py::test_includes_all_types` |
| R10 upload admin-only (viewer 403 / anon 401), no insert | `test_ingest_upload.py::test_upload_requires_admin` |
| R10 cross-origin upload rejected, no insert | `test_ingest_upload.py::test_upload_cross_origin_rejected` |
| R10 list requires auth; viewer allowed | `test_transactions_list.py::test_list_requires_auth`, `::test_viewer_can_list` |
| R10 oversize upload rejected without full parse | `test_ingest_upload.py::test_oversize_upload_rejected` |
| R11 admin sees upload, viewer doesn't; summary rendered | `Upload.test.tsx` |
| R11 table renders rows; filters re-query; pagination | `TransactionsTable.test.tsx` |

---

## Adversarial gate

**Mode:** independent clean-context sub-agent (general-purpose), run once against
the drafted spec and tests. Four findings returned — no HIGH, no security
findings (so no security re-gate). All dispositioned **fixed**. No risks
acknowledged (the `Acknowledged risks` table in constitution.md is unchanged for
this feature). The gate explicitly cleared the high-value surfaces (dedup
identity, atomicity, NULL-aware matching, exact-cents, authz/CSRF,
pagination/clamp, filter composition) as well-tested against the real foundation
contracts.

- **F1 (MEDIUM, coverage) — table's `<th scope="col">` a11y requirement
  (R11/WCAG) was unverified.** *Disposition: fixed.* `TransactionsTable.test.tsx`
  now asserts every column header is a real `columnheader` with `scope="col"`, so
  a `<div>`-table no longer passes green.
- **F2 (MEDIUM, coverage) — upload summary's `aria-live` requirement was
  unverified.** *Disposition: fixed.* `Upload.test.tsx` now asserts the summary
  region carries an `aria-live` attribute, not just the count text.
- **F3 (LOW, integrity) — R10 promised "rejected without being fully
  buffered/parsed," which the test cannot observe.** *Disposition: fixed.* R10 now
  splits an **observable** acceptance (reject + no insert) from a **design-intent**
  note (the pre-buffer/streamed size check is a `/build` responsibility,
  unobservable here because `UploadFile` spools to disk).
- **F4 (LOW, integrity) — `python-multipart` is a new runtime dependency not
  flagged; its absence would error the whole upload suite.** *Disposition: fixed.*
  D2 now names it as the one new dependency `/build` must add to
  `pyproject.toml`.
