# Spec: Rules Categorization

**Feature:** rules-categorization-004
**Declaration:** `features/rules-categorization-004/declaration.md`

This feature delivers deterministic, rules-only categorization on top of the
slice-3 transaction store: a pure categorization engine; a categorize step on the
existing CSV-upload path; a review queue with a single-transaction fix and a
rule-suggestion-on-fix; a full rules editor; and a re-categorization sweep that
runs when a rule is saved so a rule reaches transactions already in the store. It
reuses foundation's auth guards, same-origin (CSRF) defense, DB access, and the
existing `transactions` / `categorize_rules` / `categories` tables; it adds one
additive schema migration. No LLM is involved (constitution: rules-only).

The matching, suggestion, and sweep-decision logic live in a plain testable module
(`app/categorize.py`), not in route handlers (constitution: "business logic lives
in modules"). The two highest-value surfaces are **rule matching/ordering** and
the **sweep's manual-vs-auto protection** — get those wrong and either the
treasurer's hand categorization is silently clobbered or every downstream number
is miscategorized.

---

## Key terms (used throughout)

- **Categorization source.** Each transaction carries a marker of *who* set its
  category: `auto` (this app's engine, via ingest or a sweep), `manual` (a human,
  via the review-fix endpoint), or unset/`NULL` (never categorized by this app —
  includes every row migrated from production). The column name is an
  implementation detail (`@scaffolding`); the three observable states are the
  contract.
- **Open transaction (the sweep target).** A transaction is *open* to
  re-categorization iff its source is `auto` **or** it is flagged
  `needs_review`. Equivalently: rows this app categorized by rule, plus rows
  flagged for review (whether flagged at ingest, or flagged by the migration's
  backlog pass for migrated-uncategorized rows — R9). **Manual rows and migrated
  *categorized* history are never open** — a `manual` row, and any row with a
  category set but source unset (migrated-and-categorized), is excluded from every
  sweep. This single definition protects hand-made and migrated *categorized*
  categorizations (R6) without a backfill, while still letting an empty-category
  migrated row be cleaned once it is flagged.
- **Signed-agnostic amount (for amount conditions).** A transaction's matchable
  amount is its present money magnitude in integer cents. A bank row populates at
  most one of `debit` / `credit` (the other is NULL — slice-3 R2), so the magnitude
  is whichever is non-NULL. To stay deterministic in the atypical case where both
  are populated, **`debit` takes precedence** over `credit`; a row with both NULL
  has no matchable amount and never satisfies an amount-bounded rule. A literal
  zero amount is a present magnitude of `0` (so a `0` row fails any positive
  `amount_min`).

---

## Part 1 — Behavioral requirements

### R1 — The engine matches by the first qualifying rule in a defined order
**As** the treasurer, **I need** categorization to be predictable, **so that** I
can reason about which rule wins and tune it.

- A rule has: a **pattern** (text), a **target category**, optional **account**
  condition, optional **amount** condition (`amount_min` / `amount_max`, either or
  both, inclusive, integer cents), a **priority** (integer), a **confidence**
  (0–100), and an **active** flag.
- A rule **matches** a transaction iff **all** of these hold:
  - the pattern is a **case-insensitive substring** of the transaction's
    `description`; and
  - if the rule has an account condition, the transaction's `account_name` equals
    it (exact match); and
  - if the rule has an amount condition, the transaction's signed-agnostic amount
    exists and lies within `[amount_min, amount_max]` (each bound optional).
- **Inactive rules are never evaluated.**
- **Acceptance (order):** among matching active rules, the winner is chosen by
  **priority descending, then pattern length descending, then rule id ascending**.
  Worked example: rules `("BANK", Transfers, prio 0)` and
  `("BANK OF AMERICA", Interest, prio 0)` both match `"BANK OF AMERICA ACH"`; the
  longer pattern wins → Interest. With priorities `("BANK", prio 10)` vs
  `("BANK OF AMERICA", prio 0)`, the higher priority wins → Transfers.
- **Acceptance (substring, case-insensitive):** pattern `"electric"` matches
  `"PUGET SOUND ELECTRIC CO"`; pattern `"ELECTRIC"` matches the same. A pattern
  that is not a substring does not match.
- **Acceptance (account condition):** a rule `("DEPOSIT", Dues 101, account=
  "Savings")` matches a `"MOBILE DEPOSIT"` row on `Savings` but **not** the same
  description on `Checking`.
- **Acceptance (amount condition):** a rule `("MCCARY", Grounds, amount_min=
  10000, amount_max=20000)` matches a `$150.00` debit (`15000`) but not a `$5.00`
  (`500`) one; a min-only or max-only bound behaves as the corresponding
  one-sided range; a row whose only amount is a credit matches on that credit's
  magnitude.
- **Acceptance (no match):** a transaction matched by no active rule yields the
  "needs review" verdict (no category, `needs_review` true), never a guessed
  category.

### R2 — Categorization runs on ingest, for newly inserted rows only
**As** the treasurer, **I need** an upload to categorize what it imports, **so
that** most rows are placed automatically and only the rest need my attention.

- The slice-3 upload path (`POST /api/transactions/upload`) now runs each
  **newly inserted** row through the engine against the current active rules,
  inside the same atomic insert transaction.
- **Acceptance (matched):** an uploaded row that matches a rule is stored with that
  rule's category as its effective category, the engine's `auto` source, the
  rule's confidence, and `needs_review` false.
- **Acceptance (unmatched):** an uploaded row that matches no rule is stored
  uncategorized, source unset, and **`needs_review` true**.
- **Acceptance (new rows only):** rows skipped as duplicates (slice-3 dedup) are
  **not** re-categorized or otherwise touched — an existing row's category,
  source, `needs_review`, and `id` are unchanged by a re-upload (preserves
  ingestion R5 and any manual fix made between uploads).
- **Acceptance (summary, additive):** the upload summary additionally reports how
  many newly added rows were **categorized** vs. flagged **needs_review**. The
  existing summary fields (`added`, `skipped_duplicate`, `unknown_account_count`,
  `unknown_accounts`, `total`) are unchanged.
- **Atomicity preserved:** categorization happens within the existing single
  transaction; any failure rolls the whole upload back (ingestion R6 still holds).

### R3 — The review queue lists and counts the flagged transactions
**As** the admin, **I need** to see exactly what needs categorizing, **so that** I
can clear it.

- **Acceptance (filter):** the existing `GET /api/transactions` gains a
  `needs_review` filter; with it true, the response contains only rows flagged for
  review, and `total` is the count of flagged rows matching any other active
  filters. Ordering, fields, pagination, and the rest of the list contract
  (ingestion R9) are unchanged. The `needs_review` flag itself is included in each
  returned transaction so the UI can render queue state.
- **Acceptance (count):** the flagged count is observable (the `total` of the
  `needs_review=true` query) so the UI can show a "Review (N)" badge.
- **Read auth:** reading the list (with or without the filter) requires
  authentication, any role (unchanged from ingestion R9/R10). The *fix* and *rule*
  actions are admin-only (R4, R5).

### R4 — A single transaction can be categorized by hand (sticky)
**As** the admin, **I need** to assign a category to a flagged transaction, **so
that** I can clear it without writing a rule.

- **Acceptance:** an admin endpoint sets one transaction's category to a chosen
  category: the effective category becomes that category, the source becomes
  `manual`, `needs_review` becomes false. The endpoint is the public contract the
  review UI posts to.
- **Acceptance (sticky):** a `manual` transaction is **never** altered by any later
  rule create/edit/sweep (R6) or re-upload (R2) — its category, source, and
  `needs_review` survive untouched even when a newly created rule's pattern would
  match it.
- **Acceptance (validation):** categorizing to a non-existent category id is
  rejected 400 with no write; targeting a non-existent transaction id is 404.
- **Acceptance (authz/CSRF):** the endpoint requires the **admin** role (viewer →
  403, anonymous → 401) and rejects cross-origin requests (403); in every rejected
  case nothing is written. (Reuses `require_admin` + `is_cross_origin`.)

### R5 — Rules are fully manageable (CRUD), admin-only
**As** the admin, **I need** to view and manage rules, **so that** I control how
categorization behaves.

- **Acceptance (list):** an admin endpoint returns all rules — each with id,
  pattern, target category (id and name), account/amount conditions, priority,
  confidence, and active flag — so the editor can render them.
- **Acceptance (create):** an admin endpoint creates a rule from a pattern
  (required, non-empty after trim), a category id (required, must exist), and
  optional account/amount conditions, priority, confidence, and active flag. When
  omitted, the **defaults are fixed** (so R1 ordering is deterministic across
  builds): **priority `0`** (below the seeded base rules, so a hand-made rule does
  not silently outrank seeded ones — the admin sets a higher priority to override),
  **confidence `100`**, **active true**, and conditions absent (NULL). It returns
  the created rule. Creating a rule
  whose pattern duplicates an existing rule's pattern (case-insensitive, same
  conditions) is rejected 400. Creating against a non-existent category is 400.
  **A successful create triggers the sweep (R6).**
- **Acceptance (update):** an admin endpoint edits a rule's pattern, category,
  conditions, priority, confidence, or active flag; editing a missing rule is 404;
  editing a pattern to collide with another rule is 400. **A successful update
  triggers the sweep (R6).**
- **Acceptance (delete):** an admin endpoint deletes a rule; deleting a missing
  rule is 404. **Delete does not run the sweep and does not retroactively alter any
  transaction** — rows previously categorized by the deleted rule keep their
  category (data-preservation; matches legacy "deleting a rule does not affect
  existing transactions").
- **Acceptance (authz/CSRF):** every rules endpoint requires the **admin** role
  (viewer → 403, anonymous → 401) and mutations reject cross-origin requests
  (403); in every rejected case nothing is written.

### R6 — Saving a rule re-categorizes the open transactions (the sweep)
**As** the treasurer, **I need** a new or corrected rule to reach the transactions
already in the store, **so that** I don't have to re-upload to apply it.

- On a successful rule **create** or **update**, the engine re-evaluates the full
  active rule set against **every open transaction** (source `auto` **or**
  `needs_review` — see Key terms) and writes the new verdict to each:
  - a row that now matches a rule → that rule's category, source `auto`, the rule's
    confidence, `needs_review` false;
  - a row that now matches no rule → uncategorized, source unset, `needs_review`
    true.
- **Acceptance (reaches stored rows):** given a flagged transaction in the store,
  creating a rule whose pattern matches it causes it to become categorized
  (`needs_review` false) **without any re-upload**; the review count drops.
- **Acceptance (manual untouched):** given a transaction a human categorized to
  category X (source `manual`), creating a rule whose pattern matches it but
  targets category Y leaves the transaction on X, source `manual`, unchanged.
- **Acceptance (migrated history untouched):** given a transaction with a category
  set but source unset (as migrated production rows are), creating a rule whose
  pattern matches it but targets a different category leaves it unchanged — it is
  not open.
- **Acceptance (corrects earlier auto):** given a transaction auto-categorized to X
  by rule A, editing rule A so it no longer matches (or adding a higher-priority
  rule B that matches) moves the transaction to the new verdict (re-flagged for
  review, or category Y) — because `auto` rows are open.
- **Acceptance (idempotent):** running the sweep twice in a row produces the same
  transaction states as running it once.
- **Atomicity:** the sweep is a single DB transaction; a failure leaves all
  transactions in their pre-sweep state.

### R7 — Rule-suggestion-on-fix offers a smart-stripped, editable pattern
**As** the admin, **I need** a good starting pattern when I turn a fix into a rule,
**so that** the rule generalizes beyond this one transaction without my hand-editing
every time.

- The engine exposes a deterministic `suggest_pattern(description)` used by an
  admin endpoint the review UI calls when the admin chooses "Create rule."
- **Suggestion heuristic (the contract):** split the description on whitespace;
  **drop any token containing 3 or more digit characters** (invoice numbers, IDs,
  long date codes); collapse the remaining tokens with single spaces and trim. If
  the result is shorter than 3 characters, fall back to the original trimmed
  description.
- **Acceptance:** `"SEATTLE UTILITIES BILL 12345" → "SEATTLE UTILITIES BILL"`;
  `"ACH PYMT 0099283 R YOUNG" → "ACH PYMT R YOUNG"`; `"Check 1042" → "Check"`;
  `"NWEDI-291390275"` (one token, ≥3 digits, would strip to empty) → falls back to
  `"NWEDI-291390275"`; `"Visa 12"` (token has only 2 digits) → `"Visa 12"`.
- The suggestion is only a **default**: the create-rule flow always lets the admin
  edit the pattern before saving (R5 validation still applies — duplicates and bad
  categories are rejected). The suggestion never auto-creates a rule.

### R8 — Internal transfers are an ordinary high-priority rule (no special code)
**As** the association, **I need** internal transfers categorized consistently,
**so that** later transfers-excluded reporting is correct — without bespoke,
hard-to-maintain transfer logic.

- The engine has **no** built-in transfer/ account-number special case. Internal
  transfers are categorized by a normal, high-priority rule whose target is the
  existing **Transfers** (type `Internal`) category. **The rule is pinned:** pattern
  **`"Transfer"`** (case-insensitive substring, per R1), **priority `200`** (above
  the seeded base rules' `100`, so it outranks them), confidence `100`, active. The
  pattern and priority are fixed here because a `@frozen` test depends on a transfer
  description matching it.
- **Acceptance (fresh DB):** on an empty database, the seeded base rule set includes
  the transfer rule (high priority, above the ordinary base rules), so a
  transfer-description row is auto-categorized to Transfers on upload. There is
  **exactly one** transfer rule after seeding, and re-running startup adds no more.
- **Acceptance (existing DB):** because legacy detected transfers in code (so a
  migrated production rules table has no transfer rule), the migration (R9)
  **idempotently inserts** the transfer rule if absent, and never inserts a
  duplicate on re-run.
- **Seed/migration ordering (correctness trap — design note):** startup runs
  migrations **before** seed, and the existing seed inserts its base rules only
  when `categorize_rules` is *empty* (all-or-nothing guard, to protect treasurer
  edits). Therefore the migration's transfer insert must **not** fire on a fresh
  empty `categorize_rules` (doing so would make the seed see a non-empty table and
  skip every base rule). The split is: the **seed** owns the transfer rule on a
  fresh DB (it is added to the seeded base rule set, inserted in the same
  empty-table branch as the others); the **migration** inserts the transfer rule
  only into an **already-populated** `categorize_rules` that lacks it (the migrated
  production case, where seed early-returns because categories already exist). The
  two paths are mutually exclusive by DB state, so the rule is created exactly
  once on every database.
- **Acknowledged tradeoff (edge case, not a defect):** a broad transfer pattern can
  over-match an external "transfer"; the remedy is the priority system — the admin
  adds a higher-priority override rule. This is the owner's chosen design
  (transfers = a rule), recorded so it isn't mistaken for a bug.

### R9 — One additive, idempotent schema migration
**As** the operator, **I need** the schema change to apply cleanly to both a fresh
DB and the migrated production DB, **so that** deploy is safe and repeatable.

- A new migration (the next version after the existing ones) **additively**:
  - adds the optional rule-condition columns to `categorize_rules` (account,
    amount-min, amount-max — all nullable);
  - adds the per-transaction categorization-source marker to `transactions`
    (nullable, default unset);
  - inserts the transfer rule (R8) if absent **and** `categorize_rules` is already
    populated (the migrated-production guard — see R8 ordering note), guarded
    further on the **Transfers** category existing (no-op if it somehow doesn't);
  - **flags the migrated backlog:** sets `needs_review` true on every transaction
    that is **uncategorized** at migration time (`category_id IS NULL`), so the
    historical uncategorized rows surface in the review queue for cleanup. (This
    leaves migrated *categorized* rows untouched — they keep their category, stay
    `needs_review` false, and stay frozen.)
- **Acceptance (idempotent):** applying migrations to an already-migrated database
  is a no-op — no duplicated transfer rule, no double-flagging, no error, existing
  data unchanged. (Re-running is gated by the `schema_migrations` version, so the
  flag-and-insert run at most once.)
- **Acceptance (preserves categorized history):** existing **categorized**
  transactions keep their categories and `needs_review` false; because the source
  marker defaults unset, every pre-existing categorized row is automatically **not
  open** (R6) — migrated categorizations are frozen with no data backfill required.
- **Acceptance (surfaces uncategorized history):** an existing transaction with no
  category becomes `needs_review` true after migration and therefore appears in the
  `needs_review` queue (R3) and is **open** to the sweep (R6) — a later rule or a
  manual fix can clear it.
- The migration follows foundation's versioned-migration mechanism (one new
  version entry; `IF NOT EXISTS` / guarded `ADD COLUMN`); it is **not** a
  destructive rebuild.

### R10 — Authorization and CSRF are enforced server-side (reuse foundation)
- **Acceptance:** all rule mutations (create/update/delete) and the
  single-transaction categorize endpoint require the **admin** role and reject
  cross-origin requests (403); a viewer gets 403, an anonymous caller 401, and no
  write occurs in any rejected case. Role is taken only from the verified session
  (reuses `require_admin`; never from client input).
- **Acceptance:** the rules **list** and the suggestion endpoint require the admin
  role (they back an admin-only UI). The transactions list (with the `needs_review`
  filter) requires authentication, any role (unchanged).

### R11 — The dashboard gains a review queue and a rules editor (admin-only)
**As** the admin, **I need** to do categorization in the app, **so that** the loop
is a real workflow, not just an API.

- **Acceptance (review queue):** an **admin** sees a review section listing the
  flagged transactions (fed by `GET /api/transactions?needs_review=true`) with a
  **count badge**. For each item the admin can pick a category and **Save** (posts
  the categorize endpoint, R4) or **Create rule** (R5/R7): choosing "Create rule"
  reveals an inline form pre-filled with the suggested pattern (fetched from the
  suggestion endpoint) and the chosen category, editable before submit; on submit
  it posts the rule and the queue refreshes to reflect the sweep. A **viewer** sees
  no review section.
- **Acceptance (rules editor):** an **admin** sees a rules table (pattern, category,
  conditions, priority, active) with controls to create, edit, enable/disable, and
  delete rules; each action calls the corresponding endpoint and the table
  refreshes. A **viewer** sees no rules editor.
- **Acceptance (a11y, WCAG 2.1 AA, scoped):** the review and rules tables use real
  header cells (`<th scope="col">`); the category selects, pattern input, and rule
  fields have associated labels; the review count badge's text is available to
  assistive tech. (Scope note under Standards.)
- The category options for the selects require category **id + name**; this feature
  adds `id` to the `/api/reference` categories payload (additive, backward
  compatible) so existing consumers are unaffected.

### Out of scope (restated from declaration)
- Any LLM/AI categorization; regex or boolean-composed patterns.
- A standalone "re-categorize all" button or any mode that overwrites `manual`
  categorizations; bulk category editing beyond the single-row review fix.
- Sweeping (re-categorizing) migrated *categorized* transactions — those stay
  frozen. (Migrated *uncategorized* rows are flagged into the review queue by the
  migration, R9, and are cleanable from there.)
- Budget, dues, transfers-excluded reporting, charts, PDF (slices 5–8); editing or
  deleting transaction amounts/dates.

---

## Part 2 — Design

### D1 — Categorization engine (new, pure logic) — `backend/app/categorize.py`
A plain, testable module with no FastAPI or DB imports (mirrors `app/ingest.py`).
The function/dataclass **names are `@scaffolding`**; the **behavior** is the
contract. It exposes, in substance:

- A rule representation (id, pattern, category_id, account condition,
  amount_min, amount_max, priority, confidence, active) the router builds from DB
  rows and passes in — the engine never reads the DB.
- `match(description, account_name, debit, credit, rules) -> result` — returns the
  winning rule's `(category_id, confidence, source="auto")` or a "needs review"
  result (`category_id=None`, `needs_review=True`). Ordering and the all-conditions
  match test per R1; inactive rules excluded; amount uses the signed-agnostic
  magnitude (Key terms).
- `suggest_pattern(description) -> str` — the R7 heuristic (drop tokens with ≥3
  digits; collapse; ≥3-char fallback).

**Behavioral properties:** R1 (ordering, substring, account, amount, no-match), R7
(suggestion). **This and the sweep (D4) are the highest-value test surface.**

### D2 — Schema migration (additive) — extends `backend/app/migrations.py`
One new version appended to `MIGRATIONS` (foundation's versioned, idempotent
mechanism — `Reuses pattern`). It adds nullable condition columns to
`categorize_rules` (account / amount-min / amount-max), a nullable source marker to
`transactions`, and an idempotent insert of the transfer rule (R8) **guarded to
fire only when `categorize_rules` is already populated** (the migrated-production
case) so it never pre-empts the seed's base-rule insertion on a fresh DB (see R8
"Seed/migration ordering"). `ADD COLUMN` is guarded against re-application by the
existing `schema_migrations` version gate (each version runs at most once). No
destructive statements (R9). The fresh-DB transfer rule is added to `app/seed.py`'s
seeded rule set, with a high priority so it outranks the ordinary base rules.

### D3 — Rules router (new) — `backend/app/routers/rules.py`
Registered in `app.main.create_app` alongside the existing routers. Admin-only
(`require_admin`) with the same-origin guard on mutations (reuses
`app.auth.is_cross_origin`, exactly as the transactions router does). Endpoints
(paths/JSON are the **public contract the frontend consumes** → `@frozen` behavior;
exact path spellings noted are stable):
- `GET /api/rules` — list rules with category names joined for display.
- `POST /api/rules` — validate (non-empty pattern, existing category, no duplicate
  per R5), insert, **call the sweep (D4)**, return the created rule (201).
- `PATCH /api/rules/{id}` — validate (404 if missing, 400 on duplicate/bad
  category), update, **call the sweep**, return the updated rule.
- `DELETE /api/rules/{id}` — delete (404 if missing); **no sweep, no transaction
  changes** (R5).
- `GET /api/rules/suggest?description=...` — return `{pattern: suggest_pattern(...)}`
  (R7). The path is `@scaffolding`; the returned suggestion behavior is `@frozen`.

Reuses `get_connection` (FK enforcement on). Rule rows for the engine and the sweep
are read here and passed into `categorize`.

### D4 — Categorize-on-ingest + sweep — extends `backend/app/routers/transactions.py`
- **Upload path (R2):** after `parse_csv` and inside the existing single insert
  transaction, load the active rules once, run `categorize.match` on each newly
  inserted row, and persist the verdict (category, source, confidence,
  `needs_review`) on that row. Duplicate-skipped rows are untouched. The summary
  gains `categorized` / `needs_review` counts; existing fields unchanged. The whole
  thing stays atomic (ingestion R6).
- **Sweep (R6):** a function (in `app.categorize` or a thin router helper) that, in
  one transaction, selects the **open** rows (source `auto` OR `needs_review`),
  re-runs `match` against the current active rules, and writes each new verdict;
  `manual` and migrated rows are excluded by the open-set query. Idempotent by
  construction (it recomputes from the rules, not from prior state). Called by the
  rules create/update endpoints (D3).
- **Single-transaction categorize (R4):** `PATCH /api/transactions/{id}` (admin,
  same-origin) sets the chosen category, marks source `manual`, clears
  `needs_review`; validates category existence (400) and row existence (404).
- **List filter (R3):** `GET /api/transactions` gains an optional `needs_review`
  filter and includes the `needs_review` flag per row; ordering/pagination/total
  contract unchanged.

**Reuses pattern:** foundation auth guards (`require_admin`/`require_auth`),
`is_cross_origin` CSRF defense, `get_connection`, the versioned-migration mechanism,
and the slice-3 upload/dedup/atomic-insert path (this feature extends it, it does
not replace it).

### D5 — Reference payload (additive) — extends `backend/app/routers/reference.py`
The `/api/reference` categories array gains an `id` field per category (currently
`name` + `type`). Additive and backward compatible; the review/rules selects use it
to post `category_id`.

### D6 — Dashboard UI — extends `frontend/src/App.tsx`
Within the admin-gated area of `DashboardShell` (parallel to the existing upload
control), add:
- a **review queue**: the flagged-transactions list with a count badge, a per-row
  category select with **Save** (PATCH categorize) and **Create rule** (fetch
  suggestion → inline editable pattern + category → POST rule → refresh);
- a **rules editor**: a rules table with create/edit/enable-disable/delete.
Reuses the existing `fetch(..., { credentials: "include" })` convention and role
plumbing. DOM/test-ids are `@scaffolding`; the behaviors (admin-only visibility,
correct endpoint calls, queue/table refresh, real `<th scope="col">` headers,
labeled controls, `aria`-exposed count) are the contract.

### D7 — Test wiring (project-level convention; applied by `/build`, recorded here)
Per `constitution.md` § Testing and the slice-3 precedent:
- **pytest:** `/build` appends `"../features/rules-categorization-004/tests/backend"`
  to `backend/pyproject.toml`'s `testpaths`. Test-module basenames are unique across
  features (this feature uses `test_categorize_*`, `test_review_*`, `test_rules_*`,
  `test_migration_v3.py`). Each backend test dir resolves the repo root from its own
  location (`parents[4]`) and puts `backend/` on `sys.path` — never an absolute path.
- **Vitest:** `/build` extends `frontend/vite.config.ts`'s `test.include` to cover
  `"../features/rules-categorization-004/tests/frontend/**/*.test.{ts,tsx}"`. Frontend
  tests import the app via the `@/` alias and pull React/testing-library through the
  external-dep aliases already configured.

---

## Coverage

| Requirement / seam | Test(s) |
|---|---|
| R1 ordering: priority then pattern-length then id | `test_categorize_engine.py::test_order_priority`, `::test_order_pattern_length`, `::test_order_id_tiebreak` |
| R1 substring, case-insensitive; non-substring no match | `test_categorize_engine.py::test_substring_case_insensitive` |
| R1 account condition narrows match | `test_categorize_engine.py::test_account_condition` |
| R1 amount condition (range, min-only, max-only, credit magnitude) | `test_categorize_engine.py::test_amount_condition` |
| R1 inactive rules skipped; no-match → needs review | `test_categorize_engine.py::test_inactive_skipped`, `::test_no_match_needs_review` |
| R2 matched row categorized (auto, conf, not flagged) on upload | `test_categorize_on_ingest.py::test_upload_matched_row_categorized` |
| R2 unmatched row flagged needs_review on upload | `test_categorize_on_ingest.py::test_upload_unmatched_row_flagged` |
| R2 re-upload doesn't re-categorize existing rows | `test_categorize_on_ingest.py::test_reupload_does_not_recategorize` |
| R2 summary gains categorized / needs_review counts | `test_categorize_on_ingest.py::test_upload_summary_categorization_counts` |
| R3 needs_review filter returns only flagged; total = count | `test_review_and_fix.py::test_review_filter_and_count` |
| R3 list still requires auth; viewer can read | `test_review_and_fix.py::test_review_list_auth` |
| R4 manual fix sets category + clears review; sticky vs sweep | `test_review_and_fix.py::test_manual_fix_sets_and_sticks` |
| R4 bad category 400 / bad txn 404, no write | `test_review_and_fix.py::test_fix_validation` |
| R4 fix authz (viewer 403 / anon 401) + cross-origin 403 | `test_review_and_fix.py::test_fix_authz`, `::test_fix_cross_origin` |
| R5 list/create/update/delete happy paths | `test_rules_api.py::test_crud_lifecycle` |
| R5 duplicate pattern 400; bad category 400; missing 404 | `test_rules_api.py::test_create_validation`, `::test_update_missing_404` |
| R5 delete does not alter existing transactions | `test_rules_api.py::test_delete_preserves_transactions` |
| R5/R10 rules mutations authz + cross-origin | `test_rules_api.py::test_rules_authz`, `::test_rules_cross_origin` |
| R6 create rule sweeps stored flagged row → categorized | `test_rules_api.py::test_create_rule_sweeps_open_rows` |
| R6 manual row untouched by matching rule | `test_review_and_fix.py::test_manual_fix_sets_and_sticks` |
| R6 migrated (source-unset categorized) row untouched | `test_rules_api.py::test_sweep_skips_migrated_categorized` |
| R6 edit corrects earlier auto; higher-priority reroutes | `test_rules_api.py::test_sweep_corrects_auto` |
| R6 sweep idempotent | `test_rules_api.py::test_sweep_idempotent` |
| R7 suggestion heuristic (all worked examples + fallback) | `test_categorize_engine.py::test_suggest_pattern`; endpoint `test_rules_api.py::test_suggest_endpoint` |
| R8 transfer rule categorizes a transfer on upload (seed) | `test_categorize_on_ingest.py::test_transfer_rule_categorizes` |
| R9 migration idempotent; transfer rule not duplicated (seed path) | `test_migration_v3.py::test_migration_idempotent_no_dup_transfer` |
| R9 migrated-DB branch: transfer inserted into a populated table; flags backlog; freezes categorized; idempotent | `test_migration_v3.py::test_migrated_db_branch` |
| R9 condition columns + source marker usable; categorized history preserved | `test_migration_v3.py::test_conditions_and_source_usable`, `::test_existing_categories_preserved` |
| R2 matched row stores the rule's confidence | `test_categorize_on_ingest.py::test_upload_matched_row_categorized` |
| R10 rules list / suggest require admin | `test_rules_api.py::test_rules_authz` |
| R11 review queue: admin sees + count; viewer doesn't; Save/Create-rule call endpoints | `ReviewQueue.test.tsx` |
| R11 rules editor: admin sees + CRUD calls; viewer doesn't; a11y headers | `RulesEditor.test.tsx` |

---

## Adversarial gate

**Mode:** independent clean-context sub-agent (general-purpose), run once against
the drafted spec and tests. Six findings returned (2 HIGH, 3 MEDIUM, 1 LOW) — no
security findings, so no security re-gate. The gate explicitly cleared the highest-
risk surfaces: the sweep's manual + migrated-history protection (both proven), no
slice-3 (ingestion-003) test collision from categorize-on-ingest, authz/CSRF
coverage on every mutating endpoint, and the schema reality (v1 already provides
`confidence`/`auto_category_id`/`priority`, so no phantom columns). All six findings
dispositioned **fixed**; **no risks acknowledged** (the constitution's Acknowledged
risks table is unchanged for this feature). One product decision surfaced alongside
the findings and was decided by the owner: migrated *uncategorized* transactions
**are** flagged into the review queue (R9), while migrated *categorized* rows stay
frozen.

- **F1 (HIGH, integrity) — the seeded transfer rule's pattern was unspecified while
  a `@frozen` test pins a transfer description to it.** *Fixed.* R8/D2 now pin the
  transfer rule: pattern `"Transfer"`, priority `200` (above the base rules' `100`).
- **F2 (HIGH, integrity) — the default priority of an admin-created rule was
  unspecified, making R1's priority-first ordering non-deterministic across builds.**
  *Fixed.* R5 now pins created-rule defaults: priority `0`, confidence `100`, active
  true, conditions NULL.
- **F3 (MEDIUM, coverage) — the migrated-production transfer-insert branch (the
  ordering-trap branch) had zero test coverage; only the seed branch was tested.**
  *Fixed.* `test_migration_v3.py::test_migrated_db_branch` stages a populated pre-v3
  DB and asserts the migration inserts exactly one transfer rule, flags the
  uncategorized backlog, freezes categorized rows, and is idempotent on re-run.
- **F4 (MEDIUM, coverage/integrity) — amount-magnitude semantics were ambiguous when
  both debit and credit are present.** *Fixed.* Key terms now pin debit-precedence
  and the zero-magnitude case; `test_categorize_engine.py::test_amount_condition`
  asserts the both-present determinism.
- **F5 (MEDIUM, integrity) — two `@frozen` tests depended on mutable seed contents
  (the `Cintas` rule).** *Fixed.* `test_upload_matched_row_categorized` and
  `test_review_filter_and_count` now create their own rule; only the explicit R8
  transfer-rule test depends on the seed (by design).
- **F6 (LOW, integrity) — a `@scaffolding` engine test pinned the internal
  `confidence` return field.** *Fixed.* The engine test now asserts only category +
  not-flagged; confidence *propagation* is asserted at the DB/ingest layer
  (`test_upload_matched_row_categorized`, a `@frozen` row-level check).
