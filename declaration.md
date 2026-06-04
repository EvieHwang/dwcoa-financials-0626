# Declaration

## What
DWCOA Financials is a web dashboard for the Denny Way Condo Owners Association that turns raw bank-export data into an at-a-glance picture of the association's finances — categorized transactions, budget-vs-actual tracking with proper timing, dues owed and paid per unit, and clean, printable reports for board meetings. It is a focused rebuild of an existing tool, deployed to a single always-on host.

## Why
The association's treasurer is a volunteer who otherwise tracks everything by hand in spreadsheets — reconciling bank exports, categorizing each transaction, prorating budgets, and chasing per-unit dues. That work is slow, error-prone, and hard to hand off when the treasurer role rotates. DWCOA Financials makes the recurring bookkeeping fast and repeatable, gives the board and homeowners a trustworthy shared view of the finances, and keeps the data portable so the next treasurer can take over with minimal training. The rebuild also moves the app off a complex serverless setup onto a simpler, cheaper always-on host that's easier to maintain.

## For whom
- **The treasurer (admin)** — the primary user. Needs to import bank data quickly, categorize transactions with minimal manual effort, manage budgets and dues, and produce board-ready reports. Needs the workflow to be repeatable month to month and handoff-friendly at year/role transitions.
- **Board members (admin or view-only)** — need a trustworthy current snapshot of the association's finances for meetings, plus printable/PDF reports to share and file.
- **Homeowners (view-only)** — the nine unit owners. Need to see the association's overall financial health and, for their own unit, what they owe, what they've paid, and what to pay to stay current.

## Out of scope
- **No AI categorization.** Categorization is rules-based only (with a manual review queue); no LLM calls.
- **No per-user accounts or per-unit logins.** Access is two shared passwords (admin / view-only); homeowners self-select their unit, not authenticated to it.
- **No automated bank integration.** Data enters only via manual CSV upload of the full transaction history.
- **No online dues payment.** The app tracks payments; it does not collect them.
- **No email, notifications, or reminders.**
- **No accounting-software integration** (QuickBooks, etc.) and no general-ledger / double-entry accounting.
- **No multi-association / multi-tenant support** — it serves this one 9-unit HOA.
- **No multi-year trend analytics** beyond per-year budget-vs-actual and dues carryover.

## Platform
Web — responsive single-page app for desktop and mobile browsers, served from a single fly.io host. Not an Apple platform; the constitution's general UX heuristics (Nielsen) and WCAG 2.1 AA apply.

## Shape (revisable)
- **Auth & session** — shared-password login, server-side verification, admin vs. view-only role, session/token handling.
- **Persistence & deploy substrate** — SQLite on a Fly volume, schema migrations + seed data, backup, and the one-time import of the legacy production DB; fly.io deploy via GitHub Actions.
- **API layer** — FastAPI endpoints that connect the frontend to the domain logic.
- **Transaction ingestion & store** — full-history CSV upload, dedup, account-number mapping, the transactions table.
- **Categorization engine** — rules matching, the review queue, and auto-suggesting rules from manual fixes.
- **Budget, dues & units model** — categories, per-year budgets with timing patterns, unit ownership, YTD proration, dues and per-unit carryover calculations.
- **Dashboard & reporting UI** — React dashboard (balances, summaries, charts), print-clean layout, and PDF/CSV export.

## Roadmap (revisable)
1. **Foundation** — app skeleton, shared-password auth, full schema + reference seed, fly.io deploy. Touches: Auth & session, Persistence & deploy substrate, API layer, Dashboard & reporting UI (shell).
2. **Legacy data migration** — one-time importer mapping the old production SQLite DB (legacy SQLite-in-S3) into the new schema; actual S3 pull/import runs from a local session with AWS access. Touches: Persistence & deploy substrate, Transaction ingestion & store, Budget, dues & units model.
3. **Ingestion** — full-history CSV upload with dedup, account mapping, transaction table + CSV export. Touches: Transaction ingestion & store, API layer, Dashboard & reporting UI.
4. **Rules categorization** — rules engine, review queue, auto-suggest-rule-on-fix, rules editor. Touches: Categorization engine, Transaction ingestion & store, API layer, Dashboard & reporting UI.
5. **Budgets** — per-year/category amounts, timing patterns, copy-year, YTD proration. Touches: Budget, dues & units model, API layer, Dashboard & reporting UI.
6. **Dashboard & reporting** — balances, income/expense summaries with remaining, charts, transfers excluded, print-clean layout + PDF. Touches: Dashboard & reporting UI, Budget, dues & units model, API layer.
7. **Dues by unit** — expected vs. paid, unit-centric outstanding balances. Touches: Budget, dues & units model, API layer, Dashboard & reporting UI.
8. **My Account** — per-unit statement, carryover, payment guidance, past-dues. Touches: Budget, dues & units model, Dashboard & reporting UI, API layer.
