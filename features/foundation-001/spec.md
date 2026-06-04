# Spec: Foundation (foundation-001)

The walking-skeleton slice. Establishes auth, persistence, the API layer, the single-app deploy, and the full database schema + reference seed — proven end-to-end and deployed. Later slices add behavior against these seams.

---

## Part 1 — Behavioral requirements

### User Story A — Shared-password login (admin & view-only)
A board member or the treasurer visits the site and logs in with a shared password. The treasurer's password grants the **admin** role; the board password grants the **view-only** role.

**Acceptance criteria**
- **A1** — `POST /api/auth/login` with the admin password returns 200 and establishes a session whose role is `admin`.
- **A2** — `POST /api/auth/login` with the board password returns 200 and establishes a session whose role is `viewer`.
- **A3** — `POST /api/auth/login` with any other password returns 401 and establishes no session.
- **A4** — The session is carried in an `HttpOnly`, `Secure`, `SameSite=Lax` cookie containing a signed token; the response body never contains the raw token or either password hash.
- **A5** — `GET /api/auth/me` returns the current role for a valid session and 401 for no/invalid/expired session.
- **A6** — `POST /api/auth/logout` clears the session cookie; a subsequent `GET /api/auth/me` returns 401.
- **A7** — Passwords are verified against hashes provided via environment/secret (`ADMIN_PASSWORD_HASH`, `BOARD_PASSWORD_HASH`); no plaintext password is stored anywhere in the repo, DB, or logs, and no password hash is ever logged.
- **A8** — State-changing requests (`POST /api/auth/login`, `POST /api/auth/logout`) are rejected with 403 when an `Origin` (or `Referer`) header is present and its origin does not match the app's own origin; requests with no `Origin` header (same-origin navigation / non-browser clients) are allowed. This blocks cross-site CSRF against the auth endpoints while keeping the same-origin SPA working.

### User Story B — Role is server-authoritative
The system decides what a user may do based only on the verified session, never on anything the client asserts.

**Acceptance criteria**
- **B1** — `GET /api/admin/config` returns 200 with app-config data for an `admin` session.
- **B2** — `GET /api/admin/config` returns 403 for a `viewer` session.
- **B3** — `GET /api/admin/config` returns 401 for no session.
- **B4** — A request that supplies a role via header, body, query param, or a tampered/re-signed cookie does **not** gain admin access; role is derived solely from the server-verified token signature.
- **B5** — Authenticated non-admin data endpoints (Story C) are reachable by both `admin` and `viewer`.

### User Story C — Dashboard shell renders real seeded data
A logged-in user sees a dashboard shell that displays data fetched from the seeded database through the API — proving the read path works end-to-end.

**Acceptance criteria**
- **C1** — `GET /api/reference` (auth required, any role) returns the seeded units (with ownership), accounts, and active categories from the database.
- **C2** — `GET /api/reference` returns 401 for no session.
- **C3** — The frontend, after login, renders the dashboard shell populated from `GET /api/reference` (e.g., the 9 units and their ownership %), not hard-coded placeholder data.
- **C4** — Before login (no session), the frontend shows the login screen and does not render the dashboard shell.
- **C5** — A `viewer` session does not see admin-only controls in the shell; an `admin` session does.

### User Story D — Persistence: schema + reproducible reference seed
The database comes up with the full schema and the stable reference data, reproducibly, on a fresh volume.

**Acceptance criteria**
- **D1** — On startup against an empty database file, all schema tables are created via versioned migrations: `transactions`, `categories`, `budgets`, `units`, `accounts`, `categorize_rules`, `unit_past_dues`, `app_config`, plus a migrations-tracking mechanism.
- **D2** — Migrations are idempotent: starting against an already-migrated database makes no further schema changes and does not error.
- **D3** — Seeding inserts the reference data when absent: **9 units** with the specified ownership ratios, **3 accounts** (`****7145`→Savings, `****9242`→Checking, `****9226`→Reserve Fund), the full **category** list, the base **categorize-rules**, the **2025 budget**, and `app_config` defaults (`current_year=2025`).
- **D4** — Seeding is idempotent: running it again does not duplicate rows or overwrite existing values (safe on every startup).
- **D5** — Monetary amounts are stored as exact integer cents (never binary floats); e.g. the 2025 `Dues 101` budget is stored as `595475`. Ownership ratios are stored as exact integer thousandths (per-mille: `0.117 → 117`), never as a binary float.
- **D6** — Seeded values match the reference data model: ownership `101/201/301 = 0.117`, `102/202/302 = 0.104`, `103/203/303 = 0.112`; `Dues 101 = $5,954.75`, `Grounds/Landscaping = $12,000.00`, `Cintas Fire Protection = $1,500.00` (full table in §Seed data).

### User Story E — Single-app deploy with gated health check
A push to `main` builds and deploys one Fly app serving both tiers, and the deploy is only "successful" if the live app is actually reachable.

**Acceptance criteria**
- **E1** — `GET /api/health` returns 200 with a small JSON body (e.g. `{"status":"ok"}`) and verifies database connectivity; it requires no authentication.
- **E2** — The backend serves the built frontend as static assets; unknown non-`/api` routes return the SPA `index.html` (client-side routing), while `/api/*` paths are never shadowed by the static handler.
- **E3** — A GitHub Actions workflow triggered on push to `main` builds the image and deploys to Fly, then performs a **post-deploy health check** that polls `/api/health` and **fails the job** if it does not return 2xx within a bounded retry window.
- **E4** — `fly.toml` declares a mounted volume for the SQLite database, and the database path is configurable via environment (defaulting to the mounted volume path).
- **E5** — `.env.example` lists every required key (`ADMIN_PASSWORD_HASH`, `BOARD_PASSWORD_HASH`, `SESSION_SECRET`, `DATABASE_PATH`) with no values; `FLY_API_TOKEN` is documented as a CI/deploy secret.

### Edge cases & failure modes
- **EC1 — Missing required secret at startup**: if `ADMIN_PASSWORD_HASH`, `BOARD_PASSWORD_HASH`, or `SESSION_SECRET` is absent, the app fails fast at startup with a clear error rather than booting in an insecure state (e.g. accepting any password or signing with a default key).
- **EC2 — Brute-force login**: the limiter counts **failed** attempts per client IP within a rolling window; once the threshold is exceeded further attempts return 429 for the remainder of the window. A *correct* password is never throttled while under the threshold, successful logins do not count toward the limit, and the window resets so the limiter never locks out a correct password indefinitely. Rate-limit state is held in-memory per app instance (so each `create_app()` starts clean). Threshold and window are configurable via `LOGIN_MAX_ATTEMPTS` / `LOGIN_WINDOW_SECONDS` with sane defaults.
- **EC3 — Expired/tampered token**: an expired or signature-invalid cookie is treated as no session (401), not a server error.
- **EC4 — Read-only DB / volume not mounted**: `/api/health` reports unhealthy (non-2xx) if the database is unreachable, so the deploy health check fails loudly instead of shipping a broken app. *(Follow-up, not this slice: the DB probe has no explicit timeout; a hung/locked SQLite file would surface as a deploy-gate retry timeout rather than a clean 503 — acceptable for now given a local single-file SQLite.)*
- **EC5 — Empty database on first boot**: first startup on a fresh volume runs migrations then seed, leaving a ready database with no manual step.

### Out of scope (this slice)
Legacy production-DB importer (own slice); CSV ingestion/dedup; rules categorization engine, review queue, rule-suggestion; budget management UI and YTD proration; dashboard charts, income/expense summaries, dues tables, PDF/CSV export; dues-by-unit math; My Account statement; automated database backup (volume + schema land here; scheduled backup is a follow-up); full WCAG 2.1 AA audit (fundamentals only this slice).

---

## Part 2 — Design

### Components & seams
- **Frontend (React + TS + Vite + Tailwind + shadcn/ui)** — login screen and a dashboard shell. Auth state derived from `GET /api/auth/me`. Fetches `GET /api/reference` to render seeded data. Built to static assets consumed by the backend. *Reuses pattern:* constitution frontend stack (new project — no existing module to reuse).
- **API layer (FastAPI)** — routers for `auth`, `admin`, `reference`, `health`, plus a static-file handler with SPA fallback. A dependency resolves the session cookie → verified role; admin routes depend on a "require admin" guard.
- **Auth & session** — login verifies the submitted password against the two env-provided hashes using the hashing library's constant-time verify; on success issues a signed token (role + expiry) set as an `HttpOnly`/`Secure`/`SameSite=Lax` cookie. The signing secret comes from `SESSION_SECRET`. Role is always read from the verified token. Login attempts are rate-limited.
- **Persistence & migrations** — a SQLite connection at `DATABASE_PATH` (default: the Fly volume mount). A migration runner applies ordered, versioned migrations and records applied versions; an idempotent seeder loads reference data. Both run at startup. Money stored as integer cents; ownership stored exactly.
- **Deploy substrate** — Dockerfile (multi-stage: `pnpm build` the frontend, assemble the backend, final image runs `uvicorn` and serves the built assets). `fly.toml` with a mounted volume and a `[checks]`/health configuration. GitHub Actions workflow: build → `flyctl deploy --remote-only` → poll `/api/health` and fail on timeout.

### Behavioral constraints (properties, not signatures)
- **BC1** — Role is never sourced from client-controlled input; only a valid token signature (verified with `SESSION_SECRET`) grants a role. Tampering with the cookie invalidates the session.
- **BC2** — No secret value (password, hash, signing key, raw token) appears in any response body, log line, or committed file. Only `.env.example` (keys, no values) is committed.
- **BC3** — The app refuses to start without its required secrets (EC1) rather than falling back to insecure defaults.
- **BC4** — Startup is idempotent and self-healing: migrations + seed converge an empty *or* already-initialized database to the same ready state without duplication or data loss.
- **BC5** — `/api/health` reflects real readiness (DB reachable), because the deploy gate depends on it telling the truth (EC4).
- **BC6** — Static-asset serving must not shadow `/api/*` routes, and client-route deep links resolve to the SPA entry (E2).
- **BC7** — Monetary values cross the API boundary as exact integer cents with a documented unit; no binary-float money anywhere. Ownership ratios are likewise stored exactly as integer thousandths (per-mille: `0.117 → 117`) and exposed by the API as the decimal ratio — never as a binary float in storage.
- **BC8** — State-changing POST endpoints reject cross-origin requests (A8) and accept a JSON body only; an HTML-form-encoded body (which cross-site forms are limited to) does not drive a state change. Together these block form- and script-based CSRF without a token, consistent with the same-origin SPA + `SameSite=Lax` cookie.
- **BC9** — No secret (password, hash, signing key, raw token) is written to any log channel at any level, because logs ship to Fly and persist (OWASP A09).

### Standards
- **OWASP Top 10** (authoritative for this slice): server-side authz (A01), no secrets in code or logs (A02/A05/A09), brute-force throttling (A07), signed-token integrity (A08), CSRF defense on state-changing endpoints (A01). CSRF is defended by an explicit same-origin check (A8/BC8) plus JSON-only bodies and a `HttpOnly; Secure; SameSite=Lax` cookie — not by `SameSite` alone.
- **WCAG 2.1 AA — fundamentals only** (per owner decision): the login form has programmatic labels, visible focus, full keyboard operability, sufficient contrast, and semantic landmarks. Full AA audit deferred until real reporting surfaces exist.
- **OpenAPI**: endpoints in this slice (`/api/health`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`, `/api/reference`, `/api/admin/config`) are conventional REST and surface through FastAPI's generated schema.

### Contracts (named intentionally — the testable interface)
These are the public shapes the test suite pins; everything else is `/build`'s choice.
- **App factory:** `app.main:create_app() -> FastAPI` returns a fully-configured app that runs migrations + seed on startup; `app.main:app = create_app()` is the uvicorn target. The factory reads config from the environment at call time.
- **Config (env):** `DATABASE_PATH` (SQLite file path), `ADMIN_PASSWORD_HASH` and `BOARD_PASSWORD_HASH` (**bcrypt** hashes), `SESSION_SECRET` (JWT signing key) — all four required; absence ⇒ fail-fast (EC1). Optional: `STATIC_DIR` (built-frontend path, defaults to bundled build), `LOGIN_MAX_ATTEMPTS` + `LOGIN_WINDOW_SECONDS` (rate-limit tuning).
- **Health probe seam:** `app.db.check_connection() -> bool` is true when the database is reachable; `/api/health` returns 503 when it is not (EC4).
- **Session:** a **JWT (HS256)** signed with `SESSION_SECRET`, carried in cookie **`dwcoa_session`** with `HttpOnly; Secure; SameSite=Lax`. Claims include `role` (`"admin"` | `"viewer"`) and `exp`. Role is read only from the verified JWT.
- **Endpoints:** `GET /api/health`, `POST /api/auth/login` (`{"password": "..."}`), `POST /api/auth/logout`, `GET /api/auth/me`, `GET /api/reference`, `GET /api/admin/config`.
- **Money over the API:** integer cents (e.g. a budget amount is `595475`, not `5954.75` or a float).
- **Frontend:** the app's root component is the default export of `@/App`; it determines auth via `GET /api/auth/me`, renders the login form when unauthenticated and the dashboard shell when authenticated, and marks admin-only UI with `data-testid="admin-only"` (rendered only for an `admin` session). The login password field is programmatically labeled.

### Seed data (authoritative for tests)
**Units** (number → ownership ratio): 101→0.117, 102→0.104, 103→0.112, 201→0.117, 202→0.104, 203→0.112, 301→0.117, 302→0.104, 303→0.112.
**Accounts**: `****7145`→Savings, `****9242`→Checking, `****9226`→Reserve Fund.
**Categories**: Dues 101–303 (Income), Interest income (Income), Bulger Safe & Lock, Cintas Fire Protection, Common Area Cleaning, Fire Alarm, Grounds/Landscaping, Homeowners Club Dues, Insurance Premiums, Seattle City Light, Other, Reserve Expenses (Expense), Reserve Contribution (Transfer), Transfers (Internal) — with default account and timing per the reference data model.
**2025 budget (annual, stored as integer cents)**: Dues 101/201/301 = 595475; Dues 102/202/302 = 529311; Dues 103/203/303 = 570027; Interest income = 2600; Reserve Contribution = 1800000; Bulger Safe & Lock = 40000; Cintas Fire Protection = 150000; Common Area Cleaning = 270000; Fire Alarm = 330000; Grounds/Landscaping = 1200000; Other = 750000; Insurance Premiums = 450000; Seattle City Light = 600000.
**Base categorize-rules**: the reference rule set (utility/vendor patterns + dues-by-owner patterns) as in `reference/.../data-model.md`.
**app_config**: `current_year=2025`, `last_upload_at=''`.

---

## Part 3 — Coverage

| Requirement / seam | Test(s) |
|---|---|
| A1–A3 login by role + bad password | `test_auth.py::test_login_admin_role`, `::test_login_viewer_role`, `::test_login_bad_password_401` |
| A4 cookie flags, no token/hash in body | `test_auth.py::test_login_sets_secure_httponly_cookie`, `::test_login_body_has_no_secrets` |
| A5 me endpoint | `test_auth.py::test_me_returns_role`, `::test_me_no_session_401` |
| A6 logout | `test_auth.py::test_logout_clears_session` |
| A7 hashes from env, no plaintext | `test_auth.py::test_passwords_verified_against_env_hashes`; `test_repo_hygiene.py::test_no_plaintext_secrets_committed` |
| A8 / BC8 CSRF same-origin guard | `test_csrf.py::test_cross_origin_post_rejected`, `::test_matching_origin_allowed`, `::test_no_origin_allowed` |
| BC9 no secret in logs | `test_auth.py::test_no_secret_in_logs` |
| B1–B3 admin endpoint gating | `test_authz.py::test_admin_config_admin_200`, `::test_admin_config_viewer_403`, `::test_admin_config_anon_401` |
| B4 role not from client input | `test_authz.py::test_role_header_ignored`, `::test_tampered_cookie_rejected` |
| B5 shared endpoints both roles | `test_authz.py::test_reference_allows_both_roles` |
| C1–C2 reference endpoint | `test_reference.py::test_reference_returns_seeded_data`, `::test_reference_requires_auth` |
| C3 shell renders seeded data | `DashboardShell.test.tsx::renders_units_from_api` |
| C4 login shown when unauthenticated | `Login.test.tsx::shows_login_when_unauthenticated` |
| C5 role-gated controls | `DashboardShell.test.tsx::hides_admin_controls_for_viewer`, `::shows_admin_controls_for_admin` |
| D1–D2 migrations create tables, idempotent | `test_migrations.py::test_all_tables_created`, `::test_migrations_idempotent` |
| D3–D4 seed presence + idempotency | `test_seed.py::test_reference_data_seeded`, `::test_seed_idempotent` |
| D5–D6 money as cents, exact seed values | `test_seed.py::test_budget_amounts_in_cents`, `::test_ownership_values`, `::test_money_is_integer_cents`, `::test_ownership_stored_exactly` |
| E1 health endpoint | `test_health.py::test_health_ok`, `::test_health_no_auth_required` |
| E2 static serving / SPA fallback / api not shadowed | `test_static.py::test_spa_fallback`, `::test_api_routes_not_shadowed`, `::test_unknown_api_route_not_shadowed` |
| E3 deploy workflow gates on health check | `test_deploy_workflow.py::test_workflow_has_gated_health_check` |
| E4 volume + configurable db path | `test_deploy_workflow.py::test_flytoml_declares_volume`; `test_migrations.py::test_db_path_from_env` |
| E5 .env.example completeness | `test_repo_hygiene.py::test_env_example_lists_required_keys` |
| EC1/BC3 fail-fast on missing secret | `test_startup.py::test_missing_secret_fails_fast` |
| EC2 brute-force rate limit + anti-lockout | `test_auth.py::test_login_rate_limited`, `::test_successful_logins_not_throttled`, `::test_correct_password_succeeds_under_threshold` |
| EC3 expired/tampered token → 401 | `test_authz.py::test_expired_token_401`, `::test_tampered_cookie_rejected` |
| EC4/BC5 health reflects DB readiness | `test_health.py::test_health_unhealthy_when_db_unreachable` |
| EC5 fresh-boot migrate+seed | `test_startup.py::test_fresh_boot_ready` |
| WCAG fundamentals (login) | `Login.test.tsx::has_labeled_inputs_and_focus` |

---

## Adversarial gate

**Mode:** independent clean-context review (fresh `general-purpose` sub-agent; read-only). Single pass, no loop.

**Findings & disposition:**

| # | Sev | Lens | Finding | Disposition |
|---|-----|------|---------|-------------|
| 1 | MEDIUM | Security | CSRF dismissed in prose; no control designed or tested on `POST /login` & `/logout`. | **Fixed** — added A8/BC8 same-origin guard (reject foreign `Origin`/`Referer` with 403, JSON-only bodies) + `test_csrf.py`. |
| 2 | MEDIUM | Security/Coverage | A7/BC2 require "no secret in logs" but only response-body + committed files were tested. | **Fixed** — added BC9 and `test_auth.py::test_no_secret_in_logs` (caplog). |
| 3 | MEDIUM | Coverage/Failure | Rate-limit test covered 429 only, not anti-lockout; process-level limiter risked cross-test flakiness. | **Fixed** — EC2 now specifies failed-attempt counting, anti-lockout, and per-app-instance in-memory state; added `test_successful_logins_not_throttled` + `test_correct_password_succeeds_under_threshold`. |
| 4 | LOW | Integrity | Ownership tested via `float()`±1e-9, so a lossy `REAL` column would pass despite D5. | **Fixed** — D5/BC7 now require integer per-mille storage; added `test_seed.py::test_ownership_stored_exactly`. |
| 5 | LOW | Coverage | "`/api/*` never shadowed" tested only a real route; an unknown `/api/...` swallowed by the SPA catch-all was untested. | **Fixed** — added `test_static.py::test_unknown_api_route_not_shadowed`. |
| 6 | LOW | Failure | Health DB probe has no timeout; a locked SQLite file could hang `/api/health`. | **Proceeded** — noted as a follow-up in EC4 (local single-file SQLite makes this low-risk this slice). |

No findings were acknowledged as standing risk (Finding 6 is a noted follow-up, not an accepted vulnerability), so no rows were added to constitution.md's Acknowledged-risks table.
