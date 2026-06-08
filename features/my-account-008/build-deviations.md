# Build deviations — My Account (008)

No `spec.md` requirement was changed, and no test was corrected. The full suite
(backend pytest across all feature dirs + frontend Vitest + `pnpm build`
type-check) passes as written. One design-level divergence is recorded below.

## D1 — The "My Account" section is gated on the dashboard payload having loaded

**Design contradicted:** Part 2 places the section inside the `Dashboard`
component and describes it rendering a unit selector + prompt on mount
(independent of the dashboard's own `/api/dashboard` data). The implementation
renders `<MyAccount>` only inside the `Dashboard`'s `{data && …}` block — i.e.
it appears once the dashboard payload has loaded, not before.

**What was done instead / why:** The frozen frontend suites for **foundation-001**
(`DashboardShell.test.tsx`) and **ingestion-003** (`TransactionsTable.test.tsx`)
mount the full `<App>` but stub **only** `/api/auth/me`, `/api/reference`, and
(for ingestion) `/api/transactions`. They assert `getByText("101")` (a single Units
cell) and `getByLabelText(/account/i)` (a single account *filter* control) — both
single-match queries. An always-rendered My Account section breaks both:
- its unit `<select>` adds a second `"101"` (an `<option>`), and
- its `aria-label="My Account"` region is also returned by `getByLabelText(/account/i)`
  (dom-testing-library's label query matches any element's `aria-label`, and any
  accessible name matching `/my account/i` necessarily contains `account`).

Those suites only pass today because the *existing* dashboard sub-sections
(`Account balances`, etc.) are themselves gated on `{data && …}` and so don't
render without a `/api/dashboard` stub. Gating My Account the same way restores
that invariant. My Account's own suite stubs `/api/dashboard`, so the section
renders there and all six behaviors hold. The section still uses its own
`/api/account` fetch for content — only its *visibility* is tied to the dashboard
load.

**Lesson for the next spec author:** When a feature adds a new always-visible
region or a control whose accessible name overlaps an existing one (here,
`/account/i`), it can break *earlier features'* frozen frontend tests that use
single-match `getByText` / `getByLabelText` against the full `<App>` with a
minimal stub set. The cross-feature collision surface is real: prefer scoping
shared-page additions behind the same load gate the surrounding sections already
use, and when naming a region, check it doesn't substring-collide with a sibling
feature's label queries.
