# Constitution

## Standards
Interface:        Apple Human Interface Guidelines
                  developer.apple.com/design/human-interface-guidelines
Accessibility:    WCAG 2.1 AA
                  w3.org/WAI/WCAG21/quickref
Security:         OWASP Top 10
                  owasp.org/www-project-top-ten
API contracts:    OpenAPI Specification
                  spec.openapis.org

Extended (apply when relevant):
API design:       Microsoft REST API Guidelines
AI integration:   OWASP Top 10 for LLMs
Security depth:   OWASP ASVS

Agents follow these without deviation unless the declaration 
explicitly requires otherwise. Deviation must be surfaced as 
a decision, not made silently.

## Architectural principles
- The spec is the contract. Its requirements are never modified during implementation; if a requirement is wrong, `/build` stops and kicks back to `/spec` rather than patching it mid-build.
- No Docker for local development unless the project has multi-service dependencies that genuinely require it.
- All deployments run through GitHub Actions, triggered by push to `main`.
- Prefer self-hosted runners (Eviebot) over SSH-based deploy steps.

### App-specific
- **Single deployable.** One Fly app serves both tiers: the FastAPI backend serves the built React frontend as static assets. No separate frontend origin, no CORS, no second service to operate.
- **SQLite is the database.** Data lives in a single SQLite file on a mounted Fly volume — not in object storage, not in a managed DB. Justified by small data volumes (hundreds of rows/year) and a single writer (the treasurer). A managed/relational DB would be a deviation requiring a recorded decision.
- **Single-writer assumption.** Only the treasurer writes; concurrent editing is not a design concern. Reads (board, homeowners) are unrestricted.
- **Rules-only categorization.** Transaction categorization is deterministic pattern-matching plus a manual review queue — no LLM calls anywhere in the system. "Learning" happens by suggesting a reusable rule when the treasurer fixes a reviewed transaction.
- **Idempotent ingestion.** The treasurer always uploads the full transaction history; the server dedups (post date + amount + description) so re-uploading is safe and never duplicates rows or clobbers existing categories.
- **The dashboard is the report.** The primary dashboard view must remain print-clean (fits on a page via browser print) and have a matching PDF export. This is a product constraint, not a nice-to-have — reporting is a first-class output, never an afterthought bolted onto a screen-only UI.
- **Data portability.** The treasurer role rotates; all data must be exportable as CSV with no proprietary lock-in, and the schema must be documented.

[Add further app-specific principles below as they are decided.]

## Patterns in use
- **Frontend stack:** React + TypeScript + Tailwind + shadcn/ui. Vanilla JS is acceptable only for stateless single-page tools.
- **UI aesthetic:** information-dense, 14px base, tight line heights, dark mode as a first-class surface.
- **UX checklist:** apply Nielsen's 10 heuristics as a general sanity-check on any interface; Apple HIG (see Standards) is the authoritative reference for platform decisions.
- **Python service layout:** `pyproject.toml` (not `requirements.txt`) for dependency and project metadata.

### App-specific
- **Backend:** Python + FastAPI, `pyproject.toml` service layout, served by `uvicorn`. Business logic (categorization, budget proration, dues math) lives in plain testable modules, not in route handlers.
- **Frontend:** React + TypeScript + Vite + Tailwind + shadcn/ui (the constitution default). Built static assets are served by the backend in production.
- **Auth:** two shared passwords (admin / view-only), verified **server-side** against hashed values; session carried as a signed token. Never trust a client-asserted role. Homeowners self-select their unit (persisted in `localStorage`) — unit selection is a convenience, not an authorization boundary.
- **Money:** represent monetary amounts as integer cents (or `Decimal`) end to end — never binary floats. Financial calculations are the highest-value test surface.
- **Budget timing:** YTD budget is prorated by each line's timing pattern (monthly / quarterly / annual), not naive months÷12. This logic is centralized and unit-tested against worked examples.
- **Migrations + seed:** schema changes are versioned migrations applied on startup; seed data (units, ownership %, categories, base rules) is reproducible. A documented one-time importer brings the legacy production SQLite DB into the new schema.

[Add further app-specific patterns below as they are established.]

## Quality gates
- All tests pass — and CI runs the same build the deploy runs. If the test runner doesn't type-check/compile (Vitest, esbuild, isolatedModules), CI also runs the production build (`tsc` / `pnpm build` / `mypy` / `go build`).
- `README.md` and `CLAUDE.md` exist and are current.
- `.env.example` lists every key the deploy workflow injects — no drift between the committed example and the actual required secrets.

### App-specific
- **Financial calculations are tested against worked examples.** Budget YTD proration (each timing pattern), dues expected/paid/outstanding, per-unit carryover, and transfers-excluded income/expense totals each have tests with hand-verified numbers. A weak test here is worse than none.
- **Ingestion dedup is tested for idempotency.** Re-uploading the same (or overlapping) history produces no duplicate rows and preserves existing categories.
- **Auth is enforced server-side.** Tests confirm view-only sessions cannot reach admin endpoints and that role is never taken from client input.
- **The dashboard prints to one page** and the PDF export matches it — verified, not assumed.
- **Post-deploy health check passes.** A deploy is successful only when the live Fly app returns healthy from a health endpoint within a bounded retry window (a `flyctl deploy` zero exit is not sufficient).

[Add further app-specific gates below as they are established.]

## Testing
Framework: [populated by /spec on first use]
Run: `[command — populated by /spec on first use]`

## Out of scope
See `declaration.md` § Out of scope for the canonical list. In brief, this codebase does **not**: use AI/LLM categorization; support per-user or per-unit logins; integrate with banks (data enters only via manual CSV upload); collect online payments; send email/notifications; integrate with accounting software or implement double-entry/general-ledger accounting; support multiple associations/tenants; or provide multi-year trend analytics beyond per-year budget-vs-actual and dues carryover.

## Decision log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-03 | Rebuild the existing AWS-serverless app fresh, spec-first, rather than port it | Evolved dev process + a simpler deploy target justify a clean rebuild; old app kept in `reference/` as reference only |
| 2026-06-03 | Deploy to fly.io as a single always-on app (not AWS Lambda/S3/CloudFront) | Persistent container removes the SQLite-in-S3 sync complexity and cold starts; simpler and cheaper to maintain |
| 2026-06-03 | SQLite on a mounted Fly volume (not Postgres or object storage) | Hundreds of rows/year, single writer; managed/relational DB would be over-engineering |
| 2026-06-03 | One Fly app serves both tiers (backend serves built frontend) | Single deployable, no CORS / second origin to operate |
| 2026-06-03 | Rules-only categorization, no LLM | Owner chose determinism + a review queue over AI cost/dependency; rule-suggestion-on-fix recovers the "learning" loop |
| 2026-06-03 | Full-history CSV upload with server-side dedup | Real-world treasurer workflow; idempotent re-uploads are safer than incremental append |
| 2026-06-03 | Keep two shared passwords (admin / view-only), hardened server-side | Trust-based 9-unit HOA; per-user accounts are unjustified overhead, but verification moves server-side to close OWASP gaps |
| 2026-06-03 | Migrate the live production DB (not fresh seed) | Existing budgets, past-dues, rules, and transactions must carry over; actual S3 pull runs from a local session with AWS access |

## Acknowledged risks
*Cross-feature accumulation surface. Each adversarial-gate finding the owner marks `acknowledged` gets one row here so the project never silently forgets that it knowingly took on risk. Severity is the unmitigated severity — an acknowledged HIGH stays HIGH. Populated by `/spec` when a finding is acknowledged.*

| Feature | Finding | Severity | Risk | Rationale | Mitigation |
|---------|---------|----------|------|-----------|------------|
[populated by the adversarial gate in /spec]
