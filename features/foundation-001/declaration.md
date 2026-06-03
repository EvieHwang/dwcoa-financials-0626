# Feature Declaration: Foundation

**Feature:** foundation-001
**Slice:** 1 of the DWCOA Financials rebuild (walking skeleton)

## What
The thinnest end-to-end slice that proves the whole stack stands up: a single Fly app where a user logs in with a shared password (admin or view-only), the React frontend loads served by the FastAPI backend, an authenticated API endpoint returns data read from a seeded SQLite database on the Fly volume, and the entire thing ships via GitHub Actions with a passing post-deploy health check.

Foundation also establishes the **full database schema** (all tables for the eventual app, via versioned migrations) and seeds the **stable reference data**: units + ownership %, accounts mapping, categories, base categorize-rules, and the 2025 budget. Later slices add behavior against these tables, not new tables.

## Why
Every later slice (ingestion, rules, budgets, dashboard, dues, My Account) hangs on these seams — auth, persistence, the API layer, the single-app deploy. Proving them end-to-end *and deployed* first means subsequent features add behavior to a known-good skeleton instead of debugging infrastructure and features at the same time. Establishing the full schema now (the data model is already known from the reference app) keeps migrations from churning slice to slice.

## Success
- A view-only user reaches the deployed URL, logs in with the board password, sees the dashboard shell with real seeded data, and is denied any admin-only action.
- An admin user logs in with the admin password and can reach an admin-only endpoint that the view-only session cannot.
- The dashboard shell renders data fetched through the authenticated API from the seeded SQLite DB on the Fly volume.
- A push to `main` builds and deploys the single Fly app; the workflow fails the job unless a post-deploy health check returns healthy within a bounded retry window.
- The role is always determined server-side from the session token, never from client-supplied input.

## Shape touched
- **Auth & session** — shared-password login, server-side verification, admin vs. view-only role, signed-token session.
- **Persistence & deploy substrate** — SQLite on a Fly volume, full schema via startup migrations, reproducible reference seed, fly.io deploy via GitHub Actions with post-deploy health check.
- **API layer** — FastAPI app, health endpoint, an authenticated data endpoint, role-gated admin endpoint, and serving the built frontend as static assets.
- **Dashboard & reporting UI** — *shell only*: login screen + an authenticated dashboard page that renders seeded data. No charts, summaries, or reports.

## Out of scope (this slice)
- The legacy production-DB importer (now its own later slice; this slice only ensures the schema fits the legacy data shape).
- CSV ingestion and dedup.
- Rules categorization engine, review queue, rule-suggestion.
- Budget management UI and YTD proration logic.
- Dashboard charts, income/expense summaries, dues tables, PDF/CSV export.
- Dues-by-unit calculations and the My Account statement.
- Database backup automation (acknowledged as a follow-up; the volume + schema land here, scheduled backup does not).
