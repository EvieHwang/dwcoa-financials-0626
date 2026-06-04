# Build deviations — foundation-001

No spec requirement was changed and no test assertion was corrected. The test
suite passes as written (47 backend, 5 frontend). The notes below record
implementation choices that diverge from the *implicit* default a reader of the
design might assume, kept here as an honest record for later slices.

## 1. Frontend test resolution for out-of-package test files
**Design context:** the design names the frontend contracts (`@/App`, auth via
`GET /api/auth/me`, `data-testid="admin-only"`) but not the test wiring. The
Foundation frontend tests live under `features/foundation-001/tests/frontend/`,
*outside* the `frontend/` package, and the run command is fixed to
`cd frontend && pnpm test`.

**What was done:** `frontend/vite.config.ts` adds, beyond the conventional
`@ -> ./src` alias:
- `server.fs.allow` extended to the repo parent so Vite may load test files
  above the package root, and
- regex aliases mapping the bare specifiers those external test files import
  directly (`react`, `react-dom`, `@testing-library/*`, `vitest`) to
  `frontend/node_modules`, because Node's upward `node_modules` resolution does
  not reach `frontend/node_modules` from the `features/` tree.

**Why:** without this, Vite cannot resolve imports for test modules that sit
outside the package. This is a build-environment accommodation, not a change to
any application contract. When later slices add their own frontend tests in the
same location, this config already covers them.

## 2. Money/ownership column types
The migration stores `budgets.annual_amount` and transaction money columns as
`INTEGER` (cents) and `units.ownership_pct` as `INTEGER` (per-mille), per
D5/BC7. The reference app used `REAL`/`DECIMAL`; the spec explicitly supersedes
that to guarantee exact storage, so this follows the spec rather than the
reference precedent.
