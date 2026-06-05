# Build deviations — ingestion-003

Honest record of where the build diverged from the spec's design or corrected a
test. The spec's *requirements* were not changed; only provisional interface
detail and two clear test errors.

## Test corrections (frozen tests with a clear error)

### 1. `test_upload_requires_admin` could not observe the anonymous (401) case
- **File:** `tests/backend/conftest.py` (fixtures `admin_client` / `viewer_client`).
- **Symptom:** the assertion `upload(client, content).status_code == 401`
  returned `403`.
- **Root cause:** `viewer_client` was defined as `viewer_client(client)` and
  returned the *shared* `client` fixture after logging in. When a test requests
  both `viewer_client` and `client`, pytest resolves `client` once and hands the
  same instance to both — so the "anonymous" `client` actually carried the
  viewer's session cookie and was forbidden (403), never unauthenticated (401).
  The R10 behavioral assertions (view-only → 403, anonymous → 401) are both
  correct; the fixture wiring just made the anon case unobservable.
- **Correction:** `admin_client` and `viewer_client` now each build their own
  `TestClient` (their own cookie jar) from `make_app()`, all pointed at the same
  `DATABASE_PATH` (migrations + seed are idempotent), so the shared `client`
  fixture stays anonymous when requested alongside them. No test assertion was
  weakened.
- **Spec-authoring lesson:** when a single test exercises multiple auth states,
  the auth fixtures must be independent sessions; deriving a "logged-in" fixture
  from the same shared client fixture the test also injects silently couples
  them and hides one of the states under test.

### 2. `test_includes_all_types` queried a category type the seed never creates
- **File:** `tests/backend/test_transactions_list.py`.
- **Symptom:** `SELECT id FROM categories WHERE type='Transfer' LIMIT 1`
  returned no row, so `.fetchone()[0]` raised `TypeError`.
- **Root cause:** the foundation seed (`backend/app/seed.py`) has no
  `Transfer`-typed category. Its transfer-like category is `"Transfers"` typed
  `Internal` (the schema's `type` CHECK allows both `Transfer` and `Internal`,
  but only `Internal` is seeded). The test assumed a `Transfer` row exists. The
  behavior under test — a transfer/internal-typed transaction is **not** excluded
  from the raw list (transfers-excluded reporting is slice 6) — is unchanged.
- **Correction:** widened the lookup to
  `WHERE type IN ('Transfer', 'Internal')`, which selects the seeded `Internal`
  "Transfers" category. The behavioral assertion (the row appears in the list)
  holds exactly as written.
- **Spec-authoring lesson:** a test that depends on seeded reference data should
  assert against what the seed actually contains. The seed's only transfer
  category is typed `Internal`; pinning `type='Transfer'` baked in a value the
  upstream seed never produces.

## Design refinements (interface detail; behavior unchanged)

### 3. Shared exact-cents converter extracted to `app/money.py`
- **Design said (D1):** "converge on a single shared exact-cents converter (e.g.
  an `app.money` helper or by reusing the existing one) rather than writing a
  second rounding implementation."
- **Done:** added `app/money.py` with `dollars_to_cents(value)` (the canonical
  half-away-from-zero, exact-decimal-string conversion). `app.ingest.to_cents`
  (string input, strips `$`/commas/whitespace, empty → `None`, unparseable →
  `ValueError`) and `app.legacy_import.to_cents` (float input) now both delegate
  to it. Legacy-migration behavior is unchanged (its 42 tests still pass).

### 4. `INGEST_MAX_UPLOAD_BYTES` retained as named in the spec
- D2 flagged the env-var name as "a scaffolding detail `/build` may rename." It
  was kept as-is (the `test_oversize_upload_rejected` test monkeypatches that
  exact name), exposed via `Config.ingest_max_upload_bytes` (default 5,000,000),
  and documented in `backend/.env.example`. No rename was needed.

### 5. Upload size bound: observable behavior pinned; memory-bounding is best-effort
- Per R10's design-intent note, FastAPI's `UploadFile` spools the body to a temp
  file before the handler runs, so the "reject before fully buffering into RAM"
  property is not observable at the test layer. The handler checks the declared
  `Content-Length` first (cheap early reject) and bounds the read
  (`file.read(max_bytes + 1)`) as a backstop; the test pins only the observable
  reject-and-no-insert outcome, which holds.
