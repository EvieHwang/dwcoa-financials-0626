# Build deviations — visual-redesign-009

This file is the feedback channel back to spec-writing. It records (1) the
sanctioned per-test navigation steps the spec's Preservation contract told
`/build` to add to the prior suites, and (2) where implementation reality
diverged from the design. **No behavioral assertion in any prior suite was
weakened or removed**, and `spec.md` was not edited.

---

## 1. Sanctioned navigation steps added to prior suites

The spec's **Preservation contract** states: because screens now sit behind
sidebar navigation, "`/build` adds a single navigation step to each prior-suite
test that targets a non-default screen — the behavioral assertions are otherwise
unchanged — and logs each such edit here." Each edit adds an async helper that
clicks the relevant item inside the `navigation` landmark, then leaves every
existing assertion verbatim.

| Suite / file | Tests touched | Nav step added |
|---|---|---|
| `ingestion-003/TransactionsTable.test.tsx` | all 4 | `gotoTransactions()` (click nav `/transactions/i`) after each `render` |
| `ingestion-003/Upload.test.tsx` | all 3 | admin tests → nav `/import\|upload/i`; viewer-absence test → nav `/transactions/i` (its settle-signal is a transaction row) |
| `rules-categorization-004/ReviewQueue.test.tsx` | all 4 | admin tests → nav `/review/i`; viewer-absence test → nav `/transactions/i` |
| `rules-categorization-004/RulesEditor.test.tsx` | all 4 | admin tests → nav `/rules/i`; viewer-absence test → nav `/transactions/i` |
| `budgets-005/BudgetEditor.test.tsx` | all 6 | `gotoBudget()` (nav `/budget/i`) after each `render` |
| `dues-by-unit-007/DuesByUnit.test.tsx` | all 4 | `gotoDues()` (nav `/dues/i`). `shows_not_tracked_note` previously waited on the Overview total-cash string as a settle signal; since the Dues screen is now separate, that wait was repointed to the not-tracked note (same behavioral assertion, on the screen under test). |
| `my-account-008/MyAccount.test.tsx` | all 6 | `gotoAccount()` (nav `/my account/i`) after each `render` (the remount test gets one after each of its two renders). |

`dashboard-006/Dashboard.test.tsx` and `foundation-001/*` were **not** edited —
Overview is the default screen and units/admin-marker live there per the contract.

These edits are the expected consequence of the all-on-one-page → nav-switched
restructure the spec mandated; they are not spec errors.

---

## 2. Design-vs-reality divergences

The design is a recommendation; where the design contradicted a load-bearing
behavioral invariant in the prior suites, the behavioral requirement won (per
`/build`'s "Design is a recommendation" rule). The recurring root cause is a
**spec-authoring lesson** worth surfacing: the `@scaffolding` suites assert money
strings with `getByText`/`getByLabelText`, which throw on *any* duplicate within
the queried scope. The spec's contract named this generally ("Unique-or-scoped
text") but it bit in several specific spots the design would otherwise have
duplicated. Each fix below preserves the numbers and the asserted behavior; it
only avoids **restating an already-asserted string elsewhere in the same region.**

| # | Design said | What was built | Why |
|---|---|---|---|
| D1 | Account balances table has a "total row" (= total cash). | Total cash shown once, in the KPI `StatCard`; no numeric total row in the balances table. | `dashboard-006 viewer_sees_same_readonly_dashboard` does `getByText(/$9,000.00/)` (unique). A KPI + a total row = two matches. |
| D2 | Reserve KPI = reserve "current vs beginning". | Reserve KPI shows `beginning_balance`; the reserve *net* ($2,600.00) appears only in the reserve detail block. | `dashboard-006 renders_reserve_and_chart` asserts `getByText(/$2,600.00/)` (unique). |
| D3 | Budget-vs-actual card subtitle "`<actual>` of `<annual>` annual · N%". | Subtitle is "of `<annual>` annual budget" — the actual is shown once, in the category row. | `dashboard-006` asserts `getByText(/$500.00/)` (unique); the subtitle restated the expense actual. |
| D4 | Dues page three stats: Expected / **Collected** / Outstanding, plus a totals row. | Stats are Expected / Outstanding / **Collection-rate %**; no totals row. | `totals.paid` equals unit 101's `paid` ($2,000.00) in the fixtures; `dues-by-unit-007 renders_dues_rows` asserts `getByText(/$2,000.00/)` (unique). A "Collected $" stat or a totals row would duplicate it. |
| D5 | My account "This year" card includes a **Paid YTD** line. | Paid YTD line omitted (this matches the *prior* implementation, which also omitted it). | `paid_ytd` ($10,000.00) equals the recent-payment amount; `my-account-008 selecting_unit_fetches_and_renders` asserts `getByText(/$10,000.00/)` (unique). |
| D6 | — | My account screen renders `null` until `/api/reference` units load. | Preserves the prior embedded behavior so the unit `<option>`s exist the moment the region first appears (the suite uses sync `getByRole("option")` right after the region resolves). |
| D7 | Import section / "Import CSV" view. | Section `aria-label="Import transactions"` (not "Import CSV"); file input wrapped in its `<label>` with `aria-label="Upload transactions CSV"`. | `getByLabelText` matches *any* element with an `aria-label`; an "Import CSV" region label double-matched `/csv\|file\|upload/i` alongside the real upload input. |
| D8 | Rules table has an **Active toggle** (custom switch). | Omitted (inactive rows simply dimmed). | Spec out-of-scope: the API has no activate/deactivate endpoint. |
| D9 | "As of" date control lives in the topbar; "role segmented control" in the topbar. | "As of" is a single app-level control in the shell topbar (read by Overview/Dues/My-account); the role control is dropped entirely. | Per US-2/US-3 and the Shared-As-of design; role is read only from `/api/auth/me`. |

### Recorded constitution-level deviations (already in the decision log)
- **Custom Tailwind + CSS-variable primitives instead of shadcn/ui** — bespoke
  fintech look + custom charts (meters, ring, bar/stack). Icons via `lucide-react`
  and fonts via `@fontsource` (self-hosted, not the Google CDN), per the design.
- **Print-clean dashboard + matching PDF export** — retired at the project level;
  this feature neither adds nor restores it.

### Theme indicator
Per spec § Tokens, the document root carries **both** the `.dark` class (what
`tailwind.config.js` `darkMode:"class"` keys off) and a `data-theme` attribute (the
token CSS alias), kept in sync by `useTheme`, so dark styling actually activates.

---

## Spec-authoring lesson (for `/retro`)
A `@scaffolding` suite that asserts money with unscoped/region-scoped
`getByText`/`getByLabelText` makes **"do not restate an asserted figure elsewhere
in that scope"** a hard constraint on the redesign. The spec's contract flagged
this in the abstract ("Unique-or-scoped text") but a future spec could save
`/build` real iteration by enumerating, per screen, which money strings the suite
pins as unique — KPIs, card subtitles, and totals rows are the usual offenders
because they legitimately re-display a figure the detail rows already show.
